"""
main.py - Entry point del Python Backtester

Orchestrazione completa:
1. Carica configurazione da .env
2. Per ogni simbolo:
   a. Carica dati OHLC
   b. Genera griglia parametri
   c. Esegue backtest per ogni combinazione
   d. Calcola metriche
   e. Salva risultati
3. Stampa riepilogo top combinazioni
"""

import sys
import os

# Forza encoding UTF-8 per la console Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# Aggiungi la directory corrente al path per import moduli
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import load_config, ConfigError, Config
from src.data_loader import load_ohlc_data
from src.utils.trade_utils import DataLoadError
from src.parameter_grid import generate_parameter_grid
from src.simulator import run_backtest
from src.metrics import calculate_metrics
from src.results_writer import write_results
from src.strategy import BacktestParams
from src.strategies import STRATEGY_REGISTRY
from src.utils import (
    Timer,
    print_header,
    print_config_summary,
    print_top_results,
    print_completion,
)

import pandas as pd
from typing import List, Optional

# Default Fase 2 (usati quando né CLI né .env li definiscono).
DEFAULT_SEARCH = "grid"
DEFAULT_N_TRIALS = 50
DEFAULT_JOBS = 1
DEFAULT_STUDY_DB = "optimization_study_optuna.db"


def parse_args(argv: Optional[List[str]] = None):
    """Parser CLI estendibile (Fase 2, F2-B03).

    Precedenza (documentata anche in --help): CLI > .env > default.
    - --search: CLI > .env SEARCH_METHOD > default "grid".
    - --n-trials: CLI > .env N_TRIALS > default 50.
    - --strategy: CLI (ripetibile/comma-separated) > config.strategies
      (da .env STRATEGIES) — riusa il registry src/strategies.
    - --jobs: CLI > .env OPTUNA_JOBS > default 1.
    - --study-db: CLI > .env OPTUNA_STUDY_DB > default
      optimization_study_optuna.db.

    Estendibilità: F3 aggiungerà --validation-mode, F4 --llm-assist
    in questo stesso parser (non creare nuovi parser monouso).
    """
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Python Backtester (Fase 2: grid + Optuna TPE). "
            "Precedenza valori: CLI > .env > default."
        ),
        epilog=(
            "Env supportati: SEARCH_METHOD, N_TRIALS, OPTUNA_JOBS, "
            "OPTUNA_STUDY_DB, STRATEGIES (via config). "
            "Estendibile: F3 aggiungerà --validation-mode, "
            "F4 --llm-assist qui."
        ),
    )
    parser.add_argument(
        "--search",
        choices=["grid", "optuna"],
        default=None,
        help=(
            "Metodo ricerca (default: grid = comportamento pre-Fase-2). "
            "Precedenza: CLI > .env SEARCH_METHOD > default grid."
        ),
    )
    parser.add_argument(
        "--n-trials",
        dest="n_trials",
        type=int,
        default=None,
        help=(
            "Budget trial Optuna (solo con --search optuna). "
            "Precedenza: CLI > .env N_TRIALS > default 50."
        ),
    )
    parser.add_argument(
        "--strategy",
        dest="strategy",
        action="append",
        default=None,
        help=(
            "Strategia dal registry (ripetibile o comma-separated, "
            "es. --strategy momentum_drop --strategy mean_reversion). "
            "Default: config.strategies (da .env STRATEGIES)."
        ),
    )
    parser.add_argument(
        "--jobs",
        dest="jobs",
        type=int,
        default=None,
        help=(
            "Job paralleli Optuna (study.optimize n_jobs). "
            "Precedenza: CLI > .env OPTUNA_JOBS > default 1. "
            "F2-B05: usare 4 per il parallelo thread-safe."
        ),
    )
    parser.add_argument(
        "--study-db",
        dest="study_db",
        default=None,
        help=(
            "Path file SQLite Optuna RDB (resumable, load_if_exists). "
            "Precedenza: CLI > .env OPTUNA_STUDY_DB > "
            "default optimization_study_optuna.db."
        ),
    )
    return parser.parse_args(argv)


def _resolve_search(args) -> str:
    cli = (args.search or "").strip().lower() if args.search else ""
    if cli:
        return cli
    env = os.getenv("SEARCH_METHOD", "").strip().lower()
    if env:
        if env not in ("grid", "optuna"):
            print(f"❌ ERRORE configurazione: SEARCH_METHOD={env!r} non valido (grid|optuna)")
            sys.exit(1)
        return env
    return DEFAULT_SEARCH


