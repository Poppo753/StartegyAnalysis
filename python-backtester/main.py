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
from typing import List


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

    # --- Valida strategie richieste (F1-S04) ---
    unknown = [s for s in config.strategies if s not in STRATEGY_REGISTRY]
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
    print(f"  🧩 Strategie: {', '.join(config.strategies)}")
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

            # Routing engine × strategia (F1-S04).
            # Motori fast/gpu: kernel hardcoded su momentum_drop → le altre
            # strategie sono supportate solo con il motore standard.
            for strategy in config.strategies:
                if config.backtest_engine == "gpu":
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