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
  const header = el("div", "page-header");
  const title = el("div");
  title.append(el("p", "eyebrow", "Analisi"), el("h2", null, "Risultati"), el("p", "page-subtitle", "Esplora le strategie, confronta i parametri e visualizza l'equity."));
  header.append(title); root.append(header);
  const filterPanel = el("section", "panel");
  const filterHead = el("div", "panel-header"); filterHead.append(el("h3", null, "Filtri e confronto"));
  filterPanel.append(filterHead);
  const filterBody = el("div", "filter-panel");
  const f1 = el("div", "filter-row");
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
  mkLabeled("Simbolo", symbol);
  const hx = document.createElement("select");
  hx.id = "res-hx";
  ["x_percent", "y_seconds", "z_percent", "ma_period", "z_threshold"].forEach((v) => opt(hx, v));
  mkLabeled("Parametro X", hx);
  const hy = document.createElement("select");
  hy.id = "res-hy";
  ["z_percent", "x_percent", "y_seconds", "ma_period", "z_threshold"].forEach((v) => opt(hy, v));
  mkLabeled("Parametro Y", hy);
  const hm = document.createElement("select");
  hm.id = "res-hm";
  ["total_pnl", "sharpe_ratio", "sortino_ratio", "total_pnl_percent"].forEach((v) => opt(hm, v));
  mkLabeled("Metrica", hm);
  filterBody.append(f1);

  const f2 = el("div", "filter-row");
  f2.style.marginTop = "14px";
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
  txt("res-fStrategy", "Strategia", 14);
  txt("res-fRegime", "Regime", 10);
  txt("res-fMinTrades", "Min. trade", 5);
  txt("res-fMinSharpe", "Sharpe min.", 5);
  txt("res-fMaxDd", "Drawdown max.", 5);
  const actions = el("div", "filter-actions");
  const reloadBtn = el("button", "btn-primary", "Applica filtri");
  reloadBtn.type = "button";
  reloadBtn.addEventListener("click", () => reloadResults(root).catch((e) => toast(e.message)));
  actions.appendChild(reloadBtn);
  const csvBtn = el("button", null, "Esporta CSV");
  csvBtn.type = "button";
  csvBtn.addEventListener("click", () => exportCsv(root));
  actions.appendChild(csvBtn);
  f2.append(actions);
  const count = el("span", "note", "");
  count.id = "res-count";
  filterBody.append(f2, el("p", "helper", "I filtri non escludono le righe quando un campo non è disponibile nei dati."));
  filterPanel.append(filterBody); root.append(filterPanel);

  const matrixPanel = el("section", "panel");
  const matrixHead = el("div", "panel-header");
  const matrixTitle = el("div"); matrixTitle.append(el("h3", null, "Mappa dei parametri"), el("p", null, "Le celle evidenziate rappresentano i valori più alti."));
  matrixHead.append(matrixTitle); matrixPanel.append(matrixHead);

  const heat = el("div", "panel-body heatmap-wrap");
  heat.id = "res-heatmap";
  matrixPanel.append(heat); root.append(matrixPanel);
  const tablePanel = el("section", "panel");
  const tableHead = el("div", "panel-header");
  const tableTitle = el("div"); tableTitle.append(el("h3", null, "Strategie"), el("p", null, "Clicca un'intestazione per ordinare."));
  tableHead.append(tableTitle, count); tablePanel.append(tableHead);
  const twrap = el("div", "table-wrap");
  const table = document.createElement("table");
  table.id = "res-grid";
  table.appendChild(document.createElement("thead"));
  table.appendChild(document.createElement("tbody"));
  twrap.appendChild(table);
  tablePanel.append(twrap); root.append(tablePanel);

  const equityPanel = el("section", "panel");
  const equityHead = el("div", "panel-header");
  const equityTitle = el("div"); equityTitle.append(el("h3", null, "Equity e drawdown"), el("p", null, "Seleziona un file trade per visualizzare l'andamento."));
  equityHead.append(equityTitle); equityPanel.append(equityHead);
  const equityBody = el("div", "panel-body");
  const f3 = el("div", "toolbar");
  const tradesSel = document.createElement("select");
  tradesSel.id = "res-tradesFile";
  const labT = document.createElement("label");
  labT.appendChild(document.createTextNode("File trade"));
  labT.appendChild(tradesSel);
  f3.appendChild(labT);
  const mode = document.createElement("select");
  mode.id = "res-mode";
  opt(mode, "signal-only", "Segnale (P&L %)");
  opt(mode, "pnl", "P&L (USDT)");
  const labM = document.createElement("label");
  labM.appendChild(document.createTextNode("Modalità"));
  labM.appendChild(mode);
  f3.appendChild(labM);
  const loadBtn = el("button", "btn-primary", "Mostra curva");
  loadBtn.type = "button";
  loadBtn.addEventListener("click", () => loadEquity(root).catch((e) => toast(e.message)));
  f3.appendChild(loadBtn);
  const info = el("span", "note", "");
  info.id = "res-equityInfo";
  f3.appendChild(info);
  equityBody.append(f3);
  const canvas = document.createElement("canvas");
  canvas.id = "res-equityCanvas";
  canvas.width = 900;
  canvas.height = 300;
  canvas.style.marginTop = "20px";
  const legend = el("div", "chart-legend");
  const l1 = el("span"), l2 = el("span", "drawdown");
  l1.append(el("i"), document.createTextNode("Equity"));
  l2.append(el("i"), document.createTextNode("Drawdown"));
  legend.append(l1, l2);
  equityBody.append(canvas, legend); equityPanel.append(equityBody); root.append(equityPanel);

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
  const total = Number(sum.count ?? (sum.rows || []).length);
  q(root, "#res-count").textContent = total + " strategie" + (total > 200 ? " · prime 200 in tabella" : "") + (sum.mock ? " · dati dimostrativi" : "");
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
    tr.appendChild(el("td", null, "Nessun risultato con i filtri selezionati."));
    tbody.appendChild(tr);
    return;
  }
  const sortKey = root.dataset.sortKey;
  const sortDir = root.dataset.sortDir;
  const headers = Object.keys(rows[0]);
  const hr = document.createElement("tr");
  headers.forEach((h) => {
    const th = document.createElement("th");
    const sortButton = el("button", "sort-button", h.replaceAll("_", " ") + (h === sortKey ? (sortDir === "asc" ? " ▲" : " ▼") : ""));
    sortButton.type = "button";
    sortButton.setAttribute("aria-label", "Ordina per " + h.replaceAll("_", " "));
    sortButton.addEventListener("click", () => {
      if (root.dataset.sortKey === h) root.dataset.sortDir = root.dataset.sortDir === "asc" ? "desc" : "asc";
      else {
        root.dataset.sortKey = h;
        root.dataset.sortDir = "desc";
      }
      reloadResults(root);
    });
    th.append(sortButton);
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
    div.appendChild(el("p", "note", "Mappa non disponibile per questa combinazione di parametri e metrica."));
    return;
  }
  let max = -Infinity;
  let min = Infinity;
  hm.grid.forEach((row) =>
    row.forEach((c) => {
      if (c !== null && c > max) max = c;
      if (c !== null && c < min) min = c;
    }),
  );
  div.appendChild(el("p", "note", String(hm.yParam) + " × " + String(hm.xParam) + " · " + String(hm.metric)));
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
      if (c !== null) {
        const strength = max === min ? 1 : (c - min) / (max - min);
        td.style.backgroundColor = "rgba(100, 216, 196, " + (0.03 + strength * 0.24).toFixed(3) + ")";
        if (strength > 0.8) td.className = "hm-hot";
      }
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
  (data.files && data.files.length ? data.files : []).forEach((f) => {
    const o = document.createElement("option");
    o.value = String(f);
    o.textContent = String(f);
    sel.appendChild(o);
  });
  const load = q(root, "#res-tradesFile").closest(".toolbar").querySelector("button");
  load.disabled = !sel.options.length;
  if (!sel.options.length) { const o = document.createElement("option"); o.textContent = "Nessun file disponibile"; o.value = ""; sel.append(o); }
}

