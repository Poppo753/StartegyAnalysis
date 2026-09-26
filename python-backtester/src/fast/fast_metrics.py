"""
fast_metrics.py - Calcolo metriche su array numpy (senza oggetti Python)

Riceve l'array dei trade dal simulatore numba e calcola tutte le metriche.
Opera interamente su numpy per mantenere la velocità.

Input: trades array float64[:, 10] con colonne:
    [0] entry_idx
    [1] exit_idx
    [2] entry_price
    [3] exit_price
    [4] max_price_during_trade
    [5] min_price_during_trade
    [6] pnl
    [7] pnl_percent
    [8] fees
    [9] reason

Output: dizionario con metriche aggregate.
"""

import numpy as np


def calculate_fast_metrics(
    trades_array: np.ndarray,
    n_trades: int,
    direction: int,
    initial_capital: float,
) -> dict[str, object]:
    """
    Calcola tutte le metriche da un array numpy di trade.

    Args:
        trades_array: array float64[:, 10] con i trade
        n_trades: numero effettivo di trade
        direction: 0=signal-only, 1=long, 2=short
        initial_capital: capitale iniziale per calcolo drawdown

    Returns:
        Dict con tutte le metriche calcolate
    """
    metrics = {
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "win_rate": 0.0,
        "total_pnl": 0.0,
        "total_pnl_percent": 0.0,
        "max_drawdown": 0.0,
        "average_pnl": 0.0,
        "best_trade": 0.0,
        "worst_trade": 0.0,
        "profit_factor": 0.0,
        "avg_mae": 0.0,
        "max_mae": 0.0,
        "avg_mfe": 0.0,
        "max_mfe": 0.0,
    }

    if n_trades == 0:
        return metrics

    metrics["total_trades"] = n_trades

    # Estrai colonne rilevanti
    pnls = trades_array[:n_trades, 6]
    pnl_percents = trades_array[:n_trades, 7]

    # --- Winning/Losing ---
    if direction == 0:  # signal-only
        metrics["winning_trades"] = int(np.sum(pnl_percents > 0))
        metrics["losing_trades"] = int(np.sum(pnl_percents <= 0))
    else:
        metrics["winning_trades"] = int(np.sum(pnls > 0))
        metrics["losing_trades"] = int(np.sum(pnls <= 0))

    # --- Win rate ---
    metrics["win_rate"] = metrics["winning_trades"] / n_trades * 100.0

    # --- Total PnL ---
    metrics["total_pnl"] = float(np.sum(pnls))
    metrics["total_pnl_percent"] = float(np.sum(pnl_percents))

    # --- Average PnL ---
    if direction == 0:  # signal-only
        metrics["average_pnl"] = float(np.mean(pnl_percents))
    else:
        metrics["average_pnl"] = float(np.mean(pnls))

    # --- Best/Worst trade ---
    if direction == 0:  # signal-only
        metrics["best_trade"] = float(np.max(pnl_percents))
        metrics["worst_trade"] = float(np.min(pnl_percents))
    else:
        metrics["best_trade"] = float(np.max(pnls))
        metrics["worst_trade"] = float(np.min(pnls))

    # --- Max Drawdown ---
    metrics["max_drawdown"] = _max_drawdown(
        pnl_percents if direction == 0 else pnls, initial_capital, direction == 0
    )

    # --- Profit Factor ---
    metrics["profit_factor"] = _profit_factor(pnls, pnl_percents, direction)

    # --- MAE / MFE (direction-aware, clipped a >= 0) ---
    # Colonne trades_array: [2]=entry, [4]=max_during, [5]=min_during
    entry_prices = trades_array[:n_trades, 2]
    max_prices = trades_array[:n_trades, 4]
    min_prices = trades_array[:n_trades, 5]
    with np.errstate(divide="ignore", invalid="ignore"):
        valid = entry_prices > 0
        if direction == 2:  # short: avverso=salita, favorevole=discesa
            mae = np.where(valid, (max_prices - entry_prices) / np.where(valid, entry_prices, 1.0) * 100.0, 0.0)
            mfe = np.where(valid, (entry_prices - min_prices) / np.where(valid, entry_prices, 1.0) * 100.0, 0.0)
        else:  # long / signal-only: avverso=discesa, favorevole=salita
            mae = np.where(valid, (entry_prices - min_prices) / np.where(valid, entry_prices, 1.0) * 100.0, 0.0)
            mfe = np.where(valid, (max_prices - entry_prices) / np.where(valid, entry_prices, 1.0) * 100.0, 0.0)
    mae = np.clip(mae, 0.0, None)
    mfe = np.clip(mfe, 0.0, None)
    metrics["avg_mae"] = round(float(np.mean(mae)), 4)
    metrics["max_mae"] = round(float(np.max(mae)), 4)
    metrics["avg_mfe"] = round(float(np.mean(mfe)), 4)
    metrics["max_mfe"] = round(float(np.max(mfe)), 4)

    return metrics


def _max_drawdown(pnls: np.ndarray, initial_capital: float, signal_only: bool = False) -> float:
    """
    Calcola max drawdown sulla equity curve (PnL cumulativo).

    Returns:
        Max drawdown in percentuale rispetto al capitale iniziale.
    """
    if len(pnls) == 0:
        return 0.0

    baseline = 0.0 if signal_only else initial_capital
    equity = baseline + np.cumsum(pnls)
    running_max = np.maximum.accumulate(np.concatenate(([baseline], equity)))[1:]
    drawdowns = running_max - equity

    max_dd = float(np.max(drawdowns))

    if signal_only:
        return max_dd
    if initial_capital > 0:
        return max_dd / initial_capital * 100.0
    return 0.0


def _profit_factor(pnls: np.ndarray, pnl_percents: np.ndarray, direction: int) -> float:
    """
    Calcola profit factor = somma profitti / |somma perdite|.

    Returns:
        Profit factor (capped a 999.99 se nessuna perdita).
    """
    if direction == 0:  # signal-only
        values = pnl_percents
    else:
        values = pnls

    gross_profit = float(np.sum(values[values > 0]))
    gross_loss = float(np.abs(np.sum(values[values < 0])))

    if gross_loss == 0:
        return 999.99 if gross_profit > 0 else 0.0

    return gross_profit / gross_loss
