/**
 * lib/runSpawn.ts — Spawn and manage backtest runs (U1-02).
 *
 * - Platform PYTHON_BIN (verified at boot, clear error if missing)
 * - argv-array spawn (shell:false)
 * - Log append stream
 * - gpu.lock ONLY when engine==="gpu" (FIFO queue otherwise)
 * - Kill + 10s force fallback
 * - 10MB rotation with head-trim + rotated flag (threshold parametric in tests)
 */
import * as fs from "fs";
import * as path from "path";
import { spawn, execFileSync, SpawnOptions, ChildProcess } from "child_process";
import { RunStore, RunRecord } from "./runStore";

export interface PythonBinInfo {
  path: string;
  version: string;
}

export interface SpawnConfig {
  runId: string;
  symbol: string;
  strategy: string;
  engine: string;
  search: string;
  nTrials: number;
  jobs: number;
  validationMode: string;
  repoRoot: string;
  logRotationThreshold?: number; // bytes, for testing
}

export interface SpawnResult {
  success: boolean;
  exitCode?: number;
  error?: string;
}

function getPlatformPythonBin(repoRoot: string = path.resolve(process.cwd(), "python-backtester")): PythonBinInfo {
  const isWindows = process.platform === "win32";
  const binRel = isWindows ? ".venv/Scripts/python.exe" : ".venv/bin/python";
  const binPath = path.resolve(repoRoot, binRel);

  if (!fs.existsSync(binPath)) {
    throw new Error(
      `Python binary not found at ${binPath}. ` +
      `Ensure the virtual environment exists (run setup) and PYTHON_BIN is correct for ${process.platform}.`
    );
  }

  // Verify it works by getting version
  let version = "unknown";
  try {
    version = execFileSync(binPath, ["--version"], { encoding: "utf8", timeout: 5000 }).trim();
  } catch {
    // Version check failed but binary exists; proceed anyway
  }

  return { path: binPath, version };
}

function buildArgv(config: SpawnConfig, pythonBin: string): string[] {
  const args = [
    "main.py",
    "--symbol", config.symbol,
    "--strategy", config.strategy,
    "--engine", config.engine,
    "--search", config.search,
    "--n-trials", String(config.nTrials),
    "--jobs", String(config.jobs),
    "--validation-mode", config.validationMode,
  ];
  return args;
}

function rotateLogIfNeeded(logPath: string, threshold: number): boolean {
  if (!fs.existsSync(logPath)) return false;
  const stats = fs.statSync(logPath);
  if (stats.size < threshold) return false;

  const content = fs.readFileSync(logPath, "utf8");
  const lines = content.split(/\r?\n/);
  if (lines.length <= 1) return false;

  // Keep the second half (head trim)
  const keepStart = Math.floor(lines.length / 2);
  const kept = lines.slice(keepStart).join("\n");
  fs.writeFileSync(logPath, kept, "utf8");
  return true;
}

export class RunSpawner {
  private store: RunStore;
  private pythonBin: PythonBinInfo;
  private repoRoot: string;
  private logRotationThreshold: number;
  private activeProcesses = new Map<string, ChildProcess>();
  private gpuQueued = new Map<string, {
    config: SpawnConfig;
    pythonBin?: string;
    resolve: (result: SpawnResult) => void;
  }>();
  private gpuQueueTimer: NodeJS.Timeout | null = null;
  private killTimers = new Map<string, () => void>();

  constructor(store: RunStore, repoRoot?: string, logRotationThreshold?: number, pythonBinOverride?: PythonBinInfo) {
    this.store = store;
    this.repoRoot = repoRoot ?? path.resolve(process.cwd(), "python-backtester");
    this.logRotationThreshold = logRotationThreshold ?? 10 * 1024 * 1024; // 10MB default
    this.pythonBin = pythonBinOverride ?? getPlatformPythonBin(this.repoRoot);
  }

  getPythonBin(): PythonBinInfo {
    return this.pythonBin;
  }

  async spawn(config: SpawnConfig, pythonBin?: string): Promise<SpawnResult> {
    const { runId, engine } = config;
    if (this.activeProcesses.has(runId) || this.gpuQueued.has(runId)) {
      return { success: false, error: "run already scheduled" };
    }
    if (engine === "gpu" && !this.store.acquireGpuLock(runId)) {
      return new Promise((resolve) => {
        this.gpuQueued.set(runId, { config, pythonBin, resolve });
        this.scheduleGpuQueueCheck();
      });
    }
    return this.launch(config, pythonBin);
  }

