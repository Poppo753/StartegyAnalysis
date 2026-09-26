/**
 * server.ts — Minimal static + JSON dashboard server (F8-U02/U03/U04).
 *
 * Zero npm dependencies (node:http/fs/path/url only). Run:
 *   npx tsx src/dashboard/server.ts --port 3000
 *
 * Reads result CSVs from python-backtester/backtest-results/{SYMBOL}/ at
 * request time (any depth: summary_*.csv / trades_*.csv). Empty/missing dir
 * -> documented mock JSON ({mock:true}), never a crash.
 */
import * as fs from "fs";
import * as http from "http";
import * as path from "path";
import { URL } from "url";
import {
  buildEquityCurve,
  buildHeatmap,
  buildReportHtml,
  DataRow,
  equityMatchesSummary,
  EquityMode,
  filterStrategies,
  mockSummaryRows,
  mockTradeRows,
  parseCsv,
  pnlSeries,
  sortRows,
  StrategyFilter,
} from "./reportData";

function findRepoRoot(start: string): string {
  let dir = start;
  for (let i = 0; i < 6; i++) {
    if (
      fs.existsSync(path.join(dir, "package.json")) &&
      fs.existsSync(path.join(dir, "python-backtester"))
    )
      return dir;
    dir = path.dirname(dir);
  }
  return path.resolve(start, "..", "..");
}

const REPO_ROOT = findRepoRoot(__dirname);
const RESULTS_ROOT = path.join(
  REPO_ROOT,
  "python-backtester",
  "backtest-results",
);
const PUBLIC_DIR = path.join(REPO_ROOT, "src", "dashboard", "public");

function listFilesRecursive(dir: string, out: string[] = []): string[] {
  let entries: fs.Dirent[] = [];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) listFilesRecursive(full, out);
    else if (e.isFile() && e.name.endsWith(".csv")) out.push(full);
  }
  return out;
}

/** Basename-only resolution inside RESULTS_ROOT (traversal-safe). */
function safeTradesPath(symbol: string, file: string): string | null {
  const base = path.basename(file);
  if (base !== file || !/^[A-Za-z0-9_.\-]+\.csv$/.test(base)) return null;
  const symbolDir = path.resolve(RESULTS_ROOT, path.basename(symbol));
  const full = path.resolve(symbolDir, base);
  const all = listFilesRecursive(symbolDir);
  return all.includes(full) ? full : null;
}

function loadSummaries(symbol: string): { rows: DataRow[]; mock: boolean } {
  const symbolDir = path.join(RESULTS_ROOT, path.basename(symbol));
  const files = listFilesRecursive(symbolDir).filter((f) =>
    path.basename(f).startsWith("summary"),
  );
  const rows: DataRow[] = [];
  for (const f of files) {
    try {
      const parsed = parseCsv(fs.readFileSync(f, "utf8"));
      const rel = path.relative(symbolDir, f);
      for (const r of parsed) rows.push({ _file: rel, ...r });
    } catch {
      // Skip unreadable files; degradation, never crash.
    }
  }
  if (rows.length === 0)
    return { rows: mockSummaryRows(), mock: true };
  return { rows, mock: false };
}

function downsample(xs: number[], max = 2000): number[] {
  if (xs.length <= max) return xs;
  const step = Math.ceil(xs.length / max);
  const out: number[] = [];
  for (let i = 0; i < xs.length; i += step) out.push(xs[i]);
  if (out[out.length - 1] !== xs[xs.length - 1]) out.push(xs[xs.length - 1]);
  return out;
}

const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

function send(res: http.ServerResponse, code: number, body: string, type: string): void {
  res.writeHead(code, { "Content-Type": type });
  res.end(body);
}

function sendJson(res: http.ServerResponse, code: number, obj: unknown): void {
  send(res, code, JSON.stringify(obj), "application/json; charset=utf-8");
}

