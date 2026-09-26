# ✅ IMPLEMENTATION CHECKLIST — Dal Masterplan v3 all'Esecuzione

## Documento Operativo Fase-per-Fase, Task-per-Task
### "Basta eseguire quanto descritto"

> **Scopo**: Questo documento traduce il `TRANSFORMATION_MASTERPLAN_v3.md` in lavoro eseguibile. Ogni task di implementazione ha: file da toccare, firme di funzione, test da scrivere, criterio di accettazione misurabile (Definition of Done), dipendenze e stima; ogni task di audit (Fase 0) ha: file da leggere, verdetto atteso onesto, evidenza richiesta. Un agente (o una persona) deve poter prendere una task e finirla senza chiedere chiarimenti.
>
> **Fonti vincolanti**: `docs/TRANSFORMATION_MASTERPLAN_v3.md` (cosa e perché) · `docs/theory/THEORETICAL_FOUNDATIONS.md` (dettagli matematici) · `docs/analysis/09_theory_vs_masterplan/THEORY_VS_MASTERPLAN_RIVALUTAZIONE.md` (perché certe cose NON si fanno).
>
> **Decisioni già prese dal proprietario**: Fase 8 (UI) NECESSARIA, non tagliabile · ordine per dipendenze + parallelizzazione su lane · budget backtest lunghi RINVIATO al momento del bisogno (punto decisionale D-1, §6).
>
> **Legenda stati**: `[ ]` da fare · `[~]` in corso (una sola per agente) · `[x]` completata e verificata (DoD soddisfatta, mai per intenzione).

---

## INDICE

