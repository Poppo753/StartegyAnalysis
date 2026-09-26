/**
 * reportData.ts — Pure dashboard logic for Fase 8 (F8-U02/U03/U04).
 *
 * Zero dependencies (stdlib only). All functions are pure and unit-tested in
 * `reportData.test.ts`. No pixels asserted: numeric/logic DoDs only.
 *
 * Data realities this module respects (grounded, not assumed):
 * - summary CSV schemas DIFFER per engine: standard (results_writer.py) has
 *   strategy/sortino/calmar/expectancy (no sharpe_ratio); fast summaries have
 *   symbol/engine/total_pnl(_percent)/max_drawdown (no sharpe/sortino/calmar);
 *   gpu summaries have sharpe_ratio/score (no symbol). Hence every accessor is
 *   column-tolerant: missing metric columns degrade, never crash.
 * - metrics.py convention: signal-only mode -> series on `pnl_percent`,
 *   otherwise on `pnl` (flat USDT equity in signal-only would mislead).
 */

export type Cell = string | number;
export interface DataRow {
  [col: string]: Cell;
}

export type EquityMode = "signal-only" | "pnl";

/** Parse a CSV string (quote-aware) with numeric coercion. Empty -> []. */
export function parseCsv(text: string): DataRow[] {
  const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length < 2) return [];
  const headers = splitCsvLine(lines[0]).map((h) => h.trim());
  const rows: DataRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const cells = splitCsvLine(lines[i]);
    const row: DataRow = {};
    for (let c = 0; c < headers.length; c++) {
      const raw = (cells[c] ?? "").trim();
      row[headers[c]] = coerceCell(raw);
    }
    rows.push(row);
  }
  return rows;
}

function splitCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        cur += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}

function coerceCell(raw: string): Cell {
  if (raw === "") return raw;
  const n = Number(raw);
  return raw.trim() !== "" && Number.isFinite(n) ? n : raw;
}

/** Numeric accessor; NaN when the column is missing/non-numeric. */
export function num(row: DataRow, key: string): number {
  const v = row[key];
  if (typeof v === "number") return v;
  if (typeof v === "string" && v.trim() !== "") {
    const n = Number(v);
    if (Number.isFinite(n)) return n;
  }
  return NaN;
}

/**
 * Pick the per-trade PnL series per the metrics.py convention:
 * signal-only -> `pnl_percent`, else `pnl`. Missing column -> [] (never throw).
 */
export function pnlSeries(tradeRows: DataRow[], mode: EquityMode): number[] {
  const key = mode === "signal-only" ? "pnl_percent" : "pnl";
  const out: number[] = [];
  for (const r of tradeRows) {
    const v = num(r, key);
    if (Number.isFinite(v)) out.push(v);
  }
  return out;
}

export interface EquityCurve {
  /** Cumulative sum starting at 0: equity[i] = sum(pnls[0..i]). */
  equity: number[];
  /** Underwater at each point: running peak minus equity, floored at 0. */
  drawdown: number[];
  maxDrawdown: number;
}

/** Build equity + underwater curves from a per-trade PnL series. */
export function buildEquityCurve(pnls: number[]): EquityCurve {
  const equity: number[] = [];
  const drawdown: number[] = [];
  let cum = 0;
  let peak = 0;
  let maxDd = 0;
  for (const p of pnls) {
    cum += p;
    equity.push(cum);
    if (cum > peak) peak = cum;
    const dd = Math.max(0, peak - cum);
    drawdown.push(dd);
    if (dd > maxDd) maxDd = dd;
  }
  return { equity, drawdown, maxDrawdown: maxDd };
}

export interface EquityCheck {
  finalEquity: number;
  /** total_pnl_percent in signal-only, else total_pnl (metrics.py convention). */
  expected: number;
  match: boolean;
}

/**
 * F8-U02 numeric DoD: final equity === summary total (within tol).
 * Summary CSVs round to 4dp, so error grows with trade count; default tol 0.05.
 */
