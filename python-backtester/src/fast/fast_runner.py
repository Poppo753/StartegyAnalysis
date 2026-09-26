"""
fast_runner.py - Orchestratore del motore fast (Numba JIT)

Gestisce:
1. Conversione DataFrame pandas -> array numpy
2. Generazione griglia parametri
3. Esecuzione batch di tutte le combinazioni
4. Raccolta metriche
5. Salvataggio risultati (summary + top N trades)
6. Output console
"""

import os
import time
import numpy as np
import pandas as pd
from itertools import product
from typing import List, Tuple

from src.config import Config
from src.fast.fast_simulator import _simulate_single, check_numba_available, NumbaMissingError
from src.fast.fast_metrics import calculate_fast_metrics


# Mapping direction stringa -> intero per numba
DIRECTION_MAP = {
    "signal-only": 0,
    "long": 1,
    "short": 2,
}

# Mapping reason intero -> stringa per output
REASON_MAP = {
    1: "drop-z",
    2: "max-hold",
    3: "end-of-data",
}


def run_fast_backtest(df: pd.DataFrame, config: Config, symbol: str) -> str:
    """
    Esegue il backtest completo in modalità fast per un simbolo.

    Args:
        df: DataFrame con colonne datetime, epoch_seconds, close, high, low
        config: configurazione completa
        symbol: simbolo in esame

    Returns:
        Percorso della cartella di output
    """
    # Verifica numba disponibile (solleva NumbaMissingError, mai sys.exit qui)
    try:
        check_numba_available()
    except NumbaMissingError as e:
        raise NumbaMissingError(
            f"{e} (motore fast richiesto ma numba assente)"
        ) from e

    # --- Conversione in array numpy ---
    epoch_ms = (df["epoch_seconds"].values * 1000).astype(np.int64)  # secondi -> millisecondi
    close = df["close"].values.astype(np.float64)
    high = df["high"].values.astype(np.float64)
    low = df["low"].values.astype(np.float64)

    # Direction come intero
    direction_int = DIRECTION_MAP[config.direction]

    # --- Genera griglia parametri ---
    combinations = list(product(config.x_values, config.y_values, config.z_values))
    n_combinations = len(combinations)

    print(f"\n  ⚡ Engine: FAST (Numba JIT)")
    print(f"  🔢 Combinazioni: {n_combinations}")
    print(f"  📊 Candele: {len(close):,}")

    # --- Warmup numba (prima compilazione) ---
    print(f"  🔥 Warmup JIT...", end="")
    warmup_start = time.time()
    _warmup_numba(epoch_ms, close, high, low, direction_int, config)
    warmup_elapsed = time.time() - warmup_start
    print(f" {warmup_elapsed:.2f}s")

    # --- Esecuzione griglia ---
    print(f"\n  🔄 Esecuzione {n_combinations} combinazioni...")
    all_results = []

    batch_start = time.time()

    for idx, (x, y, z) in enumerate(combinations, 1):
        # Progress
        if idx % 10 == 0 or idx == n_combinations:
            print(
                f"    [{idx}/{n_combinations}] "
                f"X={x}% Y={y}s Z={z}%",
                end="\r",
            )

        # Timer per singola combinazione
        combo_start = time.time()

        # Esegui simulazione numba
        trades_array, n_trades = _simulate_single(
            epoch_ms,
            close,
            high,
            low,
            np.float64(x),
            np.int64(y),
            np.float64(z),
            np.int64(config.max_hold_seconds),
            np.float64(config.position_size),
            np.float64(config.fee_rate),
            np.float64(config.slippage_rate),
            np.int64(direction_int),
        )

        combo_elapsed = time.time() - combo_start

        # Calcola metriche
        metrics = calculate_fast_metrics(
            trades_array,
            n_trades,
            direction_int,
            config.initial_capital,
        )

        # Salva risultato
        all_results.append({
            "x_percent": x,
            "y_seconds": y,
            "z_percent": z,
            "metrics": metrics,
            "trades_array": trades_array.copy() if n_trades > 0 else np.empty((0, 10)),
            "n_trades": n_trades,
            "runtime_seconds": combo_elapsed,
        })

    print()  # Newline dopo progress
    batch_elapsed = time.time() - batch_start
    print(f"  ⏱️  Backtest fast {symbol}: {batch_elapsed:.2f}s")

    # --- Ordina risultati ---
    # Priorità: combinazioni con trade > combinazioni senza trade
    # Poi ordina per PnL decrescente
    if config.direction == "signal-only":
        all_results.sort(
            key=lambda r: (
                r["metrics"]["total_trades"] > 0,  # True (1) > False (0)
                r["metrics"]["total_pnl_percent"],
            ),
            reverse=True,
        )
    else:
        all_results.sort(
            key=lambda r: (
                r["metrics"]["total_trades"] > 0,
                r["metrics"]["total_pnl"],
            ),
            reverse=True,
        )

    # --- Stampa top 10 ---
    _print_fast_top_results(all_results, config.direction)

    # --- Salva output ---
    output_dir = _save_fast_results(
        all_results=all_results,
        config=config,
        symbol=symbol,
        df=df,
        epoch_ms=epoch_ms,
    )

    return output_dir


