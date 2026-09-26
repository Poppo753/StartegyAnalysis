# ✅ UI UNIFICATA — CHECKLIST DI IMPLEMENTAZIONE (Step 4)

## Fasi, task atomiche, DoD misurabili, test finali

> Fonti vincolanti: `docs/analysis/17_unified_ui_idea.md` (concept) · `18_unified_ui_expanded.md` (decisioni D1–D10 + fix verifica) · `19_unified_ui_verification.md` (cosa è stato corretto e perché).
> Legenda: `[ ]` da fare · `[~]` in corso · `[x]` verificata. Lane: **BE** (backend, `routes/`+`lib/`) e **FE** (frontend, `public/`) lavorano in parallelo sui contratti §D3 — mai sullo stesso file.

---

## FASE U0 — Scaffolding a comportamento zero (0.5–1gg)

Obiettivo: struttura moduli senza cambiare nessun comportamento. Gate: `jest` + `tsc` verdi + smoke identico a pre-U0.

- [x] **U0-01 · Directory + `.gitignore`**
  Creare `src/dashboard/routes/`, `src/dashboard/lib/`; aggiungere `dashboard-data/` a `.gitignore` (log + registry job, rigenerabili).
  DoD: dir esistenti, git ignora `dashboard-data/`.

- [x] **U0-02 · Spostamento 1:1 codice results**
  Spostare il codice endpoint results da `server.ts` a `routes/results.ts` (import puri, zero logica cambiata); `server.ts` resta solo wiring. NON toccare `reportData.ts` né i suoi test.
  DoD: PRIMA dello spostamento, catturare baseline (`/api/summaries`, `/api/report` su DCRUSDT salvati su file); dopo: `npx jest` verde (stessi 14+ test, nessun test modificato); `tsc --noEmit` pulito; risposte identiche alla baseline.

## FASE U1 — Backend system/config/runs (2–3gg, Lane BE)

- [x] **U1-01 · `lib/runStore.ts` + `lib/validateRun.ts`**
  Store: load/save/list per-run JSON in `dashboard-data/runs/` (root parametricabile per i test su tmp dirs, mai fixture nella repo); transizioni `queued→running→done|failed|cancelled`, `unknown` post-crash; `validateRun`: allowlist flag (search/n-trials/jobs/validation-mode/engine/strategy/symbol), tipi/range, rigetto injection (`;`, `&&`, `$()`, backtick, `--` extra).
  Test `runStore.validate.test.ts`: transizioni legali/illegali; injection → 400 con motivo; trial fuori range → 400; strategia da dir listing (mock fs).
  DoD: test verdi; nessuna esecuzione, solo validazione+store.

- [x] **U1-02 · `lib/runSpawn.ts`**
  `PYTHON_BIN` per piattaforma (verifica esistenza al boot), spawn argv-array (`shell:false`), append log stream, `gpu.lock` solo se `engine==="gpu"` (coda FIFO: gli altri run gpu restano `queued`), kill + forzato dopo 10s, rotazione 10MB con taglio testa + flag `rotated`.
  Test: spawn di comando fittizio portabile (es. `node -e "process.exit(n)"`, non python) per transizioni done/failed/cancel; lock gpu seriale su 2 run fake; rotazione con log sintetico >10MB (soglia parametricabile nei test, non 10MB reali).
  DoD: mai shell; mai comando fuori allowlist (test tenta bypass e fallisce).

- [x] **U1-03 · `routes/system.ts` + `routes/runs.ts`**
  `GET /api/status` (python version, venvOk, diskFree, studyDb, lastRuns), `GET /api/config` (symbols da `data/`, strategies da listing `src/strategies/*.py`, engine, flags), CRUD runs + `log?fromLine=` (`{totalLines,lines,eof,rotated}`) + `cancel` + `reconcile` (solo `unknown`).
  Verificare `--engine` in `main.py parse_args()`: se assente, aggiungerlo seguendo il pattern F2-B03 (unica modifica Python consentita, additiva).
  DoD: `tsc` pulito; test endpoint con store fake (stati, 400 su input cattivi, reconcile rifiutato su run `done`).

## FASE U2 — Frontend 5 viste (2–3gg, Lane FE, parallela a U1)

Contratti congelati da D3: sviluppare contro mock JSON con la forma esatta, wiring reale in U3.

- [x] **U2-01 · Shell + tema + `api.js`**
  `index.html` nav 5 viste; `css/theme.css` (variabili, dark/light, responsive ≤720px); `js/api.js` (fetch wrapper, errori → toast, mai `innerHTML` non escapato — helper `esc`).
  DoD: navigazione tra viste senza reload; toggle tema persistito.

- [x] **U2-02 · Viste home + newRun (form data-driven)**
  Home: `/api/status` + ultimi run. NewRun: form costruito da `/api/config` (nuovo flag CLI futuro = appare da solo); validazione client = stessa allowlist (duplicata per UX, fonte di verità resta il server); submit → `POST /api/runs` → redirect a Runs.
  DoD: form renderizzato da mock config con flag extra fittizio → campo appare senza toccare il codice vista.

- [x] **U2-03 · Vista runs + viste results/report**
  Runs: lista + poll log (`fromLine`, 2s) + cancel + reconcile (solo `unknown`) + progresso con `progressNote: "stima"` visibile. Results/report: split dell'attuale `app.js` per vista + link/embed Optuna (`:8080`, badge da `/api/optuna-status` se banale, altrimenti solo link).
  DoD: cancel ferma il polling; `unknown` mostra reconcile; report degrada F3/F5 come oggi.

## FASE U3 — Integrazione + gate finale (1gg)

- [x] **U3-01 · Wiring + smoke + full suite**
  Mock → reale; `npx jest` verde; `tsc --noEmit` pulito; smoke live: boot, `/api/status`, `/api/config`, `POST /api/runs` micro-run reale `--search optuna --n-trials 1` fino a `done` (veloce e reale; grid 1×1×1 impossibile senza toccare `.env`, MAI modificare il `.env` utente), `GET log`, run visibile in results, `/api/report` 200; poi secondo run cancellato subito (queued→cancelled live).
  DoD: micro-run completa end-to-end e appare in results; cancel verificato live; `.env` intatto.

## NON-FARE (vincolante)

Framework frontend · proxy Optuna · auth · lettura `.db` da Node · spawn con shell · nuove dipendenze npm · modifiche a logica results/Python oltre `--engine` · pixel-test.

## DoD GLOBALE

Checklist 100% `[x]` + `jest` verde + `tsc` pulito + smoke U3 ok + commit per milestone (U0 / U1+U2 / U3).
