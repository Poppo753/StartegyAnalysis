/**
 * lib/validateRun.ts — Input validation for run creation (U1-01).
 *
 * Allowlist flags: engine, strategy, symbol, search, nTrials, jobs, validationMode.
 * Types/ranges enforced. Injection rejection (; && $() backtick extra --).
 */
import * as fs from "fs";
import * as path from "path";
import { listStrategyCatalog } from "./strategyCatalog";
import { validateRunOverrides } from "./runOptions";

export interface ValidatedRunInput {
  symbol: string;
  strategy: string;
  engine: string;
  search: string;
  nTrials: number;
  jobs: number;
  validationMode: string;
  dataset?: string;
  overrides?: Record<string, string>;
}

export interface ValidationResult {
  ok: boolean;
  data?: ValidatedRunInput;
  error?: string;
}

const ENGINES = ["standard", "fast", "gpu"];
const SEARCH_METHODS = ["grid", "optuna"];
const VALIDATION_MODES = ["off", "purged", "cpcv", "walkforward"];

function listStrategies(): string[] {
  return listStrategyCatalog().filter((entry) => entry.runnable && (entry.grid || entry.optuna)).map((entry) => entry.name);
}

function listSymbols(dataRoot: string): string[] {
  if (!fs.existsSync(dataRoot)) return [];
  return fs.readdirSync(dataRoot, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name);
}

function hasInjectionAttempt(value: string): boolean {
  const patterns = [
    /;/,
    /&&/,
    /\$\(/,
    /`/,
    /--/,
  ];
  return patterns.some((p) => p.test(value));
}

function validateRange(name: string, value: number, min: number, max: number): string | null {
  if (!Number.isInteger(value) || value < min || value > max) {
    return `${name} must be an integer between ${min} and ${max}`;
  }
  return null;
}

export function validateRunInput(
  input: Record<string, unknown>,
  dataRoot: string,
  baseEnv: Record<string, string> = {},
): ValidationResult {
  const symbol = String(input.symbol ?? "").trim();
  const strategy = String(input.strategy ?? "").trim();
  const engine = String(input.engine ?? "").trim();
  const search = String(input.search ?? "").trim();
  const nTrials = input.nTrials;
  const jobs = input.jobs;
  const validationMode = String(input.validationMode ?? "").trim();
  const dataset = input.dataset === undefined ? "" : String(input.dataset).trim();

  if (hasInjectionAttempt(symbol) || hasInjectionAttempt(strategy) ||
      hasInjectionAttempt(engine) || hasInjectionAttempt(search) ||
      hasInjectionAttempt(validationMode)) {
    return { ok: false, error: "injection attempt detected in string fields" };
  }

  if (typeof nTrials === "string" && hasInjectionAttempt(nTrials)) {
    return { ok: false, error: "injection attempt detected in nTrials" };
  }
  if (typeof jobs === "string" && hasInjectionAttempt(jobs)) {
    return { ok: false, error: "injection attempt detected in jobs" };
  }

  const strategies = listStrategies();
  const symbols = listSymbols(dataRoot);

  if (!symbol || !symbols.includes(symbol)) {
    return { ok: false, error: `invalid symbol: ${symbol}` };
  }
  if (!strategy || !strategies.includes(strategy)) {
    return { ok: false, error: `invalid strategy: ${strategy}` };
  }
  if (!engine || !ENGINES.includes(engine)) {
    return { ok: false, error: `invalid engine: ${engine}` };
  }
  if (!search || !SEARCH_METHODS.includes(search)) {
    return { ok: false, error: `invalid search: ${search}` };
  }
  if (!validationMode || !VALIDATION_MODES.includes(validationMode)) {
    return { ok: false, error: `invalid validationMode: ${validationMode}` };
  }

  const nTrialsNum = Number(nTrials);
  const jobsNum = Number(jobs);

  const nTrialsErr = validateRange("nTrials", nTrialsNum, 1, 5000);
  if (nTrialsErr) return { ok: false, error: nTrialsErr };

  const jobsErr = validateRange("jobs", jobsNum, 1, 8);
  if (jobsErr) return { ok: false, error: jobsErr };

  if (search === "optuna" && engine !== "standard") {
    return { ok: false, error: "optuna search only supported with standard engine" };
  }

  const strategyInfo = listStrategyCatalog().find((entry) => entry.name === strategy);
  if (strategyInfo && ((search === "grid" && !strategyInfo.grid) ||
      (search === "optuna" && !strategyInfo.optuna) ||
      (engine === "fast" && !strategyInfo.fast) ||
      (engine === "gpu" && !strategyInfo.gpu))) {
    return { ok: false, error: `strategy ${strategy} does not support ${search}/${engine}` };
  }

  const checked = validateRunOverrides(input.overrides, baseEnv);
  if (checked.error) return { ok: false, error: checked.error };
  const overrides = { ...checked.overrides };
  if (input.searchSpace !== undefined) {
    if (search !== "optuna" || !strategyInfo || !input.searchSpace ||
        typeof input.searchSpace !== "object" || Array.isArray(input.searchSpace)) {
      return { ok: false, error: "invalid Optuna search space" };
    }
    const searchSpace = input.searchSpace as Record<string, unknown>;
    const accepted: Record<string, [number, number]> = {};
    for (const [key, value] of Object.entries(searchSpace)) {
      const original = strategyInfo.parameterSpace[key];
      if (!original || !Array.isArray(value) || value.length !== 2) return { ok: false, error: `invalid Optuna bounds: ${key}` };
      const [lo, hi] = value;
      const integer = original[2].startsWith("int");
      if (typeof lo !== "number" || typeof hi !== "number" || !Number.isFinite(lo) || !Number.isFinite(hi) ||
          (integer && (!Number.isInteger(lo) || !Number.isInteger(hi))) ||
          lo < original[0] || hi > original[1] || lo > hi ||
          (original[2].endsWith("_log") && lo <= 0)) {
        return { ok: false, error: `invalid Optuna bounds: ${key}` };
      }
      accepted[key] = [lo, hi];
    }
    if (Object.keys(accepted).length) overrides.OPTUNA_SPACE = JSON.stringify(accepted);
  }
  if (dataset) {
    const match = /^ohlc_([A-Za-z0-9]+)_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.csv$/.exec(dataset);
    if (!match || !fs.existsSync(path.join(dataRoot, symbol, "ohlc", dataset))) {
      return { ok: false, error: "dataset not available for symbol" };
    }
    overrides.TIMEFRAME = match[1];
    overrides.START_DATE = match[2];
    overrides.END_DATE = match[3];
  }

  return {
    ok: true,
    data: {
      symbol,
      strategy,
      engine,
      search,
      nTrials: nTrialsNum,
      jobs: jobsNum,
      validationMode,
      ...(dataset ? { dataset } : {}),
      ...(Object.keys(overrides).length ? { overrides } : {}),
    },
  };
}

export { ENGINES, SEARCH_METHODS, VALIDATION_MODES, listStrategies, listSymbols };
