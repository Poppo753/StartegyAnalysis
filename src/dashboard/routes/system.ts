/**
 * routes/system.ts — System + config endpoints (U1-03).
 *
 *   GET /api/status → { python, venvOk, diskFreeGb, studyDb, lastRuns }
 *   GET /api/config → { symbols, strategies, engine, flags }
 *
 * Contracts frozen by docs/analysis/18_unified_ui_expanded.md §D3: field names
 * are exactly as written there. Verification fixes honoured here:
 * strategies = listing of python-backtester/src/strategies/*.py (minus
 * __init__), re-validated server-side on every POST (see routes/runs.ts);
 * engine list exposed for the GPU lock; never reads a .db file (existence
 * only); never uses a shell (execFileSync argv array, no shell).
 */
import * as fs from "fs";
import * as http from "http";
import * as path from "path";
import { execFileSync } from "child_process";
import { URL } from "url";
import {
  ENGINES,
  SEARCH_METHODS,
  VALIDATION_MODES,
  listStrategies,
} from "../lib/validateRun";
import { listStrategyCatalog, StrategyInfo } from "../lib/strategyCatalog";
import { RUN_OPTIONS, RunOptionSpec } from "../lib/runOptions";
import { RunRecord, RunStore, createRunStore } from "../lib/runStore";
import { PythonBinInfo } from "../lib/runSpawn";
import { REPO_ROOT } from "./results";

const DATA_ROOT = path.join(REPO_ROOT, "data");
const BACKTESTER_ROOT = path.join(REPO_ROOT, "python-backtester");
const DASHBOARD_DATA_ROOT = path.join(REPO_ROOT, "dashboard-data");
const LAST_RUNS_LIMIT = 10;

/** One entry of the flag allowlist served by /api/config (D3). */
export interface FlagSpec {
  name: string;
  type: "enum" | "int";
  values?: string[];
  min?: number;
  max?: number;
  default: string | number;
}

export interface RunConfig {
  symbols: string[];
  datasetSymbols: string[];
  strategies: string[];
  strategyCatalog: StrategyInfo[];
  engine: string[];
  flags: FlagSpec[];
  runOptions: RunOptionSpec[];
  /**
   * Additive (not part of the D3 frozen contract): per-symbol data
   * availability for the configured .env date range. The UI uses it to show
   * available timeframes and to explain why a symbol is (not) offered.
   * `symbols` above remains the authoritative "runnable" list.
   */
  symbolAvailability: SymbolAvailability[];
  /** START_DATE..END_DATE read from .env, or null when absent/unparseable. */
  configuredRange: { start: string; end: string } | null;
}

export interface RunSummary {
  id: string;
  symbol: string;
  strategy: string;
  engine: string;
  status: RunRecord["status"];
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
  exitCode?: number;
  progress?: number;
  progressNote?: string;
}

export interface SystemStatus {
  python: string;
  venvOk: boolean;
  diskFreeGb: number;
  studyDb: boolean;
  lastRuns: RunSummary[];
}

export interface SystemDeps {
  store: RunStore;
  dataRoot?: string;
  envPath?: string;
  strategies?: string[];
  /** undefined = resolve at request time; null = "no python available". */
  pythonBin?: PythonBinInfo | null;
}

/**
 * The allowlist served by /api/config. Built from validateRun's exported
 * enums plus the D3-frozen int ranges/defaults (the lib enforces exactly the
 * same ranges inside validateRunInput).
 */
export const RUN_FLAGS: FlagSpec[] = [
  { name: "search", type: "enum", values: SEARCH_METHODS.slice(), default: "grid" },
  { name: "n-trials", type: "int", min: 1, max: 5000, default: 30 },
  { name: "jobs", type: "int", min: 1, max: 8, default: 1 },
  { name: "validation-mode", type: "enum", values: VALIDATION_MODES.slice(), default: "off" },
];

function sendJson(res: http.ServerResponse, code: number, obj: unknown): void {
  res.writeHead(code, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(obj));
}

let sharedStore: RunStore | null = null;

/** Lazy singleton run store (dashboard-data/runs), shared with routes/runs.ts. */
export function sharedRunStore(): RunStore {
  if (!sharedStore) sharedStore = createRunStore(DASHBOARD_DATA_ROOT);
  return sharedStore;
}

/** Drop the cached store (tests). */
export function resetSharedRunStore(): void {
  sharedStore = null;
}

function platformBinRelative(): string {
  return process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python";
}

/**
 * PYTHON_BIN resolution at the route seam: $PYTHON_BIN if set, else the
 * platform path under python-backtester/ (this repo's venv layout, the same
 * one package.json points at). execFileSync with an argv array: no shell.
 */
export function resolvePythonBin(): PythonBinInfo | null {
  const fromEnv = process.env.PYTHON_BIN;
  const candidates = fromEnv
    ? [fromEnv]
    : [path.join(BACKTESTER_ROOT, platformBinRelative())];
  for (const candidate of candidates) {
    const binPath = path.resolve(candidate);
    if (!fs.existsSync(binPath)) continue;
    let version = "unknown";
    try {
      version = execFileSync(binPath, ["--version"], {
        encoding: "utf8",
        timeout: 5000,
      }).trim();
    } catch {
      // Binary exists but did not answer --version: existence is what counts.
    }
    return { path: binPath, version };
  }
  return null;
}

