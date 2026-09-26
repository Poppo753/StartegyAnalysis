import { validateRunOverrides } from "./runOptions";

describe("validateRunOverrides", () => {
  test("accepts a per-run grid and clears the configured range", () => {
    expect(validateRunOverrides({ X_VALUES: "0.2, 0.5", Y_RANGE: "10:30:10", FEE_RATE: "0.001" },
      { X_RANGE: "0.1:1:0.1" })).toEqual({ overrides: {
        X_VALUES: "0.2, 0.5", X_RANGE: "", Y_RANGE: "10:30:10", FEE_RATE: "0.001",
      } });
  });

  test("rejects unsupported options and malformed ranges", () => {
    expect(validateRunOverrides({ PYTHONPATH: "/tmp" }).error).toMatch(/unsupported/);
    expect(validateRunOverrides({ X_RANGE: "1:0.5:0.1" }).error).toMatch(/intervallo non valido/);
    expect(validateRunOverrides({ Y_RANGE: "1:1000:1" }).error).toMatch(/massimo 101/);
    expect(validateRunOverrides({ X_VALUES: "0.1", X_RANGE: "0.1:1:0.1" }).error).toMatch(/non entrambi/);
  });

  test("checks ratios with the values inherited from .env", () => {
    expect(validateRunOverrides({ TRAIN_RATIO: "0.8" }, { VALIDATION_RATIO: "0.3" }).error)
      .toMatch(/supera 1/);
    expect(validateRunOverrides({ TRAIN_RATIO: "0.6" }, { VALIDATION_RATIO: "0.3" }).error)
      .toBeUndefined();
  });
});
