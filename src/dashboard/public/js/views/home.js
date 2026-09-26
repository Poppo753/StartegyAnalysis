/* views/home.js — U2-02: GET /api/status + last runs. Mock fallback, exact contract shape. */
"use strict";

import { apiGet } from "../api.js";

export const MOCK_STATUS = {
  python: "3.10.0 (mock)",
  venvOk: true,
  diskFreeGb: 412.3,
  studyDb: true,
  lastRuns: [
    { id: "20260926-142310-momentum", status: "done", symbol: "DCRUSDT", strategy: "momentum_drop" },
    { id: "20260926-150012-meanrev", status: "running", symbol: "DCRUSDT", strategy: "mean_reversion" },
  ],
};

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}

function badgeForBool(ok) {
  const s = el("span", "badge " + (ok ? "ok" : "err"), ok ? "ok" : "fail");
  return s;
}

export async function mountHome(root) {
  if (root.dataset.init === "1") {
    return refreshHome(root);
  }
  root.dataset.init = "1";
  root.innerHTML = "";
  root.appendChild(el("h2", null, "Home · system status"));
  const btn = el("button", null, "Refresh");
  btn.type = "button";
  btn.addEventListener("click", () => refreshHome(root));
  root.appendChild(btn);
  const status = el("div", null, "loading…");
  status.id = "home-status";
  root.appendChild(status);
  const h3 = el("h3", null, "Last runs");
  root.appendChild(h3);
  const runs = el("div", null, "loading…");
  runs.id = "home-runs";
  root.appendChild(runs);
  await refreshHome(root);
}

async function refreshHome(root) {
  const sBox = root.querySelector("#home-status");
  const rBox = root.querySelector("#home-runs");
  sBox.textContent = "loading…";
  sBox.className = "loading";
  rBox.textContent = "loading…";
  rBox.className = "loading";
  let data;
  let mocked = false;
  try {
    data = await apiGet("/api/status");
  } catch {
    // Backend built in parallel: degrade to mock JSON with the EXACT contract shape.
    data = MOCK_STATUS;
    mocked = true;
  }
  sBox.innerHTML = "";
  sBox.className = "";
  const grid = el("div", "grid2");
  const kv = (k, node) => {
    const d = el("div", "kv");
    d.appendChild(el("div", "k", k));
    const v = el("div", "v");
    if (typeof node === "string") v.textContent = node;
    else v.appendChild(node);
    d.appendChild(v);
    return d;
  };
  grid.appendChild(kv("python", String(data.python ?? "n/a") + (mocked ? " (MOCK — backend offline)" : "")));
  grid.appendChild(kv("venv", badgeForBool(!!data.venvOk)));
  grid.appendChild(
    kv("disk free (GB)", typeof data.diskFreeGb === "number" ? String(data.diskFreeGb) : String(data.diskFreeGb ?? "n/a")),
  );
  grid.appendChild(kv("studyDb", badgeForBool(!!data.studyDb)));
  sBox.appendChild(grid);
  if (mocked) sBox.appendChild(el("p", "note", "MOCK — /api/status unreachable, showing contract-shaped sample."));

  rBox.innerHTML = "";
  rBox.className = "";
  const runs = Array.isArray(data.lastRuns) ? data.lastRuns : [];
  if (!runs.length) {
    rBox.appendChild(el("p", "empty", "no recent runs"));
    return;
  }
  const wrap = el("div", "table-wrap");
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const hr = document.createElement("tr");
  ["id", "status", "symbol", "strategy"].forEach((h) => hr.appendChild(el("th", null, h)));
  thead.appendChild(hr);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  runs.forEach((r) => {
    const tr = document.createElement("tr");
    tr.appendChild(el("td", null, String(r.id ?? "")));
    const st = document.createElement("td");
    st.appendChild(el("span", "badge", String(r.status ?? "")));
    tr.appendChild(st);
    tr.appendChild(el("td", null, String(r.symbol ?? r.sym ?? "")));
    tr.appendChild(el("td", null, String(r.strategy ?? "")));
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  rBox.appendChild(wrap);
}
