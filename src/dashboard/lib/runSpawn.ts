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
import { spawn, SpawnOptions, ChildProcess } from "child_process";
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

function getPlatformPythonBin(): PythonBinInfo {
  const isWindows = process.platform === "win32";
  const binRel = isWindows ? ".venv/Scripts/python.exe" : ".venv/bin/python";
  const binPath = path.resolve(process.cwd(), binRel);

  if (!fs.existsSync(binPath)) {
    throw new Error(
      `Python binary not found at ${binPath}. ` +
      `Ensure the virtual environment exists (run setup) and PYTHON_BIN is correct for ${process.platform}.`
    );
  }

  // Verify it works by getting version
  let version = "unknown";
  try {
    const { execSync } = require("child_process");
    version = execSync(`"${binPath}" --version`, { encoding: "utf8", timeout: 5000 }).trim();
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
  private activeProcess: ChildProcess | null = null;
  private currentRunId: string | null = null;
  private gpuQueued: string[] = [];

  constructor(store: RunStore, repoRoot?: string, logRotationThreshold?: number, pythonBinOverride?: PythonBinInfo) {
    this.store = store;
    this.repoRoot = repoRoot ?? path.resolve(process.cwd(), "python-backtester");
    this.logRotationThreshold = logRotationThreshold ?? 10 * 1024 * 1024; // 10MB default
    this.pythonBin = pythonBinOverride ?? getPlatformPythonBin();
  }

  getPythonBin(): PythonBinInfo {
    return this.pythonBin;
  }

  async spawn(config: SpawnConfig, pythonBin?: string): Promise<SpawnResult> {
    const { runId, engine } = config;

    // Handle GPU queue
    if (engine === "gpu") {
      if (!this.store.acquireGpuLock(runId)) {
        // Re-queue: transition back to queued
        this.store.transition(runId, "queued");
        this.gpuQueued.push(runId);
        return { success: false, error: "GPU busy, re-queued" };
      }
    }

    this.currentRunId = runId;
    this.store.transition(runId, "running");

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
      const child = spawn(binPath, argv, options);
      this.activeProcess = child;

      let killed = false;
      let forceKilled = false;

      const cleanup = () => {
        this.activeProcess = null;
        this.currentRunId = null;
      };

      const handleExit = (code: number | null, signal: NodeJS.Signals | null) => {
        if (killed && !forceKilled) {
          // Was cancelled via kill()
          this.store.transition(runId, "cancelled");
          const record = this.store.load(runId);
          if (record) {
            record.exitCode = code ?? (signal ? 128 + (signal as any) : 1);
            this.store.save(record);
          }
          resolve({ success: false, exitCode: code ?? 1, error: "cancelled" });
        } else if (code === 0) {
          this.store.transition(runId, "done");
          const record = this.store.load(runId);
          if (record) {
            record.exitCode = 0;
            this.store.save(record);
          }
          resolve({ success: true, exitCode: 0 });
        } else {
          this.store.transition(runId, "failed");
          const record = this.store.load(runId);
          if (record) {
            record.exitCode = code ?? 1;
            this.store.save(record);
          }
          resolve({ success: false, exitCode: code ?? 1, error: `exited with code ${code}` });
        }
        cleanup();

        // Process GPU queue
        if (engine === "gpu") {
          this.store.releaseGpuLock(runId);
          if (this.gpuQueued.length > 0) {
            const next = this.gpuQueued.shift()!;
            // The next run will be picked up by the caller re-trying
          }
        }
      };

      child.on("exit", handleExit);

      child.stdout?.on("data", (chunk: Buffer) => {
        this.store.appendLog(runId, chunk.toString("utf8"));
        // Check rotation
        const rotated = rotateLogIfNeeded(
          path.join(this.store["runsDir"], `${runId}.log`),
          this.logRotationThreshold
        );
        // Note: rotated flag is checked on readLog, not stored here
      });

      child.stderr?.on("data", (chunk: Buffer) => {
        this.store.appendLog(runId, chunk.toString("utf8"));
        const rotated = rotateLogIfNeeded(
          path.join(this.store["runsDir"], `${runId}.log`),
          this.logRotationThreshold
        );
      });

      // Store reference for kill()
      this.activeProcess = child;
    });
  }

  kill(runId: string): boolean {
    if (this.activeProcess && this.currentRunId === runId) {
      this.activeProcess.kill("SIGTERM");
      // Force kill after 10s
      setTimeout(() => {
        if (this.activeProcess && this.currentRunId === runId) {
          this.activeProcess.kill("SIGKILL");
        }
      }, 10000);
      return true;
    }
    return false;
  }

  getGpuQueued(): string[] {
    return [...this.gpuQueued];
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