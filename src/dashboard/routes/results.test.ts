import * as fs from "fs";
import * as http from "http";
import * as path from "path";
import { URL } from "url";
import { handleResultsRoutes, RESULTS_ROOT } from "./results";

function request(url: string): { code: number; body: any } {
  let code = 0;
  let body = "";
  const req = { method: "GET" } as http.IncomingMessage;
  const res = {
    writeHead: (status: number) => { code = status; },
    end: (text: string) => { body = text; },
  } as unknown as http.ServerResponse;
  expect(handleResultsRoutes(req, res, new URL(url, "http://localhost"))).toBe(true);
  return { code, body: JSON.parse(body) };
}

test.each(["summaries", "trades-files", "equity", "heatmap", "report"])(
  "rejects traversal symbol for /api/%s",
  (route) => {
    const result = request(`/api/${route}?symbol=..`);
    expect(result.code).toBe(400);
    expect(result.body).toEqual({ error: "invalid symbol" });
  },
);

test("equity accepts a nested trades file returned by trades-files", () => {
  fs.mkdirSync(RESULTS_ROOT, { recursive: true });
  const symbolDir = fs.mkdtempSync(path.join(RESULTS_ROOT, "TEST"));
  const symbol = path.basename(symbolDir);
  try {
    const nested = path.join(symbolDir, "nested");
    fs.mkdirSync(nested);
    fs.writeFileSync(path.join(nested, "trades_fixture.csv"), "pnl,pnl_percent\n1,2\n");
    const files = request(`/api/trades-files?symbol=${symbol}`);
    expect(files.code).toBe(200);
    expect(files.body.files).toEqual([path.join("nested", "trades_fixture.csv")]);
    const equity = request(`/api/equity?symbol=${symbol}&mode=pnl&trades=${encodeURIComponent(files.body.files[0])}`);
    expect(equity.code).toBe(200);
    expect(equity.body.mock).toBe(false);
  } finally {
    fs.rmSync(symbolDir, { recursive: true, force: true });
  }
});