export function equityMatchesSummary(
  tradeRows: DataRow[],
  summaryRow: DataRow,
  mode: EquityMode,
  tol = 0.05,
): EquityCheck {
  const series = pnlSeries(tradeRows, mode);
  const finalEquity = series.reduce((a, b) => a + b, 0);
  const expected = num(
    summaryRow,
    mode === "signal-only" ? "total_pnl_percent" : "total_pnl",
  );
  const match =
    Number.isFinite(expected) && Math.abs(finalEquity - expected) <= tol;
  return { finalEquity, expected, match };
}

export interface Heatmap {
  xParam: string;
  yParam: string;
  metric: string;
  xVals: number[];
  yVals: number[];
  /** grid[j][i] = mean(metric) at (xVals[i], yVals[j]), null when no rows. */
  grid: (number | null)[][];
}

/**
 * Generic 2-param heatmap (F8-U03): params are NOT hardcoded — any two numeric
 * columns work (e.g. x_percent x z_percent for momentum, ma_period x
 * z_threshold for mean_reversion). Metric is any numeric column
 * (total_pnl / sharpe_ratio / sortino_ratio ...). Cells aggregate by mean.
 */
export function buildHeatmap(
  rows: DataRow[],
  xParam: string,
  yParam: string,
  metric: string,
): Heatmap {
  const xSet = new Set<number>();
  const ySet = new Set<number>();
  const buckets = new Map<string, number[]>();
  for (const r of rows) {
    const x = num(r, xParam);
    const y = num(r, yParam);
    const m = num(r, metric);
    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(m))
      continue;
    xSet.add(x);
    ySet.add(y);
    const k = `${x}|||${y}`;
    const b = buckets.get(k);
    if (b) b.push(m);
    else buckets.set(k, [m]);
  }
  const xVals = [...xSet].sort((a, b) => a - b);
  const yVals = [...ySet].sort((a, b) => a - b);
  const grid: (number | null)[][] = yVals.map((y) =>
    xVals.map((x) => {
      const b = buckets.get(`${x}|||${y}`);
      if (!b || b.length === 0) return null;
      return b.reduce((a, v) => a + v, 0) / b.length;
    }),
  );
  return { xParam, yParam, metric, xVals, yVals, grid };
}

export interface StrategyFilter {
  strategy?: string;
  regime?: string;
  minTrades?: number;
  minSharpe?: number;
  maxDd?: number;
}

/**
 * Filterable/sortable strategy table (F8-U03).
 * Column-tolerant: a criterion whose column is absent from a row does NOT
 * exclude that row (fast/gpu CSVs lack sharpe_ratio/regime/strategy). Such
 * degradation is documented in the UI; filtering on unavailable data must
 * never silently empty the view.
 */
export function filterStrategies(
  rows: DataRow[],
  f: StrategyFilter,
): DataRow[] {
  return rows.filter((r) => {
    if (f.strategy !== undefined && f.strategy !== "") {
      const s = String(r["strategy"] ?? "");
      if (s !== "" && s.toLowerCase() !== f.strategy.toLowerCase()) return false;
    }
    if (f.regime !== undefined && f.regime !== "") {
      const g = String(r["regime"] ?? "");
      if (g !== "" && g.toLowerCase() !== f.regime.toLowerCase()) return false;
    }
    if (f.minTrades !== undefined && Number.isFinite(f.minTrades)) {
      const t = num(r, "total_trades");
      if (Number.isFinite(t) && t < f.minTrades) return false;
    }
    if (f.minSharpe !== undefined && Number.isFinite(f.minSharpe)) {
      const s = num(r, "sharpe_ratio");
      if (Number.isFinite(s) && s < f.minSharpe) return false;
    }
    if (f.maxDd !== undefined && Number.isFinite(f.maxDd)) {
      const d = num(r, "max_drawdown");
      if (Number.isFinite(d) && d > f.maxDd) return false;
    }
    return true;
  });
}

