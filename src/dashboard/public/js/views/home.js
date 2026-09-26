"use strict";
import { apiGet } from "../api.js";

export const MOCK_STATUS = {
  python: "3.10.0 (mock)", venvOk: true, diskFreeGb: 412.3, studyDb: true,
  lastRuns: [{ id: "20260926-142310-momentum", status: "done", symbol: "DCRUSDT", strategy: "momentum_drop" }],
};
function el(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; }
function status(s) { const v = String(s ?? "unknown"); const labels = { done: "Completata", failed: "Fallita", cancelled: "Annullata", running: "In corso", queued: "In coda", unknown: "Da verificare" }; return el("span", "badge " + (v === "done" ? "ok" : v === "failed" || v === "cancelled" ? "err" : v === "unknown" ? "warn" : ""), labels[v] || v); }
function boolBadge(v) { return el("span", "badge " + (v ? "ok" : "err"), v ? "Pronto" : "Non disponibile"); }
function metric(name, value) { const d = el("div", "kv"); d.append(el("div", "k", name)); const v = el("div", "v"); if (value instanceof Node) v.append(value); else v.textContent = value; d.append(v); return d; }

export async function mountHome(root) {
  if (root.dataset.init === "1") return refreshHome(root);
  root.dataset.init = "1";
  root.innerHTML = "";
  const header = el("div", "page-header");
  const title = el("div");
  title.append(el("p", "eyebrow", "Panoramica"), el("h2", null, "Il tuo workspace"), el("p", "page-subtitle", "Controlla l'ambiente e riprendi dalle ultime esecuzioni."));
  const actions = el("div", "page-actions");
  const refresh = el("button", null, "Aggiorna stato"); refresh.type = "button"; refresh.addEventListener("click", () => refreshHome(root));
  const newRun = el("a", "btn btn-primary", "+ Nuovo backtest"); newRun.href = "#/new";
  actions.append(refresh, newRun); header.append(title, actions); root.append(header);
  root.append(el("p", "section-caption", "Stato del sistema"));
  const state = el("div", "grid2"); state.id = "home-status"; root.append(state);
  const panel = el("section", "panel"); panel.style.marginTop = "28px";
  const ph = el("div", "panel-header"); const phText = el("div"); phText.append(el("h3", null, "Ultime esecuzioni"), el("p", null, "Le attività più recenti del workspace."));
  const link = el("a", "text-link", "Tutte le esecuzioni →"); link.href = "#/runs"; ph.append(phText, link);
  const body = el("div"); body.id = "home-runs"; panel.append(ph, body); root.append(panel);
  await refreshHome(root);
}

async function refreshHome(root) {
  const sBox = root.querySelector("#home-status"), rBox = root.querySelector("#home-runs");
  sBox.textContent = "Caricamento dello stato…"; sBox.className = "grid2 loading";
  rBox.textContent = "Caricamento esecuzioni…"; rBox.className = "loading";
  let data;
  try { data = await apiGet("/api/status"); }
  catch {
    sBox.className = "panel error"; sBox.textContent = "Stato del sistema non disponibile. Verifica che il server della dashboard sia attivo e riprova.";
    rBox.className = "empty"; rBox.textContent = "Impossibile recuperare le esecuzioni.";
    return;
  }
  sBox.className = "grid2"; sBox.innerHTML = "";
  sBox.append(
    metric("Python", String(data.python ?? "N/D")),
    metric("Ambiente virtuale", boolBadge(!!data.venvOk)),
    metric("Spazio libero", typeof data.diskFreeGb === "number" ? data.diskFreeGb.toLocaleString("it-IT", {maximumFractionDigits: 1}) + " GB" : "N/D"),
    metric("Database studi", boolBadge(!!data.studyDb)),
  );
  rBox.innerHTML = ""; rBox.className = "";
  const runs = Array.isArray(data.lastRuns) ? data.lastRuns : [];
  if (!runs.length) { rBox.className = "empty"; rBox.textContent = "Nessuna esecuzione recente. Crea un backtest per iniziare."; return; }
  const wrap = el("div", "table-wrap"), table = el("table"), thead = el("thead"), hr = el("tr");
  ["Esecuzione", "Stato", "Simbolo", "Strategia"].forEach(h => hr.append(el("th", null, h))); thead.append(hr); table.append(thead);
  const tbody = el("tbody");
  runs.forEach(r => { const tr = el("tr"); tr.append(el("td", "run-id", String(r.id ?? ""))); const st = el("td"); st.append(status(r.status)); tr.append(st, el("td", null, String(r.symbol ?? r.sym ?? "")), el("td", null, String(r.strategy ?? "").replaceAll("_", " "))); tbody.append(tr); });
  table.append(tbody); wrap.append(table); rBox.append(wrap);
}
