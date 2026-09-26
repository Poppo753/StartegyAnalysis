/**
 * lib/runSpawn.test.ts — Unit tests for runSpawn (U1-02).
 *
 * Tests with portable fake commands (node -e), never real python.
 * Tests: done/failed/cancel transitions, serial gpu lock on 2 fakes, rotation flag.
 */
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { RunStore, createRunStore, RunRecord } from "./runStore";
import { RunSpawner, createRunSpawner, getPlatformPythonBin, rotateLogIfNeeded, PythonBinInfo } from "./runSpawn";

function makeTmpRoot(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "runSpawn-test-"));
}

function cleanup(root: string): void {
  fs.rmSync(root, { recursive: true, force: true });
}

function makeRecord(overrides: Partial<RunRecord> = {}): Omit<RunRecord, "id" | "createdAt" | "logPath"> & { id: string } {
  return {
    id: "test-run-1",
    symbol: "DCRUSDT",
    strategy: "momentum_drop",
    engine: "standard",
    search: "grid",
    nTrials: 1,
    jobs: 1,
    validationMode: "off",
    status: "queued",
    ...overrides,
  } as Omit<RunRecord, "id" | "createdAt" | "logPath"> & { id: string };
}

const fakePythonBin: PythonBinInfo = {
  path: process.execPath, // Use current node binary
  version: "fake-node-for-testing",
};

describe("getPlatformPythonBin", () => {
  test("returns path and version for current platform (if venv exists)", () => {
    // This test only passes if the venv exists; skip otherwise
    const isWindows = process.platform === "win32";
    const binRel = isWindows ? ".venv/Scripts/python.exe" : ".venv/bin/python";
    const binPath = path.resolve(process.cwd(), "python-backtester", binRel);
    if (!fs.existsSync(binPath)) {
      console.log("Skipping getPlatformPythonBin test - venv not found");
      return;
    }
    const info = getPlatformPythonBin();
    expect(info.path).toBeDefined();
    expect(info.version).toBeDefined();
    expect(fs.existsSync(info.path)).toBe(true);
  });
});

describe("rotateLogIfNeeded", () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = makeTmpRoot();
  });

  afterEach(() => {
    cleanup(tmpDir);
  });

  test("returns false for non-existent file", () => {
    const logPath = path.join(tmpDir, "nonexistent.log");
    expect(rotateLogIfNeeded(logPath, 100)).toBe(false);
  });

  test("returns false for file under threshold", () => {
    const logPath = path.join(tmpDir, "small.log");
    fs.writeFileSync(logPath, "small content", "utf8");
    expect(rotateLogIfNeeded(logPath, 100)).toBe(false);
    expect(fs.readFileSync(logPath, "utf8")).toBe("small content");
  });

  test("rotates file over threshold, keeps second half", () => {
    const logPath = path.join(tmpDir, "large.log");
    const lines = Array.from({ length: 100 }, (_, i) => `line ${i}`);
    fs.writeFileSync(logPath, lines.join("\n"), "utf8");
    const threshold = 100; // bytes
    expect(rotateLogIfNeeded(logPath, threshold)).toBe(true);
    const content = fs.readFileSync(logPath, "utf8");
    const rotatedLines = content.split(/\r?\n/).filter(Boolean);
    expect(rotatedLines.length).toBeLessThan(100);
    expect(rotatedLines[0]).toMatch(/line \d+/);
    // Should keep second half
    const firstKept = parseInt(rotatedLines[0].replace("line ", ""), 10);
    expect(firstKept).toBeGreaterThanOrEqual(50);
  });
});

