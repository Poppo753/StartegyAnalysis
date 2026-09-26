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
from src.utils import (
    Timer,
    print_header,
    print_config_summary,
    print_top_results,
    print_completion,
)

import pandas as pd
from typing import List


def run_standard_engine(
    config: Config,
    symbol: str,
    df: pd.DataFrame,
    params_list: List[BacktestParams],
    n_combinations: int,
) -> str:
    """
    Esegue il backtest con il motore standard (Python puro + pandas).
    Logica originale della Fase 1.
    """
    print(f"\n  🔧 Engine: STANDARD")
    print(f"\n  🔄 Esecuzione {n_combinations} combinazioni...")
    results = []

    with Timer(f"Backtest {symbol}"):
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
    output_dir = write_results(results, config, symbol)
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


def main() -> None:
    """Funzione principale del backtester (boundary CLI: unici sys.exit consentiti)."""
    # --- Header ---
    print_header()

    # --- Carica configurazione (boundary CLI: qui è lecito exit) ---
    print("⚙️  Caricamento configurazione...")
    try:
        config = load_config()
    except ConfigError as e:
        print(f"❌ ERRORE configurazione: {e}")
        sys.exit(1)

    # --- Genera griglia parametri (usata anche per conteggio) ---
    params_list = generate_parameter_grid(config)
    n_combinations = len(params_list)

    # --- Stampa riepilogo ---
    print_config_summary(
        symbols=config.symbols,
        start_date=config.start_date,
        end_date=config.end_date,
        n_combinations=n_combinations,
        direction=config.direction,
    )
    print(f"  🏎️  Engine: {config.backtest_engine.upper()}")

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

            # Routing engine
            if config.backtest_engine == "gpu":
                output_dir = run_gpu_engine(config, symbol, df)
            elif config.backtest_engine == "fast":
                output_dir = run_fast_engine(config, symbol, df)
            else:
                output_dir = run_standard_engine(
                    config, symbol, df, params_list, n_combinations
                )

            all_output_dirs.append(output_dir)

    # --- Completamento ---
    for output_dir in all_output_dirs:
        print_completion(output_dir, total_timer.elapsed)


if __name__ == "__main__":
    main()