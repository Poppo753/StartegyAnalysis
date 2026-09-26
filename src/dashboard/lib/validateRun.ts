/**
 * lib/validateRun.ts — Input validation for run creation (U1-01).
 *
 * Allowlist flags: engine, strategy, symbol, search, nTrials, jobs, validationMode.
 * Types/ranges enforced. Injection rejection (; && $() backtick extra --).
 */
import * as fs from "fs";
import * as path from "path";

export interface ValidatedRunInput {
  symbol: string;
  strategy: string;
  engine: string;
  search: string;
  nTrials: number;
  jobs: number;
  validationMode: string;
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
  const strategiesDir = path.resolve(__dirname, "..", "..", "..", "python-backtester", "src", "strategies");
  if (!fs.existsSync(strategiesDir)) return [];
  return fs.readdirSync(strategiesDir)
    .filter((f) => f.endsWith(".py") && f !== "__init__.py")
    .map((f) => f.replace(/\.py$/, ""));
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
  dataRoot: string
): ValidationResult {
  const symbol = String(input.symbol ?? "").trim();
  const strategy = String(input.strategy ?? "").trim();
  const engine = String(input.engine ?? "").trim();
  const search = String(input.search ?? "").trim();
  const nTrials = input.nTrials;
  const jobs = input.jobs;
  const validationMode = String(input.validationMode ?? "").trim();

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
    },
  };
}

export { ENGINES, SEARCH_METHODS, VALIDATION_MODES, listStrategies, listSymbols };