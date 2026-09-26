# Analisi Completa della Repository — Documentazione

## Panoramica

Questa cartella contiene l'analisi dettagliata di **tutti** i cambiamenti proposti per la repo `Binance OHLC Pipeline`.

Ogni caso segue il formato enterprise obbligatorio (riferimento: `01_retry_logic/analysis.md`):
`Codice originale` → `Bug Identificati` → `Alternative A/B/C con Pro/Contro` → `Soluzione Scelta` → `Impatto (Previene / Rischio / Test richiesti)`.

## Indice

| Cartella | Caso | Descrizione | Stato |
|----------|------|-------------|-------|
| `01_retry_logic` | Bug #1 | Fix Retry Logic (binanceClient.ts) | ✅ Implementato |
| `02_race_condition` | Bug #2 | Fix Race Condition Merge | ✅ Implementato |
| `03_data_split` | Bug #3 | Fix Data-based Split | ✅ Implementato |
| `04_jszip` | Miglioramento #4 | Sostituzione child_process con jszip | ✅ Implementato |
| `05_shared_ohlc` | Miglioramento #5 | Logica OHLC Condivisa | ✅ Implementato |
| `06_unit_tests` | Miglioramento #6 | Test Unitari | ✅ Configurato |
| `07_gzip` | Miglioramento #7 | Compressione Gzip | ✅ Utilità creata |
| `08_governance` | Governance | Code Governance e Struttura | ✅ Documentato |
| `09_xml_parsing_fix` | Fix #9 | XML parsing con regex escapata su tag `<Key>` (bulkAvailability.ts) | ✅ Implementato |
| `10_dead_code_removal` | Rimozione #10 | Rimozione aggregateToOhlc.ts, `OHLCAggregator.fromArray` unico | ✅ Implementato |
| `11_shared_trade_utils` | Refactoring #11 | Modulo condiviso trade_utils.py + re-export data_loader.py | ✅ Implementato |
| `12_gpu_sliding_window_fix` | Fix #12 | Binary search + forward scan in gpu_simulator.py / gpu_fallback.py | ✅ Implementato |
| `13_gpu_prange_fix` | Fix #13 | Thread-safety prange (solo `results[tid]`) + warmup con guardia | ✅ Implementato |
| `15_config_error_exceptions` | Fix #15 | `ConfigError` raise-only in config.py, catch al boundary CLI | ✅ Implementato |
| `17_python_type_hints` | Miglioramento #17 | Type hints verificati su tutti i moduli `src/` | ✅ Implementato |
| `20_pyproject_toml` | Config #20 | pyproject.toml (PEP 517/518, `setuptools.build_meta`) | ✅ Implementato |
| `21_dockerfile` | Config #21 | Dockerfile multi-stage TS + Python slim, `.dockerignore` | ✅ Implementato |
| `22_json_logging` | Miglioramento #22 | JSON structured logging su stderr (jsonLogger.ts + logger.ts) | ✅ Implementato |
| `23_mae_mfe_backtester` | Feature #23 | MAE/MFE direction-aware (simulator, strategy, metrics, fast_metrics) | ✅ Implementato |
| `24_kfold_crossvalidation` | Feature #24 | K-fold temporale expanding window, `k_fold_split(df, k)` | ✅ Implementato |
| `25_profiler_integration` | Feature #25 | Profiler cProfile+tracemalloc + `@profile` (profiling.py) | ✅ Implementato |

## Riepilogo Cambiamenti Implementati

### TypeScript Pipeline
- `src/binance/binanceClient.ts` — Refactoring retry con `for` loop esplicito
- `src/binance/bulkAvailability.ts` — XML check con regex escapata su tag `<Key>` (`escapeRegex`)
- `src/pipeline/downloadAggTrades.ts` — Merge basato su streaming
- `src/storage/jsonlWriter.ts` — Supporto gzip, streaming per grandi array, JSONL
- `src/pipeline/ohlcAggregator.ts` — Classe condivisa `OHLCAggregator` (`fromStream`/`fromArray`/`fmt`/`normalizeTimestamp`)
- `src/pipeline/runPipeline.ts` — Usa `OHLCAggregator`
- `src/storage/csvWriter.ts` — Usa `OHLCAggregator.fmt`
- `src/extractRange.ts` — Usa `OHLCAggregator` utilities
- `src/binance/bulkDownloader.ts` — jszip al posto di child_process
- `src/utils/gzipUtils.ts` — Utilità gzip compression
- `src/utils/jsonLogger.ts` — Structured JSON logging su stderr (`LOG_LEVEL`, `LOG_SERVICE`, safe-stringify)
- `src/utils/logger.ts` — Flag `JSON_LOGGING` + API `logger.json.*`
- `src/utils/rateLimiter.test.ts` — Test unitari
- `src/utils/dateUtils.test.ts` — Test unitari
- `src/pipeline/ohlcAggregator.test.ts` — Test unitari
- `src/config/config.test.ts` — Test unitari con ConfigError
- `jest.config.js` — Configurazione Jest
- `src/config/config.ts` — ConfigError exception handling

