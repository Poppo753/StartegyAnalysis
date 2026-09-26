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
  root.appendChild(el("h2", null, "Report"));
  root.appendChild(
    el("p", "note", "Full HTML report comes from the existing /api/report endpoint (F3/F5 degrade to “not available” as today)."),
  );

  const bar = el("div");
  const lab = document.createElement("label");
  lab.appendChild(document.createTextNode("Symbol "));
  const sym = document.createElement("input");
  sym.id = "rep-symbol";
  sym.value = "DCRUSDT";
  sym.size = 10;
  lab.appendChild(sym);
  bar.appendChild(lab);
  const load = el("button", null, "Load report");
  load.type = "button";
  bar.appendChild(load);
  const open = document.createElement("a");
  open.id = "rep-open";
  open.target = "_blank";
  open.rel = "noopener";
  open.textContent = "open full report";
  open.href = "/api/report?symbol=" + encodeURIComponent(sym.value);
  bar.appendChild(open);
  root.appendChild(bar);

  const frame = document.createElement("iframe");
  frame.id = "rep-frame";
  frame.className = "report-frame";
  // Sandboxed embed per D5 (no scripts from report needed).
  frame.setAttribute("sandbox", "allow-same-origin");
  frame.title = "backtest report";
  frame.src = "/api/report?symbol=" + encodeURIComponent(sym.value);
  root.appendChild(frame);
  const err = el("p", "field-error", "");
  err.id = "rep-error";
  root.appendChild(err);

  load.addEventListener("click", () => {
    const s = sym.value.trim() || "DCRUSDT";
    const url = "/api/report?symbol=" + encodeURIComponent(s);
    err.textContent = "";
    open.href = url;
    frame.src = url;
  });
  frame.addEventListener("error", () => {
    err.textContent = "report failed to load";
  });

  // Optuna block: always a plain link; badge upgrades best-effort.
  root.appendChild(el("h3", null, "Optuna"));
  const obox = el("div");
  const link = document.createElement("a");
  link.id = "rep-optuna-link";
  link.target = "_blank";
  link.rel = "noopener";
  link.href = optunaBase();
  link.textContent = "open Optuna dashboard (:8080)";
  obox.appendChild(link);
  obox.appendChild(document.createTextNode(" "));
  const badge = el("span", "badge", "status unknown");
  badge.id = "rep-optuna-badge";
  obox.appendChild(badge);
  root.appendChild(obox);

  // BEST-EFFORT: raw fetch (no toast), any failure -> plain link, no crash.
  refreshOptunaBadge(badge);
}

async function refreshOptunaBadge(badge) {
  try {
    const res = await fetch("/api/optuna-status", { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    const running = !!(data && data.running);
    badge.textContent = running ? "optuna: running" : "optuna: stopped";
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
    badge.textContent = "optuna: status n/a";
    badge.className = "badge";
  }
}
