/**
 * reportData.test.ts — Logic tests for F8-U02/U03/U04 (no pixels, no server).
 */
import * as fs from "fs";
import * as path from "path";
import {
  buildEquityCurve,
  buildHeatmap,
  buildReportHtml,
  DataRow,
  equityMatchesSummary,
  filterStrategies,
  mockSummaryRows,
  mockTradeRows,
  parseCsv,
  pnlSeries,
  sortRows,
  toCsv,
} from "./reportData";

function repoRoot(): string {
  // src/dashboard/reportData.test.ts -> repo root (works under ts-jest too).
  return path.resolve(__dirname, "..", "..");
}

describe("equity math (F8-U02)", () => {
  test("cumulative equity + underwater on synthetic series", () => {
    const c = buildEquityCurve([10, -5, 3]);
    expect(c.equity).toEqual([10, 5, 8]);
    expect(c.drawdown).toEqual([0, 5, 2]);
    expect(c.maxDrawdown).toBe(5);
  });

  test("empty series -> empty curves, zero drawdown", () => {
    const c = buildEquityCurve([]);
    expect(c.equity).toEqual([]);
    expect(c.drawdown).toEqual([]);
    expect(c.maxDrawdown).toBe(0);
  });

  test("metrics.py convention: signal-only uses pnl_percent, else pnl", () => {
    const trades: DataRow[] = [
      { pnl: 100, pnl_percent: 1.5 },
      { pnl: -50, pnl_percent: -0.5 },
    ];
    expect(pnlSeries(trades, "signal-only")).toEqual([1.5, -0.5]);
    expect(pnlSeries(trades, "pnl")).toEqual([100, -50]);
  });

  test("DoD numeric on REAL data: final equity === total_pnl of the CSV", () => {
    const base = path.join(
      repoRoot(),
      "python-backtester",
      "backtest-results",
      "DCRUSDT",
      "fast",
    );
    const trades = parseCsv(
      fs.readFileSync(
        path.join(base, "trades_best_001_x1.2_y5_z1.5.csv"),
        "utf8",
      ),
    );
    const summaries = parseCsv(
      fs.readFileSync(
        path.join(base, "summary_2026-01-01_2026-05-05.csv"),
        "utf8",
      ),
    );
    const summary = summaries.find(
      (r) => r["x_percent"] === 1.2 && r["y_seconds"] === 5 && r["z_percent"] === 1.5,
    );
    expect(summary).toBeDefined();
    // Equity on the `pnl` path (metrics.py non-signal-only convention).
    const check = equityMatchesSummary(trades, summary as DataRow, "pnl");
    expect(check.finalEquity).toBeCloseTo(20.5849, 2);
    expect(check.expected).toBeCloseTo(20.5849, 4);
    expect(check.match).toBe(true);
  });

  test("mock trades sum to mock summary total (signal-only)", () => {
    const check = equityMatchesSummary(
      mockTradeRows(),
      mockSummaryRows()[0],
      "signal-only",
    );
    expect(check.finalEquity).toBeCloseTo(20.5849, 4);
    expect(check.match).toBe(true);
  });
});

