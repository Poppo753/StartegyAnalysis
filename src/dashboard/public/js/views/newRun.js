/* views/newRun.js — U2-02: form BUILT from /api/config at runtime (data-driven).
 * Proves data-drivenness: MOCK_CONFIG contains one EXTRA fictitious flag
 * ("fictitious-extra-flag") which appears with zero view-code changes because
 * fields are rendered by iterating config.flags generically.
 * Client validation mirrors the allowlist for UX only; server is source of truth.
 */
"use strict";

import { apiGet, apiPost, toast } from "../api.js";

export const MOCK_CONFIG = {
  symbols: ["DCRUSDT", "BTCUSDT"],
  strategies: ["momentum_drop", "mean_reversion"],
  engine: ["standard", "fast", "gpu"],
  flags: [
    { name: "search", type: "enum", values: ["grid", "optuna"], default: "grid" },
    { name: "n-trials", type: "int", min: 1, max: 5000, default: 30 },
    { name: "jobs", type: "int", min: 1, max: 8, default: 1 },
    { name: "validation-mode", type: "enum", values: ["off", "purged", "cpcv", "walkforward"], default: "off" },
    // EXTRA fictitious flag: must render with zero view-code changes.
    { name: "fictitious-extra-flag", type: "enum", values: ["alpha", "beta"], default: "alpha" },
  ],
};

