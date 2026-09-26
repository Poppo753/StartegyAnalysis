import * as fs from "fs";
import * as path from "path";
import { execFileSync } from "child_process";

export interface StrategyInfo {
  name: string;
  runnable: boolean;
  grid: boolean;
  optuna: boolean;
  fast: boolean;
  gpu: boolean;
  parameters: string[];
  parameterSpace: Record<string, [number, number, string]>;
}

const BACKTESTER_ROOT = path.resolve(__dirname, "..", "..", "..", "python-backtester");
const PYTHON = process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python";
let cache: { signature: string; entries: StrategyInfo[] } | null = null;

export function listStrategyCatalog(): StrategyInfo[] {
  const directory = path.join(BACKTESTER_ROOT, "src", "strategies");
  const binary = path.resolve(process.env.PYTHON_BIN || path.join(BACKTESTER_ROOT, PYTHON));
  if (!fs.existsSync(binary)) return [];
  const files = fs.readdirSync(directory).filter((name) => name.endsWith(".py"));
  const signature = [binary, fs.statSync(path.join(BACKTESTER_ROOT, "dashboard_catalog.py")).mtimeMs,
    ...files.map((name) => `${name}:${fs.statSync(path.join(directory, name)).mtimeMs}`)].join("|");
  const copy = (entry: StrategyInfo): StrategyInfo => ({ ...entry, parameters: [...entry.parameters],
    parameterSpace: Object.fromEntries(Object.entries(entry.parameterSpace).map(([key, bounds]) => [key, [...bounds]])) });
  if (cache?.signature === signature) return cache.entries.map(copy);
  try {
    const output = execFileSync(binary, ["dashboard_catalog.py"], {
      cwd: BACKTESTER_ROOT,
      encoding: "utf8",
      timeout: 15000,
      maxBuffer: 1024 * 1024,
    });
    const parsed: unknown = JSON.parse(output);
    if (!Array.isArray(parsed)) return [];
    const entries = parsed.filter((item): item is StrategyInfo =>
      item && typeof item.name === "string" && typeof item.runnable === "boolean" &&
      typeof item.grid === "boolean" && typeof item.optuna === "boolean" &&
      typeof item.fast === "boolean" && typeof item.gpu === "boolean" &&
      Array.isArray(item.parameters) && item.parameters.every((value: unknown) => typeof value === "string") &&
      item.parameterSpace && typeof item.parameterSpace === "object");
    cache = { signature, entries };
    return entries.map(copy);
  } catch {
    return [];
  }
}
