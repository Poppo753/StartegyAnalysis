/* views/results.js — U2-03: split of app.js (results part) per-view, same behavior + endpoints.
 * Existing endpoints kept as-is: /api/summaries, /api/heatmap, /api/trades-files, /api/equity.
 * app.js on disk is left untouched; this module is the per-view split used by the 5-view shell.
 */
"use strict";

import { apiGet, toast } from "../api.js";

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}

function opt(sel, value, label) {
  const o = document.createElement("option");
  o.value = value;
  o.textContent = label ?? value;
  sel.appendChild(o);
}

export async function mountResults(root) {
  if (root.dataset.init === "1") return reloadResults(root);
  root.dataset.init = "1";
  root.innerHTML = "";
  root.appendChild(el("h2", null, "Results · strategies + equity"));
  root.appendChild(
    el("p", "note", "Conventions: signal-only mode draws equity on pnl_percent, otherwise on pnl (metrics.py). Filters on unavailable columns do not exclude rows."),
  );

  const s1 = el("h3", null, "Strategies (heatmap params + filters + CSV export)");
  root.appendChild(s1);
  const f1 = el("div");
  const mkLabeled = (labelText, input) => {
    const lab = document.createElement("label");
    lab.appendChild(document.createTextNode(labelText + " "));
    lab.appendChild(input);
    f1.appendChild(lab);
    return lab;
  };
  const symbol = document.createElement("input");
  symbol.id = "res-symbol";
  symbol.value = "DCRUSDT";
  symbol.size = 10;
  mkLabeled("Symbol", symbol);
  const hx = document.createElement("select");
  hx.id = "res-hx";
  ["x_percent", "y_seconds", "z_percent", "ma_period", "z_threshold"].forEach((v) => opt(hx, v));
  mkLabeled("X param", hx);
  const hy = document.createElement("select");
  hy.id = "res-hy";
  ["z_percent", "x_percent", "y_seconds", "ma_period", "z_threshold"].forEach((v) => opt(hy, v));
  mkLabeled("Y param", hy);
  const hm = document.createElement("select");
  hm.id = "res-hm";
  ["total_pnl", "sharpe_ratio", "sortino_ratio", "total_pnl_percent"].forEach((v) => opt(hm, v));
  mkLabeled("Metric", hm);
  root.appendChild(f1);

  const f2 = el("div");
  const txt = (id, placeholder, size) => {
    const i = document.createElement("input");
    i.id = id;
    i.placeholder = placeholder;
    i.size = size;
    const lab = document.createElement("label");
    lab.appendChild(document.createTextNode(placeholder + " "));
    lab.appendChild(i);
    f2.appendChild(lab);
    return i;
  };
  txt("res-fStrategy", "strategy", 14);
  txt("res-fRegime", "regime", 10);
  txt("res-fMinTrades", "min trades", 5);
  txt("res-fMinSharpe", "min Sharpe", 5);
  txt("res-fMaxDd", "max DD", 5);
  const reloadBtn = el("button", null, "Reload");
  reloadBtn.type = "button";
  reloadBtn.addEventListener("click", () => reloadResults(root).catch((e) => toast(e.message)));
  f2.appendChild(reloadBtn);
  const csvBtn = el("button", null, "Export CSV");
  csvBtn.type = "button";
  csvBtn.addEventListener("click", () => exportCsv(root));
  f2.appendChild(csvBtn);
  const count = el("span", "note", "");
  count.id = "res-count";
  f2.appendChild(count);
  root.appendChild(f2);

  const heat = el("div");
  heat.id = "res-heatmap";
  heat.style.marginTop = "1rem";
  root.appendChild(heat);
  const twrap = el("div", "table-wrap");
  twrap.style.marginTop = "1rem";
  const table = document.createElement("table");
  table.id = "res-grid";
  table.appendChild(document.createElement("thead"));
  table.appendChild(document.createElement("tbody"));
  twrap.appendChild(table);
  root.appendChild(twrap);

  root.appendChild(el("h3", null, "Equity + drawdown per strategy"));
  const f3 = el("div");
  const tradesSel = document.createElement("select");
  tradesSel.id = "res-tradesFile";
  const labT = document.createElement("label");
  labT.appendChild(document.createTextNode("trades file "));
  labT.appendChild(tradesSel);
  f3.appendChild(labT);
  const mode = document.createElement("select");
  mode.id = "res-mode";
  opt(mode, "signal-only", "signal-only (pnl_percent)");
  opt(mode, "pnl", "pnl (USDT)");
  const labM = document.createElement("label");
  labM.appendChild(document.createTextNode("mode "));
  labM.appendChild(mode);
  f3.appendChild(labM);
  const loadBtn = el("button", null, "Load");
  loadBtn.type = "button";
  loadBtn.addEventListener("click", () => loadEquity(root).catch((e) => toast(e.message)));
  f3.appendChild(loadBtn);
  const info = el("span", "note", "");
  info.id = "res-equityInfo";
  f3.appendChild(info);
  root.appendChild(f3);
  const canvas = document.createElement("canvas");
  canvas.id = "res-equityCanvas";
  canvas.width = 900;
  canvas.height = 220;
  root.appendChild(canvas);

  root.dataset.sortKey = "total_pnl";
  root.dataset.sortDir = "desc";
  root.dataset.lastRows = "[]";
  await reloadResults(root);
}