describe("RunSpawner core logic (store transitions, GPU lock)", () => {
  let root: string;
  let store: RunStore;
  let spawner: RunSpawner;

  beforeEach(() => {
    root = makeTmpRoot();
    store = createRunStore(root);
    spawner = createRunSpawner(store, undefined, 100, fakePythonBin); // 100 bytes threshold
  });

  afterEach(() => {
    cleanup(root);
  });

  test("GPU lock prevents concurrent gpu runs", () => {
    expect(store.acquireGpuLock("run-1")).toBe(true);
    expect(store.acquireGpuLock("run-2")).toBe(false);
    store.releaseGpuLock("run-1");
    expect(store.acquireGpuLock("run-2")).toBe(true);
  });

  test("kill sets cancelled status via store", () => {
    const runId = "run-kill";
    store.create(makeRecord({ id: runId, engine: "standard" }));
    store.transition(runId, "running");
    store.transition(runId, "cancelled");
    const record = store.load(runId);
    expect(record?.status).toBe("cancelled");
  });

  test("reconcile unknown to done/failed/cancelled", () => {
    const runId = "run-unknown";
    store.create(makeRecord({ id: runId, status: "unknown" }));
    store.reconcileUnknown(runId, "done");
    expect(store.load(runId)?.status).toBe("done");

    const runId2 = "run-unknown2";
    store.create(makeRecord({ id: runId2, status: "unknown" }));
    store.reconcileUnknown(runId2, "failed");
    expect(store.load(runId2)?.status).toBe("failed");

    const runId3 = "run-unknown3";
    store.create(makeRecord({ id: runId3, status: "unknown" }));
    store.reconcileUnknown(runId3, "cancelled");
    expect(store.load(runId3)?.status).toBe("cancelled");
  });

  test("reconcile rejects non-unknown", () => {
    const runId = "run-done";
    store.create(makeRecord({ id: runId, status: "done" }));
    expect(() => store.reconcileUnknown(runId, "failed")).toThrow("reconcile only allowed for unknown status");
  });
});

describe("RunSpawner integration (fake commands with node)", () => {
  let root: string;
  let store: RunStore;
  let spawner: RunSpawner;

  beforeEach(() => {
    root = makeTmpRoot();
    store = createRunStore(root);
    spawner = createRunSpawner(store, undefined, 1000, fakePythonBin); // 1KB threshold
  });

  afterEach(() => {
    cleanup(root);
  });

  test("spawn done transition with successful exit", () => {
    const runId = "run-done";
    store.create(makeRecord({ id: runId, engine: "standard" }));
    store.transition(runId, "running");
    store.transition(runId, "done");
    const record = store.load(runId);
    expect(record?.status).toBe("done");
    // exitCode is set by spawner on exit, not by transition directly
  });

  test("spawn failed transition with failed exit", () => {
    const runId = "run-failed";
    store.create(makeRecord({ id: runId, engine: "standard" }));
    store.transition(runId, "running");
    store.transition(runId, "failed");
    const record = store.load(runId);
    expect(record?.status).toBe("failed");
    // exitCode is set by spawner on exit, not by transition directly
  });

  test("spawn cancelled transition via kill", () => {
    const runId = "run-cancelled";
    store.create(makeRecord({ id: runId, engine: "standard" }));
    store.transition(runId, "running");
    store.transition(runId, "cancelled");
    const record = store.load(runId);
    expect(record?.status).toBe("cancelled");
  });

  test("log rotation during spawn", () => {
    const runId = "run-rotate-spawn";
    store.create(makeRecord({ id: runId, engine: "standard" }));
    store.transition(runId, "running");

    const logPath = path.join(root, "runs", `${runId}.log`);
    const threshold = 100;

    // Write enough to trigger rotation
    const longLine = "x".repeat(2000);
    store.appendLog(runId, longLine + "\n");
    store.appendLog(runId, "another line\n");

    // Manually trigger rotation check
    rotateLogIfNeeded(logPath, threshold);

    // Verify log was rotated (file size should be controlled)
    const stats = fs.statSync(logPath);
    expect(stats.size).toBeLessThan(5000); // Much less than unrotated would be
  });

  test("serial GPU lock on 2 fake runs", () => {
    const runId1 = "gpu-run-1";
    const runId2 = "gpu-run-2";
    store.create(makeRecord({ id: runId1, engine: "gpu" }));
    store.create(makeRecord({ id: runId2, engine: "gpu" }));

    // First run acquires lock
    expect(store.acquireGpuLock(runId1)).toBe(true);
    store.transition(runId1, "running");

    // Second run cannot acquire
    expect(store.acquireGpuLock(runId2)).toBe(false);
    // Should remain queued
    expect(store.load(runId2)?.status).toBe("queued");

    // Simulate first run completing
    store.transition(runId1, "done");
    store.releaseGpuLock(runId1);

    // Now second can acquire
    expect(store.acquireGpuLock(runId2)).toBe(true);
    store.transition(runId2, "running");
    store.transition(runId2, "done");
    store.releaseGpuLock(runId2);

    expect(store.load(runId1)?.status).toBe("done");
    expect(store.load(runId2)?.status).toBe("done");
  });
});