def _warmup_numba(
    epoch_ms: np.ndarray,
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    direction_int: int,
    config: Config,
):
    """
    Esegue una prima chiamata a _simulate_single per triggerare la compilazione JIT.
    Usa un piccolo subset dei dati.
    """
    # Usa solo le prime 100 candele per il warmup
    if len(close) < 100:
        return
    n_warmup = min(100, len(close))
    _simulate_single(
        epoch_ms[:n_warmup],
        close[:n_warmup],
        high[:n_warmup],
        low[:n_warmup],
        np.float64(config.x_values[0]),
        np.int64(config.y_values[0]),
        np.float64(config.z_values[0]),
        np.int64(config.max_hold_seconds),
        np.float64(config.position_size),
        np.float64(config.fee_rate),
        np.float64(config.slippage_rate),
        np.int64(direction_int),
    )


def _print_fast_top_results(all_results: List[dict], direction: str, top_n: int = 10) -> None:
    """Stampa le top N combinazioni in console."""
    top = all_results[:top_n]

    is_signal_only = (direction == "signal-only")

    print(f"\n  🏆 Top {min(top_n, len(top))} combinazioni (fast):")
    print("  " + "-" * 88)

    if is_signal_only:
        print(f"    {'#':<3} {'X%':<6} {'Y(s)':<6} {'Z%':<6} {'Trades':<8} {'Win%':<7} {'PnL%':<10} {'Avg%':<8} {'PF':<7} {'ms':<6}")
        print("  " + "-" * 88)
        for idx, r in enumerate(top, 1):
            m = r["metrics"]
            print(
                f"    {idx:<3} "
                f"{r['x_percent']:<6.1f} "
                f"{r['y_seconds']:<6} "
                f"{r['z_percent']:<6.1f} "
                f"{m['total_trades']:<8} "
                f"{m['win_rate']:<7.1f} "
                f"{m['total_pnl_percent']:<10.4f} "
                f"{m['average_pnl']:<8.4f} "
                f"{m['profit_factor']:<7.2f} "
                f"{r['runtime_seconds']*1000:<6.1f}"
            )
    else:
        print(f"    {'#':<3} {'X%':<6} {'Y(s)':<6} {'Z%':<6} {'Trades':<8} {'Win%':<7} {'PnL($)':<10} {'MaxDD%':<8} {'PF':<7} {'ms':<6}")
        print("  " + "-" * 88)
        for idx, r in enumerate(top, 1):
            m = r["metrics"]
            print(
                f"    {idx:<3} "
                f"{r['x_percent']:<6.1f} "
                f"{r['y_seconds']:<6} "
                f"{r['z_percent']:<6.1f} "
                f"{m['total_trades']:<8} "
                f"{m['win_rate']:<7.1f} "
                f"{m['total_pnl']:<10.4f} "
                f"{m['max_drawdown']:<8.4f} "
                f"{m['profit_factor']:<7.2f} "
                f"{r['runtime_seconds']*1000:<6.1f}"
            )

    print("  " + "-" * 88)
    print()


