/**
 * routes/runs.test.ts — Unit tests for /api/runs CRUD + log + cancel + reconcile
 * (U1-03).
 *
 * Store root and data root are tmp dirs, the spawner is a fake that mimics
 * lib/runSpawn transitions: no process is ever spawned.
 */
import * as fs from "fs";
import * as http from "http";
import * as os from "os";
import * as path from "path";
import { Readable } from "stream";
import { URL } from "url";
import { RunRecord, RunStore, createRunStore } from "../lib/runStore";
import { SpawnConfig, SpawnResult } from "../lib/runSpawn";
import { RunSpawnerLike, RunsDeps, handleRunsRoutes, makeRunId } from "./runs";
import { BACKTESTER_ROOT } from "./system";

interface FakeSpawner extends RunSpawnerLike {
  calls: SpawnConfig[];
}

function makeTmpRoot(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "runs-test-"));
}

function cleanup(root: string): void {
  fs.rmSync(root, { recursive: true, force: true });
}

/**
 * data root + a fixture .env whose range MATCHES the ohlc filename, so the
 * symbol is runnable (tests must never read the repo's real .env).
 */
function makeDataRoot(root: string): { dataRoot: string; envPath: string } {
  const dataRoot = path.join(root, "data");
  fs.mkdirSync(path.join(dataRoot, "DCRUSDT"), { recursive: true });
  fs.writeFileSync(
    path.join(dataRoot, "DCRUSDT", "ohlc_1s_2026-01-01_2026-01-02.csv"),
    "a,b\n",
    "utf8",
  );
  const envPath = path.join(root, ".env");
  fs.writeFileSync(
    envPath,
    ["START_DATE=2026-01-01", "END_DATE=2026-01-02", ""].join("\n"),
    "utf8",
  );
  return { dataRoot, envPath };
}

function makeRecord(overrides: Partial<RunRecord> = {}): Omit<RunRecord, "id" | "createdAt" | "logPath"> & {
  id: string;
} {
  return {
    id: "run-1",
    symbol: "DCRUSDT",
    strategy: "momentum_drop",
    engine: "standard",
    search: "grid",
    nTrials: 30,
    jobs: 1,
    validationMode: "off",
    status: "queued",
    ...overrides,
  } as Omit<RunRecord, "id" | "createdAt" | "logPath"> & { id: string };
}

/** Fake spawner: records argv configs, optionally holds the run "running". */
function makeFakeSpawner(store: RunStore, hold = false): FakeSpawner {
  const calls: SpawnConfig[] = [];
  let onKill: (() => void) | null = null;
  return {
    calls,
    spawn(config: SpawnConfig): Promise<SpawnResult> {
      calls.push(config);
      if (!hold) return Promise.resolve({ success: true, exitCode: 0 });
      store.transition(config.runId, "running");
      return new Promise<SpawnResult>((resolve) => {
        onKill = () => {
          store.transition(config.runId, "cancelled");
          resolve({ success: false, error: "cancelled" });
        };
      });
    },
    kill(): boolean {
      if (!onKill) return false;
      const fire = onKill;
      onKill = null;
      fire();
      return true;
    },
  };
}

function makeRes(): { res: http.ServerResponse; out: { code: number; body: any } } {
  const out: { code: number; body: any } = { code: 0, body: null };
  const res = {
    writeHead(code: number) {
      out.code = code;
      return res;
    },
    end(body?: string) {
      out.body = body ? JSON.parse(body) : null;
      return res;
    },
  } as unknown as http.ServerResponse;
  return { res, out };
}

interface CallResult {
  handled: boolean;
  code: number;
  body: any;
}

async function call(
  method: string,
  pathname: string,
  deps: RunsDeps,
  body?: unknown
): Promise<CallResult> {
  const { res, out } = makeRes();
  const payload = body === undefined ? "" : JSON.stringify(body);
  const req = Object.assign(Readable.from(payload ? [payload] : []), {
    method,
    url: pathname,
    headers: { "content-length": String(Buffer.byteLength(payload)) },
  }) as unknown as http.IncomingMessage;
  const handled = handleRunsRoutes(req, res, new URL(pathname, "http://localhost"), deps);
  // Route bodies are read asynchronously: let the microtask queue drain.
  await new Promise((resolve) => setImmediate(resolve));
  return { handled, code: out.code, body: out.body };
}

const VALID_BODY = {
  symbol: "DCRUSDT",
  strategy: "momentum_drop",
  engine: "standard",
  search: "grid",
  nTrials: 30,
  jobs: 1,
  validationMode: "off",
};

