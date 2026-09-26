/* views/report.js — U2-03: split of app.js report part + Optuna link (best-effort badge).
 * Embeds existing /api/report HTML in a sandboxed iframe + "open" link.
 * Optuna: link to :8080 always; status badge BEST-EFFORT — if /api/optuna-status
 * is missing, show plain link, no crash, no toast spam.
 */
"use strict";

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}

function optunaBase() {
  try {
    const host = window.location.hostname || "127.0.0.1";
    return "http://" + host + ":8080";
  } catch {
    return "http://127.0.0.1:8080";
  }
}

export function mountReport(root) {
  if (root.dataset.init === "1") return;
  root.dataset.init = "1";
  root.innerHTML = "";
  const header = el("div", "page-header");
  const title = el("div");
  title.append(el("p", "eyebrow", "Report"), el("h2", null, "Report dettagliato"), el("p", "page-subtitle", "Consulta il report completo dei backtest per il simbolo selezionato."));
  header.append(title); root.append(header);

  const panel = el("section", "panel");
  const panelHead = el("div", "panel-header");
  const panelTitle = el("div"); panelTitle.append(el("h3", null, "Analisi per simbolo"), el("p", null, "Il report viene generato dai risultati disponibili."));
  panelHead.append(panelTitle); panel.append(panelHead);
  const bar = el("div", "panel-body toolbar");
  const lab = document.createElement("label");
  lab.appendChild(document.createTextNode("Simbolo"));
  const sym = document.createElement("input");
  sym.id = "rep-symbol";
  sym.value = "DCRUSDT";
  sym.size = 10;
  lab.appendChild(sym);
  bar.appendChild(lab);
  const load = el("button", "btn-primary", "Carica report");
  load.type = "button";
  bar.appendChild(load);
  const open = document.createElement("a");
  open.id = "rep-open";
  open.target = "_blank";
  open.rel = "noopener";
  open.className = "text-link";
  open.textContent = "Apri in una nuova scheda ↗";
  open.href = "/api/report?symbol=" + encodeURIComponent(sym.value);
  bar.appendChild(open);
  panel.append(bar);

  const frame = document.createElement("iframe");
  frame.id = "rep-frame";
  frame.className = "report-frame";
  // Sandboxed embed per D5 (no scripts from report needed).
  frame.setAttribute("sandbox", "allow-same-origin");
  frame.title = "Report del backtest";
  frame.src = "/api/report?symbol=" + encodeURIComponent(sym.value);
  panel.append(frame);
  const err = el("p", "field-error", "");
  err.id = "rep-error";
  panel.append(err); root.append(panel);

  load.addEventListener("click", () => {
    const s = sym.value.trim() || "DCRUSDT";
    const url = "/api/report?symbol=" + encodeURIComponent(s);
    err.textContent = "";
    open.href = url;
    frame.src = url;
  });
  frame.addEventListener("error", () => {
    err.textContent = "Impossibile caricare il report.";
  });

  const optunaPanel = el("section", "panel");
  const optunaHead = el("div", "panel-header");
  const optunaTitle = el("div"); optunaTitle.append(el("h3", null, "Ottimizzazione Optuna"), el("p", null, "Apri la dashboard Optuna se il servizio locale è attivo."));
  optunaHead.append(optunaTitle); optunaPanel.append(optunaHead);
  const obox = el("div", "panel-body insight-strip");
  const link = document.createElement("a");
  link.id = "rep-optuna-link";
  link.target = "_blank";
  link.rel = "noopener";
  link.href = optunaBase();
  link.textContent = "Apri Optuna ↗";
  obox.appendChild(link);
  obox.appendChild(document.createTextNode(" "));
  const badge = el("span", "badge", "Stato sconosciuto");
  badge.id = "rep-optuna-badge";
  obox.appendChild(badge);
  optunaPanel.append(obox); root.append(optunaPanel);

  // BEST-EFFORT: raw fetch (no toast), any failure -> plain link, no crash.
  refreshOptunaBadge(badge);
}

async function refreshOptunaBadge(badge) {
  try {
    const res = await fetch("/api/optuna-status", { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    const running = !!(data && data.running);
    badge.textContent = running ? "Attivo" : "Non attivo";
    badge.className = "badge " + (running ? "ok" : "warn");
    if (data && data.port) {
      try {
        const url = new URL(badge.parentNode.querySelector("a").href);
        url.port = String(data.port);
        badge.parentNode.querySelector("a").href = url.toString();
      } catch {
        // keep plain link
      }
    }
  } catch {
    // Missing endpoint -> plain link, no crash (contract: BEST-EFFORT).
    badge.textContent = "Stato non disponibile";
    badge.className = "badge";
  }
}
