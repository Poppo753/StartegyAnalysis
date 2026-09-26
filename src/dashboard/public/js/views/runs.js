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
  const labels = { done: "Completata", failed: "Fallita", cancelled: "Annullata", running: "In corso", queued: "In coda", unknown: "Da verificare" };
  return el("span", ("badge " + kind).trim(), labels[s] || s);
}

export async function mountRuns(root) {
  if (root.dataset.init === "1") return refreshRuns(root);
  root.dataset.init = "1";
  root.innerHTML = "";
  const header = el("div", "page-header");
  const title = el("div");
  title.append(el("p", "eyebrow", "Monitoraggio"), el("h2", null, "Esecuzioni"), el("p", "page-subtitle", "Segui l'avanzamento dei backtest e apri i log di dettaglio."));
  const bar = el("div", "page-actions");
  const refreshBtn = el("button", null, "Aggiorna elenco");
  refreshBtn.type = "button";
  refreshBtn.addEventListener("click", () => refreshRuns(root));
  bar.appendChild(refreshBtn);
  const link = el("a", "btn btn-primary", "+ Nuovo backtest"); link.href = "#/new";
  bar.appendChild(link);
  header.append(title, bar); root.appendChild(header);
  const panel = el("section", "panel");
  const ph = el("div", "panel-header");
  const phText = el("div"); phText.append(el("h3", null, "Tutte le esecuzioni"), el("p", null, "L'avanzamento mostrato è una stima."));
  ph.append(phText); panel.append(ph);
  const list = el("div", null, "loading…");
  list.id = "runs-list";
  list.className = "loading";
  panel.appendChild(list); root.append(panel);
  const logPanel = el("section", "panel");
  const logHead = el("div", "panel-header"); logHead.append(el("h3", null, "Log esecuzione"));
  const detail = el("div", "panel-body");
  detail.id = "runs-detail";
  detail.appendChild(el("p", "note", "Seleziona “Log” su un'esecuzione per vedere i messaggi in tempo reale."));
  logPanel.append(logHead, detail); root.append(logPanel);
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
  try {
    runs = await apiGet("/api/runs");
    if (!Array.isArray(runs)) runs = [];
  } catch {
    list.className = "error";
    list.textContent = "Impossibile caricare le esecuzioni. Verifica il server e riprova.";
    return;
  }
  list.innerHTML = "";
  list.className = "";
  if (!runs.length) {
    const empty = el("div", "empty");
    empty.append(el("p", null, "Non ci sono ancora esecuzioni."), el("a", "text-link empty-action", "Crea il primo backtest →"));
    empty.querySelector("a").href = "#/new";
    list.appendChild(empty);
    return;
  }
  const wrap = el("div", "table-wrap");
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const hr = document.createElement("tr");
  ["Esecuzione", "Simbolo", "Strategia", "Motore", "Stato", "Avanzamento", "Avviata", "Azioni"].forEach((h) =>
    hr.appendChild(el("th", null, h)),
  );
  thead.appendChild(hr);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  runs.forEach((r) => {
    const tr = document.createElement("tr");
    tr.appendChild(el("td", "run-id", String(r.id ?? "")));
    tr.appendChild(el("td", null, String(r.symbol ?? "")));
    tr.appendChild(el("td", null, String(r.strategy ?? "").replaceAll("_", " ")));
    tr.appendChild(el("td", null, String(r.engine ?? "")));
    const st = document.createElement("td");
    st.appendChild(statusBadge(r.status));
    tr.appendChild(st);
    // Visible progressNote "stima": never a fake-precise bar.
    const prog = el("td");
    const progBox = el("div", "progress");
    const p = Number(r.progress);
    if (Number.isFinite(p)) {
      const track = el("span", "progress-track"), fill = el("span", "progress-fill");
      fill.style.width = String(Math.max(0, Math.min(100, p))) + "%";
      track.append(fill); progBox.append(track);
    }
    progBox.append(el("span", "progress-label", Number.isFinite(p) ? Math.round(p) + "% · stima" : "—"));
    prog.append(progBox); tr.append(prog);
    const started = r.startedAt ? new Date(r.startedAt) : null;
    tr.appendChild(el("td", null, started && !Number.isNaN(started.valueOf()) ? started.toLocaleString("it-IT") : "—"));
    const act = document.createElement("td");
    const actions = el("div", "row-actions");
    const logBtn = el("button", "btn-small", "Log");
    logBtn.type = "button";
    logBtn.addEventListener("click", () => startLog(root, String(r.id)));
    actions.appendChild(logBtn);
    const stt = String(r.status ?? "");
    if (stt === "queued" || stt === "running") {
      const c = el("button", "btn-small btn-danger", "Annulla");
      c.type = "button";
      c.addEventListener("click", () => cancelRun(root, String(r.id)));
      actions.appendChild(c);
    }
    // Reconcile shown ONLY for unknown (D4 crash recovery).
    if (stt === "unknown") {
      const rc = el("button", "btn-small", "Risolvi stato");
      rc.type = "button";
      rc.title = "mark terminal state after crash";
      rc.addEventListener("click", () => reconcileRun(root, String(r.id)));
      actions.appendChild(rc);
    }
    act.append(actions);
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
    toast("Esecuzione annullata: " + id, "ok");
  } catch {
    return;
  }
  // DoD: cancel ferma il polling.
  if (root.dataset.logRun === id) stopLogPolling(root);
  await refreshRuns(root);
}

async function reconcileRun(root, id) {
  const choice = window.prompt("Stato finale per " + id + " (done, failed, cancelled):", "failed");
  if (!choice) return;
  if (!["done", "failed", "cancelled"].includes(choice)) { toast("Seleziona done, failed o cancelled."); return; }
  try {
    await apiPost("/api/runs/" + encodeURIComponent(id) + "/reconcile", { status: choice });
    toast("Stato aggiornato: " + id, "ok");
  } catch {
    return;
  }
  await refreshRuns(root);
}

async function fetchLog(id, fromLine) {
  return apiGet("/api/runs/" + encodeURIComponent(id) + "/log?fromLine=" + encodeURIComponent(String(fromLine)));
}

async function startLog(root, id) {
  stopLogPolling(root);
  const detail = root.querySelector("#runs-detail");
  detail.innerHTML = "";
  detail.appendChild(el("h4", null, "Esecuzione " + id));
  const meta = el("p", "note", "Caricamento del log…");
  detail.appendChild(meta);
  const pre = document.createElement("pre");
  pre.tabIndex = 0;
  detail.appendChild(pre);
  const stopBtn = el("button", "btn-small", "Interrompi aggiornamento");
  stopBtn.type = "button";
  stopBtn.addEventListener("click", () => {
    stopLogPolling(root);
    meta.textContent = "Aggiornamento interrotto · " + received + " righe ricevute";
  });
  detail.appendChild(stopBtn);

  let cursor = 0;
  let received = 0;
  let dataEof = false;
  let inFlight = false;
  root.dataset.logRun = id;
  const tick = async () => {
    if (inFlight) return;
    inFlight = true;
    try {
      const data = await fetchLog(id, cursor);
      if (data && data.rotated) {
        pre.textContent = "";
        cursor = 0;
        received = 0;
        meta.textContent = "Il file di log è stato sostituito. Lettura ripresa dall'inizio.";
      }
      const lines = data && Array.isArray(data.lines) ? data.lines : [];
      lines.forEach((ln) => {
        // textContent-safe append (never innerHTML with log data).
        pre.appendChild(document.createTextNode(String(ln) + "\n"));
      });
      received += lines.length;
      if (typeof data.nextLine === "number") cursor = data.nextLine;
      else if (typeof data.totalLines === "number") cursor = data.totalLines;
      else cursor += lines.length;
      meta.textContent = received + " righe ricevute" +
        (data.truncated ? " · Altre righe disponibili: il log è ancora in caricamento." : " · Aggiornamento ogni 2 secondi");
      if (data.rotated) meta.textContent = "Il file di log è stato sostituito. " + meta.textContent;
      pre.scrollTop = pre.scrollHeight;
      if (data.eof) {
        dataEof = true;
        stopLogPolling(root);
        meta.textContent += " · Esecuzione terminata.";
      }
    } catch (e) {
      dataEof = true;
      meta.textContent = "Impossibile aggiornare il log: " + (e && e.message ? e.message : String(e));
      stopLogPolling(root);
    } finally {
      inFlight = false;
    }
  };
  await tick();
  if (detail.isConnected && !dataEof) {
    const timer = setInterval(tick, 2000);
    root.dataset.pollId = String(timer);
  }
}