/**
 * Parse a python-backtester/.env file into a plain key→value map.
 * Same source of truth python's load_config() reads, so the UI can only
 * offer symbol/range combinations that are actually runnable.
 * Returns {} when the file is absent (never throws: a missing .env must not
 * break the dashboard, it just degrades the symbol list to "any ohlc_ file").
 */
export function readEnvFile(envPath: string): Record<string, string> {
  const out: Record<string, string> = {};
  if (!fs.existsSync(envPath)) return out;
  let raw: string;
  try {
    raw = fs.readFileSync(envPath, "utf8");
  } catch {
    return out;
  }
  for (const line of raw.split(/\r?\n/)) {
    const t = line.trim();
    if (t === "" || t.startsWith("#")) continue;
    const eq = t.indexOf("=");
    if (eq <= 0) continue;
    const k = t.slice(0, eq).trim();
    let v = t.slice(eq + 1).trim();
    if (
      (v.startsWith('"') && v.endsWith('"')) ||
      (v.startsWith("'") && v.endsWith("'"))
    ) {
      v = v.slice(1, -1);
    }
    if (k) out[k] = v;
  }
  return out;
}

/** Timeframe label of an ohlc csv filename, or null if it is not one. */
export function ohlcTimeframe(fileName: string): string | null {
  const m = /^ohlc_([^_]+)_(.+)\.csv$/.exec(fileName);
  return m ? m[1] : null;
}

/** date range encoded in `ohlc_{tf}_{start}_{end}.csv`, or null. */
export function ohlcRange(fileName: string): { start: string; end: string } | null {
  const m = /^ohlc_[^_]+_(.+)\.csv$/.exec(fileName);
  if (!m) return null;
  const parts = m[1].split("_");
  if (parts.length < 2) return null;
  return { start: parts[0], end: parts.slice(1).join("_") };
}

/** Every timeframe present for a symbol inside a dir (direct or one nested level). */
function listOhlcFiles(symbolDir: string): string[] {
  const found: string[] = [];
  const scan = (dir: string, depth: number): void => {
    if (depth > 1) return;
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const e of entries) {
      if (e.isFile() && ohlcTimeframe(e.name) !== null) found.push(e.name);
      else if (e.isDirectory()) scan(path.join(dir, e.name), depth + 1);
    }
  };
  scan(symbolDir, 0);
  return found;
}

/**
 * Runnability of one symbol, given the configured date range.
 * `hasConfiguredRange: false` means .env carried no range (degraded mode:
 * the symbol is listed if it has any ohlc_ file, matching python's behaviour
 * of failing loudly at load time rather than at UI level).
 */
export interface SymbolAvailability {
  symbol: string;
  hasConfiguredRange: boolean;
  availableTimeframes: string[];
  hasDataForRange: boolean;
  datasets: { file: string; timeframe: string; start: string; end: string }[];
}

/**
 * Symbols with their data availability (D3 + smoke finding 2026-09-26).
 * The UI must only offer what can actually run: a symbol whose ohlc files do
 * not cover the configured START_DATE..END_DATE fails inside python with
 * "File non trovato", which is a worse experience than not listing it.
 */
