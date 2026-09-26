/**
 * lib/validateRun.test.ts — Unit tests for validateRun (U1-01).
 */
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { validateRunInput, ENGINES, SEARCH_METHODS, VALIDATION_MODES } from "./validateRun";

function makeTmpDataRoot(): string {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "validateRun-test-"));
  fs.mkdirSync(path.join(tmp, "DCRUSDT"), { recursive: true });
  fs.mkdirSync(path.join(tmp, "BTCUSDT"), { recursive: true });
  return tmp;
}

function cleanup(tmp: string): void {
  fs.rmSync(tmp, { recursive: true, force: true });
}

describe("validateRunInput", () => {
  let dataRoot: string;

  beforeEach(() => {
    dataRoot = makeTmpDataRoot();
  });

  afterEach(() => {
    cleanup(dataRoot);
  });

  test("valid input passes", () => {
    const res = validateRunInput({
      symbol: "DCRUSDT",
      strategy: "momentum_drop",
      engine: "standard",
      search: "grid",
      nTrials: 30,
      jobs: 1,
      validationMode: "off",
    }, dataRoot);
    expect(res.ok).toBe(true);
    expect(res.data).toEqual({
      symbol: "DCRUSDT",
      strategy: "momentum_drop",
      engine: "standard",
      search: "grid",
      nTrials: 30,
      jobs: 1,
      validationMode: "off",
    });
  });

  test("an exact nested dataset overrides timeframe and dates for this run", () => {
    const dataset = "ohlc_5m_2026-02-01_2026-02-02.csv";
    fs.mkdirSync(path.join(dataRoot, "DCRUSDT", "ohlc"));
    fs.writeFileSync(path.join(dataRoot, "DCRUSDT", "ohlc", dataset), "a,b\n");
    const res = validateRunInput({ symbol: "DCRUSDT", dataset, strategy: "momentum_drop",
      engine: "standard", search: "grid", nTrials: 2, jobs: 1, validationMode: "off",
      overrides: { X_VALUES: "0.2,0.5" } }, dataRoot);
    expect(res.ok).toBe(true);
    expect(res.data?.overrides).toMatchObject({ X_VALUES: "0.2,0.5", X_RANGE: "",
      TIMEFRAME: "5m", START_DATE: "2026-02-01", END_DATE: "2026-02-02" });
    expect(validateRunInput({ symbol: "DCRUSDT", dataset: "ohlc_5m_2026-02-03_2026-02-04.csv",
      strategy: "momentum_drop", engine: "standard", search: "grid", nTrials: 2,
      jobs: 1, validationMode: "off" }, dataRoot).error).toMatch(/dataset not available/);
  });

  test("only runnable strategies and compatible engines are accepted", () => {
    const base = { symbol: "DCRUSDT", engine: "standard", search: "grid",
      nTrials: 2, jobs: 1, validationMode: "off" };
    expect(validateRunInput({ ...base, strategy: "mia" }, dataRoot).error).toMatch(/invalid strategy/);
    expect(validateRunInput({ ...base, strategy: "mean_reversion", engine: "fast" }, dataRoot).error)
      .toMatch(/does not support/);
  });

  test("Optuna bounds are checked against the strategy parameter space", () => {
    const base = { symbol: "DCRUSDT", strategy: "mean_reversion", engine: "standard",
      search: "optuna", nTrials: 2, jobs: 1, validationMode: "off" };
    const valid = validateRunInput({ ...base, searchSpace: { ma_period: [20, 50] } }, dataRoot);
    expect(valid.ok).toBe(true);
    expect(valid.data?.overrides?.OPTUNA_SPACE).toBe('{"ma_period":[20,50]}');
    expect(validateRunInput({ ...base, searchSpace: { ma_period: [1, 50] } }, dataRoot).error)
      .toMatch(/invalid Optuna bounds/);
    expect(validateRunInput({ ...base, searchSpace: { unknown: [1, 2] } }, dataRoot).error)
      .toMatch(/invalid Optuna bounds/);
  });

  test("invalid symbol fails", () => {
    const res = validateRunInput({
      symbol: "INVALID",
      strategy: "momentum_drop",
      engine: "standard",
      search: "grid",
      nTrials: 30,
      jobs: 1,
      validationMode: "off",
    }, dataRoot);
    expect(res.ok).toBe(false);
    expect(res.error).toMatch(/invalid symbol/);
  });

  test("invalid strategy fails", () => {
    const res = validateRunInput({
      symbol: "DCRUSDT",
      strategy: "unknown_strategy",
      engine: "standard",
      search: "grid",
      nTrials: 30,
      jobs: 1,
      validationMode: "off",
    }, dataRoot);
    expect(res.ok).toBe(false);
    expect(res.error).toMatch(/invalid strategy/);
  });

  test("invalid engine fails", () => {
    const res = validateRunInput({
      symbol: "DCRUSDT",
      strategy: "momentum_drop",
      engine: "quantum",
      search: "grid",
      nTrials: 30,
      jobs: 1,
      validationMode: "off",
    }, dataRoot);
    expect(res.ok).toBe(false);
    expect(res.error).toMatch(/invalid engine/);
  });

  test("invalid search fails", () => {
    const res = validateRunInput({
      symbol: "DCRUSDT",
      strategy: "momentum_drop",
      engine: "standard",
      search: "random",
      nTrials: 30,
      jobs: 1,
      validationMode: "off",
    }, dataRoot);
    expect(res.ok).toBe(false);
    expect(res.error).toMatch(/invalid search/);
  });

  test("invalid validationMode fails", () => {
    const res = validateRunInput({
      symbol: "DCRUSDT",
      strategy: "momentum_drop",
      engine: "standard",
      search: "grid",
      nTrials: 30,
      jobs: 1,
      validationMode: "kfold",
    }, dataRoot);
    expect(res.ok).toBe(false);
    expect(res.error).toMatch(/invalid validationMode/);
  });

  test("nTrials out of range fails", () => {
    const res = validateRunInput({
      symbol: "DCRUSDT",
      strategy: "momentum_drop",
      engine: "standard",
      search: "grid",
      nTrials: 0,
      jobs: 1,
      validationMode: "off",
    }, dataRoot);
    expect(res.ok).toBe(false);
    expect(res.error).toMatch(/nTrials must be an integer between 1 and 5000/);
  });

  test("nTrials too high fails", () => {
    const res = validateRunInput({
      symbol: "DCRUSDT",
      strategy: "momentum_drop",
      engine: "standard",
      search: "grid",
      nTrials: 5001,
      jobs: 1,
      validationMode: "off",
    }, dataRoot);
    expect(res.ok).toBe(false);
    expect(res.error).toMatch(/nTrials must be an integer between 1 and 5000/);
  });

  test("jobs out of range fails", () => {
    const res = validateRunInput({
      symbol: "DCRUSDT",
      strategy: "momentum_drop",
      engine: "standard",
      search: "grid",
      nTrials: 30,
      jobs: 9,
      validationMode: "off",
    }, dataRoot);
    expect(res.ok).toBe(false);
    expect(res.error).toMatch(/jobs must be an integer between 1 and 8/);
  });

  test("optuna with non-standard engine fails", () => {
    const res = validateRunInput({
      symbol: "DCRUSDT",
      strategy: "momentum_drop",
      engine: "fast",
      search: "optuna",
      nTrials: 30,
      jobs: 1,
      validationMode: "off",
    }, dataRoot);
    expect(res.ok).toBe(false);
    expect(res.error).toMatch(/optuna search only supported with standard engine/);
  });

  describe("injection attempts", () => {
    const injectionPayloads = [
      "; rm -rf /",
      "&& cat /etc/passwd",
      "$(cat /etc/passwd)",
      "`cat /etc/passwd`",
      "--extra-flag",
      "value;echo hacked",
      "value&&echo hacked",
      "value$(echo hacked)",
      "value`echo hacked`",
      "value--extra",
    ];

    for (const payload of injectionPayloads) {
      test(`rejects injection in symbol: ${payload}`, () => {
        const res = validateRunInput({
          symbol: payload,
          strategy: "momentum_drop",
          engine: "standard",
          search: "grid",
          nTrials: 30,
          jobs: 1,
          validationMode: "off",
        }, dataRoot);
        expect(res.ok).toBe(false);
        expect(res.error).toMatch(/injection attempt/);
      });

      test(`rejects injection in strategy: ${payload}`, () => {
        const res = validateRunInput({
          symbol: "DCRUSDT",
          strategy: payload,
          engine: "standard",
          search: "grid",
          nTrials: 30,
          jobs: 1,
          validationMode: "off",
        }, dataRoot);
        expect(res.ok).toBe(false);
        expect(res.error).toMatch(/injection attempt/);
      });

      test(`rejects injection in engine: ${payload}`, () => {
        const res = validateRunInput({
          symbol: "DCRUSDT",
          strategy: "momentum_drop",
          engine: payload,
          search: "grid",
          nTrials: 30,
          jobs: 1,
          validationMode: "off",
        }, dataRoot);
        expect(res.ok).toBe(false);
        expect(res.error).toMatch(/injection attempt/);
      });

      test(`rejects injection in search: ${payload}`, () => {
        const res = validateRunInput({
          symbol: "DCRUSDT",
          strategy: "momentum_drop",
          engine: "standard",
          search: payload,
          nTrials: 30,
          jobs: 1,
          validationMode: "off",
        }, dataRoot);
        expect(res.ok).toBe(false);
        expect(res.error).toMatch(/injection attempt/);
      });

      test(`rejects injection in validationMode: ${payload}`, () => {
        const res = validateRunInput({
          symbol: "DCRUSDT",
          strategy: "momentum_drop",
          engine: "standard",
          search: "grid",
          nTrials: 30,
          jobs: 1,
          validationMode: payload,
        }, dataRoot);
        expect(res.ok).toBe(false);
        expect(res.error).toMatch(/injection attempt/);
      });
    }

    test("rejects injection in nTrials string", () => {
      const res = validateRunInput({
        symbol: "DCRUSDT",
        strategy: "momentum_drop",
        engine: "standard",
        search: "grid",
        nTrials: "30; rm -rf /",
        jobs: 1,
        validationMode: "off",
      }, dataRoot);
      expect(res.ok).toBe(false);
      expect(res.error).toMatch(/injection attempt/);
    });

    test("rejects injection in jobs string", () => {
      const res = validateRunInput({
        symbol: "DCRUSDT",
        strategy: "momentum_drop",
        engine: "standard",
        search: "grid",
        nTrials: 30,
        jobs: "1 && rm -rf /",
        validationMode: "off",
      }, dataRoot);
      expect(res.ok).toBe(false);
      expect(res.error).toMatch(/injection attempt/);
    });
  });
});

describe("constants", () => {
  test("ENGINES includes standard, fast, gpu", () => {
    expect(ENGINES).toEqual(["standard", "fast", "gpu"]);
  });

  test("SEARCH_METHODS includes grid, optuna", () => {
    expect(SEARCH_METHODS).toEqual(["grid", "optuna"]);
  });

  test("VALIDATION_MODES includes off, purged, cpcv, walkforward", () => {
    expect(VALIDATION_MODES).toEqual(["off", "purged", "cpcv", "walkforward"]);
  });
});
