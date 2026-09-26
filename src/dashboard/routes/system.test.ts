/**
 * routes/system.test.ts — Unit tests for /api/status + /api/config (U1-03).
 *
 * Store root and data root are tmp dirs; the strategies allowlist is injected
 * so the test never depends on the Python registry contents.
 */
import * as fs from "fs";
import * as http from "http";
import * as os from "os";
import * as path from "path";
import { Readable } from "stream";
import { URL } from "url";
import { createRunStore, RunRecord, RunStore } from "../lib/runStore";
import {
  RUN_FLAGS,
  SystemDeps,
  diskFreeGb,
  getRunConfig,
  getStatus,
  handleSystemRoutes,
  listDataSymbols,
  listSymbolAvailability,
  resolvePythonBin,
  runSummary,
  studyDbExists,
} from "./system";

function makeTmpRoot(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "system-test-"));
}

function cleanup(root: string): void {
  fs.rmSync(root, { recursive: true, force: true });
}

function makeStore(root: string): RunStore {
  return createRunStore(path.join(root, "dashboard-data"));
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

/**
 * data root with one dir holding an ohlc_ file and one without.
 * Covers BOTH real layouts: flat (ohlc_ directly in the symbol dir) and
 * nested (data/{SYMBOL}/ohlc/ohlc_*.csv — how the pipeline actually writes it).
 */
function makeDataRoot(root: string): string {
  const dataRoot = path.join(root, "data");
  fs.mkdirSync(path.join(dataRoot, "DCRUSDT"), { recursive: true });
  fs.mkdirSync(path.join(dataRoot, "UNIUSDT", "ohlc"), { recursive: true });
  fs.mkdirSync(path.join(dataRoot, "NO_OHLC"), { recursive: true });
  // flat layout
  fs.writeFileSync(path.join(dataRoot, "DCRUSDT", "ohlc_1s_2026-01-01.csv"), "a,b\n", "utf8");
  fs.writeFileSync(path.join(dataRoot, "DCRUSDT", "aggTrades_x.jsonl"), "{}\n", "utf8");
  // nested layout (real: data/{SYMBOL}/ohlc/ohlc_1s_*.csv)
  fs.writeFileSync(path.join(dataRoot, "UNIUSDT", "ohlc", "ohlc_1s_2026-01-01.csv"), "a,b\n", "utf8");
  fs.writeFileSync(path.join(dataRoot, "NO_OHLC", "aggTrades_x.jsonl"), "{}\n", "utf8");
  return dataRoot;
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

function call(
  method: string,
  pathname: string,
  deps: SystemDeps
): { handled: boolean; code: number; body: any } {
  const { res, out } = makeRes();
  const req = Object.assign(Readable.from([]), {
    method,
    url: pathname,
  }) as unknown as http.IncomingMessage;
  const handled = handleSystemRoutes(req, res, new URL(pathname, "http://localhost"), deps);
  return { handled, code: out.code, body: out.body };
}

describe("routes/system — /api/config", () => {
  let root: string;
  let dataRoot: string;
  let store: RunStore;
  let deps: SystemDeps;
  let envPath: string;

  beforeEach(() => {
    root = makeTmpRoot();
    dataRoot = makeDataRoot(root);
    // Fixture .env: tests must never read the repo's real .env.
    envPath = path.join(root, ".env");
    fs.writeFileSync(
      envPath,
      ["START_DATE=2026-01-01", "END_DATE=2026-01-02", ""].join("\n"),
      "utf8",
    );
    store = makeStore(root);
    deps = {
      store,
      dataRoot,
      envPath,
      strategies: ["momentum_drop", "mean_reversion"],
    };
  });

  afterEach(() => cleanup(root));

  test("symbols = symbols whose ohlc files cover the configured range", () => {
    // Fixture: DCRUSDT ohlc_1s_2026-01-01.csv (no range suffix → no match),
    // UNIUSDT ohlc/ohlc_1s_2026-01-01.csv (flat, no range) → none matches the
    // range 2026-01-01..2026-01-02, so the runnable list is empty.
    expect(listDataSymbols(dataRoot, envPath)).toEqual([]);
  });

  test("symbolAvailability reports every symbol with ohlc data + timeframes", () => {
    const avail = listSymbolAvailability(dataRoot, envPath);
    expect(avail.map((a) => a.symbol)).toEqual(["DCRUSDT", "NO_OHLC", "UNIUSDT"].filter((s) => s !== "NO_OHLC"));
    const dcr = avail.find((a) => a.symbol === "DCRUSDT");
    expect(dcr?.availableTimeframes).toEqual(["1s"]);
    expect(dcr?.hasConfiguredRange).toBe(true);
    expect(dcr?.hasDataForRange).toBe(false);
  });

  test("symbols empty when data root missing", () => {
    expect(listDataSymbols(path.join(root, "nope"), envPath)).toEqual([]);
  });

  test("degraded mode: no .env range → every symbol with ohlc data is listed", () => {
    const noEnv = path.join(root, "missing.env");
    expect(listDataSymbols(dataRoot, noEnv)).toEqual(["DCRUSDT", "UNIUSDT"]);
    const avail = listSymbolAvailability(dataRoot, noEnv);
    expect(avail.every((a) => a.hasDataForRange)).toBe(true);
    expect(avail.every((a) => a.hasConfiguredRange)).toBe(false);
  });

  test("range match makes the symbol runnable", () => {
    fs.writeFileSync(
      path.join(dataRoot, "DCRUSDT", "ohlc_5m_2026-01-01_2026-01-02.csv"),
      "a,b\n",
      "utf8",
    );
    expect(listDataSymbols(dataRoot, envPath)).toEqual(["DCRUSDT"]);
  });

  test("config exposes symbols, strategies, engine and flags", () => {
    fs.writeFileSync(
      path.join(dataRoot, "DCRUSDT", "ohlc_1s_2026-01-01_2026-01-02.csv"),
      "a,b\n",
      "utf8",
    );
    const config = getRunConfig(deps);
    expect(config.symbols).toEqual(["DCRUSDT"]);
    expect(config.strategies).toEqual(["momentum_drop", "mean_reversion"]);
    expect(config.engine).toEqual(["standard", "fast", "gpu"]);
    expect(config.configuredRange).toEqual({ start: "2026-01-01", end: "2026-01-02" });
    expect(config.symbolAvailability.length).toBeGreaterThan(0);
  });

  test("flags match the frozen D3 allowlist", () => {
    expect(getRunConfig(deps).flags).toEqual([
      { name: "search", type: "enum", values: ["grid", "optuna"], default: "grid" },
      { name: "n-trials", type: "int", min: 1, max: 5000, default: 30 },
      { name: "jobs", type: "int", min: 1, max: 8, default: 1 },
      {
        name: "validation-mode",
        type: "enum",
        values: ["off", "purged", "cpcv", "walkforward"],
        default: "off",
      },
    ]);
  });

  test("flag values are copies (config cannot mutate the allowlist)", () => {
    const config = getRunConfig(deps);
    config.flags[0].values!.push("mutated");
    expect(RUN_FLAGS[0].values).toEqual(["grid", "optuna"]);
  });

  test("strategies default to the python-backtester listing when not injected", () => {
    const config = getRunConfig({ store });
    expect(Array.isArray(config.strategies)).toBe(true);
    expect(config.strategies).not.toContain("__init__");
    expect(config.strategies.every((s) => /^[a-z0-9_]+$/.test(s))).toBe(true);
  });

  test("GET /api/config returns 200 with the contract shape", () => {
    const r = call("GET", "/api/config", deps);
    expect(r.handled).toBe(true);
    expect(r.code).toBe(200);
    // D3 frozen fields + the two additive availability fields.
    expect(Object.keys(r.body).sort()).toEqual([
      "configuredRange",
      "engine",
      "flags",
      "strategies",
      "symbolAvailability",
      "symbols",
    ]);
  });

  test("GET /api/config works without an injected strategy list", () => {
    const r = call("GET", "/api/config", { store, dataRoot, envPath });
    expect(r.code).toBe(200);
    expect(Array.isArray(r.body.symbols)).toBe(true);
    expect(Array.isArray(r.body.symbolAvailability)).toBe(true);
  });
});

describe("routes/system — /api/status", () => {
  let root: string;
  let dataRoot: string;
  let store: RunStore;

  beforeEach(() => {
    root = makeTmpRoot();
    dataRoot = makeDataRoot(root);
    store = makeStore(root);
  });

  afterEach(() => cleanup(root));

  test("GET /api/status returns the frozen contract shape", () => {
    const r = call("GET", "/api/status", {
      store,
      dataRoot,
      pythonBin: { path: process.execPath, version: "Python 3.11.0" },
    });
    expect(r.handled).toBe(true);
    expect(r.code).toBe(200);
    expect(Object.keys(r.body).sort()).toEqual([
      "diskFreeGb",
      "lastRuns",
      "python",
      "studyDb",
      "venvOk",
    ]);
    expect(r.body.python).toBe("Python 3.11.0");
    expect(r.body.venvOk).toBe(true);
    expect(typeof r.body.diskFreeGb).toBe("number");
    expect(typeof r.body.studyDb).toBe("boolean");
    expect(r.body.lastRuns).toEqual([]);
  });

  test("missing python degrades to python=\"not found\" + venvOk=false", () => {
    const r = call("GET", "/api/status", { store, dataRoot, pythonBin: null });
    expect(r.code).toBe(200);
    expect(r.body.python).toBe("not found");
    expect(r.body.venvOk).toBe(false);
  });

  test("venvOk=false when the configured binary does not exist", () => {
    const r = call("GET", "/api/status", {
      store,
      dataRoot,
      pythonBin: { path: path.join(root, "no-such-python"), version: "Python 3.11.0" },
    });
    expect(r.body.venvOk).toBe(false);
  });

  test("lastRuns carries newest-first run summaries from the store", () => {
    store.create(makeRecord({ id: "run-old" }));
    const old = store.load("run-old")!;
    old.createdAt = "2026-01-01T00:00:00.000Z";
    store.save(old);
    store.create(makeRecord({ id: "run-new", status: "running" }));
    const recent = store.load("run-new")!;
    recent.createdAt = "2026-09-26T14:23:10.000Z";
    store.save(recent);

    const status = getStatus({ store, dataRoot, pythonBin: null });
    expect(status.lastRuns.map((r) => r.id)).toEqual(["run-new", "run-old"]);
    expect(status.lastRuns[0]).toEqual({
      id: "run-new",
      symbol: "DCRUSDT",
      strategy: "momentum_drop",
      engine: "standard",
      status: "running",
      createdAt: "2026-09-26T14:23:10.000Z",
    });
    // logPath never leaks to the client.
    expect(Object.keys(status.lastRuns[0])).not.toContain("logPath");
  });

  test("lastRuns is capped at 10 entries", () => {
    for (let i = 0; i < 12; i++) {
      const record = store.create(makeRecord({ id: `run-${i}` }));
      record.createdAt = `2026-09-26T14:00:${String(i).padStart(2, "0")}.000Z`;
      store.save(record);
    }
    const status = getStatus({ store, dataRoot, pythonBin: null });
    expect(status.lastRuns).toHaveLength(10);
    expect(status.lastRuns[0].id).toBe("run-11");
  });

  test("runSummary drops filesystem-only fields", () => {
    const record = store.create(makeRecord({ id: "run-1" }));
    const summary = runSummary(record);
    expect(summary.id).toBe("run-1");
    expect(Object.keys(summary)).not.toContain("logPath");
    expect(Object.keys(summary)).not.toContain("nTrials");
  });

  test("diskFreeGb is a positive number for the repo root", () => {
    expect(diskFreeGb()).toBeGreaterThan(0);
  });

  test("studyDbExists is a boolean and never opens a .db", () => {
    expect(typeof studyDbExists()).toBe("boolean");
  });
});

describe("routes/system — resolvePythonBin", () => {
  let root: string;
  const savedEnv = process.env.PYTHON_BIN;

  beforeEach(() => {
    root = makeTmpRoot();
  });

  afterEach(() => {
    if (savedEnv === undefined) delete process.env.PYTHON_BIN;
    else process.env.PYTHON_BIN = savedEnv;
    cleanup(root);
  });

  test("uses $PYTHON_BIN when set (no shell, argv array)", () => {
    process.env.PYTHON_BIN = process.execPath;
    const bin = resolvePythonBin();
    expect(bin).not.toBeNull();
    expect(bin!.path).toBe(path.resolve(process.execPath));
    expect(fs.existsSync(bin!.path)).toBe(true);
    expect(bin!.version.length).toBeGreaterThan(0);
  });

  test("returns null when the configured binary is missing", () => {
    process.env.PYTHON_BIN = path.join(root, "missing-python");
    expect(resolvePythonBin()).toBeNull();
  });

  test("falls back to the platform venv path when $PYTHON_BIN is unset", () => {
    delete process.env.PYTHON_BIN;
    const bin = resolvePythonBin();
    if (bin) expect(fs.existsSync(bin.path)).toBe(true);
    else expect(bin).toBeNull();
  });
});

describe("routes/system — dispatch", () => {
  let root: string;
  let store: RunStore;

  beforeEach(() => {
    root = makeTmpRoot();
    store = makeStore(root);
  });

  afterEach(() => cleanup(root));

  test("unrelated path is not handled", () => {
    const r = call("GET", "/api/report", { store });
    expect(r.handled).toBe(false);
  });

  test("POST /api/status is not handled (falls through to static)", () => {
    const r = call("POST", "/api/status", { store });
    expect(r.handled).toBe(false);
  });
});
