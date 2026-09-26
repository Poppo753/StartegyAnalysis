# 📋 MILESTONE F3 — REPORT DI CHIUSURA

Data: 2026-09-26 · Esecuzione: 1 subagent (Lane A) · Verifica indipendente: suite rieseguita + wiring `main.py` riletto dal coordinatore.

## Fase 3: Validazione robusta (F3-V01…V07)

- `scipy==1.15.3` pinnato; `sharpe_ratio` annualizzato in `metrics.py` + campo aggiunto a `BacktestResult` (verificato: mancava davvero nel codice).
- `src/validation/`: `cross_validator.py` (`PurgedKFold` K=5/embargo 1%, riusa `_boundary_to_run_start` da `data_splitter`, + `CombinatorialPurgedCV` con cap 5.000/seed 42), `protocol.py` (`apply_pbo_gate` con semaforo + N_trials nel log), `dsr.py` (operativa `SR×(1−2×PBO)` + esatta `φ/Φ` via scipy), `walk_forward.py` (6m/1m/0.5m, BO-per-finestra con fallback, niente t-test/Shapiro).
- **Check critico v3 superato con margini ampi**: random → PBO medio 0.90 (min 0.533); edge iniettato → PBO 0.0.
- `main.py`: `--validation-mode {off,purged,cpcv,walkforward}` (default off ≡ pre-Fase-3); holdout ultimi 6 mesi con warning su riuso; mode `cpcv` = trade-proxy documentata (6 gruppi contigui sul top-1, `calculate_pbo`/`calculate_dsr`/`apply_pbo_gate` reali — non uno stub; per CPCV bar-level: `CombinatorialPurgedCV + split_oos_pnl`).
- Deviazione accettata: test Sharpe in `test_validation_sharpe.py` invece di estendere `test_metrics.py` (lock file del coordinatore; solo collocazione).

## Suite finale (rieseguita dal coordinatore)

- `pytest tests/ -q` → **169 passed, 1 skipped** (skip pre-esistente documentato)

**Primo milestone di fiducia raggiunto. Via libera a Fase 4 (Lane A).**