const server = http.createServer((req, res) => {
  try {
    const url = new URL(req.url ?? "/", "http://localhost");
    const q = url.searchParams;

    if (url.pathname === "/api/summaries") {
      const symbol = q.get("symbol") || "DCRUSDT";
      const { rows, mock } = loadSummaries(symbol);
      const filter: StrategyFilter = {
        strategy: q.get("strategy") || undefined,
        regime: q.get("regime") || undefined,
        minTrades: q.get("minTrades") ? Number(q.get("minTrades")) : undefined,
        minSharpe: q.get("minSharpe") ? Number(q.get("minSharpe")) : undefined,
        maxDd: q.get("maxDd") ? Number(q.get("maxDd")) : undefined,
      };
      const sortKey = q.get("sort") || "total_pnl";
      const dir = q.get("dir") === "asc" ? "asc" : "desc";
      const out = sortRows(filterStrategies(rows, filter), sortKey, dir);
      sendJson(res, 200, { symbol, mock, count: out.length, rows: out });
      return;
    }

    if (url.pathname === "/api/trades-files") {
      const symbol = q.get("symbol") || "DCRUSDT";
      const symbolDir = path.join(RESULTS_ROOT, path.basename(symbol));
      const files = listFilesRecursive(symbolDir)
        .filter((f) => path.basename(f).startsWith("trades"))
        .map((f) => path.relative(symbolDir, f));
      sendJson(res, 200, { symbol, files });
      return;
    }

    if (url.pathname === "/api/equity") {
      const symbol = q.get("symbol") || "DCRUSDT";
      const file = q.get("trades") || "";
      const mode = (q.get("mode") === "pnl" ? "pnl" : "signal-only") as EquityMode;
      const full = safeTradesPath(symbol, file);
      if (!full) {
        // Documented mock fallback (empty dir / unknown file).
        const trades = mockTradeRows();
        const curve = buildEquityCurve(
          trades.map((t) => Number(t[mode === "signal-only" ? "pnl_percent" : "pnl"])),
        );
        const check = equityMatchesSummary(trades, mockSummaryRows()[0], mode);
        sendJson(res, 200, {
          symbol, mode, mock: true, n: trades.length,
          equity: downsample(curve.equity), drawdown: downsample(curve.drawdown),
          maxDrawdown: curve.maxDrawdown, ...check,
        });
        return;
      }
      const trades = parseCsv(fs.readFileSync(full, "utf8"));
      const curve = buildEquityCurve(pnlSeries(trades, mode));
      // Counterpart summary row: match by x/y/z params when present.
      const { rows } = loadSummaries(symbol);
      const first = trades[0] ?? {};
      const summary =
        rows.find(
          (r) =>
            String(r["x_percent"] ?? "") === String(first["x_percent"] ?? "§") &&
            String(r["y_seconds"] ?? "") === String(first["y_seconds"] ?? "§") &&
            String(r["z_percent"] ?? "") === String(first["z_percent"] ?? "§"),
        ) ?? {};
      const check = equityMatchesSummary(trades, summary, mode);
      sendJson(res, 200, {
        symbol, mode, mock: false, file: path.basename(full), n: trades.length,
        equity: downsample(curve.equity), drawdown: downsample(curve.drawdown),
        maxDrawdown: curve.maxDrawdown, ...check,
      });
      return;
    }

    if (url.pathname === "/api/heatmap") {
      const symbol = q.get("symbol") || "DCRUSDT";
      const xParam = q.get("x") || "x_percent";
      const yParam = q.get("y") || "z_percent";
      const metric = q.get("metric") || "total_pnl";
      const { rows, mock } = loadSummaries(symbol);
      sendJson(res, 200, { symbol, mock, heatmap: buildHeatmap(rows, xParam, yParam, metric) });
      return;
    }

    if (url.pathname === "/api/report") {
      const symbol = q.get("symbol") || "DCRUSDT";
      const mode = (q.get("mode") === "pnl" ? "pnl" : "signal-only") as EquityMode;
      const { rows } = loadSummaries(symbol);
      const top = sortRows(rows, "total_pnl", "desc")[0];
      let equity = null;
      if (top) {
        const symbolDir = path.join(RESULTS_ROOT, path.basename(symbol));
        const tradesFiles = listFilesRecursive(symbolDir).filter((f) =>
          path.basename(f).startsWith("trades"),
        );
        if (tradesFiles.length > 0) {
          const trades = parseCsv(fs.readFileSync(tradesFiles[0], "utf8"));
          const curve = buildEquityCurve(pnlSeries(trades, mode));
          const check = equityMatchesSummary(trades, top, mode);
          equity = { ...curve, ...check, mode };
        }
      }
      const numericCols = top ? Object.keys(top).filter((k) => typeof top[k] === "number") : [];
      const heatmap =
        numericCols.length >= 2
          ? buildHeatmap(rows, numericCols[0], numericCols[1], "total_pnl")
          : null;
      const html = buildReportHtml({
        config: { symbol, resultsDir: `python-backtester/backtest-results/${symbol}`, mode },
        summaryRows: rows,
        equity,
        heatmap,
        pboDsr: null, // F3 not wired to CSVs: degrades to "not available".
        regime: null, // F5 not wired to CSVs: degrades to "not available".
      });
      send(res, 200, html, "text/html; charset=utf-8");
      return;
    }

    // Static files from src/dashboard/public ("/" -> index.html).
    const rel = url.pathname === "/" ? "index.html" : url.pathname.replace(/^\/+/, "");
    const full = path.resolve(PUBLIC_DIR, path.normalize(rel));
    if (!full.startsWith(path.resolve(PUBLIC_DIR)) || !fs.existsSync(full) || fs.statSync(full).isDirectory()) {
      send(res, 404, "not found", "text/plain; charset=utf-8");
      return;
    }
    send(res, 200, fs.readFileSync(full, "utf8"), MIME[path.extname(full)] ?? "text/plain; charset=utf-8");
  } catch (e) {
    sendJson(res, 500, { error: e instanceof Error ? e.message : String(e) });
  }
});

function parsePort(): number {
  const i = process.argv.indexOf("--port");
  const v = i >= 0 ? Number(process.argv[i + 1]) : NaN;
  return Number.isFinite(v) ? v : Number(process.env.PORT) || 3000;
}

if (require.main === module) {
  const port = parsePort();
  server.listen(port, "127.0.0.1", () => {
    // eslint-disable-next-line no-console
    console.log(`dashboard at http://127.0.0.1:${port}/ (results: ${RESULTS_ROOT})`);
  });
}

export { server };