describe("routes/runs — POST /api/runs", () => {
  let root: string;
  let store: RunStore;
  let spawner: FakeSpawner;
  let deps: RunsDeps;

  beforeEach(() => {
    root = makeTmpRoot();
    store = createRunStore(path.join(root, "dashboard-data"));
    spawner = makeFakeSpawner(store);
    deps = { store, spawner, ...makeDataRoot(root), strategies: ["momentum_drop"] };
  });

  afterEach(() => cleanup(root));

  test("201 happy path: creates a queued run and enqueues the spawn", async () => {
    const r = await call("POST", "/api/runs", deps, VALID_BODY);
    expect(r.handled).toBe(true);
    expect(r.code).toBe(201);
    expect(r.body.status).toBe("queued");
    expect(r.body.id).toMatch(/^\d{8}-\d{6}-momentum_drop$/);

    const record = store.load(r.body.id);
    expect(record).not.toBeNull();
    expect(record!.status).toBe("queued");
    expect(record!.symbol).toBe("DCRUSDT");
    expect(fs.existsSync(record!.logPath)).toBe(true);
  });

  test("spawn receives the allowlisted argv config (no shell, no extra flags)", async () => {
    const r = await call("POST", "/api/runs", deps, VALID_BODY);
    expect(spawner.calls).toHaveLength(1);
    expect(spawner.calls[0]).toEqual({
      runId: r.body.id,
      symbol: "DCRUSDT",
      strategy: "momentum_drop",
      engine: "standard",
      search: "grid",
      nTrials: 30,
      jobs: 1,
      validationMode: "off",
      repoRoot: BACKTESTER_ROOT,
    });
  });

  test("201 with kebab-case flag names (D3 flag names) also works", async () => {
    const r = await call("POST", "/api/runs", deps, {
      symbol: "DCRUSDT",
      strategy: "momentum_drop",
      engine: "standard",
      search: "grid",
      "n-trials": 7,
      jobs: 2,
      "validation-mode": "purged",
    });
    expect(r.code).toBe(201);
    const record = store.load(r.body.id)!;
    expect(record.nTrials).toBe(7);
    expect(record.jobs).toBe(2);
    expect(record.validationMode).toBe("purged");
  });

  test("400 on unknown strategy re-validated against the config allowlist", async () => {
    const r = await call("POST", "/api/runs", { ...deps, strategies: ["mean_reversion"] }, VALID_BODY);
    expect(r.code).toBe(400);
    expect(r.body.error).toMatch(/unknown strategy: momentum_drop/);
    expect(spawner.calls).toHaveLength(0);
    expect(store.list()).toHaveLength(0);
  });

  test("400 on a strategy that is not in the python registry", async () => {
    const r = await call("POST", "/api/runs", deps, { ...VALID_BODY, strategy: "not_a_strategy" });
    expect(r.code).toBe(400);
    expect(r.body.error).toMatch(/invalid strategy/);
    expect(store.list()).toHaveLength(0);
  });

  test("400 on unknown engine", async () => {
    const r = await call("POST", "/api/runs", deps, { ...VALID_BODY, engine: "quantum" });
    expect(r.code).toBe(400);
    expect(r.body.error).toMatch(/invalid engine/);
    expect(spawner.calls).toHaveLength(0);
  });

  test("400 on unknown symbol (server-side symbol allowlist)", async () => {
    const r = await call("POST", "/api/runs", deps, { ...VALID_BODY, symbol: "NOPEUSDT" });
    expect(r.code).toBe(400);
    expect(r.body.error).toMatch(/invalid symbol/);
  });

  test("400 on injection attempt", async () => {
    const r = await call("POST", "/api/runs", deps, { ...VALID_BODY, symbol: "DCRUSDT; rm -rf /" });
    expect(r.code).toBe(400);
    expect(r.body.error).toMatch(/injection attempt/);
    expect(store.list()).toHaveLength(0);
  });

  test("400 on injection attempt in the strategy field", async () => {
    const r = await call("POST", "/api/runs", deps, {
      ...VALID_BODY,
      strategy: "momentum_drop && whoami",
    });
    expect(r.code).toBe(400);
    expect(r.body.error).toMatch(/injection attempt/);
  });

  test("400 on out-of-range nTrials", async () => {
    const r = await call("POST", "/api/runs", deps, { ...VALID_BODY, nTrials: 99999 });
    expect(r.code).toBe(400);
    expect(r.body.error).toMatch(/nTrials must be an integer between 1 and 5000/);
  });

  test("400 on a non-object body", async () => {
    const r = await call("POST", "/api/runs", deps, ["nope"]);
    expect(r.code).toBe(400);
    expect(typeof r.body.error).toBe("string");
  });

  test("400 when no python/spawner is available", async () => {
    const r = await call(
      "POST",
      "/api/runs",
      { ...deps, spawner: null, pythonBin: null },
      VALID_BODY
    );
    expect(r.code).toBe(400);
    expect(r.body.error).toMatch(/python not found/);
    expect(store.list()).toHaveLength(0);
  });

  test("two runs in the same second get distinct ids", async () => {
    const first = await call("POST", "/api/runs", deps, VALID_BODY);
    const second = await call("POST", "/api/runs", deps, VALID_BODY);
    expect(second.body.id).not.toBe(first.body.id);
    expect(store.list()).toHaveLength(2);
  });

  test("makeRunId produces a store-safe id", () => {
    expect(store.load(makeRunId("momentum_drop", store))).toBeNull();
    expect(makeRunId("momentum_drop", store)).toMatch(/^[\w\-]+$/);
  });
});

