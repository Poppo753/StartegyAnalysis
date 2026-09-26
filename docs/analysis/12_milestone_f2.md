# 📋 MILESTONE F2 — REPORT DI CHIUSURA

Data: 2026-09-26 · Esecuzione: 1 subagent (Lane A) · Verifica indipendente: suite rieseguita dal coordinatore.

## Fase 2: Motore BO (F2-B01…B05)

- `optuna==5.0.0` pinnato in `requirements.txt`, installato in `.venv`.
- `src/searcher/bayesian_optimizer.py` (nuovo): mapping kind→`suggest_*` (`float/int/*_log`), score via path standard, `TPESampler(20)` + `MedianPruner(5)`; solo TPE, niente GP/EI/UCB.
- `main.py`: `parse_args()` creato (precedenza CLI > .env > default) con `--search/--n-trials/--strategy/--jobs/--study-db`; routing grid≡pre-Fase-2; study RDB `optimization_study_optuna.db` con `load_if_exists` (resume verificato 2→4 trial).
- `tests/test_bayesian_optimizer.py`: spazio 27 punti, ottimo ritrovato 5/5 seed; budget 10 batte random.
- Parallelismo: criterio DoD soddisfatto (4-job 1.77× < 2.5×) ma SENZA speedup reale — l'assunto "njit rilascia il GIL" è falso (`nogil=False` di default, repo senza `nogil=True`); path standard è GIL-bound. Riportato onestamente, non nascosto.

## Deviazioni dichiarate (§14.3, accettate)

- `src/config.py` NON toccato (lock del coordinatore): `search_method/n_trials` via env (`SEARCH_METHOD/N_TRIALS/OPTUNA_JOBS/OPTUNA_STUDY_DB`) in `main.py`. Equivalente, zero modifiche a file Fase 1.
- `.gitignore`: aggiunto `optimization_study_optuna.db` + `*.db` (rigenerabili) — fix coordinatore.

## Suite finale (rieseguita dal coordinatore)

- `pytest tests/ -q` → **110 passed, 1 skipped** (skip pre-esistente documentato)

## Uso (dal report agente, unica doc)

- Grid: `python main.py` o `--search grid [--strategy X]`
- Optuna: `python main.py --search optuna --n-trials 30 [--strategy X] [--jobs 4] [--study-db FILE]`
- Resume: stesso comando + stesso db (per ricominciare: cancellare il `.db` o cambiare `--study-db`)

**Via libera a Fase 3 (Lane A).**
