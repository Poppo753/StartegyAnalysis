# 🎨 UNIFIED UI — ESPANSIONE CON DECISIONI (Step 2)

## Da "idea" a "specifica implementabile"

> Basato su `17_unified_ui_idea.md` (Step 1). Ogni decisione sotto è presa e motivata; dove esisteva un'alternativa, è scritto perché è stata scartata. Nulla è lasciato a "si vedrà in implementazione" tranne ciò che è marcato ESPLICITO.

---

## D1. Stack: estendere lo esistente, zero framework

**Deciso**: server `node:http` stdlib (già in uso) + frontend vanilla JS (ES modules) + CSS con variabili. Nessun React/Vue/Svelte, nessun build step oltre `tsc`, nessun npm package nuovo.

**Perché, contro le alternative:**
- *React/Vite*: +build, +200MB deps, +complessità per 5 viste CRUD-ish. Scartato: sproporzionato.
- *HTMX/Alpine*: middle-ground allettante, ma introduce una dipendenza e un paradigma per un team di uno. Scartato: vanilla basta.
- *Estendere stdlib+vanilla (scelto)*: `tsx` e `jest`+`ts-jest` già presenti e verdi; i test di logica restano unit-test puri come `reportData.test.ts`; il server resta un file leggibile. Costo ≈ 0 nuove dipendenze.

## D2. Layout file (modularità fisica)

```
src/dashboard/
  server.ts            ( wiring: crea http server, monta le route — resta sottile )
  routes/
    results.ts         (spostato da server.ts: /api/summaries, /trades-files, /equity, /heatmap, /report)
    runs.ts            (NUOVO: /api/runs CRUD + log + cancel)
    system.ts          (NUOVO: /api/status [spazio disco, venv ok, studi], /api/config [flag disponibili])
  lib/
    reportData.ts      (esistente, intatto)
    runStore.ts        (NUOVO: registry job su file JSON: load/save/list/append-log)
    runSpawn.ts        (NUOVO: spawn python con allowlist flag, kill, capture)
    validateRun.ts     (NUOVO: validazione input run contro allowlist + tipi)
  public/
    index.html         (shell + nav 5 viste)
    css/theme.css      (NUOVO: variabili tema chiaro/scuro, layout, tabelle)
    js/
      api.js           (NUOVO: fetch wrapper + errori)
      views/home.js    (NUOVO)
      views/newRun.js  (NUOVO: form data-driven da /api/config)
      views/runs.js    (NUOVO: lista + log polling + cancel)
      views/results.js (adatta esistente app.js: split per vista)
      views/report.js  (link al report HTML esistente + embed)
```

**Regola anti-s spaghetti**: `server.ts` solo wiring; ogni route un file; `public/js` un modulo per vista; niente stato globale condiviso oltre `api.js`.

## D3. Contratti API (il vero scheletro — il frontend è un client come un altro)

```
GET  /api/status
→ { python: "3.10.0", venvOk: true, diskFreeGb: 412.3,
    studyDb: true|false, lastRuns: [{id, status, ...}] }

GET  /api/config                      # rende il form data-driven (adattabilità)
→ { symbols: ["DCRUSDT", ...],         # sottocartelle di data/ con file ohlc
    strategies: ["momentum_drop", "mean_reversion"],
      # MECCANISMO (fix verifica): listing di python-backtester/src/strategies/*.py
      # (meno __init__), validato server-side contro allowlist a ogni POST
    engine: ["standard", "fast", "gpu"],   # fix verifica: serve per il lock GPU
    flags: [                           # allowlist: SOLO questi arrivano a spawn
      { name: "search", type: "enum", values: ["grid","optuna"], default: "grid" },
      { name: "n-trials", type: "int", min: 1, max: 5000, default: 30 },
      { name: "jobs", type: "int", min: 1, max: 8, default: 1 },
      { name: "validation-mode", type: "enum",
        values: ["off","purged","cpcv","walkforward"], default: "off" } ] }

POST /api/runs { symbol, strategy, engine, search, nTrials, jobs, validationMode }
→ 201 { id: "20260926-142310-momentum", status: "queued" }
   400 { error } se validazione fallisce (strategia/engine ignoti, trial fuori range...)

GET  /api/runs                        → [{ id, symbol, strategy, engine, status, startedAt,
                                            finishedAt, exitCode, progress }...]
GET  /api/runs/:id                    → dettaglio + ultimi N log lines
GET  /api/runs/:id/log?fromLine=1234  → { totalLines, lines: [...], eof, rotated }
  # fix verifica: offset a RIGHE (non byte: la rotazione li invaliderebbe);
  # rotated=true se il log è stato troncato dall'ultima lettura
POST /api/runs/:id/cancel             → { status: "cancelled" } (kill + flussaggio log)
POST /api/runs/:id/reconcile {status} → { status } (solo per run `unknown` post-crash)

GET  /api/optuna-status               → { running: true|false, port: 8080 }
```

**Progresso onesto**: percentuale stimata da parsing stdout (contatori trial) + tempo trascorso + campo `progressNote: "stima"`. Mai barre finte precise. Fix verifica: NIENTE lettura `.db` da Node (richiederebbe un driver SQLite = nuova dipendenza, contraddice D1).

## D4. Job manager (dettaglio tecnico vincolante)

