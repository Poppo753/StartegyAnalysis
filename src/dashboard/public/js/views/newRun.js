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
  const header = el("div", "page-header");
  const title = el("div");
  title.append(el("p", "eyebrow", "Configurazione"), el("h2", null, "Nuovo backtest"), el("p", "page-subtitle", "Scegli mercato e strategia, regola i parametri e avvia una nuova analisi."));
  const btn = el("button", null, "Ricarica opzioni");
  btn.type = "button";
  btn.addEventListener("click", () => refreshNewRun(root));
  header.append(title, btn);
  root.appendChild(header);
  const box = el("div", null, "loading…");
  box.id = "newrun-box";
  box.className = "loading";
  root.appendChild(box);
  await refreshNewRun(root);
}

async function refreshNewRun(root) {
  const box = root.querySelector("#newrun-box");
  box.innerHTML = "";
  box.textContent = "loading…";
  box.className = "loading";
  let cfg;
  try {
    cfg = await apiGet("/api/config");
  } catch {
    box.className = "panel error";
    box.textContent = "Impossibile caricare le opzioni. Verifica la connessione al server e riprova.";
    return;
  }
  box.innerHTML = "";
  box.className = "";
  box.appendChild(buildForm(cfg));
}

export function buildForm(cfg) {
  const form = document.createElement("form");
  form.id = "newrun-form";
  form.noValidate = true;
  form.className = "panel";
  const basics = el("div", "form-section");
  const basicsHeading = el("div", "form-section-title");
  basicsHeading.append(el("h3", null, "01 / Impostazioni principali"), el("p", null, "Mercato, strategia e motore di esecuzione"));
  basics.append(basicsHeading);
  const basicsGrid = el("div", "form-grid");
  basics.append(basicsGrid);
  form.append(basics);
  const extras = el("div", "form-section");
  const extrasHeading = el("div", "form-section-title");
  extrasHeading.append(el("h3", null, "02 / Parametri avanzati"), el("p", null, "Ottimizzazione e validazione della strategia"));
  extras.append(extrasHeading);
  const extrasGrid = el("div", "form-grid");
  extras.append(extrasGrid);
  form.append(extras);
  const names = { symbol: "Simbolo", dataset: "Dati e periodo", strategy: "Strategia", engine: "Motore", search: "Metodo di ricerca", "n-trials": "Numero di prove", jobs: "Processi paralleli", "validation-mode": "Tipo di validazione" };
  const displayName = (name) => names[name] || name.replaceAll(/[-_]/g, " ").replace(/^./, c => c.toUpperCase());

  const addSelect = (name, labelText, options, def) => {
    const wrap = el("div", "field");
    const lab = document.createElement("label");
    lab.textContent = displayName(labelText);
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
    basicsGrid.appendChild(wrap);
    return sel;
  };

  const symbols = Array.isArray(cfg.datasetSymbols) ? cfg.datasetSymbols : (Array.isArray(cfg.symbols) ? cfg.symbols : []);
  const strategies = Array.isArray(cfg.strategies) ? cfg.strategies : [];
  const engines = Array.isArray(cfg.engine) ? cfg.engine : [];
  const symbolSelect = addSelect("symbol", "symbol", symbols, symbols[0]);
  const datasetSelect = addSelect("dataset", "dataset", [], "");
  const strategySelect = addSelect("strategy", "strategy", strategies, strategies[0]);
  const engineSelect = addSelect("engine", "engine", engines, engines[0]);
  function updateDatasets() {
    datasetSelect.innerHTML = "";
    const info = (cfg.symbolAvailability || []).find((item) => item.symbol === symbolSelect.value);
    const datasets = Array.isArray(info?.datasets) ? info.datasets : [];
    datasets.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.file;
      option.textContent = `${item.timeframe} · ${item.start} → ${item.end}`;
      datasetSelect.appendChild(option);
    });
    const preferred = datasets.find((item) => cfg.configuredRange &&
      item.start === cfg.configuredRange.start && item.end === cfg.configuredRange.end);
    if (preferred) datasetSelect.value = preferred.file;
    datasetSelect.disabled = datasets.length === 0;
  }
  symbolSelect.addEventListener("change", updateDatasets);
  updateDatasets();
  const prototypes = (cfg.strategyCatalog || []).filter((item) => !item.runnable).map((item) => item.name);
  if (prototypes.length) basics.appendChild(el("p", "note", `Strategie in sviluppo, non avviabili: ${prototypes.join(", ")}.`));

  // Generic flag rendering: every entry in cfg.flags becomes a field.
  // Unknown future types fall back to a text input so they still appear.
  const flags = Array.isArray(cfg.flags) ? cfg.flags : [];
  flags.forEach((f) => {
    const wrap = el("div", "field");
    const lab = document.createElement("label");
    const fname = String(f.name ?? "flag");
    lab.textContent = displayName(fname);
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
      wrap.appendChild(el("span", "note", "Intervallo: " + String(f.min ?? "−∞") + " – " + String(f.max ?? "+∞")));
    }
    wrap.appendChild(el("span", "field-error", ""));
    extrasGrid.appendChild(wrap);
  });

  const optionGroups = [
    ["grid", "03 / Griglia dei parametri", "Valori della strategia e modalità dinamica"],
    ["trading", "04 / Trading e costi", "Capitale, posizione, durata e costi"],
    ["engine", "05 / Motore e ricerca", "Impostazioni Fast, GPU e Optuna"],
    ["filters", "06 / Filtri", "Soglie applicate ai risultati"],
  ];
  optionGroups.forEach(([group, title, description]) => {
    const specs = (cfg.runOptions || []).filter((option) => option.group === group);
    if (!specs.length) return;
    const details = el("details", "run-option-group");
    details.dataset.optionGroup = group;
    const summary = el("summary", null, title);
    details.append(summary, el("p", "note", `${description}. Lascia vuoto per usare il valore del file .env.`));
    const grid = el("div", "form-grid");
    specs.forEach((spec) => {
      const field = el("div", "field");
      field.dataset.optionKey = spec.key;
      const label = el("label", null, spec.label);
      const id = `nr-option-${spec.key}`;
      label.htmlFor = id;
      let control;
      if (spec.type === "bool" || spec.type === "enum") {
        control = document.createElement("select");
        const choices = spec.type === "bool" ? ["true", "false"] : (spec.values || []);
        [["", "Usa .env"], ...choices.map((value) => [value, value])].forEach(([value, text]) => {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = text;
          control.appendChild(option);
        });
      } else {
        control = document.createElement("input");
        control.type = spec.type === "int" || spec.type === "float" ? "number" : "text";
        if (control.type === "number") control.step = spec.type === "int" ? "1" : "any";
        if (spec.min !== undefined) control.min = String(spec.min);
        if (spec.max !== undefined) control.max = String(spec.max);
        control.placeholder = spec.current ? `Attuale: ${spec.current}` : "Usa .env";
      }
      control.id = id;
      control.name = `option:${spec.key}`;
      label.appendChild(control);
      field.appendChild(label);
      if (spec.hint) field.appendChild(el("span", "note", spec.hint));
      grid.appendChild(field);
    });
    details.appendChild(grid);
    form.appendChild(details);
  });

  const searchSpaceDetails = el("details", "run-option-group");
  searchSpaceDetails.id = "nr-search-space";
  searchSpaceDetails.append(el("summary", null, "07 / Limiti della ricerca Optuna"),
    el("p", "note", "Restringi i limiti dei parametri della strategia selezionata. I campi vuoti mantengono i limiti originali."));
  const searchSpaceGrid = el("div", "form-grid");
  searchSpaceDetails.appendChild(searchSpaceGrid);
  form.appendChild(searchSpaceDetails);
  const searchSelect = form.querySelector('[name="flag:search"]');
  function updateSearchSpace() {
    searchSpaceDetails.hidden = searchSelect?.value !== "optuna";
    searchSpaceGrid.innerHTML = "";
    const info = (cfg.strategyCatalog || []).find((item) => item.name === strategySelect.value);
    for (const [key, bounds] of Object.entries(info?.parameterSpace || {})) {
      const field = el("div", "field");
      field.appendChild(el("label", null, key.replaceAll("_", " ")));
      const pair = el("div", "bound-pair");
      ["min", "max"].forEach((bound, index) => {
        const input = document.createElement("input");
        input.type = "number";
        input.step = bounds[2].startsWith("int") ? "1" : "any";
        input.placeholder = `${bound === "min" ? "Min" : "Max"}: ${bounds[index]}`;
        input.dataset.searchKey = key;
        input.dataset.bound = bound;
        input.dataset.original = String(bounds[index]);
        input.setAttribute("aria-label", `${key} ${bound}`);
        pair.appendChild(input);
      });
      field.appendChild(pair);
      searchSpaceGrid.appendChild(field);
    }
  }

  function updateCompatibility() {
    const info = (cfg.strategyCatalog || []).find((item) => item.name === strategySelect.value);
    for (const option of engineSelect.options) {
      option.disabled = !!info && option.value !== "standard" && !info[option.value];
    }
    if (engineSelect.selectedOptions[0]?.disabled) engineSelect.value = "standard";
    if (searchSelect) {
      for (const option of searchSelect.options) option.disabled = option.value === "optuna" && engineSelect.value !== "standard";
      if (searchSelect.selectedOptions[0]?.disabled) searchSelect.value = "grid";
    }
    for (const spec of cfg.runOptions || []) {
      const field = [...form.querySelectorAll("[data-option-key]")].find((item) => item.dataset.optionKey === spec.key);
      if (!field) continue;
      field.hidden = !!((spec.strategies && !spec.strategies.includes(strategySelect.value)) ||
        (spec.engines && !spec.engines.includes(engineSelect.value)) ||
        (spec.searches && !spec.searches.includes(searchSelect?.value)) ||
        (searchSelect?.value === "optuna" && spec.optunaParameter && info?.parameterSpace?.[spec.optunaParameter]));
    }
    for (const group of form.querySelectorAll("[data-option-group]")) {
      group.hidden = ![...group.querySelectorAll("[data-option-key]")].some((field) => !field.hidden);
    }
    const optunaOnly = searchSelect?.value === "optuna";
    for (const name of ["n-trials", "jobs"]) {
      const input = form.querySelector(`[name="${toFieldKey(name)}"]`);
      if (input) input.closest(".field").hidden = !optunaOnly;
    }
    updateSearchSpace();
  }
  strategySelect.addEventListener("change", updateCompatibility);
  engineSelect.addEventListener("change", updateCompatibility);
  searchSelect?.addEventListener("change", updateCompatibility);
  updateCompatibility();

  const err = el("p", "field-error", "");
  err.id = "nr-error";
  err.setAttribute("role", "alert");
  const footer = el("div", "form-footer");
  const info = el("div");
  info.append(el("p", null, "Controlla i parametri prima di avviare l'esecuzione."), err);
  const submit = el("button", null, "Avvia backtest →");
  submit.type = "submit";
  footer.append(info, submit);
  form.appendChild(footer);

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
  const dataset = get("dataset");
  if (Array.isArray(cfg.datasetSymbols) && !dataset) return { payload: null, error: "Seleziona dati e periodo disponibili" };
  const allowedSymbols = Array.isArray(cfg.datasetSymbols) ? cfg.datasetSymbols : cfg.symbols;
  if (Array.isArray(allowedSymbols) && allowedSymbols.length && !allowedSymbols.map(String).includes(symbol))
    return { payload: null, error: "unknown symbol: " + symbol };
  if (Array.isArray(cfg.strategies) && cfg.strategies.length && !cfg.strategies.map(String).includes(strategy))
    return { payload: null, error: "unknown strategy: " + strategy };
  if (Array.isArray(cfg.engine) && cfg.engine.length && !cfg.engine.map(String).includes(engine))
    return { payload: null, error: "unknown engine: " + engine };
  if (INJECTION_RE.test(symbol + strategy + engine)) return { payload: null, error: "rejected: possible injection" };

  // Payload: contract keys + verbatim flag names (extras survive with zero code change).
  const payload = { symbol, strategy, engine };
  if (dataset) payload.dataset = dataset;
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
  const overrides = {};
  for (const option of cfg.runOptions || []) {
    const field = [...form.querySelectorAll("[data-option-key]")].find((item) => item.dataset.optionKey === option.key);
    if (field?.hidden) continue;
    const raw = get(`option:${option.key}`);
    if (raw) overrides[option.key] = raw;
  }
  if (Object.keys(overrides).length) payload.overrides = overrides;
  if (payload.search === "optuna") {
    const searchSpace = {};
    const info = (cfg.strategyCatalog || []).find((item) => item.name === strategy);
    for (const [key, bounds] of Object.entries(info?.parameterSpace || {})) {
      const pair = [...form.querySelectorAll("[data-search-key]")].filter((input) => input.dataset.searchKey === key);
      if (pair.length !== 2 || (!pair[0].value.trim() && !pair[1].value.trim())) continue;
      searchSpace[key] = pair.map((input, index) => Number(input.value.trim() || bounds[index]));
    }
    if (Object.keys(searchSpace).length) payload.searchSpace = searchSpace;
  }
  return { payload, error: null };
}