def _resolve_int_env(cli_val, env_name: str, default: int) -> int:
    if cli_val is not None:
        return int(cli_val)
    raw = os.getenv(env_name, "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            print(f"❌ ERRORE configurazione: {env_name}={raw!r} non intero")
            sys.exit(1)
    return default


def _resolve_study_db(args) -> str:
    if args.study_db:
        return str(args.study_db)
    env = os.getenv("OPTUNA_STUDY_DB", "").strip()
    return env if env else DEFAULT_STUDY_DB


def _resolve_strategies(args, config: Config) -> List[str]:
    if not args.strategy:
        return list(config.strategies)
    out: List[str] = []
    for item in args.strategy:
        for part in str(item).split(","):
            name = part.strip().lower()
            if name:
                out.append(name)
    # Deduplica preservando ordine.
    seen = set()
    uniq = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq if uniq else list(config.strategies)


def run_optuna_engine(
    config: Config,
    symbol: str,
    df: pd.DataFrame,
    strategy: str = "momentum_drop",
    n_trials: int = DEFAULT_N_TRIALS,
    n_jobs: int = DEFAULT_JOBS,
    study_db: str = DEFAULT_STUDY_DB,
) -> str:
    """Esegue la ricerca Optuna TPE sullo path motore standard (F2-B03).

    Crea/riuso study RDB sqlite:///<study_db> con nome
    optuna_<symbol>_<strategy> (load_if_exists=True → resumable),
    ottimizza strategy.score(result), rivaluta il best per CSV.
    """
    from src.searcher import BayesianOptimizer

    cls = STRATEGY_REGISTRY[strategy]
    strat_obj = cls()
    is_mr = type(strat_obj).__name__ == "MeanReversionZScore" or strategy in (
        "mean_reversion",
        "mean_reversion_zscore",
    )
    base_params = {
        "max_hold_seconds": config.max_hold_seconds,
        "initial_capital": config.initial_capital,
        "position_size": config.position_size,
        "fee_rate": config.fee_rate,
        "slippage_rate": config.slippage_rate,
        "direction": "long" if is_mr else config.direction,
    }
    storage = f"sqlite:///{study_db}"
    study_name = f"optuna_{symbol}_{strategy}"
    print(f"\n  🔧 Engine: OPTUNA (TPE)")
    print(f"  📦 Strategia: {strategy}")
    print(f"  🎯 Trial: {n_trials} | jobs: {n_jobs} | db: {study_db} | study: {study_name}")
    opt = BayesianOptimizer(
        strat_obj,
        n_startup_trials=20,
        base_params=base_params,
        symbol=symbol,
        storage=storage,
        study_name=study_name,
        n_jobs=n_jobs,
    )
    out = opt.optimize(df, n_trials=int(n_trials), n_jobs=int(n_jobs))
    best_params = out["best_params"]
    best_value = out["best_value"]
    print(f"  🏆 Best value (score): {best_value:.6f}")
    print(f"  🏆 Best params: {best_params}")
    # Rivaluta il best sullo stesso path per produrre CSV/drawdown coerenti.
    _, best_result = opt._evaluate(best_params, df)
    print_top_results([best_result], top_n=1)
    print(f"  💾 Salvataggio risultati (best)...")
    output_dir = write_results([best_result], config, symbol, strategy=strategy)
    print(f"  💾 Study RDB: {study_db} (resume: riusa --search optuna con stesso db/study)")
    return output_dir


def run_standard_engine(
    config: Config,
    symbol: str,
    df: pd.DataFrame,
    params_list: List[BacktestParams],
    n_combinations: int,
    strategy: str = "momentum_drop",
) -> str:
    """
    Esegue il backtest con il motore standard (Python puro + pandas).
    Logica originale della Fase 1.
    """
    print(f"\n  🔧 Engine: STANDARD")
    print(f"  📦 Strategia: {strategy}")
    print(f"\n  🔄 Esecuzione {n_combinations} combinazioni...")
    results = []

    with Timer(f"Backtest {symbol} [{strategy}]"):
        for idx, params in enumerate(params_list, 1):
            # Progress ogni 10 combinazioni o alla fine
            if idx % 10 == 0 or idx == n_combinations:
                print(
                    f"    [{idx}/{n_combinations}] "
                    f"X={params.x_percent}% Y={params.y_seconds}s Z={params.z_percent}%",
                    end="\r",
                )

            # Esegui simulazione
            trades = run_backtest(df, params, symbol)

            # Calcola metriche
            result = calculate_metrics(trades, params, symbol)
            results.append(result)

        print()  # Newline dopo progress

    # Stampa top risultati
    print_top_results(results, top_n=10)

    # Salva risultati
    print(f"  💾 Salvataggio risultati...")
    output_dir = write_results(results, config, symbol, strategy=strategy)
    return output_dir


def run_standard_engine_mean_reversion(
    config: Config,
    symbol: str,
    df: pd.DataFrame,
    strategy: str = "mean_reversion",
) -> str:
    """
    Esegue il backtest mean-reversion con il motore standard (F1-S04).

    Griglia dimostrativa 2x2 su (ma_period, z_threshold); hold/size/fees/
    slippage/capital da config, direction forzata a long (strategia long-only).
    I risultati usano BacktestParams mappati (x=z_threshold, y=ma_period,
    z=banda di uscita) così metriche e writer restano riusabili.
    """
    from src.strategies.mean_reversion import MeanReversionZScore

    mr = MeanReversionZScore()
    ma_periods = [10, 20]
    z_thresholds = [1.0, 2.0]
    print(f"\n  🔧 Engine: STANDARD")
    print(f"  📦 Strategia: {strategy} (long-only)")
    print(f"\n  🔄 Esecuzione {len(ma_periods) * len(z_thresholds)} combinazioni...")
    results = []

    n_combinations = len(ma_periods) * len(z_thresholds)
    with Timer(f"Backtest {symbol} [{strategy}]"):
        idx = 0
        for ma_period in ma_periods:
            for z_threshold in z_thresholds:
                idx += 1
                if idx % 10 == 0 or idx == n_combinations:
                    print(
                        f"    [{idx}/{n_combinations}] "
                        f"MA={ma_period} Z={z_threshold}",
                        end="\r",
                    )
                mr_params = {
                    "ma_period": ma_period,
                    "z_threshold": z_threshold,
                    "max_hold_seconds": config.max_hold_seconds,
                    "initial_capital": config.initial_capital,
                    "position_size": config.position_size,
                    "fee_rate": config.fee_rate,
                    "slippage_rate": config.slippage_rate,
                }
                trades = mr.run_backtest(df, mr_params, symbol)
                params = BacktestParams(
                    x_percent=z_threshold,
                    y_seconds=ma_period,
                    z_percent=0.1,
                    max_hold_seconds=config.max_hold_seconds,
                    initial_capital=config.initial_capital,
                    position_size=config.position_size,
                    fee_rate=config.fee_rate,
                    slippage_rate=config.slippage_rate,
                    direction="long",
                )
                results.append(calculate_metrics(trades, params, symbol))

        print()  # Newline dopo progress

    # Stampa top risultati
    print_top_results(results, top_n=10)

    # Salva risultati
    print(f"  💾 Salvataggio risultati...")
    output_dir = write_results(results, config, symbol, strategy=strategy)
    return output_dir


def run_fast_engine(config: Config, symbol: str, df: pd.DataFrame) -> str:
    """
    Esegue il backtest con il motore fast (Numba JIT).
    Fase 2 - ottimizzato per griglie grandi.
    """
    from src.fast.fast_runner import run_fast_backtest
    from src.fast.fast_simulator import NumbaMissingError
    try:
        output_dir = run_fast_backtest(df, config, symbol)
    except NumbaMissingError as e:
        print(f"❌ ERRORE: {e}")
        sys.exit(1)
    return output_dir


def run_gpu_engine(config: Config, symbol: str, df: pd.DataFrame) -> str:
    """
    Esegue la pipeline GPU/screening (Fase 3).
    Include: screening massivo, filtri, validazione TRAIN/VALIDATION.
    Fallback automatico su fast CPU se GPU non disponibile.
    """
    from src.gpu.gpu_runner import run_gpu_pipeline
    from src.fast.fast_simulator import NumbaMissingError
    try:
        output_dir = run_gpu_pipeline(df, config, symbol)
    except NumbaMissingError as e:
        print(f"❌ ERRORE: {e}")
        sys.exit(1)
    return output_dir


def main(argv: Optional[List[str]] = None) -> None:
    """Funzione principale del backtester (boundary CLI: unici sys.exit consentiti)."""
    args = parse_args(argv)
    # --- Header ---
    print_header()

    # --- Carica configurazione (boundary CLI: qui è lecito exit) ---
    print("⚙️  Caricamento configurazione...")
    try:
        config = load_config()
    except ConfigError as e:
        print(f"❌ ERRORE configurazione: {e}")
        sys.exit(1)

    # --- Risolvi ricerca/strategy con precedenza CLI > .env > default ---
    search = _resolve_search(args)
    n_trials = _resolve_int_env(args.n_trials, "N_TRIALS", DEFAULT_N_TRIALS)
    n_jobs = _resolve_int_env(args.jobs, "OPTUNA_JOBS", DEFAULT_JOBS)
    study_db = _resolve_study_db(args)
    strategies = _resolve_strategies(args, config)
    if search == "optuna":
        if n_trials <= 0:
            print(f"❌ ERRORE configurazione: --n-trials/N_TRIALS deve essere > 0 ({n_trials})")
            sys.exit(1)
        if n_jobs <= 0:
            print(f"❌ ERRORE configurazione: --jobs/OPTUNA_JOBS deve essere > 0 ({n_jobs})")
            sys.exit(1)

    # --- Genera griglia parametri (usata anche per conteggio) ---
    params_list = generate_parameter_grid(config)
    n_combinations = len(params_list)

    # --- Valida strategie richieste (F1-S04; CLI --strategy riusa config.strategies) ---
    unknown = [s for s in strategies if s not in STRATEGY_REGISTRY]
    if unknown:
        print(f"❌ ERRORE configurazione: strategie sconosciute: {unknown} "
              f"(disponibili: {sorted(STRATEGY_REGISTRY)})")
        sys.exit(1)

    # --- Stampa riepilogo ---
    print_config_summary(
        symbols=config.symbols,
        start_date=config.start_date,
        end_date=config.end_date,
        n_combinations=n_combinations,
        direction=config.direction,
    )
    print(f"  🧩 Strategie: {', '.join(strategies)}")
    print(f"  🏎️  Engine: {config.backtest_engine.upper()}")
    print(f"  🔍 Search: {search}"
          + (f" (n_trials={n_trials}, jobs={n_jobs}, db={study_db})" if search == "optuna" else ""))

    # --- Esegui backtest per ogni simbolo ---
    all_output_dirs = []

    with Timer("Tempo totale") as total_timer:
        for symbol in config.symbols:
            print(f"\n{'='*60}")
            print(f"  📊 Simbolo: {symbol}")
            print(f"{'='*60}")

            # Carica dati OHLC (boundary CLI: qui è lecito exit)
            print(f"\n  📥 Caricamento dati...")
            try:
                df = load_ohlc_data(config, symbol)
            except DataLoadError as e:
                print(f"❌ ERRORE caricamento dati {symbol}: {e}")
                sys.exit(1)
            n_candles = len(df)
            print(f"  📈 Candele caricate: {n_candles:,}")

            # Routing search × engine × strategia (F1-S04 + F2-B03).
            # Grid: comportamento pre-Fase-2 invariato.
            # Optuna: path TPE standard per ogni strategia (ignora
            # backtest_engine fast/gpu: i kernel sono momentum-only e non
            # espongono score; BO usa sempre lo standard path + RDB resumable).
            for strategy in strategies:
                if search == "optuna":
                    output_dir = run_optuna_engine(
                        config, symbol, df, strategy=strategy,
                        n_trials=n_trials, n_jobs=n_jobs, study_db=study_db,
                    )
                elif config.backtest_engine == "gpu":
                    if strategy != "momentum_drop":
                        print(f"  ⚠️  Strategia {strategy} non supportata dal motore GPU "
                              f"(kernel momentum-only): salto.")
                        continue
                    output_dir = run_gpu_engine(config, symbol, df)
                elif config.backtest_engine == "fast":
                    if strategy != "momentum_drop":
                        print(f"  ⚠️  Strategia {strategy} non supportata dal motore FAST "
                              f"(kernel momentum-only): salto.")
                        continue
                    output_dir = run_fast_engine(config, symbol, df)
                elif strategy == "momentum_drop":
                    output_dir = run_standard_engine(
                        config, symbol, df, params_list, n_combinations,
                        strategy=strategy,
                    )
                else:
                    output_dir = run_standard_engine_mean_reversion(
                        config, symbol, df, strategy=strategy,
                    )

                all_output_dirs.append(output_dir)

    # --- Completamento ---
    for output_dir in all_output_dirs:
        print_completion(output_dir, total_timer.elapsed)


if __name__ == "__main__":
    main()