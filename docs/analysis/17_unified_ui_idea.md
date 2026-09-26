# 🎨 UNIFIED UI — DOCUMENTO IDEA (Step 1)

## Interfaccia Unica per Usare il Progetto in Modo Semplice e Funzionale

> **Problema**: oggi il progetto si usa in tre posti separati — riga di comando per lanciare (`python main.py ...`), dashboard `:3000` per vedere i risultati, Optuna Dashboard `:8080` per gli studi. Manca il pezzo centrale: **avviare, seguire e gestire i run da interfaccia**.
>
> **Idea**: un'unica interfaccia web su una sola porta che (a) lancia run con un form (simbolo, strategia, motore di ricerca, trial, validazione), (b) li segue in tempo reale (stato, log, progresso, cancel), (c) riusa le visualizzazioni esistenti (risultati, equity, heatmap, report), (d) collega Optuna Dashboard invece di duplicarla.

---

## 1. Stato attuale (verificato, non presunto)

| Pezzo | Dove | Come si usa oggi |
|---|---|---|
| Lancio run | `python-backtester/main.py` | CLI: `--search/--strategy/--n-trials/--jobs/--study-db/--validation-mode` (F2–F3) |
| Risultati/equity/heatmap/report | `src/dashboard/server.ts` (`:3000`) | API JSON + pagina statica; fallback mock se dir vuota |
| Studi Optuna | `optuna-dashboard` (`:8080`, dep isolata) | Processo separato sullo stesso `.db` |
| Dati | `python-backtester/backtest-results/{SYMBOL}/` | CSV summary + trades (colonne variabili per engine) |

## 2. Concept: 5 viste, 1 porta

```
:3000 ┌──────────────────────────────────────────────┐
      │ ① HOME — stato sistema (ultimi run, salute)  │
      │ ② NEW RUN — form lancio (NUOVO, il pezzo     │
      │    mancante: simbolo, strategia, search,     │
      │    trial, jobs, validation → avvia)          │
      │ ③ RUNS — lista run + log live + progresso +  │
      │    cancel (NUOVO: job manager)               │
      │ ④ RESULTS — esistente (tabella, equity,      │
      │    heatmap) riusato com'è                    │
      │ ⑤ REPORT — esistente riusato com'è           │
      │ + link/embed Optuna Dashboard (riuso,        │
      │   non duplicato)                             │
      └──────────────────────────────────────────────┘
```

## 3. Il pezzo nuovo: job manager (cuore dell'idea)

I run durano minuti/ore: non possono vivere dentro una request HTTP. Serve un gestore job:

- `POST /api/runs` con JSON validato (allowlist di flag, MAI shell libera) → `spawn(python main.py, [...])`, stdout/stderr in log file per run.
- Registry job su file JSON (`runs/{id}.json`: stato queued/running/done/failed/cancelled, progresso stimato, exit code).
- `GET /api/runs` (lista), `GET /api/runs/:id/log?offset=` (polling log), `POST /api/runs/:id/cancel` (kill).
- Solo `127.0.0.1` (già così), nessun comando arbitrario eseguibile.
- A run finito, results/report esistenti lo vedono subito (stessi CSV, zero adattamenti).

## 4. Principi (dati dall'utente, non negoziabili)

- **Carino ma non esagerato**: tema pulito con variabili CSS, responsive, zero kit pesanti.
- **Modulare e scalabile**: frontend a viste/moduli ES separati, backend a route separate, API JSON-first (la UI è un client come un altro).
- **Riuso > rewrite**: risultati/equity/heatmap/report e Optuna Dashboard restano, si integrano.
- **Adattabile ai cambiamenti**: nuovi flag CLI = nuova riga di config nel form (data-driven), nuove strategie appaiono da sole (registry), nuove metriche = nuove colonne (accessor tolleranti già esistenti).

## 5. Cosa NON è

- Non un rewrite del backend Python (che resta CLI-first, testato: 227 test).
- Non un duplicato di Optuna Dashboard (link/embed, non rebuild).
- Non un sistema multi-utente/auth (locale, single-user per ora).

---
*Step 2 (espansione con decisioni) in `18_unified_ui_expanded.md`.*