const INJECTION_RE = /(;|&&|\$\(|`|--)/;

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}

function toFieldKey(name) {
  return "flag:" + name;
}

export async function mountNewRun(root) {
  if (root.dataset.init === "1") return refreshNewRun(root);
  root.dataset.init = "1";
  root.innerHTML = "";
  root.appendChild(el("h2", null, "New run · data-driven form"));
  root.appendChild(el("p", "note", "Fields are built from GET /api/config at runtime. A new CLI flag appears automatically."));
  const box = el("div", null, "loading…");
  box.id = "newrun-box";
  box.className = "loading";
  root.appendChild(box);
  const btn = el("button", null, "Reload config");
  btn.type = "button";
  btn.addEventListener("click", () => refreshNewRun(root));
  root.appendChild(btn);
  await refreshNewRun(root);
}

async function refreshNewRun(root) {
  const box = root.querySelector("#newrun-box");
  box.innerHTML = "";
  box.textContent = "loading…";
  box.className = "loading";
  let cfg;
  let mocked = false;
  try {
    cfg = await apiGet("/api/config");
  } catch {
    cfg = MOCK_CONFIG;
    mocked = true;
  }
  box.innerHTML = "";
  box.className = "";
  if (mocked) box.appendChild(el("p", "note", "MOCK config — /api/config unreachable. Includes EXTRA flag “fictitious-extra-flag”."));
  box.appendChild(buildForm(cfg));
}

export function buildForm(cfg) {
  const form = document.createElement("form");
  form.id = "newrun-form";
  form.noValidate = true;

  const addSelect = (name, labelText, options, def) => {
    const wrap = el("div", "field");
    const lab = document.createElement("label");
    lab.textContent = labelText + " ";
    lab.htmlFor = "nr-" + name;
    const sel = document.createElement("select");
    sel.id = "nr-" + name;
    sel.name = name;
    (options || []).forEach((o) => {
      const op = document.createElement("option");
      op.value = String(o);
      op.textContent = String(o);
      if (String(o) === String(def)) op.selected = true;
      sel.appendChild(op);
    });
    lab.appendChild(sel);
    wrap.appendChild(lab);
    wrap.appendChild(el("span", "field-error", ""));
    form.appendChild(wrap);
    return sel;
  };

  const symbols = Array.isArray(cfg.symbols) ? cfg.symbols : [];
  const strategies = Array.isArray(cfg.strategies) ? cfg.strategies : [];
  const engines = Array.isArray(cfg.engine) ? cfg.engine : [];
  addSelect("symbol", "symbol", symbols, symbols[0]);
  addSelect("strategy", "strategy", strategies, strategies[0]);
  addSelect("engine", "engine", engines, engines[0]);

  // Generic flag rendering: every entry in cfg.flags becomes a field.
  // Unknown future types fall back to a text input so they still appear.
  const flags = Array.isArray(cfg.flags) ? cfg.flags : [];
  flags.forEach((f) => {
    const wrap = el("div", "field");
    const lab = document.createElement("label");
    const fname = String(f.name ?? "flag");
    lab.textContent = fname + " ";
    lab.htmlFor = "nr-" + toFieldKey(fname);
    let input;
    if (f.type === "enum" && Array.isArray(f.values)) {
      input = document.createElement("select");
      f.values.forEach((v) => {
        const op = document.createElement("option");
        op.value = String(v);
        op.textContent = String(v);
        if (String(v) === String(f.default)) op.selected = true;
        input.appendChild(op);
      });
    } else if (f.type === "int" || f.type === "float" || f.type === "number") {
      input = document.createElement("input");
      input.type = "number";
      if (f.min !== undefined) input.min = String(f.min);
      if (f.max !== undefined) input.max = String(f.max);
      if (f.step !== undefined) input.step = String(f.step);
      else if (f.type === "int") input.step = "1";
      else input.step = "any";
      if (f.default !== undefined) input.value = String(f.default);
    } else if (f.type === "bool") {
      input = document.createElement("select");
      ["true", "false"].forEach((v) => {
        const op = document.createElement("option");
        op.value = v;
        op.textContent = v;
        if (String(f.default) === v) op.selected = true;
        input.appendChild(op);
      });
    } else {
      // Fallback for any future/unknown flag type (incl. fictitious extras).
      input = document.createElement("input");
      input.type = "text";
      if (f.default !== undefined) input.value = String(f.default);
      if (f.values && Array.isArray(f.values)) {
        // If values present but type unknown, offer datalist without constraining.
        const dl = document.createElement("datalist");
        dl.id = "nr-dl-" + fname;
        f.values.forEach((v) => {
          const op = document.createElement("option");
          op.value = String(v);
          dl.appendChild(op);
        });
        input.setAttribute("list", "nr-dl-" + fname);
        wrap.appendChild(dl);
      }
    }
    input.id = "nr-" + toFieldKey(fname);
    input.name = toFieldKey(fname);
    input.dataset.flagName = fname;
    input.dataset.flagType = String(f.type ?? "string");
    if (f.min !== undefined) input.dataset.min = String(f.min);
    if (f.max !== undefined) input.dataset.max = String(f.max);
    if (f.values) input.dataset.values = JSON.stringify(f.values);
    lab.appendChild(input);
    wrap.appendChild(lab);
    if (f.min !== undefined || f.max !== undefined) {
      wrap.appendChild(el("span", "note", " range " + String(f.min ?? "-inf") + "…" + String(f.max ?? "+inf")));
    }
    wrap.appendChild(el("span", "field-error", ""));
    form.appendChild(wrap);
  });

  const err = el("p", "field-error", "");
  err.id = "nr-error";
  form.appendChild(err);
  const submit = el("button", null, "Start run");
  submit.type = "submit";
  form.appendChild(submit);

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    err.textContent = "";
    const { payload, error } = collectAndValidate(form, cfg);
    if (error) {
      err.textContent = error;
      toast(error);
      return;
    }
    submit.disabled = true;
    try {
      const created = await apiPost("/api/runs", payload);
      toast("run created: " + (created && created.id ? created.id : "(ok)"), "ok");
      // Redirect to Runs view per contract.
      window.location.hash = "#/runs";
    } catch {
      // apiPost already toasted (400 {error} included).
    } finally {
      submit.disabled = false;
    }
  });
  return form;
}

export function collectAndValidate(form, cfg) {
  const get = (name) => {
    const n = form.querySelector('[name="' + CSS.escape(name) + '"]');
    return n ? String(n.value ?? "").trim() : "";
  };
  const symbol = get("symbol");
  const strategy = get("strategy");
  const engine = get("engine");
  if (!symbol) return { payload: null, error: "symbol is required" };
  if (!strategy) return { payload: null, error: "strategy is required" };
  if (!engine) return { payload: null, error: "engine is required" };
  if (Array.isArray(cfg.symbols) && cfg.symbols.length && !cfg.symbols.map(String).includes(symbol))
    return { payload: null, error: "unknown symbol: " + symbol };
  if (Array.isArray(cfg.strategies) && cfg.strategies.length && !cfg.strategies.map(String).includes(strategy))
    return { payload: null, error: "unknown strategy: " + strategy };
  if (Array.isArray(cfg.engine) && cfg.engine.length && !cfg.engine.map(String).includes(engine))
    return { payload: null, error: "unknown engine: " + engine };
  if (INJECTION_RE.test(symbol + strategy + engine)) return { payload: null, error: "rejected: possible injection" };

  // Payload: contract keys + verbatim flag names (extras survive with zero code change).
  const payload = { symbol, strategy, engine };
  const flags = Array.isArray(cfg.flags) ? cfg.flags : [];
  for (const f of flags) {
    const fname = String(f.name);
    const raw = get(toFieldKey(fname));
    if (INJECTION_RE.test(raw)) return { payload: null, error: "rejected: possible injection in " + fname };
    if (f.type === "enum" && Array.isArray(f.values)) {
      if (!f.values.map(String).includes(raw)) return { payload: null, error: "invalid value for " + fname + ": " + raw };
      payload[fname] = raw;
    } else if (f.type === "int") {
      const n = Number(raw);
      if (!Number.isInteger(n)) return { payload: null, error: fname + " must be an integer" };
      if (f.min !== undefined && n < Number(f.min)) return { payload: null, error: fname + " below min " + f.min };
      if (f.max !== undefined && n > Number(f.max)) return { payload: null, error: fname + " above max " + f.max };
      payload[fname] = n;
    } else if (f.type === "float" || f.type === "number") {
      const n = Number(raw);
      if (!Number.isFinite(n)) return { payload: null, error: fname + " must be a number" };
      if (f.min !== undefined && n < Number(f.min)) return { payload: null, error: fname + " below min " + f.min };
      if (f.max !== undefined && n > Number(f.max)) return { payload: null, error: fname + " above max " + f.max };
      payload[fname] = n;
    } else {
      payload[fname] = raw;
    }
  }
  // Back-compat camelCase aliases for the frozen POST contract.
  if (payload["search"] !== undefined) payload.search = payload["search"];
  if (payload["n-trials"] !== undefined) payload.nTrials = payload["n-trials"];
  if (payload["jobs"] !== undefined) payload.jobs = payload["jobs"];
  if (payload["validation-mode"] !== undefined) payload.validationMode = payload["validation-mode"];
  return { payload, error: null };
}