describe("filters + sort + CSV export (F8-U03)", () => {
  const rows: DataRow[] = [
    { strategy: "momentum_drop", regime: "TRENDING", total_trades: 200, sharpe_ratio: 1.2, max_drawdown: 2.0, total_pnl: 10 },
    { strategy: "momentum_drop", regime: "RANGING", total_trades: 30, sharpe_ratio: 0.4, max_drawdown: 8.0, total_pnl: 5 },
    { strategy: "mean_reversion", regime: "RANGING", total_trades: 64, sharpe_ratio: 1.5, max_drawdown: 2.2, total_pnl: 9 },
    { strategy: "mean_reversion", regime: "TRENDING", total_trades: 5, sharpe_ratio: -0.2, max_drawdown: 12.0, total_pnl: -3 },
  ];

  test("strategy filter", () => {
    expect(filterStrategies(rows, { strategy: "mean_reversion" })).toHaveLength(2);
  });

  test("regime filter", () => {
    const out = filterStrategies(rows, { regime: "ranging" });
    expect(out).toHaveLength(2);
    expect(out.every((r) => r["regime"] === "RANGING")).toBe(true);
  });

  test("min trades + min sharpe + max DD combine", () => {
    const out = filterStrategies(rows, {
      minTrades: 20,
      minSharpe: 1.0,
      maxDd: 5.0,
    });
    expect(out.map((r) => r["total_pnl"])).toEqual([10, 9]);
  });

  test("missing metric column degrades (row passes, never silently dropped)", () => {
    const noSharpe: DataRow[] = [{ strategy: "x", total_trades: 50 }];
    expect(filterStrategies(noSharpe, { minSharpe: 99 })).toHaveLength(1);
  });

  test("sort + CSV export round-trip", () => {
    const sorted = sortRows(rows, "total_pnl", "desc");
    expect(sorted.map((r) => r["total_pnl"])).toEqual([10, 9, 5, -3]);
    const csv = toCsv(sorted);
    const back = parseCsv(csv);
    expect(back).toHaveLength(4);
    expect(back[0]["total_pnl"]).toBe(10);
  });
});

describe("heatmap (F8-U03, generic params)", () => {
  test("momentum params: x_percent x z_percent, metric total_pnl", () => {
    const rows: DataRow[] = [
      { x_percent: 1.0, z_percent: 0.5, total_pnl: 4 },
      { x_percent: 1.0, z_percent: 0.5, total_pnl: 6 },
      { x_percent: 2.0, z_percent: 0.5, total_pnl: 1 },
      { x_percent: 1.0, z_percent: 1.5, total_pnl: 3 },
    ];
    const hm = buildHeatmap(rows, "x_percent", "z_percent", "total_pnl");
    expect(hm.xVals).toEqual([1, 2]);
    expect(hm.yVals).toEqual([0.5, 1.5]);
    expect(hm.grid[0][0]).toBeCloseTo(5); // mean of 4,6
    expect(hm.grid[0][1]).toBe(1);
    expect(hm.grid[1][1]).toBeNull(); // no rows
  });

  test("mean-reversion params: ma_period x z_threshold, metric sharpe_ratio", () => {
    const rows: DataRow[] = [
      { ma_period: 20, z_threshold: 1.0, sharpe_ratio: 0.9 },
      { ma_period: 50, z_threshold: 1.0, sharpe_ratio: 1.4 },
      { ma_period: 20, z_threshold: 2.0, sharpe_ratio: 0.2 },
    ];
    const hm = buildHeatmap(rows, "ma_period", "z_threshold", "sharpe_ratio");
    expect(hm.xVals).toEqual([20, 50]);
    expect(hm.yVals).toEqual([1, 2]);
    expect(hm.grid[0][1]).toBeCloseTo(1.4);
    expect(hm.grid[1][0]).toBeCloseTo(0.2);
  });
});

describe("report template (F8-U04)", () => {
  test("F1+F2-only inputs: F3/F5 degrade to 'not available', no crash", () => {
    const html = buildReportHtml({
      config: { symbol: "DCRUSDT", engine: "fast" },
      summaryRows: mockSummaryRows(),
      equity: null,
      heatmap: null,
      pboDsr: null,
      regime: null,
    });
    expect(html).toMatch("not available");
    expect(html).toMatch("Top-10");
    expect(html).not.toMatch("undefined");
  });

  test("full inputs render PBO/DSR + regime + equity", () => {
    const curve = buildEquityCurve([5, -1, 2]);
    const html = buildReportHtml({
      config: { symbol: "SMOKE" },
      summaryRows: mockSummaryRows(),
      topN: 2,
      equity: {
        ...curve,
        finalEquity: 6,
        expected: 6,
        match: true,
        mode: "pnl",
      },
      heatmap: buildHeatmap(mockSummaryRows(), "x_percent", "z_percent", "total_pnl"),
      pboDsr: { pbo: 0.08, pboVerdict: "SOLID", dsr: 1.3, nTrials: 120 },
      regime: { current: "TRENDING", detail: "ADX high" },
    });
    expect(html).toMatch("SOLID");
    expect(html).toMatch("TRENDING");
    expect(html).toMatch("<svg");
  });
});