def _save_fast_results(
    all_results: List[dict],
    config: Config,
    symbol: str,
    df: pd.DataFrame,
    epoch_ms: np.ndarray,
) -> str:
    """
    Salva summary CSV e trades CSV per le top N combinazioni.

    Output in: backtest-results/{SYMBOL}/fast/
    """
    # Directory di output
    output_dir = os.path.join(config.output_dir, symbol, "fast")
    os.makedirs(output_dir, exist_ok=True)

    # --- Summary CSV ---
    summary_filename = f"summary_{config.start_date}_{config.end_date}.csv"
    summary_path = os.path.join(output_dir, summary_filename)

    summary_rows = []
    for r in all_results:
        m = r["metrics"]
        summary_rows.append({
            "symbol": symbol,
            "engine": "fast",
            "x_percent": r["x_percent"],
            "y_seconds": r["y_seconds"],
            "z_percent": r["z_percent"],
            "total_trades": m["total_trades"],
            "winning_trades": m["winning_trades"],
            "losing_trades": m["losing_trades"],
            "win_rate": round(m["win_rate"], 2),
            "total_pnl": round(m["total_pnl"], 4),
            "total_pnl_percent": round(m["total_pnl_percent"], 4),
            "max_drawdown": round(m["max_drawdown"], 4),
            "average_pnl": round(m["average_pnl"], 4),
            "best_trade": round(m["best_trade"], 4),
            "worst_trade": round(m["worst_trade"], 4),
            "profit_factor": round(m["profit_factor"], 4),
            "runtime_seconds": round(r["runtime_seconds"], 6),
        })

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(summary_path, index=False)
    print(f"  📄 Summary salvato: {summary_path}")

    # --- Trades CSV per top N combinazioni ---
    top_n = min(config.fast_top_n, len(all_results))
    timestamps_dt = df["datetime"].values  # numpy datetime64 array

    for rank, r in enumerate(all_results[:top_n], 1):
        if r["n_trades"] == 0:
            continue

        trades_filename = (
            f"trades_best_{rank:03d}_x{r['x_percent']}_y{r['y_seconds']}_z{r['z_percent']}.csv"
        )
        trades_path = os.path.join(output_dir, trades_filename)

        _save_trades_csv(
            trades_array=r["trades_array"],
            n_trades=r["n_trades"],
            symbol=symbol,
            x_percent=r["x_percent"],
            y_seconds=r["y_seconds"],
            z_percent=r["z_percent"],
            timestamps_dt=timestamps_dt,
            filepath=trades_path,
        )

    print(f"  📄 Trades salvati per top {top_n} combinazioni")

    return output_dir


def _save_trades_csv(
    trades_array: np.ndarray,
    n_trades: int,
    symbol: str,
    x_percent: float,
    y_seconds: int,
    z_percent: float,
    timestamps_dt: np.ndarray,
    filepath: str,
) -> None:
    """
    Converte l'array numpy dei trade in un CSV leggibile.

    Mappa gli indici entry/exit ai datetime originali.
    Converte i codici reason in stringhe.
    """
    rows = []
    for t in range(n_trades):
        entry_idx = int(trades_array[t, 0])
        exit_idx = int(trades_array[t, 1])

        # Converti indici in datetime
        entry_time = pd.Timestamp(timestamps_dt[entry_idx])
        exit_time = pd.Timestamp(timestamps_dt[exit_idx])

        # Converti reason code
        reason_code = int(trades_array[t, 9])
        reason_str = REASON_MAP.get(reason_code, f"unknown-{reason_code}")

        rows.append({
            "symbol": symbol,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "entry_price": trades_array[t, 2],
            "exit_price": trades_array[t, 3],
            "max_price_during_trade": trades_array[t, 4],
            "min_price_during_trade": trades_array[t, 5],
            "pnl": round(trades_array[t, 6], 6),
            "pnl_percent": round(trades_array[t, 7], 4),
            "fees": round(trades_array[t, 8], 6),
            "reason": reason_str,
            "x_percent": x_percent,
            "y_seconds": y_seconds,
            "z_percent": z_percent,
        })

    trades_df = pd.DataFrame(rows)
    trades_df.to_csv(filepath, index=False)