  private drainGpuQueue(): void {
    const next = this.gpuQueued.entries().next().value;
    if (!next) {
      if (this.gpuQueueTimer) clearInterval(this.gpuQueueTimer);
      this.gpuQueueTimer = null;
      return;
    }
    const [runId, queued] = next;
    if (!this.store.acquireGpuLock(runId)) return;
    this.gpuQueued.delete(runId);
    if (this.gpuQueued.size === 0 && this.gpuQueueTimer) {
      clearInterval(this.gpuQueueTimer);
      this.gpuQueueTimer = null;
    }
    void this.launch(queued.config, queued.pythonBin).then(queued.resolve);
  }

  private scheduleGpuQueueCheck(): void {
    if (this.gpuQueueTimer) return;
    this.gpuQueueTimer = setInterval(() => this.drainGpuQueue(), 1000);
    this.gpuQueueTimer.unref();
  }

  private async launch(config: SpawnConfig, pythonBin?: string): Promise<SpawnResult> {
    const { runId, engine } = config;
    try {
      this.store.transition(runId, "running");
    } catch (error) {
      if (engine === "gpu") {
        this.store.releaseGpuLock(runId);
        this.drainGpuQueue();
      }
      return { success: false, error: String(error) };
    }
    const binPath = pythonBin ?? this.pythonBin.path;
    const argv = buildArgv(config, binPath);
    const cwd = this.repoRoot;

    const options: SpawnOptions = {
      cwd,
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
      stdio: ["ignore", "pipe", "pipe"],
      shell: false,
    };

    return new Promise((resolve) => {
      let child: ChildProcess;
      try {
        child = spawn(binPath, argv, options);
      } catch (error) {
        this.store.transition(runId, "failed");
        if (engine === "gpu") {
          this.store.releaseGpuLock(runId);
          this.drainGpuQueue();
        }
        resolve({ success: false, error: String(error) });
        return;
      }
      this.activeProcesses.set(runId, child);
      let cancelled = false;
      let processError: Error | null = null;
      let forceTimer: NodeJS.Timeout | null = null;

      const append = (chunk: Buffer): void => {
        try {
          this.store.appendLog(runId, chunk.toString("utf8"));
          rotateLogIfNeeded(path.join(this.store["runsDir"], `${runId}.log`), this.logRotationThreshold);
        } catch (error) {
          processError = error instanceof Error ? error : new Error(String(error));
          child.kill();
        }
      };
      child.stdout?.on("data", append);
      child.stderr?.on("data", append);
      child.on("error", (error) => { processError = error; });
      child.on("close", (code) => {
        if (forceTimer) clearTimeout(forceTimer);
        this.activeProcesses.delete(runId);
        this.killTimers.delete(runId);
        const exitCode = code ?? 1;
        const status = cancelled ? "cancelled" : processError || code !== 0 ? "failed" : "done";
        let error: string | undefined;
        try {
          const current = this.store.load(runId);
          if (current && (current.status === "running" || current.status === "queued")) {
            this.store.transition(runId, status);
          }
          const record = this.store.load(runId);
          if (record) {
            record.exitCode = exitCode;
            this.store.save(record);
          }
        } catch (e) {
          error = String(e);
        } finally {
          if (engine === "gpu") {
            this.store.releaseGpuLock(runId);
            this.drainGpuQueue();
          }
        }
        resolve({
          success: status === "done" && !error,
          exitCode,
          error: error ?? (cancelled ? "cancelled" : processError?.message ?? (code === 0 ? undefined : `exited with code ${code}`)),
        });
      });
      this.killTimers.set(runId, () => {
        cancelled = true;
        child.kill("SIGTERM");
        forceTimer = setTimeout(() => {
          if (this.activeProcesses.get(runId) === child) child.kill("SIGKILL");
        }, 10000);
        forceTimer.unref();
      });
    });
  }

  kill(runId: string): boolean {
    const queued = this.gpuQueued.get(runId);
    if (queued) {
      this.gpuQueued.delete(runId);
      queued.resolve({ success: false, error: "cancelled" });
      if (this.gpuQueued.size === 0) this.drainGpuQueue();
      return true;
    }
    const kill = this.killTimers.get(runId);
    if (kill) {
      kill();
      return true;
    }
    return false;
  }

  getGpuQueued(): string[] {
    return [...this.gpuQueued.keys()];
  }
}

export function createRunSpawner(
  store: RunStore,
  repoRoot?: string,
  logRotationThreshold?: number,
  pythonBinOverride?: PythonBinInfo
): RunSpawner {
  return new RunSpawner(store, repoRoot, logRotationThreshold, pythonBinOverride);
}

export { getPlatformPythonBin, buildArgv, rotateLogIfNeeded };
