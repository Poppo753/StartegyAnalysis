# Changelog — Binance OHLC Pipeline

Formato basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/).

## [Unreleased]

### Aggiunto
- **Retry Logic Fix** (`src/binance/binanceClient.ts`): refactoring del retry con `for` loop esplicito, elimina `while(true)` rischioso (caso #01).
- **Race Condition Fix** (`src/pipeline/downloadAggTrades.ts`): merge basato su stream invece di `readFileSync`/`appendFileSync` (caso #02).
- **Data-based Split** (`python-backtester/src/gpu/data_splitter.py`): split basato su date reali, non indici (caso #03).
- **Cross-platform Unzip** (`src/binance/bulkDownloader.ts`): sostituzione `child_process` con `jszip` (caso #04).
- **Shared OHLC Aggregator** (`src/pipeline/ohlcAggregator.ts`): classe condivisa per aggregazione OHLC (caso #05).
- **Unit Tests** (`src/**/*.test.ts`, `python-backtester/tests/`): suite di test unitari per TypeScript e Python (caso #06).
- **Gzip Support** (`src/storage/jsonlWriter.ts`, `src/utils/gzipUtils.ts`): supporto nativo per file `.jsonl.gz` (caso #07).
- **JSON Structured Logging** (`src/utils/jsonLogger.ts`): log JSON su stderr con `service`, filtro `LOG_LEVEL`, safe-stringify anti-circolare; `logger.json.*` in `src/utils/logger.ts`, commutazione via `JSON_LOGGING=true` (caso #22).
- **MAE/MFE nel backtester**: `mae_pct`/`mfe_pct` direction-aware in `_execute_trade` (`simulator.py`), campi su `Trade` e `avg_mae`/`avg_mfe` su `BacktestResult` (`strategy.py`), aggregazione in `metrics.py`, versione su array con clip ≥ 0 in `fast_metrics.py`, tracking in `gpu_runner.py` (caso #23).
- **K-Fold Temporal Cross-Validation** (`python-backtester/src/gpu/data_splitter.py`): `k_fold_split(df, k)` expanding window su `k+1` chunk con `_boundary_to_run_start` anti-leakage e assert (caso #24).
- **Profiler integrato** (`python-backtester/src/profiling.py`): `Profiler` cProfile+tracemalloc, decoratore `@profile`, attivazione via `PROFILING=1`, stdlib-only (caso #25).
- **Modulo condiviso trade_utils** (`python-backtester/src/utils/trade_utils.py`): `DataLoadError`, `load_trades`, `calc_metrics`, `format_metrics`/`diagnose`, `load_ohlc_data` (caso #11).
- **pyproject.toml** (`python-backtester/pyproject.toml`): manifest PEP 517/518 con `setuptools.build_meta`, `requires-python >= 3.10`, config pytest (caso #20).
- **Type hints** su tutti i moduli `python-backtester/src/` (caso #17).
- **Documentazione enterprise** (`docs/analysis/09_*` … `docs/analysis/25_*`): tutti i casi 09-25 riscritti nel formato Codice originale → Bug → Alternative A/B/C → Soluzione → Impatto, verificati sul codice reale.
- **Predicato filtro download** (`src/pipeline/downloadAggTrades.ts`): `isTradeInWindow()` esportato con documentazione delle tre clausole + 5 test in `downloadAggTrades.test.ts` (gap #4, semantica bit-identica).
- **Dockerfile** (`Dockerfile`, `python-backtester/Dockerfile`, `.dockerignore`): build riproducibili multi-stage/slim, `data/` come volume, `.env` a runtime (caso #21, doc `21_dockerfile`).

### Modificato
- `src/pipeline/aggregateStreaming.ts` — Usa `OHLCAggregator`.
- `src/extractRange.ts` — Usa `OHLCAggregator.fmt` e `normalizeTimestamp`.
- `src/storage/csvWriter.ts` — Usa `OHLCAggregator.fmt`.
- `src/pipeline/aggregateToOhlc.ts` — Usa `OHLCAggregator.fromArray`.
- `src/binance/bulkAvailability.ts` — Check disponibilità via regex escapata su tag S3 `<Key>` invece di `includes()` (caso #09).
- `python-backtester/src/gpu/gpu_simulator.py` — Binary search O(log n) + forward scan limitata alla finestra, nei kernel statico e dynamic-Y (caso #12).
- `python-backtester/src/gpu/gpu_fallback.py` — Screening `prange` con accumulatori thread-local e scritture disgiunte `results[tid]`; stesso pattern binary-search del kernel CUDA (casi #12, #13).
- `python-backtester/src/fast/fast_runner.py` — Warmup JIT con guardia `len(close) < 100` (caso #13).
- `python-backtester/src/fast/fast_simulator.py` — Array `_simulate_single` a 10 colonne (era 12 con 2 colonne garbage che ingannavano il rilevamento dynamic-Y in `gpu_runner`); loop dynamic-Y riscritto con binary-search + forward scan; `check_numba_available()` solleva `NumbaMissingError` invece di `sys.exit`; stub non-numba tipizzati (audit gap).
- `python-backtester/main.py` — Catch `NumbaMissingError` al boundary CLI nei motori fast/gpu (audit gap).
- `src/pipeline/downloadAggTrades.ts` — `mergeDayFiles` riscritto: pump manuale senza `pipeline`-in-loop (chiudeva il sink al primo file), output `.gz` ricompresso via unico `createGzip`, `writeEmptyGzip` per caso vuoto, funzione esportata per testabilità (audit gap).
- `src/storage/jsonlWriter.ts` — `getGzipPath("….jsonl")` ora rende `"….jsonl.gz"` invece di `"….jsonl.jsonl.gz"` (doppia estensione: `aggregateOnly.ts` non trovava mai il file con gzip attivo) (audit gap).
- `src/pipeline/downloadAggTrades.ts` — Nuovo `isTradeInWindow()` esportato con semantica bit-identica e commento per-clausola (la guardia `<= windowEndMs` serve alle pagine `fromId` senza `endTime`) (gap #4).
- `python-backtester/trade_profile.py`, `stoploss_analysis.py` — `main() -> int` con `sys.exit(main())` solo in `__main__`; errori "nessun file" su stderr con exit code 2; import-safe (audit gap).
- `python-backtester/src/utils/__init__.py` — Type hints completi su `Timer` e `print_*` (audit gap #17).
- `python-backtester/src/profiling.py` — Output ASCII-only: `print()` di libreria non deve mai sollevare `UnicodeEncodeError` su console Windows cp1252 (audit smoke test).
- `python-backtester/src/config.py` — Tutti gli errori sollevano `ConfigError` (sottoclasse di `ValueError`); rimossi `print`/`sys.exit` dal modulo, unico catch+exit al boundary CLI in `main.py` (caso #15).
- `python-backtester/src/data_loader.py` — Ridotto a re-export di `load_ohlc_data`/`DataLoadError` da `trade_utils` (caso #11).
- `docs/analysis/22_json_logging/analysis.md` — Sostituito il contenuto errato su `jsonlWriter` con la documentazione reale di `jsonLogger.ts`/`logger.ts`.
- `docs/analysis/25_profiler_integration/analysis.md` — Sostituito il contenuto incompleto (solo `Timer`) con la documentazione reale di `profiling.py`.

### Rimosso
- `src/pipeline/aggregateToOhlc.ts` — Rimosso: funzionalità coperta da `OHLCAggregator.fromArray` (caso #10).
- `src/utils/rateLimiter.ts` — Non più usato direttamente dal `binanceClient.ts` (il `GlobalRateLimiter` rimane).
- `train_ratio` dalla firma di `k_fold_split` — Parametro inutilizzato; geometria dei fold determinata da `k` (caso #24).
- Fold-0 con TRAIN vuoto dal K-fold — Ogni fold ora ha TRAIN non-vuoto (`range(1, k+1)`, caso #24).

### Corretto
- Falsi positivi `bulkAvailability` per sottostringa, match fuori `<Key>` e metacaratteri regex non escapati (caso #09).
- Complessità O(n·finestra) della ricerca lookback/minimo-finestra nei motori GPU/CPU (caso #12).
- First-run penalty JIT inclusa nei benchmark fast; crash del warmup su dataset < 100 candele (caso #13).
- `print`+`exit` nel loader di configurazione: ora raise-only e testabile (caso #15).
- Inversione MAE↔MFE sugli short; medie avvelenate da `entry_price = 0` nel path fast (caso #23).
- Leakage da timestamp duplicati al confine dei fold; split degeneri silenziosi (caso #24).
- Backend string in doc caso #20: il file reale usa `setuptools.build_meta`.

## [1.0.0] — Initial Release
- Pipeline TypeScript completa per download dati Binance.
- Python backtester con 3 motori (standard/fast/gpu).
- Architettura modulare con separazione TypeScript/JSONL/CSV.