describe("routes/runs — GET /api/runs", () => {
  let root: string;
  let store: RunStore;
  let deps: RunsDeps;

  beforeEach(() => {
    root = makeTmpRoot();
    store = createRunStore(path.join(root, "dashboard-data"));
    deps = { store, spawner: makeFakeSpawner(store), ...makeDataRoot(root) };
  });

  afterEach(() => cleanup(root));

  test("empty list", async () => {
    const r = await call("GET", "/api/runs", deps);
    expect(r.code).toBe(200);
    expect(r.body).toEqual([]);
  });

  test("newest first, without logPath", async () => {
    store.create(makeRecord({ id: "run-old" }));
    const old = store.load("run-old")!;
    old.createdAt = "2026-01-01T00:00:00.000Z";
    store.save(old);
    store.create(makeRecord({ id: "run-new" }));
    const recent = store.load("run-new")!;
    recent.createdAt = "2026-09-26T14:23:10.000Z";
    store.save(recent);

    const r = await call("GET", "/api/runs", deps);
    expect(r.code).toBe(200);
    expect(r.body.map((x: any) => x.id)).toEqual(["run-new", "run-old"]);
    expect(r.body[0]).toEqual({
      id: "run-new",
      symbol: "DCRUSDT",
      strategy: "momentum_drop",
      engine: "standard",
      status: "queued",
      createdAt: "2026-09-26T14:23:10.000Z",
    });
  });

  test("progress is estimated from the log and always tagged stima", async () => {
    store.create(makeRecord({ id: "run-progress", status: "running" }));
    store.appendLog("run-progress", "[1/40] trial 10/40\n");
    const r = await call("GET", "/api/runs", deps);
    expect(r.body[0].progress).toBe(25);
    expect(r.body[0].progressNote).toBe("stima");
  });

  test("no progress key for terminal runs", async () => {
    store.create(makeRecord({ id: "run-done", status: "done" }));
    const r = await call("GET", "/api/runs", deps);
    expect(r.body[0].progress).toBeUndefined();
    expect(r.body[0].progressNote).toBeUndefined();
  });
});

