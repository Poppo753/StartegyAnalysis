# 🎨 UI UNIFICATA — GUIDA COMPLETA (Post-implementazione)

## Come si usa, cosa fa, come è fatta

> Implementata il 2026-09-26 · commit `a59e413` · 249 test jest · 227 test pytest · `tsc` pulito · smoke live verificato.
> Metodo seguito: `17_unified_ui_idea.md` (idea) → `18_unified_ui_expanded.md` (decisioni) → `19_unified_ui_verification.md` (verifica avversariale) → `IMPLEMENTATION_CHECKLIST_UI.md` (task) → questo documento.

---

## 1. Come si lancia (il 90% di ciò che serve)

```powershell
npm run dashboard          # apre la UI su http://127.0.0.1:3000
```

Per la ricerca Optuna (separata, serve solo se la usi):
```powershell
pip install -r python-backtester/requirements-ui.txt   # una volta sola
npm run dashboard:optuna                                # http://127.0.0.1:8080
```

Stop: `Ctrl+C` nel terminale.

## 2. Le 5 viste

| Vista | A cosa serve | Cosa fa |
|---|---|---|
| **Home** | salute del sistema | Python/venv OK?, disco libero, esiste lo study Optuna, ultimi 10 run |
| **New Run** | **lanciare un backtest** (il pezzo che mancava) | form costruito da `/api/config`: simbolo, strategia, motore, ricerca, trial, jobs, validazione → `POST /api/runs` |
| **Runs** | seguire i run | lista, **log in tempo reale** (poll 2s), annullamento, riconciliazione se il server è crashato |
| **Results** | analizzare | tabella filtrabile e ordinabile, equity curve, drawdown, heatmap parametri (assi e metrica scelti da te) |
| **Report** | riassunto | report HTML completo + link a Optuna Dashboard |

## 3. Flusso tipico

```
Home → New Run (compili) → Runs (guardi il log) → Results (leggi i numeri) → Report (condividi)
```

## 4. Cosa puoi scegliere nel form

- **Simbolo**: solo quelli con dati per il range configurato nel `.env` (vedi §7)
- **Strategia**: `momentum_drop`, `mean_reversion` (dal listing reale di `python-backtester/src/strategies/`)
- **Motore**: `standard`, `fast` (Numba), `gpu`
- **Ricerca**: `grid` (esaustiva) o `optuna` (intelligente, con pruning)
- **Trial / Jobs**: quanti tentativi, quanti in parallelo
- **Validazione**: `off`, `purged`, `cpcv`, `walkforward`

## 5. Come è fatta (architettura)

```
┌─ Browser ──────────────────────────────────────────────┐
│  5 viste ES modules (public/js/views/*.js)              │
│  form DATA-DRIVEN: nuovi flag CLI future = 1 riga      │
└──────────────────────┬──────────────────────────────────┘
                       │ fetch (JSON)
┌──────────────────────▼──────────────────────────────────┐
│  server.ts — solo wiring (94 righe)                     │
│  ├── routes/system.ts   /api/status, /api/config       │
│  ├── routes/runs.ts     /api/runs, log, cancel         │
│  └── routes/results.ts  sommari, equity, heatmap, report│
│  lib/runStore.ts    registro run su disco               │
│  lib/validateRun.ts  ALLOWLIST (mai shell)              │
│  lib/runSpawn.ts    spawn argv + lock GPU + log         │
└──────────────────────┬──────────────────────────────────┘
                       │ spawn (shell:false)
┌──────────────────────▼──────────────────────────────────┐
│  python main.py --symbol X --engine Y ...               │
│  → CSV in backtest-results/ → le viste Results lo leggono│
└─────────────────────────────────────────────────────────┘
```

**Sicurezza**: nessun comando da shell, mai. Ogni flag passa da allowlist; injection tipo `DCRUSDT; rm -rf` → `400`. Verificato live.

**Modularità**: `server.ts` non contiene logica; ogni route è un file; ogni vista è un file. Aggiungere una vista = 1 file + 1 voce di nav.