export function listSymbolAvailability(
  dataRoot: string = DATA_ROOT,
  envPath: string = path.join(BACKTESTER_ROOT, ".env"),
): SymbolAvailability[] {
  if (!fs.existsSync(dataRoot)) return [];
  const env = readEnvFile(envPath);
  const start = env.START_DATE ?? "";
  const end = env.END_DATE ?? "";
  const hasConfiguredRange = /^\d{4}-\d{2}-\d{2}$/.test(start) && /^\d{4}-\d{2}-\d{2}$/.test(end);
  const out: SymbolAvailability[] = [];
  for (const entry of fs.readdirSync(dataRoot, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const files = listOhlcFiles(path.join(dataRoot, entry.name));
    if (files.length === 0) continue;
    const datasets: SymbolAvailability["datasets"] = [];
    const ohlcDir = path.join(dataRoot, entry.name, "ohlc");
    try {
      for (const file of fs.readdirSync(ohlcDir)) {
        const range = ohlcRange(file);
        const timeframe = ohlcTimeframe(file);
        if (range && timeframe && /^\d{4}-\d{2}-\d{2}$/.test(range.start) &&
            /^\d{4}-\d{2}-\d{2}$/.test(range.end) &&
            fs.statSync(path.join(ohlcDir, file)).isFile()) {
          datasets.push({ file, timeframe, start: range.start, end: range.end });
        }
      }
    } catch { /* Flat legacy layout has no runnable dataset directory. */ }
    const timeframes = Array.from(
      new Set(files.map((f) => ohlcTimeframe(f) as string).filter(Boolean)),
    ).sort();
    const hasDataForRange = hasConfiguredRange
      ? files.some((f) => {
          const r = ohlcRange(f);
          return r !== null && r.start === start && r.end === end;
        })
      : true;
    out.push({
      symbol: entry.name,
      hasConfiguredRange,
      availableTimeframes: timeframes,
      hasDataForRange,
      datasets,
    });
  }
  return out.sort((a, b) => a.symbol.localeCompare(b.symbol));
}

/**
 * Subdirs of data/ that can actually be backtested with the configured range.
 * Real layout is data/{SYMBOL}/ohlc/ohlc_{tf}_{start}_{end}.csv, so the lookup
 * goes one level deep. When .env has no parseable range, falls back to "has
 * any ohlc_ file" (degraded mode, same as python failing at load time).
 */
export function listDataSymbols(
  dataRoot: string = DATA_ROOT,
  envPath: string = path.join(BACKTESTER_ROOT, ".env"),
): string[] {
  return listSymbolAvailability(dataRoot, envPath)
    .filter((s) => s.hasDataForRange)
    .map((s) => s.symbol);
}

/** Free space in GiB, one decimal. 0 when the platform/fs cannot report it. */
export function diskFreeGb(dir: string = REPO_ROOT): number {
  try {
    const st = fs.statfsSync(dir);
    return Math.round(((st.bavail * st.bsize) / 1024 ** 3) * 10) / 10;
  } catch {
    return 0;
  }
}

/** True when an Optuna study *.db exists. Never opens it (no SQLite dep). */
export function studyDbExists(): boolean {
  for (const dir of [BACKTESTER_ROOT, REPO_ROOT]) {
    try {
      if (fs.readdirSync(dir).some((f) => f.toLowerCase().endsWith(".db"))) return true;
    } catch {
      // Missing/unreadable dir: keep scanning, never crash.
    }
  }
  return false;
}

/** Strip filesystem-only fields, keep the D3 summary shape. */
export function runSummary(record: RunRecord): RunSummary {
  return {
    id: record.id,
    symbol: record.symbol,
    strategy: record.strategy,
    engine: record.engine,
    status: record.status,
    createdAt: record.createdAt,
    startedAt: record.startedAt,
    finishedAt: record.finishedAt,
    exitCode: record.exitCode,
    progress: record.progress,
    progressNote: record.progressNote,
  };
}

export function getStatus(deps: SystemDeps): SystemStatus {
  const bin = deps.pythonBin !== undefined ? deps.pythonBin : resolvePythonBin();
  let records: RunRecord[] = [];
  try {
    records = deps.store.list();
  } catch {
    records = [];
  }
  return {
    python: bin ? bin.version : "not found",
    venvOk: !!bin && fs.existsSync(bin.path),
    diskFreeGb: diskFreeGb(),
    studyDb: studyDbExists(),
    lastRuns: records.slice(0, LAST_RUNS_LIMIT).map(runSummary),
  };
}

export function getRunConfig(deps: SystemDeps): RunConfig {
  const envPath = deps.envPath ?? path.join(BACKTESTER_ROOT, ".env");
  const availability = listSymbolAvailability(deps.dataRoot ?? DATA_ROOT, envPath);
  const env = readEnvFile(envPath);
  const start = env.START_DATE ?? "";
  const end = env.END_DATE ?? "";
  const configuredRange =
    /^\d{4}-\d{2}-\d{2}$/.test(start) && /^\d{4}-\d{2}-\d{2}$/.test(end)
      ? { start, end }
      : null;
  return {
    symbols: availability.filter((s) => s.hasDataForRange).map((s) => s.symbol),
    datasetSymbols: availability.filter((s) => s.datasets.length > 0).map((s) => s.symbol),
    strategies: deps.strategies ?? listStrategies(),
    strategyCatalog: listStrategyCatalog(),
    engine: ENGINES.slice(),
    flags: RUN_FLAGS.map((f) => ({ ...f, values: f.values ? f.values.slice() : undefined })),
    runOptions: RUN_OPTIONS.map((option) => ({ ...option, values: option.values?.slice(), current: env[option.key] ?? "" })),
    symbolAvailability: availability,
    configuredRange,
  };
}

/**
 * Handle system routes. Returns true when the request was handled
 * (same contract as handleResultsRoutes).
 */
export function handleSystemRoutes(
  req: http.IncomingMessage,
  res: http.ServerResponse,
  url: URL,
  deps?: SystemDeps,
): boolean {
  if (req.method !== "GET" && req.method !== "HEAD") return false;
  const d: SystemDeps = deps ?? { store: sharedRunStore() };

  if (url.pathname === "/api/status") {
    sendJson(res, 200, getStatus(d));
    return true;
  }

  if (url.pathname === "/api/config") {
    sendJson(res, 200, getRunConfig(d));
    return true;
  }

  return false;
}

export { DATA_ROOT, BACKTESTER_ROOT, DASHBOARD_DATA_ROOT, LAST_RUNS_LIMIT };
