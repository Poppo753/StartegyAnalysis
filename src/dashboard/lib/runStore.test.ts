/**
 * lib/runStore.test.ts — Unit tests for runStore (U1-01).
 */
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { RunStore, createRunStore, RunRecord } from "./runStore";

function makeTmpRoot(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "runStore-test-"));
}

function cleanup(root: string): void {
  fs.rmSync(root, { recursive: true, force: true });
}

function makeRecord(overrides: Partial<RunRecord> = {}): RunRecord {
  return {
    id: "test-run-1",
    symbol: "DCRUSDT",
    strategy: "momentum_drop",
    engine: "standard",
    search: "grid",
    nTrials: 30,
    jobs: 1,
    validationMode: "off",
    status: "queued",
    createdAt: new Date().toISOString(),
    logPath: "",
    ...overrides,
  };
}

describe("RunStore", () => {
  let root: string;
  let store: RunStore;

  beforeEach(() => {
    root = makeTmpRoot();
    store = createRunStore(root);
  });

  afterEach(() => {
    cleanup(root);
  });

  test("create saves record with logPath", () => {
    const input = makeRecord({ id: "run-1" });
    const record = store.create(input);
    expect(record.id).toBe("run-1");
    expect(record.logPath).toContain("run-1.log");
    expect(record.createdAt).toBeDefined();
    expect(fs.existsSync(record.logPath)).toBe(true);
  });

  test("load returns record", () => {
    const input = makeRecord({ id: "run-1" });
    store.create(input);
    const loaded = store.load("run-1");
    expect(loaded).not.toBeNull();
    expect(loaded!.id).toBe("run-1");
  });

  test("load returns null for missing", () => {
    const loaded = store.load("missing");
    expect(loaded).toBeNull();
  });

  test("list returns sorted records", async () => {
    const r1 = store.create(makeRecord({ id: "run-1" }));
    // Small delay to ensure different timestamps
    await new Promise((resolve) => setTimeout(resolve, 10));
    const r2 = store.create(makeRecord({ id: "run-2" }));
    const list = store.list();
    expect(list).toHaveLength(2);
    expect(list[0].id).toBe("run-2");
    expect(list[1].id).toBe("run-1");
  });

  describe("valid transitions", () => {
    const validTransitions: [RunRecord["status"], RunRecord["status"]][] = [
      ["queued", "running"],
      ["queued", "cancelled"],
      ["running", "done"],
      ["running", "failed"],
      ["running", "cancelled"],
      ["unknown", "done"],
      ["unknown", "failed"],
      ["unknown", "cancelled"],
    ];

    for (const [from, to] of validTransitions) {
      test(`${from} → ${to} allowed`, () => {
        const record = store.create(makeRecord({ id: "run-1", status: from }));
        const updated = store.transition("run-1", to);
        expect(updated.status).toBe(to);
        if (to === "running") expect(updated.startedAt).toBeDefined();
        if (["done", "failed", "cancelled"].includes(to)) expect(updated.finishedAt).toBeDefined();
      });
    }
  });

  describe("invalid transitions", () => {
    const invalidTransitions: [RunRecord["status"], RunRecord["status"]][] = [
      ["queued", "done"],
      ["queued", "failed"],
      ["done", "running"],
      ["done", "failed"],
      ["failed", "done"],
      ["cancelled", "running"],
      ["running", "queued"],
    ];

    for (const [from, to] of invalidTransitions) {
      test(`${from} → ${to} throws`, () => {
        const record = store.create(makeRecord({ id: "run-1", status: from }));
        expect(() => store.transition("run-1", to)).toThrow(`invalid transition ${from} → ${to}`);
      });
    }
  });

  test("transition on missing run throws", () => {
    expect(() => store.transition("missing", "running")).toThrow("run not found");
  });

  test("appendLog writes to log file", () => {
    store.create(makeRecord({ id: "run-1" }));
    store.appendLog("run-1", "line 1\n");
    store.appendLog("run-1", "line 2\n");
    const logPath = path.join(root, "runs", "run-1.log");
    const content = fs.readFileSync(logPath, "utf8");
    expect(content).toBe("line 1\nline 2\n");
  });

  test("appendLog on missing run throws", () => {
    expect(() => store.appendLog("missing", "test")).toThrow("run not found");
  });

  describe("readLog", () => {
    test("returns lines from offset", () => {
      store.create(makeRecord({ id: "run-1" }));
      store.appendLog("run-1", "line 1\nline 2\nline 3\n");
      const result = store.readLog("run-1", 2);
      expect(result.totalLines).toBe(3);
      expect(result.lines).toEqual(["line 2", "line 3"]);
      expect(result.eof).toBe(true);
      expect(result.rotated).toBe(false);
    });

    test("returns empty for missing log file", () => {
      store.create(makeRecord({ id: "run-1" }));
      const result = store.readLog("run-1", 1);
      expect(result.totalLines).toBe(0);
      expect(result.lines).toEqual([]);
      expect(result.eof).toBe(true);
      expect(result.rotated).toBe(false);
    });

    test("readLog on missing run throws", () => {
      expect(() => store.readLog("missing", 1)).toThrow("run not found");
    });
  });

  describe("reconcileUnknown", () => {
    test("allows reconcile for unknown status", () => {
      const record = store.create(makeRecord({ id: "run-1", status: "unknown" }));
      const updated = store.reconcileUnknown("run-1", "done");
      expect(updated.status).toBe("done");
    });

    test("rejects reconcile for non-unknown status", () => {
      store.create(makeRecord({ id: "run-1", status: "done" }));
      expect(() => store.reconcileUnknown("run-1", "failed")).toThrow("reconcile only allowed for unknown status");
    });

    test("rejects reconcile for missing run", () => {
      expect(() => store.reconcileUnknown("missing", "done")).toThrow("run not found");
    });
  });

  describe("GPU lock", () => {
    test("acquireGpuLock succeeds when free", () => {
      expect(store.acquireGpuLock("run-1")).toBe(true);
      expect(store.acquireGpuLock("run-2")).toBe(false);
    });

    test("releaseGpuLock releases lock", () => {
      store.acquireGpuLock("run-1");
      store.releaseGpuLock("run-1");
      expect(store.acquireGpuLock("run-2")).toBe(true);
    });

    test("releaseGpuLock ignores other run id", () => {
      store.acquireGpuLock("run-1");
      store.releaseGpuLock("run-2");
      expect(store.acquireGpuLock("run-2")).toBe(false);
    });
  });

  test("invalid run id throws", () => {
    expect(() => store.create(makeRecord({ id: "../../../etc/passwd" }))).toThrow("invalid run id");
    expect(() => store.load("../../../etc/passwd")).toThrow("invalid run id");
  });
});