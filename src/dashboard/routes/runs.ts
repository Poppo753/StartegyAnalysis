/**
 * routes/runs.ts — Runs CRUD + log + cancel + reconcile (U1-03).
 *
 *   POST   /api/runs                 → 201 { id, status: "queued" } | 400 { error }
 *   GET    /api/runs                 → [ summary... ] (newest first)
 *   GET    /api/runs/:id             → summary + last N log lines
 *   GET    /api/runs/:id/log?fromLine=n → { totalLines, lines, eof, rotated }
 *   POST   /api/runs/:id/cancel      → { status: "cancelled" }
 *   POST   /api/runs/:id/reconcile   → { status } (only from "unknown")
 *
 * Contracts frozen by docs/analysis/18_unified_ui_expanded.md §D3. Log
 * offsets are line-based (never bytes) so rotation cannot corrupt a poll.
 * Nothing here ever builds a shell string: the argv array comes from
 * lib/runSpawn and the allowlist from lib/validateRun.
 */
import * as fs from "fs";
import * as http from "http";
import { URL } from "url";
import { RunRecord, RunStore, createRunStore } from "../lib/runStore";
import { PythonBinInfo, SpawnConfig, SpawnResult, createRunSpawner } from "../lib/runSpawn";
import { validateRunInput } from "../lib/validateRun";
import {
  BACKTESTER_ROOT,
  DASHBOARD_DATA_ROOT,
  DATA_ROOT,
  RunSummary,
  getRunConfig,
  resolvePythonBin,
  runSummary,
} from "./system";

/** Minimal surface of lib/runSpawn used here (fakeable in tests). */
export interface RunSpawnerLike {
  spawn(config: SpawnConfig, pythonBin?: string): Promise<SpawnResult>;
  kill(runId: string): boolean;
}

export interface RunsDeps {
  store: RunStore;
  /** null = python unavailable, POST /api/runs answers 400 with the reason. */
  spawner: RunSpawnerLike | null;
  dataRoot?: string;
  /** .env path used to resolve the configured date range (symbol runnability). */
  envPath?: string;
  strategies?: string[];
  pythonBin?: PythonBinInfo | null;
  /** Lines returned by GET /api/runs/:id (default 200). */
  logTail?: number;
}

const BODY_LIMIT_BYTES = 64 * 1024;
/** Per-response line cap (D10: never ship a whole log in one response). */
const LOG_MAX_LINES = 2000;
const LOG_TAIL_LINES = 200;
const TRIAL_RE = /trial\s+(\d+)\s*\/\s*(\d+)/i;
const PROGRESS_LOG_MAX_BYTES = 1024 * 1024;

function sendJson(res: http.ServerResponse, code: number, obj: unknown): void {
  res.writeHead(code, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(obj));
}

function errorText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

let defaultDeps: RunsDeps | null = null;

/** Lazily built production deps (no work at import time). */
export function getDefaultRunsDeps(): RunsDeps {
  if (!defaultDeps) {
    const store = createRunStore(DASHBOARD_DATA_ROOT);
    const pythonBin = resolvePythonBin();
    let spawner: RunSpawnerLike | null = null;
    if (pythonBin) {
      try {
        spawner = createRunSpawner(store, BACKTESTER_ROOT, undefined, pythonBin);
      } catch {
        spawner = null;
      }
    }
    defaultDeps = { store, spawner, pythonBin };
  }
  return defaultDeps;
}

/** Drop the cached deps (tests). */
export function resetDefaultRunsDeps(): void {
  defaultDeps = null;
}

/** In-flight spawn promises, per store: cancel awaits the real transition. */
const pendingSpawnsByStore = new WeakMap<RunStore, Map<string, Promise<SpawnResult>>>();

function pendingSpawns(store: RunStore): Map<string, Promise<SpawnResult>> {
  let map = pendingSpawnsByStore.get(store);
  if (!map) {
    map = new Map();
    pendingSpawnsByStore.set(store, map);
  }
  return map;
}

async function readJsonBody(req: http.IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    const buf = Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk));
    size += buf.length;
    if (size > BODY_LIMIT_BYTES) throw new Error("request body too large");
    chunks.push(buf);
  }
  const raw = Buffer.concat(chunks).toString("utf8").trim();
  if (!raw) return {};
  const parsed: unknown = JSON.parse(raw);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("body must be a JSON object");
  }
  return parsed as Record<string, unknown>;
}

/** D3 sends camelCase; /api/config flag names are kebab-case. Accept both. */
function normalizeBody(body: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = { ...body };
  const aliases: [string, string][] = [
    ["n-trials", "nTrials"],
    ["validation-mode", "validationMode"],
  ];
  for (const [kebab, camel] of aliases) {
    if (out[camel] === undefined && out[kebab] !== undefined) out[camel] = out[kebab];
  }
  return out;
}

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