describe("routes/runs — GET /api/runs/:id and /log", () => {
  let root: string;
  let store: RunStore;
  let deps: RunsDeps;

  beforeEach(() => {
    root = makeTmpRoot();
    store = createRunStore(path.join(root, "dashboard-data"));
    deps = { store, spawner: makeFakeSpawner(store), ...makeDataRoot(root) };
    store.create(makeRecord({ id: "run-1" }));
    store.appendLog("run-1", "line 1\nline 2\nline 3\n");
  });

  afterEach(() => cleanup(root));

  test("detail = summary + last N log lines", async () => {
    const r = await call("GET", "/api/runs/run-1", { ...deps, logTail: 2 });
    expect(r.code).toBe(200);
    expect(r.body.id).toBe("run-1");
    expect(r.body.status).toBe("queued");
    expect(r.body.log).toEqual({
      totalLines: 3,
      lines: ["line 2", "line 3"],
      eof: true,
      rotated: false,
    });
    expect(r.body.logPath).toBeUndefined();
  });

  test("log returns the lines and a cursor for the next request", async () => {
    const r = await call("GET", "/api/runs/run-1/log?fromLine=1", deps);
    expect(r.code).toBe(200);
    expect(Object.keys(r.body).sort()).toEqual(["eof", "lines", "nextLine", "rotated", "totalLines", "truncated"]);
    expect(r.body.totalLines).toBe(3);
    expect(r.body.lines).toEqual(["line 1", "line 2", "line 3"]);
    expect(r.body.eof).toBe(true);
    expect(r.body.rotated).toBe(false);
    expect(r.body.nextLine).toBe(4);
    expect(r.body.truncated).toBe(false);
  });

  test("log offset is line-based", async () => {
    const r = await call("GET", "/api/runs/run-1/log?fromLine=2", deps);
    expect(r.body.totalLines).toBe(3);
    expect(r.body.lines).toEqual(["line 2", "line 3"]);
    expect(r.body.eof).toBe(true);
  });

  test("log fromLine=0 returns everything (frontend cursor start)", async () => {
    const r = await call("GET", "/api/runs/run-1/log?fromLine=0", deps);
    expect(r.body.lines).toEqual(["line 1", "line 2", "line 3"]);
  });

  test("a capped log response exposes a cursor and does not skip lines", async () => {
    store.appendLog("run-1", Array.from({ length: 2005 }, (_, i) => `extra ${i}\n`).join(""));
    const first = await call("GET", "/api/runs/run-1/log?fromLine=0", deps);
    expect(first.body.lines).toHaveLength(2000);
    expect(first.body.lines[0]).toBe("line 1");
    expect(first.body.truncated).toBe(true);
    expect(first.body.eof).toBe(false);
    expect(first.body.nextLine).toBe(2001);
    const second = await call("GET", `/api/runs/run-1/log?fromLine=${first.body.nextLine}`, deps);
    expect(second.body.lines).toHaveLength(8);
    expect(second.body.lines[0]).toBe("extra 1997");
    expect(second.body.truncated).toBe(false);
    expect(second.body.eof).toBe(true);
    expect(second.body.nextLine).toBe(2009);
  });

  test("detects a shorter rotated log and restarts its cursor", async () => {
    fs.writeFileSync(store.load("run-1")!.logPath, "new line\n");
    const r = await call("GET", "/api/runs/run-1/log?fromLine=50", deps);
    expect(r.body.lines).toEqual(["new line"]);
    expect(r.body.rotated).toBe(true);
    expect(r.body.nextLine).toBe(2);
  });

  test("log of an empty run is eof with zero lines", async () => {
    store.create(makeRecord({ id: "run-empty" }));
    const r = await call("GET", "/api/runs/run-empty/log", deps);
    expect(r.body).toEqual({ totalLines: 0, lines: [], eof: true, rotated: false, nextLine: 1, truncated: false });
  });

  test("404 unknown run id on detail and log", async () => {
    const detail = await call("GET", "/api/runs/nope", deps);
    expect(detail.code).toBe(404);
    expect(detail.body.error).toBe("unknown run");
    const log = await call("GET", "/api/runs/nope/log?fromLine=1", deps);
    expect(log.code).toBe(404);
  });

  test("404 for a path-traversal id", async () => {
    const r = await call("GET", "/api/runs/..%2F..%2Fetc%2Fpasswd", deps);
    expect(r.handled).toBe(true);
    expect(r.code).toBe(404);
  });
});

describe("routes/runs — cancel", () => {
  let root: string;
  let store: RunStore;

  beforeEach(() => {
    root = makeTmpRoot();
    store = createRunStore(path.join(root, "dashboard-data"));
  });

  afterEach(() => cleanup(root));

  test("cancels a running run (kill + awaited transition)", async () => {
    const spawner = makeFakeSpawner(store, true);
    const deps: RunsDeps = { store, spawner, ...makeDataRoot(root) };
    store.create(makeRecord({ id: "run-live", status: "queued" }));
    store.transition("run-live", "running");

    const r = await call("POST", "/api/runs/run-live/cancel", deps, {});
    expect(r.code).toBe(200);
    expect(r.body).toEqual({ status: "cancelled" });
    expect(store.load("run-live")!.status).toBe("cancelled");
    expect(store.load("run-live")!.finishedAt).toBeDefined();
  });

  test("cancels a queued run that was never spawned", async () => {
    const deps: RunsDeps = {
      store,
      spawner: makeFakeSpawner(store),
      ...makeDataRoot(root),
    };
    store.create(makeRecord({ id: "run-queued" }));
    const r = await call("POST", "/api/runs/run-queued/cancel", deps, {});
    expect(r.code).toBe(200);
    expect(r.body).toEqual({ status: "cancelled" });
    expect(store.load("run-queued")!.status).toBe("cancelled");
  });

  test("409 when the run is already terminal", async () => {
    const deps: RunsDeps = {
      store,
      spawner: makeFakeSpawner(store),
      ...makeDataRoot(root),
    };
    store.create(makeRecord({ id: "run-done", status: "done" }));
    const r = await call("POST", "/api/runs/run-done/cancel", deps, {});
    expect(r.code).toBe(409);
    expect(r.body.error).toMatch(/cannot cancel run in status done/);
    expect(store.load("run-done")!.status).toBe("done");
  });

  test("404 unknown run id", async () => {
    const deps: RunsDeps = {
      store,
      spawner: makeFakeSpawner(store),
      ...makeDataRoot(root),
    };
    const r = await call("POST", "/api/runs/nope/cancel", deps, {});
    expect(r.code).toBe(404);
  });
});

