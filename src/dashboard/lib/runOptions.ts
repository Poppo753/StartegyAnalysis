/** Per-run overrides for settings already supported by Python's load_config(). */
export type OptionType = "int" | "float" | "enum" | "bool" | "list-int" | "list-float" | "range-int" | "range-float" | "study-db";

export interface RunOptionSpec {
  key: string;
  label: string;
  group: "grid" | "trading" | "engine" | "filters";
  type: OptionType;
  min?: number;
  max?: number;
  values?: string[];
  hint?: string;
  current?: string;
  strategies?: string[];
  engines?: string[];
  searches?: string[];
  optunaParameter?: string;
}

export const RUN_OPTIONS: RunOptionSpec[] = [
  { key: "X_VALUES", label: "Valori X (%)", group: "grid", type: "list-float", min: 0.000001, strategies: ["momentum_drop"], engines: ["standard", "fast", "gpu"], searches: ["grid"], hint: "Numeri separati da virgola, es. 0.2,0.5,1" },
  { key: "Y_VALUES", label: "Valori Y (secondi)", group: "grid", type: "list-int", min: 1, strategies: ["momentum_drop"], searches: ["grid"], hint: "Es. 10,30,60" },
  { key: "Z_VALUES", label: "Valori Z (%)", group: "grid", type: "list-float", min: 0.000001, strategies: ["momentum_drop"], searches: ["grid"], hint: "Es. 0.1,0.2,0.5" },
  { key: "MA_PERIODS", label: "Periodi media mobile", group: "grid", type: "list-int", min: 2, strategies: ["mean_reversion"], searches: ["grid"], hint: "Es. 10,20" },
  { key: "Z_THRESHOLDS", label: "Soglie Z-score", group: "grid", type: "list-float", min: 0.000001, strategies: ["mean_reversion"], searches: ["grid"], hint: "Es. 1,2" },
  { key: "X_RANGE", label: "Intervallo X", group: "grid", type: "range-float", min: 0.000001, strategies: ["momentum_drop"], searches: ["grid"], hint: "Alternativa ai valori X: inizio:fine:passo" },
  { key: "Y_RANGE", label: "Intervallo Y", group: "grid", type: "range-int", min: 1, strategies: ["momentum_drop"], searches: ["grid"], hint: "Alternativa ai valori Y: inizio:fine:passo" },
  { key: "Z_RANGE", label: "Intervallo Z", group: "grid", type: "range-float", min: 0.000001, strategies: ["momentum_drop"], searches: ["grid"], hint: "Alternativa ai valori Z: inizio:fine:passo" },
  { key: "Y_DYNAMIC", label: "Y dinamico", group: "grid", type: "bool", strategies: ["momentum_drop"], searches: ["grid"] },
  { key: "Y_MAX_WINDOW", label: "Finestra Y massima (s)", group: "grid", type: "int", min: 1, max: 10000000, strategies: ["momentum_drop"], engines: ["gpu"], searches: ["grid"] },
  { key: "MAX_HOLD_SECONDS", label: "Durata massima trade (s)", group: "trading", type: "int", min: 1, max: 10000000, optunaParameter: "max_hold_seconds" },
  { key: "INITIAL_CAPITAL", label: "Capitale iniziale", group: "trading", type: "float", min: 0.000001, max: 1000000000000 },
  { key: "POSITION_SIZE", label: "Dimensione posizione", group: "trading", type: "float", min: 0.000001, max: 1000000000000, optunaParameter: "position_size" },
  { key: "FEE_RATE", label: "Commissione (quota)", group: "trading", type: "float", min: 0, max: 1, optunaParameter: "fee_rate", hint: "0.001 = 0,1%" },
  { key: "SLIPPAGE_RATE", label: "Slippage (quota)", group: "trading", type: "float", min: 0, max: 1, optunaParameter: "slippage_rate", hint: "0.0005 = 0,05%" },
  { key: "DIRECTION", label: "Direzione", group: "trading", type: "enum", values: ["signal-only", "long", "short"], strategies: ["momentum_drop"] },
  { key: "FAST_TOP_N", label: "Migliori risultati", group: "engine", type: "int", min: 1, max: 10000, engines: ["fast", "gpu"] },
  { key: "GPU_BATCH_SIZE", label: "Dimensione batch GPU", group: "engine", type: "int", min: 1, max: 1000000, engines: ["gpu"] },
  { key: "TRAIN_RATIO", label: "Quota training", group: "engine", type: "float", min: 0, max: 1, engines: ["gpu"] },
  { key: "VALIDATION_RATIO", label: "Quota validazione", group: "engine", type: "float", min: 0, max: 1, engines: ["gpu"] },
  { key: "OPTUNA_STUDY_DB", label: "Database studio Optuna", group: "engine", type: "study-db", searches: ["optuna"], hint: "Nome file .db nella cartella del backtester" },
  { key: "MIN_TRADES", label: "Trade minimi", group: "filters", type: "int", min: 0, max: 100000000, engines: ["gpu"] },
  { key: "MIN_WIN_RATE", label: "Win rate minimo (%)", group: "filters", type: "float", min: 0, max: 100, engines: ["gpu"] },
  { key: "MIN_PROFIT_FACTOR", label: "Profit factor minimo", group: "filters", type: "float", min: 0, max: 1000000, engines: ["gpu"] },
  { key: "MAX_DRAWDOWN_FILTER", label: "Drawdown massimo (%)", group: "filters", type: "float", min: 0, max: 1000000, engines: ["gpu"] },
  { key: "SKIP_FILTERS", label: "Salta filtri", group: "filters", type: "bool", engines: ["gpu"] },
];