/** Sort rows by a column (numeric when possible, else lexicographic). */
export function sortRows(
  rows: DataRow[],
  key: string,
  dir: "asc" | "desc" = "desc",
): DataRow[] {
  const sign = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const an = num(a, key);
    const bn = num(b, key);
    if (Number.isFinite(an) && Number.isFinite(bn)) return (an - bn) * sign;
    return String(a[key] ?? "").localeCompare(String(b[key] ?? "")) * sign;
  });
}

/** CSV export of the current view (F8-U03). */
export function toCsv(rows: DataRow[]): string {
  if (rows.length === 0) return "";
  const headers = Object.keys(rows[0]);
  const esc = (v: Cell): string => {
    const s = String(v ?? "");
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [
    headers.join(","),
    ...rows.map((r) => headers.map((h) => esc(r[h] ?? "")).join(",")),
  ].join("\n");
}

export interface ReportPboDsr {
  pbo: number;
  pboVerdict: string;
  dsr: number;
  nTrials: number;
}

export interface ReportRegime {
  current: string;
  detail: string;
}

export interface ReportInput {
  /** Free-form config snapshot (symbol, dates, engine, direction ...). */
  config: DataRow;
  /** Summary rows; top-N by total_pnl is derived inside. */
  summaryRows: DataRow[];
  topN?: number;
  equity: (EquityCurve & EquityCheck & { mode: EquityMode }) | null;
  heatmap: Heatmap | null;
  /** F3 section: null -> renders "not available". */
  pboDsr?: ReportPboDsr | null;
  /** F5 section: null -> renders "not available". */
  regime?: ReportRegime | null;
}

function escHtml(v: unknown): string {
  return String(v ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function section(title: string, body: () => string): string {
  try {
    return `<section><h2>${escHtml(title)}</h2>${body()}</section>`;
  } catch (e) {
    return `<section><h2>${escHtml(title)}</h2><p>unavailable: ${escHtml(
      e instanceof Error ? e.message : String(e),
    )}</p></section>`;
  }
}

function sparkline(values: number[], w = 560, h = 120): string {
  if (values.length === 0) return "<p>(no equity points)</p>";
  const step = Math.max(1, Math.floor(values.length / 200));
  const pts: number[] = [];
  for (let i = 0; i < values.length; i += step) pts.push(values[i]);
  if (pts[pts.length - 1] !== values[values.length - 1])
    pts.push(values[values.length - 1]);
  const lo = Math.min(...pts);
  const hi = Math.max(...pts);
  const span = hi - lo > 0 ? hi - lo : 1;
  const path = pts
    .map(
      (v, i) =>
        `${((i / Math.max(1, pts.length - 1)) * w).toFixed(1)},${(
          h - ((v - lo) / span) * (h - 8) - 4
        ).toFixed(1)}`,
    )
    .join(" ");
  return `<svg width="${w}" height="${h}" role="img" aria-label="equity curve"><polyline points="${path}" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>`;
}

/**
 * Full HTML report (F8-U04). Graceful degradation: F3 (PBO/DSR) and F5
 * (regime) sections render "not available" when their inputs are absent.
 * Never throws for missing data.
 */
export function buildReportHtml(input: ReportInput): string {
  const topN = input.topN ?? 10;
  const top = sortRows(input.summaryRows, "total_pnl", "desc").slice(0, topN);
  const parts: string[] = [
    "<!doctype html><html><head><meta charset=\"utf-8\">" +
      "<title>Backtest report</title></head><body><h1>Backtest report</h1>",
  ];

  parts.push(
    section("Config", () => {
      const rows = Object.entries(input.config ?? {})
        .map(([k, v]) => `<tr><td>${escHtml(k)}</td><td>${escHtml(v)}</td></tr>`)
        .join("");
      return rows === "" ? "<p>not available</p>" : `<table>${rows}</table>`;
    }),
  );

  parts.push(
    section(`Top-${topN} strategies`, () => {
      if (top.length === 0) return "<p>not available (no summary rows)</p>";
      const headers = Object.keys(top[0]);
      const head = `<tr>${headers.map((h) => `<th>${escHtml(h)}</th>`).join("")}</tr>`;
      const body = top
        .map(
          (r) =>
            `<tr>${headers.map((h) => `<td>${escHtml(r[h] ?? "")}</td>`).join("")}</tr>`,
        )
        .join("");
      return `<table>${head}${body}</table>`;
    }),
  );

  parts.push(
    section("Equity / drawdown", () => {
      const e = input.equity;
      if (!e) return "<p>not available (no trades file selected)</p>";
      return (
        `<p>mode=${escHtml(e.mode)} final=${e.finalEquity.toFixed(4)} ` +
        `expected=${Number.isFinite(e.expected) ? e.expected.toFixed(4) : "n/a"} ` +
        `match=${e.match} maxDD=${e.maxDrawdown.toFixed(4)}</p>` +
        sparkline(e.equity)
      );
    }),
  );

  parts.push(
    section("Parameter heatmap", () => {
      const hm = input.heatmap;
      if (!hm || hm.xVals.length === 0 || hm.yVals.length === 0)
        return "<p>not available (no heatmap data)</p>";
      const head =
        `<tr><th>${escHtml(hm.yParam)} \\ ${escHtml(hm.xParam)}</th>` +
        hm.xVals.map((x) => `<th>${escHtml(x)}</th>`).join("") +
        "</tr>";
      const body = hm.yVals
        .map(
          (y, j) =>
            `<tr><td>${escHtml(y)}</td>` +
            hm.grid[j]
              .map((c) => `<td>${c === null ? "—" : escHtml(c.toFixed(4))}</td>`)
              .join("") +
            "</tr>",
        )
        .join("");
      return `<p>metric=${escHtml(hm.metric)}</p><table>${head}${body}</table>`;
    }),
  );

  parts.push(
    section("Validation — PBO / DSR (F3)", () => {
      const v = input.pboDsr ?? null;
      if (!v)
        return "<p>not available (F3 validation not run for this symbol)</p>";
      return `<p>PBO=${escHtml(v.pbo)} verdict=${escHtml(v.pboVerdict)} DSR=${escHtml(v.dsr)} N_trials=${escHtml(v.nTrials)}</p>`;
    }),
  );

  parts.push(
    section("Regime (F5)", () => {
      const g = input.regime ?? null;
      if (!g)
        return "<p>not available (F5 meta-analysis not run for this symbol)</p>";
      return `<p>current=${escHtml(g.current)} — ${escHtml(g.detail)}</p>`;
    }),
  );

  parts.push("</body></html>");
  return parts.join("\n");
}

/** Synthetic fallback rows when backtest-results/ is empty (documented mock). */
export function mockSummaryRows(): DataRow[] {
  return [
    { strategy: "momentum_drop", x_percent: 1.2, y_seconds: 5, z_percent: 1.5, total_trades: 192, total_pnl: 20.5849, total_pnl_percent: 20.5849, max_drawdown: 1.6287, sharpe_ratio: 1.1, regime: "TRENDING" },
    { strategy: "momentum_drop", x_percent: 1.0, y_seconds: 5, z_percent: 1.5, total_trades: 379, total_pnl: 15.2388, total_pnl_percent: 15.2388, max_drawdown: 3.1688, sharpe_ratio: 0.8, regime: "RANGING" },
    { strategy: "mean_reversion", ma_period: 50, z_threshold: 1.5, total_trades: 64, total_pnl: 9.41, total_pnl_percent: 9.41, max_drawdown: 2.2, sharpe_ratio: 1.4, regime: "RANGING" },
  ];
}

/** Synthetic fallback trades matching mockSummaryRows()[0] totals. */
export function mockTradeRows(): DataRow[] {
  return [
    { pnl: 12.0, pnl_percent: 12.0 },
    { pnl: -2.5, pnl_percent: -2.5 },
    { pnl: 11.0849, pnl_percent: 11.0849 },
  ];
}