function q(root, sel) {
  return root.querySelector(sel);
}

function symVal(root) {
  return (q(root, "#res-symbol").value || "DCRUSDT").trim();
}

export async function reloadResults(root) {
  const sortKey = root.dataset.sortKey || "total_pnl";
  const sortDir = root.dataset.sortDir || "desc";
  const p = new URLSearchParams({
    symbol: symVal(root),
    x: q(root, "#res-hx").value,
    y: q(root, "#res-hy").value,
    metric: q(root, "#res-hm").value,
    strategy: q(root, "#res-fStrategy").value,
    regime: q(root, "#res-fRegime").value,
    minTrades: q(root, "#res-fMinTrades").value,
    minSharpe: q(root, "#res-fMinSharpe").value,
    maxDd: q(root, "#res-fMaxDd").value,
    sort: sortKey,
    dir: sortDir,
  });
  let sum, heat;
  try {
    [sum, heat] = await Promise.all([apiGet("/api/summaries?" + p.toString()), apiGet("/api/heatmap?" + p.toString())]);
  } catch (e) {
    q(root, "#res-count").textContent = "failed: " + (e && e.message ? e.message : String(e));
    return;
  }
  root.dataset.lastRows = JSON.stringify(sum.rows || []);
  q(root, "#res-count").textContent = String(sum.count) + " rows" + (sum.mock ? " (MOCK — results dir empty)" : "");
  renderTable(root, sum.rows || []);
  renderHeatmap(root, heat.heatmap);
  await reloadTradesFiles(root);
}

