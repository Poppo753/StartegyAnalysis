/* views/runs.js — U2-03: list + 2s log polling (fromLine) + cancel + reconcile (unknown only)
 * + visible progressNote "stima".
 */
"use strict";

import { apiGet, apiPost, toast } from "../api.js";

export const MOCK_RUNS = [
  {
    id: "20260926-142310-momentum", symbol: "DCRUSDT", strategy: "momentum_drop", engine: "standard",
    status: "done", startedAt: "2026-09-26T14:23:10Z", finishedAt: "2026-09-26T14:25:01Z",
    exitCode: 0, progress: 100, progressNote: "stima",
  },
  {
    id: "20260926-150012-meanrev", symbol: "DCRUSDT", strategy: "mean_reversion", engine: "gpu",
    status: "running", startedAt: "2026-09-26T15:00:12Z", finishedAt: null,
    exitCode: null, progress: 42, progressNote: "stima",
  },
  {
    id: "20260926-151000-crash", symbol: "BTCUSDT", strategy: "momentum_drop", engine: "fast",
    status: "unknown", startedAt: "2026-09-26T15:10:00Z", finishedAt: null,
    exitCode: null, progress: 10, progressNote: "stima",
  },
];

const MOCK_LOGS = {
  "20260926-142310-momentum": { totalLines: 3, lines: ["[mock] start", "[mock] trial 1/1", "[mock] done"], eof: true, rotated: false },
  "20260926-150012-meanrev": { totalLines: 2, lines: ["[mock] start", "[mock] trial 12/30"], eof: false, rotated: false },
  "20260926-151000-crash": { totalLines: 1, lines: ["[mock] process lost"], eof: true, rotated: false },
};

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}

function statusBadge(status) {
  const s = String(status ?? "");
  const kind = s === "done" ? "ok" : s === "failed" || s === "cancelled" ? "err" : s === "unknown" ? "warn" : "";
  return el("span", ("badge " + kind).trim(), s);
}

export async function mountRuns(root) {
  if (root.dataset.init === "1") return refreshRuns(root);
  root.dataset.init = "1";
  root.innerHTML = "";
  root.appendChild(el("h2", null, "Runs"));
  const bar = el("div", null);
  const refreshBtn = el("button", null, "Refresh");
  refreshBtn.type = "button";
  refreshBtn.addEventListener("click", () => refreshRuns(root));
  bar.appendChild(refreshBtn);
  bar.appendChild(el("span", "note", " log polling: 2s with ?fromLine=n · reconcile only for “unknown” · progress is a stima"));
  root.appendChild(bar);
  const list = el("div", null, "loading…");
  list.id = "runs-list";
  list.className = "loading";
  root.appendChild(list);
  root.appendChild(el("h3", null, "Run log"));
  const detail = el("div", null);
  detail.id = "runs-detail";
  detail.appendChild(el("p", "note", "select “Log” on a run to tail its log"));
  root.appendChild(detail);
  // Stop polling when leaving the view.
  root.dataset.pollId = "";
  root.dataset.logRun = "";
  await refreshRuns(root);
}

export function stopLogPolling(root) {
  if (root.dataset.pollId) {
    clearInterval(Number(root.dataset.pollId));
    root.dataset.pollId = "";
  }
}