1. [§1 — Inventario chiuso delle modifiche v3](#1--inventario-chiuso-delle-modifiche-v3)
2. [§2 — Grafo delle dipendenze e lane parallele](#2--grafo-delle-dipendenze-e-lane-parallele)
3. [§3 — Fase 0: Verifica e correzione](#3--fase-0-verifica-e-correzione-12-giorni)
4. [§4 — Fase 1: Interfaccia Strategy + vincolo GPU + metriche](#4--fase-1-interfaccia-strategy--vincolo-gpu--metriche-35-giorni)
5. [§5 — Fase 2: Motore BO](#5--fase-2-motore-bo-35-giorni)
6. [§6 — Fase 3: Validazione robusta](#6--fase-3-validazione-robusta-57-giorni) *(include punto decisionale D-1)*
7. [§7 — Fase 4: Strategy generation](#7--fase-4-strategy-generation-510-giorni)
8. [§8 — Fase 5: Meta-analysis](#8--fase-5-meta-analysis-510-giorni)
9. [§9 — Fase 6: Feature engineering](#9--fase-6-feature-engineering-35-giorni)
10. [§10 — Fase 7: Multi-timeframe](#10--fase-7-multi-timeframe-35-giorni)
11. [§11 — Fase 8: UI/Dashboard](#11--fase-8-uidashboard-24-settimane-necessaria)
12. [§12 — Stop point: valore anche se ci si ferma](#12--stop-point-valore-anche-se-ci-si-ferma)
13. [§13 — Lista NON-FARE (voci scartate dalla v3)](#13--lista-non-fare-voci-scartate-dalla-v3)
14. [§14 — Protocollo di esecuzione per agenti](#14--protocollo-di-esecuzione-per-agenti)

---

## 1 — Inventario chiuso delle modifiche v3

Ogni riga è una modifica tracciabile del masterplan v3. La colonna "Task" indica dove viene eseguita. Nulla fuori da questa tabella va implementato (vedi §13).

| ID | Modifica v3 | Tipo | Sezione v3 | Task |
|----|-------------|------|------------|------|
| CHG-001 | Sortino / Calmar / Expectancy in metriche | Nuova metrica | §5.3, Glossario | F1-M01, F1-M02, F1-M03 |
| CHG-002 | Kelly = sizing, non metrica (chiarimento) | Correzione doc | §5.3, Glossario | Nessun codice (solo policy: non aggiungere Kelly a `StrategyResult`) |
| CHG-003 | Principio GPU-per-archetipo + contratto `gpu_param_arrays` / `gpu_metric_names` | Vincolo design | §6.1 | F1-G01, F1-G02 |
| CHG-004 | DSR: due formulazioni distinte + prerequisiti | Correzione doc + specifica | §§5.6, 6.2, 8.4.3 | F3-V05 (solo dopo prerequisiti F3-V01) |
| CHG-005 | Semaforo PBO 3 fasce + disclaimer + `evaluate_pbo` | Specifica | §§5.6, 6.2, 7.3 | F3-V04 |
| CHG-006 | Sharpe Ratio in `metrics.py` + `scipy` (prerequisiti DSR) | Prerequisito | §5.6-nota-v3 | F3-V01 |
| CHG-007 | Stazionarietà / fracdiff (nota futura) | Nota futura | §5.1 | NON attivare (prerequisiti: modello ML + `fracdiff`) |
| CHG-008 | Dollar / Volume Bars (nota futura) | Nota futura | §5.1 | NON attivare (prerequisito: limiti attribuiti al campionamento) |
| CHG-009 | IC / IR / alpha decay quantitativo (nota futura) | Nota futura | §5.7 | NON attivare (prerequisiti: segnali continui + numerosità + produzione) |
| CHG-010 | Meta-Labeling §5.8 (nota futura) | Nota futura | §5.8 | NON attivare (prerequisiti: Fase 1 + Fase 5/6 + storico etichettato) |
| CHG-011 | RF importance post-Fase-6, no Bagging/Stacking | Vincolo | Fase 5-nota-v3 | F5-R01 (gated su F6), mai Bagging/Stacking |
| CHG-012 | HMM / CUSUM solo produzione (nota futura) | Nota futura | §5.7 | NON attivare nel discovery |
| CHG-013 | Interfaccia `TradingStrategy` + 2 strategie + routing `main.py` | Architettura | Fase 1 | F1-S01…F1-S04, F1-G01, F1-M01 |
| CHG-014 | Optuna TPESampler + MedianPruner + study persistente | Architettura | Fase 2 | F2-B01…F2-B05 |
| CHG-015 | PurgedKFold + CPCV + Walk-Forward + `--validation-mode` (incl. Sharpe/scipy + semaforo + DSR) | Architettura | Fase 3 | F3-V01…F3-V07 |
| CHG-016 | Crossover / Mutation / Template registry (no LLM obbligatorio) | Architettura | Fase 4 | F4-G01…F4-G04 (LLM: F4-G05 opzionale esplicito) |
| CHG-017 | Regime detector (soglie) + clustering + focus allocator | Architettura | Fase 5 | F5-A01…F5-A04 |
| CHG-018 | Indicator factory (SMA/EMA/RSI/BB/ATR/MACD/OBV/VWAP) | Architettura | Fase 6 | F6-E01…F6-E04 |
| CHG-019 | `ohlcAggregator.ts` con intervallo + 1m/5m/1h/1d | Architettura | Fase 7 | F7-T01…F7-T03 |
| CHG-020 | Optuna Dashboard + equity/drawdown/heatmap + tabella + report | Prodotto | Fase 8 | F8-U01…F8-U04 |

---

## 2 — Grafo delle dipendenze e lane parallele

```
F0 (verifica; le lane B/C partono appena finiti i task F0 che le riguardano, senza attendere F0-10)
 └─▶ F1 (strategy + GPU contract + metriche CHG-001)
       ├─▶ F2 (Optuna) ──────────────┐
       │                              ▼
       ├─▶ F6 (features; Lane B, partita già da F0 — file disgiunti, zero overlap con F1)
       │                              ▼
       └─▶ F3 (validazione; needs: F1 + Sharpe[F3-V01]; F2 raccomandato ma non bloccante)
             ├─▶ F4 (generation; needs: F1; F3 raccomandato)
             └─▶ F5 (meta; needs: F3; RF needs: F6) ──▶ F8 (UI; needs: F1 formati + F2 study)

Lane C (TypeScript): parte appena chiusi i task TS di F0 (F0-02…F0-06, F0-09), senza attendere F0-py né F0-10:
  F0-ts ─▶ F7 (multi-timeframe) ─▶ supporta F8 (dati multi-TF per i grafici)

Lane D (UI, Fase 8): scheletro avviabile dopo F1+F2 (formati risultati + study Optuna noti);
  wiring completo dopo F3 (metriche validate) e F7 (dati multi-TF).
```

**Regole di parallelizzazione per agenti:**
- LANE-A (Python core, sequenziale): F0-py → F1 → F2 → F3 → F4 → F5. Un agente alla volta; ogni fase chiude con i suoi test verdi prima di passare oltre.
- LANE-B (Features, parallela): F6 parte appena chiusa F0 (tocca solo `src/features/` + `tests/test_features*.py`, disgiunti da tutto il resto). F5-R01 (RF) parte solo a F5+F6 chiuse.
- LANE-C (TypeScript, parallela): parte appena chiusi F0-02…F0-06 e F0-09 (non attende task Python né F0-10). Unico punto di contatto: formato CSV OHLC (contratto stabile, non modificare colonne senza avvisare Lane A).
- LANE-D (UI, Fase 8): parte dopo F1+F2; mock dei dati di F3/F7 per sviluppare le viste, wiring reale quando disponibili.
- **Mai due agenti sullo stesso file contemporaneamente.** I file condivisi (`main.py`, `requirements.txt`) si modificano in task dedicate con lock esplicito (vedi §14).

**Stime oneste (dal masterplan v3, ricalibrate col grounding):** F0 2–3gg (somma task 4.0gg, wall parallelo A+C ≈ 2.5gg) · F1 3–5gg · F2 3–5gg · F3 5–7gg · F4 5–10gg · F5 5–10gg · F6 3–5gg · F7 3–5gg · F8 2–4 sett. Sequenziale puro: ~7–12 settimane. Con 3 lane (A+B/C+D): ~5–8 settimane.

---

## 3 — Fase 0: Verifica e correzione (2–3 giorni)

**Obiettivo**: chiudere ogni voce dubbia con un verdetto verificato (corretto / da correggere / già corretto + test di regressione). Output: lista bug aperti con priorità. **Nessuna nuova funzionalità.**

> Stato verificato il 2026-09-25 (grounding): `config.py` solleva già `ConfigError` (mai `sys.exit`); warmup fast ha già la guardia `len(close) < 100 → return`; `aggregateToOhlc.ts` NON esiste (voce già chiusa); `xml.includes` NON trovato (verificare il parser attuale); `main.py` usa `sys.exit` solo al boundary CLI con try/except tipizzati (pattern documentato — da confermare, non da "correggere alla cieca").

- [x] **F0-01 · data_splitter: regression test (già corretto, pinnare il comportamento)**
  File: `python-backtester/tests/test_data_splitter.py` (estendere), `src/gpu/data_splitter.py` (leggere, non modificare salvo bug).
  Operazione: aggiungere test che lo split è data-based — train tutto `<` validation su `datetime`, con dataset a cavallo di mese/anno e con buchi temporali.
  DoD: `pytest tests/test_data_splitter.py` verde; il test fallisce se qualcuno reintroduce split per indice.
  Dipendenze: nessuna. Stima: 0.5gg. Lane: A.

- [x] **F0-02 · bulkDownloader jszip: verifica + chiusura**
  File: `src/binance/bulkDownloader.ts` (leggere).
  Operazione: confermare import/uso `jszip` e assenza di `child_process`/unzip esterno; se confermato, chiudere la voce con nota nel report Fase 0.
  DoD: evidenza (riga di import + chiamata `loadAsync`) citata nel report; nessuno `spawn`/`exec` nel file.
  Dipendenze: nessuna. Stima: 0.25gg. Lane: C.

- [x] **F0-03 · Retry semantics `binanceClient.ts`: decidere e pinnare**
  File: `src/binance/binanceClient.ts`, nuovo `src/binance/binanceClient.test.ts` (o estendere suite esistente; runner: `jest.config.js` presente).
  Operazione: leggere il loop (`for attempt … MAX_RETRIES`) e il layer HTTP effettivo (verificare nel file: axios vs fetch nativo); decidere e DOCUMENTARE la semantica (tentativi totali = 1 + MAX_RETRIES retry); verificare backoff `2^(attempt-1)`; scrivere test mockando quel layer: (a) 429 poi successo → ok dopo N tentativi; (b) sempre 500 → throw dopo esaurimento; (c) 4xx non-retryable → throw immediato senza retry.
  DoD: semantica scritta in commento sopra `MAX_RETRIES`; 3 test verdi; nessun cambio di comportamento non documentato.
  Dipendenze: nessuna. Stima: 0.5gg. Lane: C.

- [x] **F0-04 · Merge barrier `downloadAggTrades.ts`: verifica (barrier prob. esistente) + test**
  File: `src/pipeline/downloadAggTrades.ts` (rr.85/108 `await`, merge r.120), `src/utils/rateLimiter.ts` (`runWithConcurrency` r.57: verificare che attenda TUTTI i job e propaghi gli errori), `src/pipeline/downloadAggTrades.test.ts` (ESISTE già con test `mergeDayFiles` — estendere, non creare).
  Operazione: (a) leggere `runWithConcurrency`: se non attende tutti i job o ingoia errori → fix lì; (b) confermare che `cleanupDir` è sync (`: void` r.331 — in tal caso nessun fix); (c) estendere il test esistente con 2 giorni simulati a delay invertiti (il giorno 2 finisce prima del giorno 1) → il merge deve vedere entrambi i file completi e ordinati. Esito atteso onesto: barrier già presente → si pinna con test, non si aggiunge codice.
  DoD: test delay-invertiti verde nel file esistente; evidenza nel report se qualche `await` mancava davvero.
  Dipendenze: nessuna. Stima: 0.5gg. Lane: C.

- [x] **F0-05 · XML `bulkAvailability.ts`: audit + pinning (impl. attuale già decente)**
  File: `src/binance/bulkAvailability.ts` (verificato: regex con `escapeRegex` su `<Key>…</Key>` rr.39–41, NON `includes`; fallback graceful r.45–48: se il check fallisce → REST API).
  Operazione: test con XML valido / malformato / vuoto / timeout axios / mese con >100 file (verificare `max-keys=100` non tronca: daily → max 31 file/mese, atteso ok); sostituire con parsing strutturato SOLO se un caso fallisce.
  DoD: 5 casi verdi oppure 1 fix mirato + 5 casi verdi; esito atteso onesto: pinning, non rewrite.
  Dipendenze: nessuna. Stima: 0.5gg. Lane: C.

- [x] **F0-06 · `jsonlWriter.ts`: audit chiamanti + instradamento per dimensione**
  File: `src/storage/jsonlWriter.ts` (confermato: `readAggTradesJsonl` carica tutto in RAM r.69, `readAggTradesJsonlStream` esiste r.108), tutti i chiamanti di `readAggTradesJsonl`.
  Operazione: per ogni chiamante, classificare (file piccoli di test vs file storici GB); instradare i secondi sullo stream; aggiungere guardia: `readAggTradesJsonl` solleva errore esplicito sopra soglia (dimensione file su disco come proxy, default 256MB, costante nominata) invece di OOM silenzioso.
  DoD: nessun chiamante su path storici usa la versione full-RAM; test con file sintetico sopra soglia → errore esplicito, non crash.
  Dipendenze: nessuna. Stima: 0.5gg. Lane: C.

- [x] **F0-07 · Warmup fast: regression test (guardia già presente)**
  File: `python-backtester/src/fast/fast_runner.py` (guardia `len(close) < 100 → return` già a r.191–192), `tests/` (nuovo `test_fast_warmup.py` o estensione).
  Operazione: test con dataset di 10/50/99/100/101 righe → nessun crash, risultati identici con/senza warmup quando applicabile.
  DoD: 5 casi verdi; la guardia esistente è pinnata contro regressioni future.
  Dipendenze: nessuna. Stima: 0.25gg. Lane: A.

- [x] **F0-08 · `sys.exit` boundary audit (atteso: già conforme, pinnare)**
  File: `src/config.py` (verificare: solo `ConfigError`, zero `sys.exit` — atteso già così), `main.py` rr.91/107/122/153 (confermare che sono tutti boundary CLI con except tipizzato: `NumbaMissingError`, `ConfigError`, `DataLoadError`), `stoploss_analysis.py:151` + `trade_profile.py:396` (verificato: entrambi script CLI con `argparse`, guardie `__main__` e docstring "sys.exit solo nel blocco __main__" — atteso già conformi).
  Operazione: per ogni sito, classificare boundary-vs-libreria; convertire in `raise` SOLO se si trova codice eseguibile all'import (fuori da funzioni/blocchi `__main__`); estendere `tests/test_config.py` con: `.env` invalido → `load_config()` solleva `ConfigError` (mai exit) — la testabilità è la prova che il pattern serve.
  DoD: zero `sys.exit` fuori da `main()`/blocchi `__main__`; test `ConfigError` verde; esito atteso onesto: nessun fix, solo pinning.
  Dipendenze: nessuna. Stima: 0.5gg. Lane: A.

- [x] **F0-09 · `aggregateToOhlc.ts`: chiudere la voce (file assente)**
  Operazione: `grep` di riferimenti residui (`aggregateToOhlc`) in `src/` e `docs/`; se nessun riferimento attivo, chiudere con nota nel report; se esistono import rotti, rimuoverli.
  DoD: zero riferimenti attivi oppure zero file orfani; voce chiusa nel report.
  Dipendenze: nessuna. Stima: 0.25gg. Lane: C.

- [x] **F0-10 · Report bug Fase 0 con priorità (output di fase)**
  File: nuovo `docs/analysis/10_phase0_report.md` (breve).
  Operazione: per ogni F0-01…F0-09: verdetto (corretto / corretto-ora / già-ok), evidenza (file:riga o test), priorità residua.
  DoD: report completo; zero voci "da verificare" rimaste; via libera a Fase 1 solo con report chiuso.
  Dipendenze: F0-01…F0-09. Stima: 0.25gg.

---

## 4 — Fase 1: Interfaccia Strategy + vincolo GPU + metriche (3–5 giorni)

**Obiettivo**: strategie come plug-in (non più hardcoded), interfaccia GPU-compatibile by-construction, metriche v3. Prerequisito: F0 chiusa.

- [x] **F1-S01 · `TradingStrategy` ABC in `src/strategy_base.py` (nuovo file)**
  Firma (vincolante, da v3 §5.3 + §6.1-nota-v3):
  ```python
  class TradingStrategy(ABC):
      @abstractmethod
      def parameter_space(self) -> Dict[str, Tuple]: ...
      # Convenzione v3 (estende lo sketch §5.3): tupla (lo, hi, kind) con
      # kind ∈ {"float", "int", "float_log", "int_log"} — i *_log servono a F2-B02
      @abstractmethod
      def generate_signals(self, df: pd.DataFrame, params: Dict) -> List[Signal]: ...
      @abstractmethod
      def validate(self, params: Dict) -> bool: ...
      def score(self, result) -> float: ...          # default v3 (pesi invariati)
      def gpu_param_arrays(self, param_grid: List[Dict]) -> Dict[str, np.ndarray]: ...
      def gpu_metric_names(self) -> List[str]: ...
  ```
  DoD: file creato, importabile, `test_strategy_base.py` verifica che classe fittizia senza un metodo astratto non istanziabile + che `parameter_space` usa solo kind ammessi.
  Dipendenze: F0. Stima: 0.5gg. Lane: A.

- [x] **F1-S02 · Refactoring `simulator.py` → `MomentumDropStrategy(TradingStrategy)`**
  File: `src/simulator.py` (estrarre logica), nuovo `src/strategies/momentum_drop.py`, `src/strategies/__init__.py`.
  Operazione: spostare entry/exit/PnL invariati; `parameter_space` = X/Y/Z + hold/fees/slippage/direction correnti; `validate` = controlli v3 §5.3; `gpu_param_arrays` restituisce `x_values/y_values/z_values` come array tipizzati.
  DoD: backtest su dataset di riferimento (stesso CSV, stessi parametri) → tutti i trade e tutte le metriche identici al vecchio `run_backtest` entro 1e-9 (confronto CSV parsati, non byte-identical: la formattazione float può differire).
  Dipendenze: F1-S01. Stima: 1gg. Lane: A.

- [x] **F1-S03 · `MeanReversionZScore(TradingStrategy)` dimostrativa**
  File: `src/strategies/mean_reversion.py` (logica v3 §5.3: MA rolling, z-score, entry/exit).
  DoD: produce segnali su dataset di riferimento; `validate` rifiuta `ma_period < 5`, `z_threshold ≤ 0`; test con serie sintetica (trend monotono → zero trade; sinusoide → almeno 1 entry + 1 exit; la strategia è long-only, NON entrambi i lati).
  Dipendenze: F1-S01. Stima: 0.75gg. Lane: A.

- [x] **F1-S04 · Routing `main.py` su lista strategie**
  File: `main.py`, `src/config.py` (aggiungere `strategies: List[str]` da `.env`, default `["momentum_drop"]`).
  Operazione: loop strategie × engine esistente; `results_writer` con colonna/suffisso strategia; mantenere output esistenti invariati per `momentum_drop` (retrocompatibilità).
  DoD: run con 2 strategie → 2 set di risultati; run solo momentum → output identici a pre-Fase-1.
  Dipendenze: F1-S02, F1-S03. Stima: 0.75gg. Lane: A.

- [x] **F1-G01 · Test contratto GPU (vincolo v3 obbligatorio)**
  File: `tests/test_strategy_base.py` (estendere).
  Operazione: per ogni strategia registrata: `gpu_param_arrays(grid)` restituisce dict di `np.ndarray` tipizzati di lunghezza `len(grid)`; `gpu_metric_names()` lunghezza fissa = 8 (le metriche del kernel attuale).
  DoD: test verde per momentum + mean-reversion; chiude il vincolo §6.1-nota-v3 prima di Fase 3.
  Dipendenze: F1-S02, F1-S03. Stima: 0.25gg. Lane: A.

- [x] **F1-M01 · Sortino/Calmar/Expectancy in `metrics.py` (CHG-001)**
  File: `src/metrics.py` (aggiungere `sortino_ratio(values, target=0.0)`, `calmar_ratio(annual_return, max_drawdown)`, `expectancy(win_rate, avg_win, avg_loss)` — solo numpy), `src/strategy.py` (`BacktestResult`: +3 campi float default 0.0), cablaggio in `calculate_metrics` con convenzione esistente (signal-only → `pnl_percent`, altrimenti `pnl`).
  DoD: valori verificati a mano su 3 casi (tutti-win / tutti-loss / misto con downside noto); `tests/test_metrics.py` esteso, verde.
  Dipendenze: nessuna. Stima: 0.5gg. Lane: A-parallela (eccezione esplicita alla sequenzialità Lane-A: file disgiunti da F1-S01…S04 — `metrics.py`, `strategy.py`, `tests/test_metrics.py` — lock §14.2 garantisce l'esclusione).

- [x] **F1-GATE · Chiusura Fase 1**
  DoD: 2 strategie via `main.py`, metriche v3 nei risultati, test contratto GPU verdi, nessuna regressione su output momentum. Solo allora: via a F2 (Lane B/C già attive da F0).

---

## 5 — Fase 2: Motore BO (3–5 giorni)

**Obiettivo**: Optuna al posto di `itertools.product`. Prerequisito: F1 chiusa. Nota v3 vincolante: TPE, non GP — niente formule EI/PI/UCB da implementare.

- [x] **F2-B01 · Dipendenze e scheletro searcher**
  File: `requirements.txt` (+`optuna`), nuovo `src/searcher/__init__.py` + `src/searcher/bayesian_optimizer.py` (classe `BayesianOptimizer(strategy, n_startup_trials=20)` con `optimize(df, n_trials)`).
  DoD: `import optuna` ok in venv; scheletro importabile; `requirements.txt` aggiornato con versione pinnata (`optuna==x.y.z` da `pip freeze`).
  Dipendenze: F1. Stima: 0.25gg. Lane: A.

- [x] **F2-B02 · Objective su `parameter_space()` + TPESampler + MedianPruner**
  File: `src/searcher/bayesian_optimizer.py`.
  Operazione: `trial.suggest_*` guidato da `strategy.parameter_space()` con mappatura kind→suggest (`float`→`suggest_float`, `int`→`suggest_int`, `*_log`→`log=True`); score = `strategy.score(result)`; `trial.report` + `should_prune`; `TPESampler(n_startup_trials=20)`, `MedianPruner(n_warmup_steps=5)`.
  DoD: 20 trial su dataset piccolo terminano; trial potati registrati come `TrialPruned`, non come errori.
  Dipendenze: F2-B01. Stima: 1gg. Lane: A.

- [x] **F2-B03 · Parser CLI in `main.py` + flag `--search {grid,optuna}`**
  File: `main.py` (verificato: NESSUN argparse oggi — va creato `parse_args()`), `src/config.py` (`search_method`, `n_trials`, default che preserva comportamento attuale = grid).
  Operazione: creare `parse_args()` con precedenza esplicita **CLI > .env > default** (documentata in `--help` e nel report di fase); routing grid vs optuna per strategia; study salvato su `optimization_study_optuna.db` (storage RDB ripristinabile). Questo parser è riusato da F3-V07 (`--validation-mode`) e F4-G05 (`--llm-assist`): disegnarlo estendibile, non monouso.
  DoD: `--search grid` ≡ output pre-Fase-2; `--search optuna --n-trials 30` produce `best_params` + db file; `main.py` senza argomenti ≡ comportamento pre-Fase-2 (retrocompatibilità totale).
  Dipendenze: F2-B02. Stima: 0.75gg. Lane: A (lock `main.py`).

- [x] **F2-B04 · Parità grid-vs-BO (test di correttezza)**
  File: `tests/test_bayesian_optimizer.py` (nuovo).
  Operazione: spazio piccolo enumerabile (es. 3×3×3=27): BO con budget ≥ 27 ritrova l'ottimo grid entro tolleranza in ≥4 seed su 5 (criterio onesto per ottimizzatore stocastico: MAI "deve sempre"); con budget 10 batte la media random su 5 seed.
  DoD: test verdi; tolleranza e seed documentati nel test.
  Dipendenze: F2-B03. Stima: 0.75gg. Lane: A.

- [x] **F2-B05 · Parallel workers (`n_jobs=4`) + doc uso**
  Operazione: `study.optimize(..., n_jobs=4)` con backend thread-safe (strategia senza stato globale; `njit` rilascia il GIL di default — verificare, non presumere); uso documentato nel report di chiusura Fase 2 (comandi, db, resume), non in README sparsi.
  DoD: run 4-job < 2.5× il tempo 1-job sullo stesso budget (speedup > 1.6×); resume da db esistente verificato.
  Dipendenze: F2-B04. Stima: 0.5gg. Lane: A.

---

## 6 — Fase 3: Validazione robusta (5–7 giorni)

**Obiettivo**: Purged K-Fold + CPCV + PBO/semaforo + DSR + Walk-Forward + `--validation-mode`. Prerequisiti: F1; F2 raccomandato. **Include il punto decisionale differito D-1.**

- [x] **F3-V01 · Prerequisiti DSR: Sharpe in `metrics.py` + `scipy` (CHG-006)**
  File: `requirements.txt` (+`scipy` pinnato), `src/strategy.py` (AGGIUNGERE `sharpe_ratio: float = 0.0` a `BacktestResult` — verificato: il campo esiste solo nello sketch v3 §5.3, NON nel codice reale), `src/metrics.py` (`sharpe_ratio(values, risk_free=0.0)` annualizzato, stessa convenzione signal-only di F1-M01), cablaggio in `calculate_metrics`.
  DoD: Sharpe verificato a mano su serie sintetica (mean/std noti, annualizzazione √252); `tests/test_metrics.py` esteso, verde.
  Dipendenze: F1 (lock `strategy.py`+`metrics.py` con F1-M01 già chiusa). Stima: 0.5gg. Lane: A.

- [x] **F3-V02 · `PurgedKFold` in `src/validation/cross_validator.py` (nuovo package)**
  Operazione: split temporali K=5, purging osservazioni con label che si estende nel test, embargo 1–5% (parametro); API `split(X, y, horizon) → (train_idx, test_idx)`.
  DoD: test sintetico — nessuna osservazione del train ha label che tocca il test (controllo esaustivo sugli indici); embargo gap verificato.
  Dipendenze: F1. Stima: 1.5gg. Lane: A.

- [x] **F3-V03 · `CombinatorialPurgedCV` + `calculate_pbo` + `evaluate_pbo` (CHG-005)**
  File: `src/validation/cross_validator.py` (estendere).
  Operazione: generazione percorsi C(N−1,K−1) **con cap pratico** (vedi D-1: enumerazione completa solo sotto soglia, altrimenti campionamento stratificato con seed); `calculate_pbo = n_negativi/n_totali`; `evaluate_pbo` con semaforo v3 (<10/10–50/>50) e disclaimer in docstring (soglie empiriche).
  DoD: **verifica critica v3**: strategia random (segnali casuali, seed multipli) → PBO > 50%; strategia con edge sintetico iniettato → PBO < 50%. Se fallisce, bug nel calcolo — non procedere.
  Dipendenze: F3-V02. Stima: 1.5gg. Lane: A.

- [x] **F3-V04 · Semaforo PBO nel protocollo (§6.2 step 5 già allineato in v3)**
  Operazione: wiring `evaluate_pbo` nel `AntiOverfittingProtocol` (§6.2): esiti `SOLID → accetta`, `POTENTIALLY_VALID → walk-forward+holdout obbligatori`, `OVERFITTED → rigetta`; loggare sempre N_trials accanto al PBO (trabocchetto v3).
  DoD: mapping deterministico verificato (9.9→SOLID, 10.1→POTENTIALLY_VALID, 49.9→POTENTIALLY_VALID, 50.1→OVERFITTED); N_trials sempre presente nel log accanto al PBO; nota operativa nel report: valori entro ±2pp dai confini si trattano come fascia gialla a prescindere (confini morbidi per l'operatore, deterministici per il codice).
  Dipendenze: F3-V03. Stima: 0.5gg. Lane: A.

- [x] **F3-V05 · DSR operativo (CHG-004, solo ora che F3-V01 esiste)**
  File: `src/validation/dsr.py` (nuovo, piccolo).
  Operazione: `calculate_dsr(sharpe, pbo)` = approssimazione `SR×(1−2×PBO)` come default operativo + `calculate_dsr_exact(sharpe, years)` = `φ/Φ` con `scipy.stats.norm` (documentare quando usare quale: operativa sempre, esatta per report finale con T in anni); regola `DSR < 0 → rigetta` nel protocollo.
  DoD: DSR negativo per strategia random ad alto PBO; DSR ≈ SR per PBO ≈ 0; test con valori noti di φ/Φ.
  Dipendenze: F3-V01, F3-V03. Stima: 0.5gg. Lane: A.

- [x] **F3-V06 · Walk-Forward con purging (no t-test/Shapiro — esclusione v3)**
  File: `src/validation/walk_forward.py` (nuovo).
  Operazione: finestre train(6m)/test(1m)/embargo(0.5m) parametrizzabili; per finestra: BO-opzionale sul train, backtest OOS sul test; output: PnL per periodo + profitability-rate + DSR + PBO (criteri v3, NON test parametrici: assunzione i.i.d. violata da finestre sovrapposte).
  DoD: run su 12+ mesi di dati → report per-periodo; strategia piatta → profitability ≈ 50% (sanity).
  Dipendenze: F3-V03, F2 (per BO-per-finestra; fallback: parametri fissi). Stima: 1.5gg. Lane: A.

- [x] **F3-V07 · Flag `--validation-mode {off,purged,cpcv,walkforward}` in `main.py` + holdout finale**
  Operazione: default `off` (comportamento invariato); holdout = ultimi 6 mesi MAI toccati da ricerca/validazione, usati una sola volta a fine protocollo; documentare che riusare l'holdout lo invalida.
  DoD: `--validation-mode off` ≡ output pre-Fase-3; `cpcv` produce PBO+DSR; holdout usato 2 volte → warning esplicito nel log.
  Dipendenze: F3-V02…F3-V06. Stima: 0.75gg. Lane: A (lock `main.py`).

- [ ] **D-1 · PUNTO DECISIONALE DIFFERITO — budget backtest lunghi (come pattuito: solo quando serve)**
  Quando scatta: al primo run CPCV/Walk-Forward su dataset reale > 6 mesi, oppure al primo OOM/timeout.
  Da decidere allora (non ora): cap percorsi CPCV (soglia enumerazione completa vs campionamento con seed), finestre WF e budget BO-per-finestra, uso GPU vs CPU per la validazione, dataset di riferimento standard per i benchmark di fase.
  DoD del punto: decisione scritta in nuovo `docs/compute_budget.md` (NON in appendice al report Fase 0, che resta congelato a fine F0); mai bloccare F3 in attesa — usare i default conservativi (cap 5.000 percorsi, seed fisso).

---

## 7 — Fase 4: Strategy generation (5–10 giorni)

**Obiettivo**: crossover/mutation parametrici + template registry. Prerequisito: F1 (F3 raccomandato per validare i generati). **LLM esplicitamente opzionale.**

- [x] **F4-G01 · `src/generator/strategy_generator.py`: tipi e registry**
  Operazione: `TEMPLATE_REGISTRY` (momentum_drop, mean_reversion_zscore, breakout, grid — spazi parametrici v3 §5.4); `generate_from_template(name, rng: np.random.Generator)` → dict parametri validati via `strategy.validate`.
  DoD: 100 generazioni → 100% `validate() == True`; seed riproducibile.
  Dipendenze: F1. Stima: 1gg. Lane: A.

- [x] **F4-G02 · `StrategyCrossover` (a livelli: archetipo / parametri / filtri)**
  Operazione: crossover parametrico (media/ranga per parametro) + crossover strutturale (entry di A + filtri di B) secondo genoma v3 §4.3; figli sempre validati, scartati se invalidi.
  DoD: figli di 2 strategie note → validi; test che entry-A/filtri-B si compongono senza eccezioni.
  Dipendenze: F4-G01. Stima: 1.5gg. Lane: A.

- [x] **F4-G03 · `StrategyMutation` (parametrica / strutturale / risk)**
  Operazione: mutazioni con ampiezza parametrizzata (σ per parametro continuo, ±1 per interi, swap per categorici); rate default 0.05.
  DoD: distribuzione delle mutazioni verificata statisticamente su 1.000 campioni (media≈0, supporto nei bounds).
  Dipendenze: F4-G01. Stima: 1gg. Lane: A.

- [x] **F4-G04 · Loop evolutivo + validazione dei generati (100 strategie test)**
  Operazione: popolazione 50 × 10 generazioni su dataset piccolo (= 500 valutazioni); ogni generato passa F3-light (split + PBO su sample ridotto, come esercizio del path — NON come giudizio di accettazione); log genealogia (genitori → figlio → score).
  DoD: tutti i generati loggati eseguibili (≥100 ispezionati); top-5 con score > baseline random; genealogia ispezionabile.
  Dipendenze: F4-G02, F4-G03 (F3-V03 per PBO-light). Stima: 2gg. Lane: A.

- [x] **F4-G05 · (OPZIONALE, esplicito) LLM-assistito — solo se richiesto dopo F4-G04**
  Operazione: prompt template v3 §5.4 + sandbox di validazione (compila? implementa interfaccia? genera segnali su fixture?); rigetto automatico se fallisce un gate.
  DoD: attivabile solo con flag `--llm-assist`; zero dipendenze obbligatorie aggiunte al core.
  Dipendenze: F4-G04. Stima: 2–3gg. Lane: A. **Default: NON fare.**

---

## 8 — Fase 5: Meta-analysis (5–10 giorni)

**Obiettivo**: regime detector (soglie) + clustering + focus allocator. Prerequisiti: F3 (risultati validati da analizzare). RF gated su F6. HMM/CUSUM e meta-labeling ESCLUSI (note future v3).

- [ ] **F5-A01 · `regime_detector.py`: ADX + Hurst + volatilità + variance ratio (soglie v3 §5.7)**
  Operazione: funzioni pure su DataFrame → etichetta regime per finestra (`TRENDING/RANGING/HIGH_VOL/NORMAL`); nessuna dipendenza ML.
  DoD: su serie sintetiche (trend lineare / sinusoide / random walk / shock) → etichette corrette ≥ 90% delle finestre.
  Dipendenze: F3. Stima: 1.5gg. Lane: A.

- [ ] **F5-A02 · `strategy_clusterer.py`: K-Means su vettori risultato**
  File: `requirements.txt` (+`scikit-learn` pinnato — serve qui per K-Means/silhouette, riusato poi da F5-R01).
  Operazione: vettore per strategia (win_rate, pnl_pct, sharpe, trades, dd, archetipo one-hot); k selezionato con silhouette su k=2..6; label cluster stabili su seed.
  DoD: strategie sintetiche dei 4 archetipi v3 si raggruppano coerentemente; report cluster leggibile.
  Dipendenze: F5-A01 + risultati F3 (prerequisito di fase). Stima: 1gg. Lane: A.

- [ ] **F5-A03 · `focus_allocator.py`: cluster × regime → budget ricerca**
  Operazione: tabella (regime_corrente × cluster → quota trial BO/generazioni); output consumabile da F2 (`n_trials` per strategia) e F4 (quale template mutare).
  DoD: scenario simulato (regime trending) → quota momentum > quota mean-reversion; integrazione secca (import senza cicli) con searcher e generator.
  Dipendenze: F5-A01, F5-A02. Stima: 1gg. Lane: A.

- [ ] **F5-A04 · Report meta ("il cervello")**
  File: nuovo `src/meta_analysis/report.py` (con `main()` + argparse minimale: `--results <dir> [--out report.md]`).
  Operazione: comando `python -m src.meta_analysis.report --results <dir>` → markdown: regime corrente, cluster, top strategie per regime, raccomandazione allocazione.
  DoD: report generato dal golden dataset con le frasi attese (assert su contenuti chiave).
  Dipendenze: F5-A03. Stima: 0.75gg. Lane: A.

- [ ] **F5-R01 · (GATED su F6) `feature_importance.py` con Random Forest**
  Operazione: solo dopo F6 chiusa; `scikit-learn` già in requirements da F5-A02; importanza feature→successo per strategia; **mai** Bagging/Stacking (esclusione v3 vincolante).
  DoD: su feature sintetiche con 1 segnale vero + 5 rumore → il segnale vero è top-1.
  Dipendenze: F5-A04 + F6 chiusa. Stima: 1gg. Lane: A.

---

## 9 — Fase 6: Feature engineering (3–5 giorni)

**Obiettivo**: indicator factory standalone. Prerequisiti: F0 chiusa (disciplina di fase; tecnicamente basta il formato OHLC). **Lane B: parallela a F1/F2.**

- [x] **F6-E01 · `src/features/indicator_factory.py`: SMA/EMA/RSI/BB/ATR**
  Operazione: funzioni pure vettoriali (pandas/numpy, niente loop Python); convenzione NaN iniziali documentata (warmup = `max(periodi)` righe).
  DoD: confronto con valori noti (RSI-14 su serie fixture calcolata a mano con seconda implementazione indipendente); tolleranza 1e-8.
  Dipendenze: F0. Stima: 1gg. Lane: B.

- [x] **F6-E02 · MACD/OBV/VWAP**
  Operazione: stesse convenzioni F6-E01; VWAP con tipico `(H+L+C)/3 × V` cumulato per sessione/giorno.
  DoD: stessi criteri F6-E01 su fixture dedicate.
  Dipendenze: F6-E01. Stima: 0.75gg. Lane: B.

- [x] **F6-E03 · Integrazione DataFrame: `add_features(df, list)`**
  Operazione: una chiamata aggiunge N colonne senza mutare l'input (copy-on-write); nomi colonne stabili (`sma_20`, `rsi_14`, …) registrati in `FEATURE_REGISTRY`.
  DoD: idempotenza (doppia chiamata → stesse colonne, nessun duplicato); test con lista vuota e indicatore ignoto (errore esplicito).
  Dipendenze: F6-E02. Stima: 0.5gg. Lane: B.

- [x] **F6-E04 · OHLC multi-timeframe lato Python (resample da 1s)**
  Operazione: `resample_ohlc(df_1s, rule)` con regole `1min/5min/1h/1d`; allineamento temporale documentato (label/closed convenzione).
  DoD (primaria, senza dipendenze esterne): OHLC 1m da fixture 1s sintetica verificata a mano (O=primo open, H=max high, L=min low, C=ultimo close, V=somma volumi, conteggio candele esatto). DoD (condizionale, solo se F7-T02 chiusa): stesso confronto contro CSV della pipeline TS.
  Dipendenze: F6-E03. Stima: 0.75gg. Lane: B.

---

## 10 — Fase 7: Multi-timeframe (3–5 giorni)

**Obiettivo**: `ohlcAggregator.ts` parametrizzato + 1m/5m/1h/1d. Prerequisiti: F0-ts. **Lane C: parallela a tutto il Python.**

- [x] **F7-T01 · `aggregateToOhlc(interval_seconds)` in `ohlcAggregator.ts`**
  Operazione: generalizzare l'aggregatore 1s esistente a intervallo arbitrario (1/60/300/3600/86400); preservare path streaming; firma retrocompatibile (`aggregateToOhlc1s` = wrapper).
  DoD: output 1s identici a pre-modifica (byte-identical su fixture); memoria: confronto RSS prima/dopo su fixture grande (stesso intervallo, 1s vs 1s) → nessun aumento oltre +10%, altrimenti ottimizzare prima di chiudere.
  Dipendenze: F0-ts. Stima: 1gg. Lane: C.

- [x] **F7-T02 · Integrazione pipeline (`runPipeline.ts` / `downloadAggTrades.ts`)**
  Operazione: flag `--timeframes 1s,1m,5m,1h,1d` (verificare se `runPipeline.ts` ha già parsing argv: se no, aggiungerlo minimale); nomi file `ohlc_{tf}_{range}.csv`; skip intervalli già presenti (idempotenza).
  DoD: run con 2 timeframe → 2 set CSV coerenti (candele 1m = aggregazione di 60 candele 1s, test esaustivo su fixture).
  Dipendenze: F7-T01. Stima: 1gg. Lane: C.

- [x] **F7-T03 · Test `ohlcAggregator.test.ts` (estendere suite esistente)**
  Operazione: buchi temporali, DST/secondi mancanti, volumi zero, ultimo bucket parziale.
  DoD: `npx jest` verde inclusi i 4 edge case; coerenza 1s→1m su dati reali (campione UNIUSDT).
  Dipendenze: F7-T02. Stima: 0.75gg. Lane: C.

---

## 11 — Fase 8: UI/Dashboard (2–4 settimane, NECESSARIA)

**Obiettivo**: visualizzazione interattiva di tutto. Prerequisiti: F1+F2 (formati risultati + study); wiring completo dopo F3/F7. Sviluppo con mock fino ad allora (Lane D).

- [ ] **F8-U01 · Optuna Dashboard sullo study RDB**
  Operazione: `pip install optuna-dashboard` (dipendenza solo-UI, isolata: non entra in `requirements.txt` core — file separato `requirements-ui.txt` o nota nel report); `optuna-dashboard` su `optimization_study_optuna.db` (stesso file di F2-B03); script `npm run dashboard:optuna` (o `optuna-dashboard sqlite:///...`); documentare porta e accesso.
  DoD: dashboard raggiungibile con history/param-importance dello study reale F2.
  Dipendenze: F2. Stima: 0.5 sett. Lane: D.

- [ ] **F8-U02 · Equity curve + drawdown per strategia**
  Operazione: endpoint/pagina che legge i CSV risultati (`backtest-results/{SYMBOL}/`) e disegna equity cumulata e underwater; convenzione `metrics.py` rispettata (modalità signal-only → equity su `pnl_percent`, altrimenti su `pnl` — in signal-only l'equity USDT è piatta per costruzione, mostrarla sarebbe fuorviante); mock JSON fino al wiring.
  DoD: su golden dataset, equity finale ≡ `total_pnl` (o `total_pnl_percent` in signal-only) del CSV (assert numerico, non visivo).
  Dipendenze: F1 (formato risultati). Stima: 0.75 sett. Lane: D.

- [ ] **F8-U03 · Parameter heatmap + tabella confronto strategie con filtri**
  Operazione: heatmap su 2 parametri a scelta (default X×Z per momentum, NON hardcoded: la strategia ha N parametri generici) con metrica a scelta (PnL/Sharpe/Sortino); tabella filtrabile (strategia, regime, min trades, min Sharpe, max DD) con ordinamento; esportazione CSV della vista.
  DoD: filtri su golden dataset restituiscono le righe attese (test su logica di filtro, non su pixel); heatmap verificata anche su mean-reversion (assi = suoi parametri, non X/Y/Z).
  Dipendenze: F8-U02. Stima: 1 sett. Lane: D.

- [ ] **F8-U04 · Report PDF/HTML completo**
  Operazione: template che assembla config, top-N, equity/drawdown, heatmap, PBO/DSR (se F3 attiva), regime corrente (se F5 attiva); sezioni assenti se la fase non è attiva (degradazione elegante, mai crash).
  DoD: report generato su golden dataset con tutte le sezioni disponibili; con sole F1+F2 attive, le sezioni F3/F5 risultano "non disponibile" senza errori.
  Dipendenze: F8-U03 (+F3/F7 per wiring completo). Stima: 0.75 sett. Lane: D.

---

## 12 — Stop point: valore anche se ci si ferma

| Dopo | Cosa si ha in mano | Vale per |
|------|--------------------|----------|
| F0 | Sistema attuale pulito, testato, con bug reali chiusi e report | baseline affidabile |
| F1 | Backtester multi-strategy + metriche v3 + contratto GPU | confrontare strategie diverse |
| F2 | Ricerca intelligente (100× meno valutazioni del grid) | esplorare spazi grandi |
| F3 | Strategie validate (PBO/DSR/WF) — **primo milestone di fiducia** | fidarsi dei risultati |
| F4 | Loop evolutivo di nuove strategie | discovery automatica |
| F5 | Report "cosa funziona in quale regime" | guidare la ricerca |
| F6–F7 | Feature + multi-timeframe | strategie avanzate |
| F8 | Prodotto completo e presentabile | uso quotidiano |

---

## 13 — Lista NON-FARE (voci scartate dalla v3)

Chi esegue una task e incontra una di queste voci, NON la implementa. Motivazioni complete in `THEORY_VS_MASTERPLAN_RIVALUTAZIONE.md`. Eccezione: riapertura solo con i prerequisiti scritti qui soddisfatti.

| Voce | Perché no | Riapribile se |
|------|-----------|---------------|
| Production Chain / Meta-Strategy Paradigm come framework | Istituzionali, zero decisioni operative ne derivano | Mai (principi già nel masterplan) |
| RL (PPO/DDPG/SAC, TradeMaster) | Altro progetto (portafoglio adattivo), zero prerequisiti | Progetto separato |
| Sample Weighting | Niente labeling/overlap nel grid search | Labeling con overlap introdotto |
| Multiple Testing (sezione autonoma) | Grid parametrico ≠ ipotesi distinte | Strategie distinte in valutazione (Fase 4+) |
| EI/PI/UCB | Usiamo TPE, non GP | GP implementato da zero (non previsto) |
| Bagging / Stacking | Ridondanti (CPCV/WF) / prerequisiti lontani | Mai per Bagging; Stacking con N strategie validate + meta-learner |
| VGP / bloat / parsimony / ADF | Generazione parametrica, non alberi | GP su alberi introdotto (non previsto) |
| t-test / Shapiro sul WF | Assunzioni violate, campione scarso | Mai (criteri v3 bastano) |
| Kelly in `StrategyResult` | È sizing, non valutazione | Modulo Bet Sizing esistente |
| CUSUM realtime | Tool di produzione | Fase produzione |
| Fracdiff / FFD nel workflow | Niente ML consumatore | Modello ML su serie (CHG-007) |
| Bibliografia nel masterplan | Già nel theory | Mai (puntatore basta) |
| Sisyphus come sezione | Retorica, principio già presente | Mai |
| HMM nel discovery | Appartiene alla produzione | Produzione (CHG-012) |
| IC/IR/AlphaMonitor ora | Niente segnali continui/produzione | CHG-009 soddisfatto |

---

## 14 — Protocollo di esecuzione per agenti

1. **Claim**: un agente prende UNA task `[ ]` → la marca `[~]` (una sola `in_progress` per agente) e dichiara la lane.
2. **Lock file condivisi**: `main.py`, `requirements.txt`, `src/strategy.py`, `src/metrics.py` — una sola task attiva per file; le altre aspettano.
3. **Grounding prima del codice**: rileggere i file toccati + la sezione v3 citata; se il codice reale contraddice la task, fermarsi e segnalare (come è successo in Fase 0: 3 voci già corrette) invece di "correggere" a vuoto.
4. **DoD o niente**: una task è `[x]` solo con DoD soddisfatta e verificata (test eseguiti, output mostrati). Mai per intenzione.
5. **Report di chiusura fase**: ogni fase chiude con i suoi test verdi + (F0, F3, F8) un mini-report in `docs/analysis/`.
6. **Divieti**: niente nuove dipendenze senza task che la prevede; niente refactor non richiesti; niente voci §13; niente modifiche a formati condivisi (CSV OHLC, CSV risultati, schema study Optuna) senza aggiornare le lane dipendenti.
7. **Definition of done globale**: F8-U04 verde + tutte le DoD di fase soddisfatte + `pytest` e `npx jest` verdi su tutto il repo.

---

> **Stato documento**: creato il 2026-09-25 da masterplan v3 (2.094 righe) + grounding sul codice reale. Ogni task cita file e righe verificati in pari data; se il codice è cambiato nel frattempo, il protocollo §14.3 impone riverifica prima dell'esecuzione.