function renderTable(root, rows) {
  const t = q(root, "#res-grid");
  const thead = t.querySelector("thead");
  const tbody = t.querySelector("tbody");
  thead.innerHTML = "";
  tbody.innerHTML = "";
  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.appendChild(el("td", null, "No rows"));
    tbody.appendChild(tr);
    return;
  }
  const sortKey = root.dataset.sortKey;
  const sortDir = root.dataset.sortDir;
  const headers = Object.keys(rows[0]);
  const hr = document.createElement("tr");
  headers.forEach((h) => {
    const th = document.createElement("th");
    // textContent only — never innerHTML with header names.
    th.textContent = h + (h === sortKey ? (sortDir === "asc" ? " ▲" : " ▼") : "");
    th.addEventListener("click", () => {
      if (root.dataset.sortKey === h) root.dataset.sortDir = root.dataset.sortDir === "asc" ? "desc" : "asc";
      else {
        root.dataset.sortKey = h;
        root.dataset.sortDir = "desc";
      }
      reloadResults(root);
    });
    hr.appendChild(th);
  });
  thead.appendChild(hr);
  rows.slice(0, 200).forEach((r) => {
    const tr = document.createElement("tr");
    headers.forEach((h) => {
      const td = document.createElement("td");
      const v = r[h];
      td.textContent = typeof v === "number" ? String(Math.round(v * 10000) / 10000) : String(v ?? "");
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}

function renderHeatmap(root, hm) {
  const div = q(root, "#res-heatmap");
  div.innerHTML = "";
  if (!hm || !hm.xVals || !hm.yVals || !hm.xVals.length || !hm.yVals.length) {
    div.appendChild(el("p", "note", "heatmap not available for these params/metric."));
    return;
  }
  let max = -Infinity;
  hm.grid.forEach((row) =>
    row.forEach((c) => {
      if (c !== null && c > max) max = c;
    }),
  );
  div.appendChild(el("p", "note", "heatmap: " + String(hm.xParam) + " × " + String(hm.yParam) + " → " + String(hm.metric)));
  const table = document.createElement("table");
  const hr = document.createElement("tr");
  hr.appendChild(el("th", null, String(hm.yParam) + " \\ " + String(hm.xParam)));
  hm.xVals.forEach((x) => hr.appendChild(el("th", null, String(x))));
  table.appendChild(hr);
  hm.yVals.forEach((y, j) => {
    const tr = document.createElement("tr");
    tr.appendChild(el("td", null, String(y)));
    hm.grid[j].forEach((c) => {
      const td = document.createElement("td");
      if (c !== null && c >= max * 0.8) td.className = "hm-hot";
      td.textContent = c === null ? "—" : String(Math.round(c * 10000) / 10000);
      tr.appendChild(td);
    });
    table.appendChild(tr);
  });
  div.appendChild(table);
}

async function reloadTradesFiles(root) {
  let data;
  try {
    data = await apiGet("/api/trades-files?symbol=" + encodeURIComponent(symVal(root)));
  } catch {
    return;
  }
  const sel = q(root, "#res-tradesFile");
  sel.innerHTML = "";
  (data.files && data.files.length ? data.files : ["(mock)"]).forEach((f) => {
    const o = document.createElement("option");
    o.value = String(f);
    o.textContent = String(f);
    sel.appendChild(o);
  });
}

async function loadEquity(root) {
  const file = q(root, "#res-tradesFile").value;
  const mode = q(root, "#res-mode").value;
  const data = await apiGet(
    "/api/equity?symbol=" + encodeURIComponent(symVal(root)) +
      "&trades=" + encodeURIComponent(file) + "&mode=" + encodeURIComponent(mode),
  );
  q(root, "#res-equityInfo").textContent =
    "n=" + String(data.n) + " mode=" + String(data.mode) + " final=" + Number(data.finalEquity).toFixed(4) +
    " expected=" + (Number.isFinite(Number(data.expected)) ? Number(data.expected).toFixed(4) : "n/a") +
    " match=" + String(data.match) + (data.mock ? " (MOCK)" : "");
  drawSeries(q(root, "#res-equityCanvas"), data.equity, data.drawdown);
}

function drawSeries(canvas, equity, drawdown) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const draw = (xs, color) => {
    if (!xs || !xs.length) return;
    const lo = Math.min.apply(null, xs);
    const hi = Math.max.apply(null, xs);
    const span = hi - lo > 0 ? hi - lo : 1;
    ctx.strokeStyle = color;
    ctx.beginPath();
    xs.forEach((v, i) => {
      const x = (i / Math.max(1, xs.length - 1)) * (canvas.width - 10) + 5;
      const y = canvas.height - 5 - ((v - lo) / span) * (canvas.height - 10);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  };
  draw(equity, "#4da3ff");
  draw(drawdown, "#f85149");
}

function exportCsv(root) {
  const rows = JSON.parse(root.dataset.lastRows || "[]");
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const escCell = (v) => {
    const s = String(v ?? "");
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const csv = [headers.join(",")]
    .concat(rows.map((r) => headers.map((h) => escCell(r[h])).join(",")))
    .join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = "strategies_view.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}
