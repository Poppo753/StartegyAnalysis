/**
 * lib/runStore.ts — Per-run JSON registry (U1-01).
 *
 * Store: load/save/list per-run JSON in dashboard-data/runs/
 * Root is parametric for tests (tmp dirs).
 * Transitions: queued → running → done | failed | cancelled + unknown (post-crash).
 */
import * as fs from "fs";
import * as path from "path";

export interface RunRecord {
  id: string;
  symbol: string;
  strategy: string;
  engine: string;
  search: string;
  nTrials: number;
  jobs: number;
  validationMode: string;
  dataset?: string;
  overrides?: Record<string, string>;
  status: "queued" | "running" | "done" | "failed" | "cancelled" | "unknown";
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
  exitCode?: number;
  progress?: number;
  progressNote?: string;
  logPath: string;
}

const VALID_TRANSITIONS: Record<string, string[]> = {
  queued: ["running", "cancelled"],
  running: ["done", "failed", "cancelled"],
  done: [],
  failed: [],
  cancelled: [],
  unknown: ["done", "failed", "cancelled"],
};

export class RunStore {
  private root: string;
  private runsDir: string;

  constructor(root?: string) {
    this.root = root ?? path.resolve(process.cwd(), "dashboard-data");
    this.runsDir = path.join(this.root, "runs");
    if (!fs.existsSync(this.runsDir)) {
      fs.mkdirSync(this.runsDir, { recursive: true });
    }
  }

  private runFile(id: string): string {
    const base = path.basename(id);
    if (base !== id || !/^[\w\-]+$/.test(base)) {
      throw new Error("invalid run id");
    }
    return path.join(this.runsDir, `${base}.json`);
  }

  private lockFile(): string {
    return path.join(this.runsDir, "gpu.lock");
  }

  acquireGpuLock(runId: string): boolean {
    const lockPath = this.lockFile();
    try {
      fs.writeFileSync(lockPath, runId, { encoding: "utf8", flag: "wx" });
      return true;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
    }
    return fs.readFileSync(lockPath, "utf8").trim() === runId;
  }

  releaseGpuLock(runId: string): void {
    const lockPath = this.lockFile();
    if (fs.existsSync(lockPath)) {
      const existing = fs.readFileSync(lockPath, "utf8").trim();
      if (existing === runId) {
        fs.unlinkSync(lockPath);
      }
    }
  }

  getGpuQueue(): string[] {
    const lockPath = this.lockFile();
    if (!fs.existsSync(lockPath)) return [];
    const current = fs.readFileSync(lockPath, "utf8").trim();
    const queue: string[] = [];
    if (current) queue.push(current);
    return queue;
  }

  create(record: Omit<RunRecord, "id" | "createdAt" | "logPath"> & { id: string }): RunRecord {
    const base = path.basename(record.id);
    if (base !== record.id || !/^[\w\-]+$/.test(base)) {
      throw new Error("invalid run id");
    }
    const full: RunRecord = {
      ...record,
      id: record.id,
      createdAt: new Date().toISOString(),
      logPath: path.join(this.runsDir, `${record.id}.log`),
    };
    // Create empty log file
    fs.writeFileSync(full.logPath, "", "utf8");
    this.save(full);
    return full;
  }

  save(record: RunRecord): void {
    fs.writeFileSync(this.runFile(record.id), JSON.stringify(record, null, 2), "utf8");
  }

  load(id: string): RunRecord | null {
    const file = this.runFile(id);
    if (!fs.existsSync(file)) return null;
    const raw = fs.readFileSync(file, "utf8");
    return JSON.parse(raw) as RunRecord;
  }

  list(): RunRecord[] {
    if (!fs.existsSync(this.runsDir)) return [];
    const files = fs.readdirSync(this.runsDir).filter((f) => f.endsWith(".json"));
    const records: RunRecord[] = [];
    for (const f of files) {
      const raw = fs.readFileSync(path.join(this.runsDir, f), "utf8");
      records.push(JSON.parse(raw) as RunRecord);
    }
    return records.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  }

  transition(id: string, newStatus: RunRecord["status"]): RunRecord {
    const record = this.load(id);
    if (!record) throw new Error("run not found");
    const allowed = VALID_TRANSITIONS[record.status] ?? [];
    if (!allowed.includes(newStatus)) {
      throw new Error(`invalid transition ${record.status} → ${newStatus}`);
    }
    const now = new Date().toISOString();
    record.status = newStatus;
    if (newStatus === "running") record.startedAt = now;
    if (newStatus === "done" || newStatus === "failed" || newStatus === "cancelled") {
      record.finishedAt = now;
    }
    this.save(record);
    return record;
  }

  appendLog(id: string, chunk: string): void {
    const record = this.load(id);
    if (!record) throw new Error("run not found");
    fs.appendFileSync(record.logPath, chunk, "utf8");
  }

  readLog(id: string, fromLine: number): { totalLines: number; lines: string[]; eof: boolean; rotated: boolean } {
    const record = this.load(id);
    if (!record) throw new Error("run not found");
    const logPath = record.logPath;
    if (!fs.existsSync(logPath)) {
      return { totalLines: 0, lines: [], eof: true, rotated: false };
    }
    const content = fs.readFileSync(logPath, "utf8");
    const lines = content.split(/\r?\n/);
    if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
    const total = lines.length;
    const start = Math.max(0, fromLine - 1);
    const slice = lines.slice(start);
    return { totalLines: total, lines: slice, eof: start + slice.length >= total, rotated: false };
  }

  reconcileUnknown(id: string, status: "done" | "failed" | "cancelled"): RunRecord {
    const record = this.load(id);
    if (!record) throw new Error("run not found");
    if (record.status !== "unknown") {
      throw new Error("reconcile only allowed for unknown status");
    }
    return this.transition(id, status);
  }
}

export function createRunStore(root?: string): RunStore {
  return new RunStore(root);
}
