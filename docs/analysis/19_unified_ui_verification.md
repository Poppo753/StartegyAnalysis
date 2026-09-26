# 🔍 UI UNIFICATA — VERIFICA AVVERSARIALE (Step 3)

## Metodo: attacco ogni decisione di `18_unified_ui_expanded.md`; regge → confermata, cede → fix

### Attacchi respinti (decisioni confermate)

- **D1 vanilla**: "5 viste in vanilla sprawlano" — vero in generale, ma moduli ES uno-per-vista + zero stato globale tengono la scala. Confermata. Aggiunta una regola: niente `innerHTML` con dati non escapati (riusare pattern `escHtml`).
- **D5 Optuna linkata**: "perché non proxy/embed pieno?" — il proxy aggiunge failure modes per zero valore; link + badge stato bastano. Confermata.
- **D6 estetica**: nessun buco funzionale. Confermata.
- **Idea doc (17)**: tutti i claim verificati (endpoint live, 933KB summaries, flag CLI, schemi CSV). Confermato.

### Attacchi riusciti → FIX applicati a `18_unified_ui_expanded.md`

1. **D3 strategie "da registry" — meccanismo assente** (TS non può importare Python). FIX: `/api/config.strategies` deriva dal listing di `python-backtester/src/strategies/*.py` (meno `__init__`), validato contro allowlist server-side.
2. **D3 offset log non specificato.** FIX: `GET /api/runs/:id/log?fromLine=` + risposta `{ totalLines, lines, eof, rotated }`.
3. **D3/D4 progresso da `.db` — richiede driver SQLite = nuova dipendenza, contraddice D1.** FIX: progresso da parsing stdout (contatori trial) + tempo trascorso; campo `progressNote: "stima"` obbligatorio. Niente lettura `.db` da Node.
4. **D4 path Python Windows-only.** FIX: costante di piattaforma (`win32` → `.venv/Scripts/python.exe`, altro → `.venv/bin/python`), verificata al boot con errore chiaro se assente.
5. **D4 SIGTERM su Windows.** FIX: `child.kill()` + fallback dopo 10s; nota piattaforma documentata.
6. **D4 reconcile manuale non azionabile.** FIX: `POST /api/runs/:id/reconcile {status}` solo per run `unknown`.
7. **D4 lock GPU senza meccanismo.** FIX: `gpu.lock` nella dir runs; serve sapere l'engine → AGGIUNTO `engine: [standard, fast, gpu]` a `/api/config` e `POST /api/runs` (gap reale: il form idea citava solo "search").
8. **Dir runs non decisa.** DECISO: `dashboard-data/runs/` (repo root) + voce `.gitignore`; rotazione log 10MB con taglio testa + flag `rotated`.
9. **Porta occupata / traversal symbol.** DECISO: fail fast con errore chiaro se `:3000` occupata; symbol sempre `path.basename` allowlist (pattern già usato dal server).
10. **D2 spostamento codice results.** Rischio wiring: mitigato con fase U0 "solo spostamento, zero comportamento" + gate jest+tsc+smoke.

### Verdetto

10 fix applicati (7 precisioni, 2 gap reali — engine-select e dir runs — 1 contraddizione risolta — progresso senza driver). Nessuna decisione ribaltata. Documenti promossi a specifiche implementabili.