### Python Backtester
- `python-backtester/src/gpu/data_splitter.py` — Data-based split + K-fold temporale expanding (`k_fold_split`, `_boundary_to_run_start`)
- `python-backtester/src/utils/trade_utils.py` — Modulo condiviso (`DataLoadError`, `load_trades`, `calc_metrics`, `format_metrics`/`diagnose`, `load_ohlc_data`)
- `python-backtester/src/data_loader.py` — Re-export da `trade_utils` (shim di compatibilità)
- `python-backtester/src/gpu/gpu_simulator.py` — Binary search O(log n) + forward scan su finestra
- `python-backtester/src/gpu/gpu_fallback.py` — `prange` thread-safe (scritture disgiunte `results[tid]`)
- `python-backtester/src/config.py` — `ConfigError` raise-only, nessun print/exit
- `python-backtester/src/strategy.py` — Type hints + campi `mae_pct`/`mfe_pct`, `avg_mae`/`avg_mfe`
- `python-backtester/src/simulator.py` — Type hints + MAE/MFE direction-aware in `_execute_trade`
- `python-backtester/src/metrics.py` — Type hints + aggregazione `avg_mae`/`avg_mfe`
- `python-backtester/src/results_writer.py` — Type hints completi
- `python-backtester/src/parameter_grid.py` — Type hints completi
- `python-backtester/src/gpu/screening_metrics.py` — Type hints completi
- `python-backtester/src/gpu/filters.py` — Type hints completi
- `python-backtester/src/gpu/gpu_detector.py` — Type hints
- `python-backtester/src/gpu/gpu_runner.py` — Type hints + MAE tracking (`_add_advanced_metrics`)
- `python-backtester/src/fast/fast_simulator.py` — Type hints + binary search
- `python-backtester/src/fast/fast_metrics.py` — Type hints + MAE/MFE direction-aware con clip
- `python-backtester/src/fast/fast_runner.py` — Type hints + warmup con guardia `len < 100`
- `python-backtester/src/profiling.py` — `Profiler` (cProfile+tracemalloc) + decoratore `@profile`, flag `PROFILING`
- `python-backtester/main.py` — Catch `ConfigError`/`DataLoadError` al boundary CLI (unico punto con `sys.exit`)
- `python-backtester/pyproject.toml` — Configurazione progetto (PEP 517/518)
- `python-backtester/tests/` — Suite di test unitari
- `python-backtester/tests/test_data_splitter.py` — Test K-fold split

### Strumenti
- `python-backtester/stoploss_analysis.py` — Analisi post-hoc stop loss
- `python-backtester/trade_profile.py` — Profiler MAE/MFE completo (extended hold analysis, time-to-reversal)

### Documentazione
- `docs/CHANGELOG.md` — Registro delle modifiche (formato Keep-a-Changelog)
- `docs/analysis/` — Analisi dettagliata per caso (formato enterprise, casi 01-25)
- `docs/analysis/README.md` — Indice completo

## Test Esecuzione

### TypeScript
```bash
npm test                   # tutti i test
npm run test:coverage      # con copertura
```

### Python
```bash
cd python-backtester
"C:\Users\loren\AppData\Local\Programs\Python\Python310\python.exe" -m pytest tests/ -v
```

### Profiler
```bash
PROFILING=1 python main.py                 # dettaglio funzioni nei blocchi profilati
python trade_profile.py                    # Analisi MAE/MFE
python trade_profile.py --ohlc ohlc.csv ...  # Con extended-hold
```