function parseNumeric(value: string, spec: RunOptionSpec, integer: boolean): string | null {
  const number = Number(value);
  if (!value.trim() || !Number.isFinite(number) || (integer && !Number.isInteger(number)) ||
      (spec.min !== undefined && number < spec.min) || (spec.max !== undefined && number > spec.max)) {
    return `${spec.label}: valore non valido`;
  }
  return null;
}

export function validateRunOverrides(raw: unknown, baseEnv: Record<string, string> = {}): { overrides?: Record<string, string>; error?: string } {
  if (raw === undefined || raw === null) return {};
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return { error: "overrides must be an object" };
  const input = raw as Record<string, unknown>;
  const specs = new Map(RUN_OPTIONS.map((spec) => [spec.key, spec]));
  const overrides: Record<string, string> = {};
  for (const [key, value] of Object.entries(input)) {
    const spec = specs.get(key);
    if (!spec) return { error: `unsupported run option: ${key}` };
    if (typeof value !== "string" && typeof value !== "number" && typeof value !== "boolean") return { error: `${key}: invalid value` };
    const text = String(value).trim();
    if (text.length > 1000 || /[\r\n\0]/.test(text)) return { error: `${key}: invalid value` };
    if (!text) continue;
    if (spec.type === "int" || spec.type === "float") {
      const error = parseNumeric(text, spec, spec.type === "int");
      if (error) return { error };
    } else if (spec.type === "enum") {
      if (!spec.values?.includes(text)) return { error: `${spec.label}: scelta non valida` };
    } else if (spec.type === "bool") {
      if (text !== "true" && text !== "false") return { error: `${spec.label}: usare true o false` };
    } else if (spec.type === "study-db") {
      if (!/^[A-Za-z0-9_-]+\.db$/.test(text)) return { error: `${spec.label}: usare un nome file .db` };
    } else if (spec.type.startsWith("list-")) {
      const values = text.split(",").map((item) => item.trim());
      if (values.length > 100 || values.some((item) => parseNumeric(item, spec, spec.type === "list-int"))) {
        return { error: `${spec.label}: elenco non valido (massimo 100 valori)` };
      }
    } else if (spec.type.startsWith("range-")) {
      const parts = text.split(":");
      if (parts.length !== 3 || parts.some((item) => parseNumeric(item, spec, spec.type === "range-int"))) {
        return { error: `${spec.label}: usare inizio:fine:passo` };
      }
      const [start, end, step] = parts.map(Number);
      if (step <= 0 || start > end || (end - start) / step > 100) return { error: `${spec.label}: intervallo non valido (massimo 101 valori)` };
    }
    overrides[key] = text;
  }
  for (const axis of ["X", "Y", "Z"]) {
    if (overrides[`${axis}_VALUES`] && overrides[`${axis}_RANGE`]) return { error: `Specificare valori o intervallo ${axis}, non entrambi` };
    if (overrides[`${axis}_VALUES`]) overrides[`${axis}_RANGE`] = "";
  }
  const train = Number(overrides.TRAIN_RATIO ?? baseEnv.TRAIN_RATIO ?? "0.7");
  const validation = Number(overrides.VALIDATION_RATIO ?? baseEnv.VALIDATION_RATIO ?? "0.3");
  if (train + validation > 1.01) return { error: "TRAIN_RATIO + VALIDATION_RATIO supera 1" };
  return Object.keys(overrides).length ? { overrides } : {};
}