async function refreshRuns(root) {
  stopLogPolling(root);
  const list = root.querySelector("#runs-list");
  list.textContent = "loading…";
  list.className = "loading";
  let runs;
  let mocked = false;
  try {
    runs = await apiGet("/api/runs");
    if (!Array.isArray(runs)) runs = [];
  } catch {
    runs = MOCK_RUNS;
    mocked = true;
  }
  list.innerHTML = "";
  list.className = "";
  if (mocked) list.appendChild(el("p", "note", "MOCK — /api/runs unreachable, showing contract-shaped sample."));
  if (!runs.length) {
    list.appendChild(el("p", "empty", "no runs yet — create one in New Run"));
    return;
  }
  const wrap = el("div", "table-wrap");
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const hr = document.createElement("tr");
  ["id", "symbol", "strategy", "engine", "status", "progress", "started", "actions"].forEach((h) =>
    hr.appendChild(el("th", null, h)),
  );
  thead.appendChild(hr);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  runs.forEach((r) => {
    const tr = document.createElement("tr");
    tr.appendChild(el("td", null, String(r.id ?? "")));
    tr.appendChild(el("td", null, String(r.symbol ?? "")));
    tr.appendChild(el("td", null, String(r.strategy ?? "")));
    tr.appendChild(el("td", null, String(r.engine ?? "")));
    const st = document.createElement("td");
    st.appendChild(statusBadge(r.status));
    tr.appendChild(st);
    // Visible progressNote "stima": never a fake-precise bar.
    const prog = String(r.progress ?? "—") + (r.progressNote === "stima" ? " (stima)" : r.progressNote ? " (" + String(r.progressNote) + ")" : "");
    tr.appendChild(el("td", null, prog));
    tr.appendChild(el("td", null, String(r.startedAt ?? "")));
    const act = document.createElement("td");
    const logBtn = el("button", null, "Log");
    logBtn.type = "button";
    logBtn.addEventListener("click", () => startLog(root, String(r.id)));
    act.appendChild(logBtn);
    const stt = String(r.status ?? "");
    if (stt === "queued" || stt === "running") {
      const c = el("button", null, "Cancel");
      c.type = "button";
      c.addEventListener("click", () => cancelRun(root, String(r.id)));
      act.appendChild(c);
    }
    // Reconcile shown ONLY for unknown (D4 crash recovery).
    if (stt === "unknown") {
      const rc = el("button", null, "Reconcile");
      rc.type = "button";
      rc.title = "mark terminal state after crash";
      rc.addEventListener("click", () => reconcileRun(root, String(r.id)));
      act.appendChild(rc);
    }
    tr.appendChild(act);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  list.appendChild(wrap);
}

async function cancelRun(root, id) {
  try {
    await apiPost("/api/runs/" + encodeURIComponent(id) + "/cancel", {});
    toast("cancelled " + id, "ok");
  } catch {
    // Mock path: backend offline — simulate locally, still stop polling per DoD.
    toast("cancel (mock) " + id, "warn");
  }
  // DoD: cancel ferma il polling.
  if (root.dataset.logRun === id) stopLogPolling(root);
  await refreshRuns(root);
}

async function reconcileRun(root, id) {
  const choice = window.prompt("reconcile " + id + " to (done/failed/cancelled)?", "failed");
  if (!choice) return;
  try {
    await apiPost("/api/runs/" + encodeURIComponent(id) + "/reconcile", { status: choice });
    toast("reconciled " + id, "ok");
  } catch {
    toast("reconcile (mock) " + id, "warn");
  }
  await refreshRuns(root);
}

async function fetchLog(id, fromLine) {
  try {
    return await apiGet("/api/runs/" + encodeURIComponent(id) + "/log?fromLine=" + encodeURIComponent(String(fromLine)));
  } catch {
    const m = MOCK_LOGS[id] || { totalLines: 0, lines: [], eof: true, rotated: false };
    if (fromLine >= m.totalLines) return { totalLines: m.totalLines, lines: [], eof: m.eof, rotated: false };
    return { totalLines: m.totalLines, lines: m.lines.slice(fromLine), eof: m.eof, rotated: false };
  }
}

async function startLog(root, id) {
  stopLogPolling(root);
  const detail = root.querySelector("#runs-detail");
  detail.innerHTML = "";
  detail.appendChild(el("h4", null, "log: " + id));
  const meta = el("p", "note", "fromLine=0 · polling every 2s");
  detail.appendChild(meta);
  const pre = document.createElement("pre");
  pre.tabIndex = 0;
  detail.appendChild(pre);
  const stopBtn = el("button", null, "Stop");
  stopBtn.type = "button";
  stopBtn.addEventListener("click", () => {
    stopLogPolling(root);
    meta.textContent = "stopped at fromLine=" + cursor;
  });
  detail.appendChild(stopBtn);

  let cursor = 0;
  root.dataset.logRun = id;
  const tick = async () => {
    try {
      const data = await fetchLog(id, cursor);
      if (data && data.rotated) {
        pre.textContent = "";
        cursor = 0;
        meta.textContent = "rotated=true — log truncated server-side, restarted at 0";
      }
      const lines = data && Array.isArray(data.lines) ? data.lines : [];
      lines.forEach((ln) => {
        // textContent-safe append (never innerHTML with log data).
        pre.appendChild(document.createTextNode(String(ln) + "\n"));
      });
      if (typeof data.totalLines === "number") cursor = data.totalLines;
      else cursor += lines.length;
      meta.textContent =
        "fromLine=" + cursor + " totalLines=" + String(data.totalLines ?? "?") +
        " eof=" + String(!!data.eof) + " rotated=" + String(!!data.rotated) + " · polling every 2s";
      pre.scrollTop = pre.scrollHeight;
      if (data.eof) {
        stopLogPolling(root);
        meta.textContent += " · stopped (eof)";
      }
    } catch (e) {
      meta.textContent = "log error: " + (e && e.message ? e.message : String(e));
      stopLogPolling(root);
    }
  };
  await tick();
  if (detail.isConnected) {
    const timer = setInterval(tick, 2000);
    root.dataset.pollId = String(timer);
  }
}