/** D3 id shape: 20260926-142310-momentum (unique per second + strategy). */
function makeRunId(strategy: string, store: RunStore): string {
  const now = new Date();
  const stamp =
    `${now.getFullYear()}${pad2(now.getMonth() + 1)}${pad2(now.getDate())}` +
    `-${pad2(now.getHours())}${pad2(now.getMinutes())}${pad2(now.getSeconds())}`;
  const base = `${stamp}-${strategy.replace(/[^\w]/g, "-")}`;
  let id = base;
  for (let n = 2; store.load(id) !== null; n++) id = `${base}-${n}`;
  return id;
}

/**
 * Honest progress: trial counter parsed from the log, always tagged
 * "stima" (D3). Never a fake-precise bar.
 */
function estimateProgress(store: RunStore, record: RunRecord): number | undefined {
  if (record.status !== "queued" && record.status !== "running") return undefined;
  try {
    if (fs.statSync(record.logPath).size > PROGRESS_LOG_MAX_BYTES) return undefined;
    const { lines } = store.readLog(record.id, 1);
    for (let i = lines.length - 1; i >= 0; i--) {
      const m = TRIAL_RE.exec(lines[i]);
      if (!m) continue;
      const total = Number(m[2]);
      return total > 0 ? Math.min(100, Math.round((Number(m[1]) / total) * 100)) : 0;
    }
  } catch {
    return undefined;
  }
  return undefined;
}

function summaryWithProgress(store: RunStore, record: RunRecord): RunSummary {
  const summary = runSummary(record);
  if (summary.progress === undefined) {
    const progress = estimateProgress(store, record);
    if (progress !== undefined) {
      summary.progress = progress;
      summary.progressNote = "stima";
    }
  }
  return summary;
}

/** Log payload in the D3 shape, capped server-side. */
function runLog(store: RunStore, id: string, fromLine: number): {
  totalLines: number;
  lines: string[];
  eof: boolean;
  rotated: boolean;
} {
  const raw = store.readLog(id, fromLine);
  const lines =
    raw.lines.length > LOG_MAX_LINES ? raw.lines.slice(raw.lines.length - LOG_MAX_LINES) : raw.lines;
  return { totalLines: raw.totalLines, lines, eof: raw.eof, rotated: raw.rotated };
}

function loadRun(res: http.ServerResponse, store: RunStore, id: string): RunRecord | null {
  try {
    const record = store.load(id);
    if (!record) {
      sendJson(res, 404, { error: "unknown run" });
      return null;
    }
    return record;
  } catch {
    // Invalid id (traversal / bad chars) counts as not found, never a crash.
    sendJson(res, 404, { error: "unknown run" });
    return null;
  }
}

function enqueueSpawn(record: RunRecord, d: RunsDeps): void {
  const spawner = d.spawner;
  if (!spawner) return;
  const store = d.store;
  const config: SpawnConfig = {
    runId: record.id,
    symbol: record.symbol,
    strategy: record.strategy,
    engine: record.engine,
    search: record.search,
    nTrials: record.nTrials,
    jobs: record.jobs,
    validationMode: record.validationMode,
    repoRoot: BACKTESTER_ROOT,
  };
  // Deferred by one microtask so the 201 still reports the real "queued".
  const spawn = Promise.resolve()
    .then(() => spawner.spawn(config))
    .catch((e: unknown): SpawnResult => {
      // Never leave a run stuck in running/queued after a spawn failure.
      try {
        const current = store.load(record.id);
        if (current && (current.status === "queued" || current.status === "running")) {
          store.transition(record.id, "failed");
        }
      } catch {
        // Already terminal (or an illegal transition): state stays as it is.
      }
      return { success: false, error: errorText(e) };
    });
  const map = pendingSpawns(store);
  map.set(record.id, spawn);
  void spawn.then(() => {
    if (map.get(record.id) === spawn) map.delete(record.id);
  });
}

async function createRun(
  req: http.IncomingMessage,
  res: http.ServerResponse,
  d: RunsDeps,
): Promise<void> {
  let body: Record<string, unknown>;
  try {
    body = normalizeBody(await readJsonBody(req));
  } catch (e) {
    sendJson(res, 400, { error: errorText(e) });
    return;
  }

  const validated = validateRunInput(body, d.dataRoot ?? DATA_ROOT);
  if (!validated.ok || !validated.data) {
    sendJson(res, 400, { error: validated.error ?? "invalid run" });
    return;
  }
  const input = validated.data;

  // Server-side allowlist re-validation against the live /api/config lists.
  const config = getRunConfig({
    store: d.store,
    dataRoot: d.dataRoot,
    envPath: d.envPath,
    strategies: d.strategies,
  });
  if (!config.symbols.includes(input.symbol)) {
    sendJson(res, 400, { error: `unknown symbol: ${input.symbol}` });
    return;
  }
  if (!config.strategies.includes(input.strategy)) {
    sendJson(res, 400, { error: `unknown strategy: ${input.strategy}` });
    return;
  }
  if (!config.engine.includes(input.engine)) {
    sendJson(res, 400, { error: `unknown engine: ${input.engine}` });
    return;
  }
  if (!d.spawner) {
    const why = d.pythonBin === null ? "python not found: no PYTHON_BIN" : "run spawner unavailable";
    sendJson(res, 400, { error: why });
    return;
  }

  let record: RunRecord;
  try {
    record = d.store.create({ ...input, id: makeRunId(input.strategy, d.store), status: "queued" });
  } catch (e) {
    sendJson(res, 500, { error: errorText(e) });
    return;
  }
  sendJson(res, 201, { id: record.id, status: record.status });
  enqueueSpawn(record, d);
}