## 6. Comandi equivalenti (la UI non è magia)

Tutto quello che fai dalla UI è riproducibile da terminale:

```powershell
cd python-backtester
.\.venv\Scripts\python main.py --symbol UNIUSDT --engine standard --search optuna --n-trials 1
```

## 7. Comportamenti onesti (le scelte documentate)

- **Simboli**: `/api/config` offre solo simboli con un file OHLC per l'esatto range `START_DATE..END_DATE` del `.env`. Per un altro range, cambia il `.env` (la UI non lo fa al posto tuo, per non mentirti sullo stato dei dati).
- **Progresso**: è una **stima** (parsing del log + tempo), etichettata come tale. Nessuna barra finta.
- **Riconciliazione**: se il server muore durante un run, quello resta `unknown` — non inventiamo un esito. Lo decidi tu.
- **Coda GPU**: un solo run GPU alla volta, gli altri in coda.
- **Log ruotati**: oltre 10 MB il file viene troncato e la risposta lo segnala con `rotated: true`.
- **Dati mancanti**: se la cartella risultati è vuota, le viste mostrano dati dimostrativi con `mock: true` — mai una schermata vuota senza spiegazione.

## 8. Dati runtime (rigenerabili, fuori dal git)

`dashboard-data/runs/` → un `.json` + un `.log` per run. Puoi cancellarli; ricostruisci lo storico solo dei run ancora in corso.

## 9. Cosa NON c'è (per onestà)

- Nessun auth (è locale, `127.0.0.1`).
- Nessuna persistenza dello storico oltre i file su disco.
- Nessun proxy verso Optuna Dashboard (link diretto, scelta deliberata per non aggiungere failure mode).
- I PDF si generano via browser (stampa → PDF), non c'è export server.

## 10. Se qualcosa non funziona

| Sintomo | Causa probabile | Cosa fare |
|---|---|---|
| `venvOk: false` | venv non trovato | `python-backtester/.venv/Scripts/python.exe` deve esistere |
| Simbolo non in lista | dati mancanti per il range del `.env` | scarica i dati con la pipeline TS, o cambia il range |
| Run `failed` | guarda il log nella vista Runs | l'errore Python è nel log, riga per riga |
| `unknown` dopo un crash | il server è morto col run attivo | riconcilia dalla vista Runs |
| Porta 3000 occupata | un'altra istanza attiva | `npx tsx src/dashboard/server.ts --port 3100` |

## 11. Verifiche fatte (non dichiarazioni)

- **249 test jest** (18 nuovi sui moduli UI) + **227 test pytest** + `tsc` pulito.
- **Smoke live reale**: `POST /api/runs` → run `momentum_drop` reale su UNIUSDT → `status: done`, exit 0, best params trovati, log 47 righe, `eof: true`.
- **Injection bloccato**: `symbol: "DCRUSDT; rm -rf"` → `400`.
- **3 bug trovati e corretti grazie allo smoke** (nessuno visibile dai test):
  1. `--engine` non era cablato nel routing → dichiarava `standard`, eseguiva `gpu`
  2. `screening_metrics.py` usava `Dict` senza import → il motore GPU era rotto
  3. `symbols` proponeva simboli senza dati per il range → fallimento garantito

---

> "Il software più utile è quello che risponde a una domanda che ti stava facendo da due ore."

## Aggiornamento interfaccia (26 settembre 2026)

La navigazione usa ora le etichette **Panoramica**, **Nuovo backtest**, **Esecuzioni**, **Risultati** e **Report**. Il form raggruppa impostazioni principali e parametri avanzati; le viste Risultati ed Esecuzioni espongono filtri, stati e azioni in pannelli dedicati. Il layout si adatta anche a schermi stretti e offre temi chiaro e scuro.

Se le API di stato, configurazione o esecuzioni non rispondono, la vista mostra un errore esplicito invece di sostituire i dati con esempi. I risultati dimostrativi restituiti dal server quando mancano i CSV restano disponibili, ma sono etichettati come tali. Il log indica quando è stato ruotato o quando resta un blocco di righe da caricare.