async function loadEquity(root) {
  const file = q(root, "#res-tradesFile").value;
  const mode = q(root, "#res-mode").value;
  const data = await apiGet(
    "/api/equity?symbol=" + encodeURIComponent(symVal(root)) +
      "&trades=" + encodeURIComponent(file) + "&mode=" + encodeURIComponent(mode),
  );
  q(root, "#res-equityInfo").textContent =
    String(data.n) + " punti · Equity finale: " + Number(data.finalEquity).toFixed(4) +
    " · Attesa: " + (Number.isFinite(Number(data.expected)) ? Number(data.expected).toFixed(4) : "N/D") +
    " · " + (data.match ? "Verificata" : "Da verificare") + (data.mock ? " · Dati dimostrativi" : "");
  drawSeries(q(root, "#res-equityCanvas"), data.equity, data.drawdown);
}

function drawSeries(canvas, equity, drawdown) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const fg = getComputedStyle(canvas).getPropertyValue("--muted").trim() || "#93a7b7";
  const grid = getComputedStyle(canvas).getPropertyValue("--border").trim() || "#273a4b";
  const draw = (xs, color, top, height, label) => {
    const values = Array.isArray(xs) ? xs.map(Number).filter(Number.isFinite) : [];
    if (!values.length) return;
    let lo = Infinity, hi = -Infinity;
    for (const v of values) { if (v < lo) lo = v; if (v > hi) hi = v; }
    const span = hi - lo || 1;
    const left = 52, right = canvas.width - 18;
    ctx.font = "11px sans-serif";
    ctx.fillStyle = fg;
    ctx.fillText(label, left, top + 12);
    ctx.fillText(hi.toFixed(2), 6, top + 25);
    ctx.fillText(lo.toFixed(2), 6, top + height);
    ctx.strokeStyle = grid;
    ctx.lineWidth = 1;
    [0, .5, 1].forEach(t => {
      const y = top + 22 + t * (height - 24);
      ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke();
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    values.forEach((v, i) => {
      const x = left + (i / Math.max(1, values.length - 1)) * (right - left);
      const y = top + height - 2 - ((v - lo) / span) * (height - 26);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  };
  draw(equity, "#4da3ff", 7, 170, "Equity");
  draw(drawdown, "#f85149", 185, 105, "Drawdown");
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