function listRuns(res: http.ServerResponse, d: RunsDeps): void {
  let records: RunRecord[] = [];
  try {
    records = d.store.list();
  } catch {
    records = [];
  }
  sendJson(res, 200, records.map((r) => summaryWithProgress(d.store, r)));
}

function runDetail(res: http.ServerResponse, d: RunsDeps, id: string): void {
  const record = loadRun(res, d.store, id);
  if (!record) return;
  const tail = Math.max(1, d.logTail ?? LOG_TAIL_LINES);
  const log = runLog(d.store, id, 1);
  const lines = log.lines.slice(Math.max(0, log.lines.length - tail));
  sendJson(res, 200, {
    ...summaryWithProgress(d.store, record),
    log: { totalLines: log.totalLines, lines, eof: log.eof, rotated: log.rotated },
  });
}

function runLogEndpoint(res: http.ServerResponse, d: RunsDeps, id: string, url: URL): void {
  if (!loadRun(res, d.store, id)) return;
  const raw = Number(url.searchParams.get("fromLine"));
  const fromLine = Number.isFinite(raw) && raw >= 0 ? Math.floor(raw) : 0;
  sendJson(res, 200, runLog(d.store, id, fromLine));
}

async function cancelRun(
  req: http.IncomingMessage,
  res: http.ServerResponse,
  d: RunsDeps,
  id: string,
): Promise<void> {
  req.resume();
  const record = loadRun(res, d.store, id);
  if (!record) return;
  if (record.status !== "queued" && record.status !== "running") {
    sendJson(res, 409, { error: `cannot cancel run in status ${record.status}` });
    return;
  }

  if (d.spawner) d.spawner.kill(id);
  // Wait for the spawner's own transition (kill + forced kill after 10s).
  const pending = pendingSpawns(d.store).get(id);
  if (pending) {
    try {
      await pending;
    } catch {
      // Spawn already reported the failure; the state below is authoritative.
    }
  }

  let current = d.store.load(id) ?? record;
  if (current.status === "queued" || current.status === "running") {
    try {
      current = d.store.transition(id, "cancelled");
    } catch {
      // Raced with a terminal transition: report the real status.
    }
  }
  sendJson(res, 200, { status: current.status });
}

async function reconcileRun(
  req: http.IncomingMessage,
  res: http.ServerResponse,
  d: RunsDeps,
  id: string,
): Promise<void> {
  const record = loadRun(res, d.store, id);
  if (!record) return;
  let body: Record<string, unknown>;
  try {
    body = await readJsonBody(req);
  } catch (e) {
    sendJson(res, 400, { error: errorText(e) });
    return;
  }
  const status = String(body.status ?? "").trim();
  if (status !== "done" && status !== "failed" && status !== "cancelled") {
    sendJson(res, 400, { error: "status must be one of done|failed|cancelled" });
    return;
  }
  if (record.status !== "unknown") {
    sendJson(res, 409, {
      error: `reconcile only allowed for unknown status (current: ${record.status})`,
    });
    return;
  }
  try {
    const updated = d.store.reconcileUnknown(id, status);
    sendJson(res, 200, { status: updated.status });
  } catch (e) {
    sendJson(res, 409, { error: errorText(e) });
  }
}

const RUN_ROUTE_RE = /^\/api\/runs\/([^/]+)(?:\/(log|cancel|reconcile))?$/;

/**
 * Handle runs routes. Returns true when the request was handled
 * (same contract as handleResultsRoutes).
 */
export function handleRunsRoutes(
  req: http.IncomingMessage,
  res: http.ServerResponse,
  url: URL,
  deps?: RunsDeps,
): boolean {
  const d = deps ?? getDefaultRunsDeps();
  const method = req.method ?? "GET";

  if (url.pathname === "/api/runs") {
    if (method === "GET" || method === "HEAD") {
      listRuns(res, d);
      return true;
    }
    if (method === "POST") {
      void createRun(req, res, d);
      return true;
    }
    return false;
  }

  const match = RUN_ROUTE_RE.exec(url.pathname);
  if (!match) return false;
  const action = match[2] ?? "";
  let id: string;
  try {
    id = decodeURIComponent(match[1]);
  } catch {
    sendJson(res, 404, { error: "unknown run" });
    return true;
  }

  if (action === "log" && (method === "GET" || method === "HEAD")) {
    runLogEndpoint(res, d, id, url);
    return true;
  }
  if (action === "" && (method === "GET" || method === "HEAD")) {
    runDetail(res, d, id);
    return true;
  }
  if (action === "cancel" && method === "POST") {
    void cancelRun(req, res, d, id);
    return true;
  }
  if (action === "reconcile" && method === "POST") {
    void reconcileRun(req, res, d, id);
    return true;
  }
  return false;
}

export { RUN_ROUTE_RE, LOG_MAX_LINES, LOG_TAIL_LINES, makeRunId };