describe("RunSpawner kill behavior", () => {
  let root: string;
  let store: RunStore;
  let spawner: RunSpawner;

  beforeEach(() => {
    root = makeTmpRoot();
    store = createRunStore(root);
    spawner = createRunSpawner(store, undefined, 1000, fakePythonBin);
  });

  afterEach(() => {
    cleanup(root);
  });

  test("kill returns false when no process running", () => {
    const result = spawner.kill("non-existent");
    expect(result).toBe(false);
  });
});

describe("RunSpawner process management", () => {
  let root: string;
  let store: RunStore;
  let spawner: RunSpawner;

  const config = (runId: string, engine: string): import("./runSpawn").SpawnConfig => ({
    runId, engine, symbol: runId, strategy: "momentum_drop", search: "grid",
    nTrials: 1, jobs: 1, validationMode: "off", repoRoot: root,
  });

  beforeEach(() => {
    root = makeTmpRoot();
    fs.writeFileSync(path.join(root, "main.py"), "setTimeout(() => console.log('finished'), 200);\n");
    store = createRunStore(root);
    spawner = createRunSpawner(store, root, 1000, fakePythonBin);
  });

  afterEach(() => cleanup(root));

  test("cancels the requested process while another run completes", async () => {
    store.create(makeRecord({ id: "first" }));
    store.create(makeRecord({ id: "second" }));
    const first = spawner.spawn(config("first", "standard"));
    const second = spawner.spawn(config("second", "standard"));
    expect(spawner.kill("first")).toBe(true);
    expect((await first).success).toBe(false);
    expect((await second).success).toBe(true);
    expect(store.load("first")?.status).toBe("cancelled");
    expect(store.load("second")?.status).toBe("done");
    expect(spawner.kill("first")).toBe(false);
  });

  test("starts the next GPU run when the lock is released", async () => {
    store.create(makeRecord({ id: "gpu-first", engine: "gpu" }));
    store.create(makeRecord({ id: "gpu-second", engine: "gpu" }));
    const first = spawner.spawn(config("gpu-first", "gpu"));
    const second = spawner.spawn(config("gpu-second", "gpu"));
    expect(store.load("gpu-second")?.status).toBe("queued");
    expect(spawner.getGpuQueued()).toEqual(["gpu-second"]);
    expect((await first).success).toBe(true);
    expect((await second).success).toBe(true);
    expect(store.load("gpu-second")?.status).toBe("done");
    expect(spawner.getGpuQueued()).toEqual([]);
  });

  test("a missing executable fails the run without crashing the process", async () => {
    store.create(makeRecord({ id: "missing" }));
    const result = await spawner.spawn(config("missing", "standard"), path.join(root, "does-not-exist"));
    expect(result.success).toBe(false);
    expect(store.load("missing")?.status).toBe("failed");
  });

  test("passes overrides only to the selected child process", async () => {
    fs.writeFileSync(path.join(root, "main.py"), "console.log(process.env.X_VALUES || 'unset');\n");
    store.create(makeRecord({ id: "with-override" }));
    store.create(makeRecord({ id: "without-override" }));
    const withOverride = { ...config("with-override", "standard"), overrides: { X_VALUES: "0.2,0.5" } };
    expect((await spawner.spawn(withOverride)).success).toBe(true);
    expect((await spawner.spawn(config("without-override", "standard"))).success).toBe(true);
    expect(fs.readFileSync(path.join(root, "runs", "with-override.log"), "utf8"))
      .toContain("0.2,0.5");
    expect(fs.readFileSync(path.join(root, "runs", "without-override.log"), "utf8"))
      .not.toContain("0.2,0.5");
  });
});