- `spawn(PYTHON_BIN, ["main.py", ...flag allowlist...], { cwd: "python-backtester/", shell: false })` — MAI shell, MAI stringa libera: argv array costruito solo da `validateRun()`. `PYTHON_BIN` = costante di piattaforma (`win32` → `.venv/Scripts/python.exe`, altro → `.venv/bin/python`), verificata al boot con errore chiaro se assente (fix verifica).
- stdout/stderr → append su `dashboard-data/runs/{id}.log` (fs stream) + `dashboard-data/runs/{id}.json` aggiornato a ogni cambio stato. Dir `dashboard-data/` ignorata da git (fix verifica: aggiungere voce `.gitignore`).
- Stati: `queued → running → done | failed | cancelled`. `cancelled` = `child.kill()` + kill forzato dopo 10s se vivo (nota piattaforma: su Windows non esiste SIGTERM POSIX, `kill()` termina il processo — documentato, non emulato).
- Concorrenza: default max 1 run GPU-attivo alla volta via `dashboard-data/runs/gpu.lock` (coda FIFO); lock acquisito solo se `engine === "gpu"`; configurabile dopo (D-1 compute budget resta il luogo della decisione, non qui).
- Crash server → al reboot i `running` diventano `unknown` (mai inventare esiti), riconciliabili via `POST /api/runs/:id/reconcile` (fix verifica).
- Rotazione log: oltre 10MB per run si taglia la testa, flag `rotated: true` nelle risposte (dettaglio in checklist).
- Porta `:3000` occupata → fail fast con errore chiaro (fix verifica). Symbol sempre via `path.basename` allowlist (pattern già usato dal server).

## D5. Integrazione esistente (riuso chirurgico)

- `results.ts` = codice attuale di `server.ts` spostato 1:1 (stessi endpoint, stessi formati) + test esistenti che continuano a passare.
- Report HTML (`buildReportHtml`) riusato via `/api/report` esistente; la vista report lo mostra in `<iframe sandbox>` + link "apri".
- Optuna Dashboard: NON duplicata. UI mostra badge stato (`/api/optuna-status`) + pulsante "apri" (`:8080`) + (se banale) `<iframe>`; niente proxy ingegnerizzato in questa iterazione (motivo: due server separati restano indipendenti e debuggabili; il proxy aggiunge failure modes per zero valore funzionale).
- Mock esistenti (`mockSummaryRows`, `mock: true`) restano per dir vuote.

## D6. Estetica "carina ma non esagerata" (sistema, non gusto)

- `theme.css`: variabili `--bg/--fg/--accent/--ok/--warn/--err/--muted`, toggle chiaro/scuro (default scuro, `prefers-color-scheme` rispettato), font di sistema (zero webfont), tabelle dense con sticky header, sparkline SVG riusate dal report.
- Layout: sidebar nav (5 viste) + contenuto; responsive (sidebar → topbar sotto 720px).
- Loading/empty/error states obbligatori per ogni vista (testati come stati, non come pixel).
- Mai `innerHTML` con dati non escapati: riusare il pattern `escHtml` (già in `reportData.ts`) in ogni vista (fix verifica).
- Niente animazioni oltre transizioni 150ms; niente chart lib (SVG hand-rolled come già fatto per sparkline; heatmap = `<table>` colorata via CSS).

## D7. Adattabilità ai cambiamenti (meccanismi, non promesse)

| Cambiamento futuro | Come viene assorbito senza rewrite |
|---|---|
| Nuovo flag CLI | +1 riga in `flags` di `/api/config` → appare nel form da solo |
| Nuova strategia | appare in `strategies` (da registry) → form + tabella la mostrano |
| Nuove metriche/colonne | accessor tolleranti esistenti + heatmap con assi liberi |
| Nuova vista | +1 file in `views/` + 1 voce nav (convenzione, non framework) |
| Auth/multi-user | `system.ts` è il seam: middleware qui, resto invariato (fuori scope ora) |

## D8. Test (stesso standard del repo)

- Unit jest su: `validateRun` (allowlist: flag ignoto → 400; injection `--x; rm` → 400), `runStore` (stati/transizioni), filtri/heatmap/equity (già coperti, estendere), `buildReportHtml` degradazione.
- Smoke live del coordinatore come per F8 (boot + 3 endpoint 200) — resta protocollo, non test committato.
- DoD globale: `npx jest` verde + `tsc --noEmit` pulito + smoke live ok.

## D9. Decisioni esplicite prese qui (log)

1. Vanilla > framework (D1). 2. Moduli per route/vista (D2). 3. API-first con contratti sopra (D3). 4. Spawn senza shell + allowlist (D4). 5. Riuso 1:1 risultati/report, Optuna linkata non duplicata (D5). 6. CSS variabili, no chart lib (D6). 7. Form data-driven da `/api/config` (D3/D7). 8. Niente auth ora, seam in `system.ts` (D2/D7). 9. Max 1 run GPU in coda FIFO di default (D4). 10. Niente proxy Optuna in questa iterazione (D5).

## D10. Rischi noti e mitigazioni

- Run lunghi + server restart → stati `unknown` + reconcile manuale (D4). Accettato: meglio che esiti inventati.
- Log giganti → `offset`-polling + troncamento server-side oltre N righe per risposta; retained su disco con rotazione semplice (max 10MB/run, poi append con taglio testa). Da specificare in checklist.
- Concorrenza GPU → coda FIFO default (D4); D-1 resta per il budget.

---
*Step 3 (verifica punto per punto) e Step 4 (checklist) nei prossimi passi del metodo.*
