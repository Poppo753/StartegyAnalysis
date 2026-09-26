/**
 * server.ts — Minimal static + JSON dashboard server (F8-U02/U03/U04, U0-02, U1-03).
 *
 * Wiring only: mounts route modules (routes/results.ts, routes/system.ts,
 * routes/runs.ts) and serves static files from src/dashboard/public.
 * Zero npm dependencies (node:http/fs/path/url only). Run:
 *   npx tsx src/dashboard/server.ts --port 3000
 *
 * Result CSVs are read from python-backtester/backtest-results/{SYMBOL}/ at
 * request time (any depth: summary_*.csv / trades_*.csv). Empty/missing dir
 * -> documented mock JSON ({mock:true}), never a crash.
 */
import * as fs from "fs";
import * as http from "http";
import * as path from "path";
import { URL } from "url";
import { handleResultsRoutes } from "./routes/results";
import { handleSystemRoutes } from "./routes/system";
import { handleRunsRoutes } from "./routes/runs";

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
const PUBLIC_DIR = path.join(REPO_ROOT, "src", "dashboard", "public");

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

    if (handleResultsRoutes(req, res, url)) return;
    if (handleSystemRoutes(req, res, url)) return;
    if (handleRunsRoutes(req, res, url)) return;

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
  server.on("error", (err: NodeJS.ErrnoException) => {
    // Fail fast with a clear message when the port is occupied.
    // eslint-disable-next-line no-console
    console.error(`dashboard: cannot listen on 127.0.0.1:${port}: ${err.message}`);
    process.exit(1);
  });
  server.listen(port, "127.0.0.1", () => {
    // eslint-disable-next-line no-console
    console.log(`dashboard at http://127.0.0.1:${port}/`);
  });
}

export { server };
