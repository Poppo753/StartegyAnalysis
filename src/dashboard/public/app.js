/* app.js — vanilla glue for the F8 dashboard. Tested logic lives in
 * reportData.ts (server side); this file only fetches + renders. */
"use strict";

let lastRows = [];
let sortKey = "total_pnl";
let sortDir = "desc";

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error("HTTP " + r.status + " for " + url);
  return r.json();
}

function symbol() {
  return (document.getElementById("symbol").value || "DCRUSDT").trim();
}

async function reload() {
  const p = new URLSearchParams({
    symbol: symbol(),
    x: document.getElementById("hx").value,
    y: document.getElementById("hy").value,
    metric: document.getElementById("hm").value,
    strategy: document.getElementById("fStrategy").value,
    regime: document.getElementById("fRegime").value,
    minTrades: document.getElementById("fMinTrades").value,
    minSharpe: document.getElementById("fMinSharpe").value,
    maxDd: document.getElementById("fMaxDd").value,
    sort: sortKey,
    dir: sortDir,
  });
  const [sum, hm] = await Promise.all([
    getJSON("/api/summaries?" + p.toString()),
    getJSON("/api/heatmap?" + p.toString()),
  ]);
  lastRows = sum.rows;
  document.getElementById("count").textContent =
    sum.count + " rows" + (sum.mock ? " (MOCK — results dir empty)" : "");
  renderTable(sum.rows);
  renderHeatmap(hm.heatmap);
  document.getElementById("reportLink").href =
    "/api/report?symbol=" + encodeURIComponent(symbol());
  await reloadTradesFiles();
}

function renderTable(rows) {
  const t = document.getElementById("grid");
  const thead = t.querySelector("thead");
  const tbody = t.querySelector("tbody");
  thead.innerHTML = "";
  tbody.innerHTML = "";
  if (!rows.length) {
    tbody.innerHTML = "<tr><td>No rows</td></tr>";
    return;
  }
  const headers = Object.keys(rows[0]);
  const hr = document.createElement("tr");
  headers.forEach((h) => {
    const th = document.createElement("th");
    th.textContent = h + (h === sortKey ? (sortDir === "asc" ? " ▲" : " ▼") : "");
    th.onclick = () => {
      if (sortKey === h) sortDir = sortDir === "asc" ? "desc" : "asc";
      else {
        sortKey = h;
        sortDir = "desc";
      }
      reload();
    };
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

function renderHeatmap(hm) {
  const div = document.getElementById("heatmap");
  if (!hm || !hm.xVals.length || !hm.yVals.length) {
    div.innerHTML = "<p class='note'>heatmap not available for these params/metric.</p>";
    return;
  }
  let max = -Infinity;
  hm.grid.forEach((row) =>
    row.forEach((c) => {
      if (c !== null && c > max) max = c;
    }),
  );
  let html =
    "<p class='note'>heatmap: " + hm.xParam + " × " + hm.yParam + " → " + hm.metric + "</p><table><tr><th>" +
    hm.yParam + " \\ " + hm.xParam + "</th>" +
    hm.xVals.map((x) => "<th>" + x + "</th>").join("") + "</tr>";
  hm.yVals.forEach((y, j) => {
    html += "<tr><td>" + y + "</td>";
    hm.grid[j].forEach((c) => {
      const cls = c !== null && c >= max * 0.8 ? " class='hm-hot'" : "";
      html += "<td" + cls + ">" + (c === null ? "—" : Math.round(c * 10000) / 10000) + "</td>";
    });
    html += "</tr>";
  });
  div.innerHTML = html + "</table>";
}

async function reloadTradesFiles() {
  const data = await getJSON("/api/trades-files?symbol=" + encodeURIComponent(symbol()));
  const sel = document.getElementById("tradesFile");
  sel.innerHTML = "";
  (data.files.length ? data.files : ["(mock)"]).forEach((f) => {
    const o = document.createElement("option");
    o.value = f;
    o.textContent = f;
    sel.appendChild(o);
  });
}

async function loadEquity() {
  const file = document.getElementById("tradesFile").value;
  const mode = document.getElementById("mode").value;
  const data = await getJSON(
    "/api/equity?symbol=" + encodeURIComponent(symbol()) +
      "&trades=" + encodeURIComponent(file) + "&mode=" + encodeURIComponent(mode),
  );
  document.getElementById("equityInfo").textContent =
    "n=" + data.n + " mode=" + data.mode + " final=" + data.finalEquity.toFixed(4) +
    " expected=" + (Number.isFinite(data.expected) ? data.expected.toFixed(4) : "n/a") +
    " match=" + data.match + (data.mock ? " (MOCK)" : "");
  drawSeries(document.getElementById("equityCanvas"), data.equity, data.drawdown);
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
  draw(equity, "#111");
  draw(drawdown, "#c00");
}

function exportCsv() {
  if (!lastRows.length) return;
  const headers = Object.keys(lastRows[0]);
  const esc = (v) => {
    const s = String(v ?? "");
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const csv = [headers.join(",")]
    .concat(lastRows.map((r) => headers.map((h) => esc(r[h])).join(",")))
    .join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = "strategies_view.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}

document.getElementById("reload").onclick = () => reload().catch((e) => alert(e.message));
document.getElementById("loadEquity").onclick = () => loadEquity().catch((e) => alert(e.message));
document.getElementById("exportCsv").onclick = exportCsv;
reload().catch((e) => {
  document.getElementById("count").textContent = "failed: " + e.message;
});