describe("routes/runs — reconcile", () => {
  let root: string;
  let store: RunStore;
  let deps: RunsDeps;

  beforeEach(() => {
    root = makeTmpRoot();
    store = createRunStore(path.join(root, "dashboard-data"));
    deps = { store, spawner: makeFakeSpawner(store), ...makeDataRoot(root) };
  });

  afterEach(() => cleanup(root));

  for (const target of ["done", "failed", "cancelled"] as const) {
    test(`allowed on unknown → ${target}`, async () => {
      store.create(makeRecord({ id: "run-unknown", status: "unknown" }));
      const r = await call("POST", "/api/runs/run-unknown/reconcile", deps, { status: target });
      expect(r.code).toBe(200);
      expect(r.body).toEqual({ status: target });
      expect(store.load("run-unknown")!.status).toBe(target);
    });
  }

  test("refused on done (409)", async () => {
    store.create(makeRecord({ id: "run-done", status: "done" }));
    const r = await call("POST", "/api/runs/run-done/reconcile", deps, { status: "failed" });
    expect(r.code).toBe(409);
    expect(r.body.error).toMatch(/reconcile only allowed for unknown status \(current: done\)/);
    expect(store.load("run-done")!.status).toBe("done");
  });

  test("refused on queued (409)", async () => {
    store.create(makeRecord({ id: "run-queued", status: "queued" }));
    const r = await call("POST", "/api/runs/run-queued/reconcile", deps, { status: "done" });
    expect(r.code).toBe(409);
    expect(store.load("run-queued")!.status).toBe("queued");
  });

  test("400 when the requested status is not a terminal one", async () => {
    store.create(makeRecord({ id: "run-unknown", status: "unknown" }));
    const r = await call("POST", "/api/runs/run-unknown/reconcile", deps, { status: "running" });
    expect(r.code).toBe(400);
    expect(r.body.error).toMatch(/status must be one of done\|failed\|cancelled/);
    expect(store.load("run-unknown")!.status).toBe("unknown");
  });

  test("400 when the status is missing", async () => {
    store.create(makeRecord({ id: "run-unknown", status: "unknown" }));
    const r = await call("POST", "/api/runs/run-unknown/reconcile", deps, {});
    expect(r.code).toBe(400);
  });

  test("404 unknown run id", async () => {
    const r = await call("POST", "/api/runs/nope/reconcile", deps, { status: "done" });
    expect(r.code).toBe(404);
  });
});

describe("routes/runs — dispatch", () => {
  let root: string;
  let store: RunStore;
  let deps: RunsDeps;

  beforeEach(() => {
    root = makeTmpRoot();
    store = createRunStore(path.join(root, "dashboard-data"));
    deps = { store, spawner: makeFakeSpawner(store), ...makeDataRoot(root) };
  });

  afterEach(() => cleanup(root));

  test("unrelated paths are not handled", async () => {
    expect((await call("GET", "/api/status", deps)).handled).toBe(false);
    expect((await call("GET", "/api/summaries", deps)).handled).toBe(false);
    expect((await call("GET", "/", deps)).handled).toBe(false);
  });

  test("DELETE /api/runs is not handled", async () => {
    expect((await call("DELETE", "/api/runs", deps)).handled).toBe(false);
  });

  test("GET /api/runs/:id/bogus is not handled", async () => {
    expect((await call("GET", "/api/runs/run-1/bogus", deps)).handled).toBe(false);
  });
});
