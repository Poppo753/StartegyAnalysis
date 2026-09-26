"""
metrics.py - Calcolo delle metriche di performance del backtest

Calcola:
- Win rate
- Total PnL
- Max drawdown (su equity curve)
- Profit factor
- Best/worst trade
- Media PnL
"""

import numpy as np
from typing import List
from src.strategy import BacktestParams, Trade, BacktestResult


def calculate_metrics(trades: List[Trade], params: BacktestParams, symbol: str) -> BacktestResult:
    """
    Calcola tutte le metriche di performance da una lista di trade.

    Args:
        trades: lista dei trade eseguiti
        params: parametri del backtest
        symbol: simbolo testato

    Returns:
        BacktestResult con tutte le metriche calcolate
    """
    result = BacktestResult(
        symbol=symbol,
        params=params,
        trades=trades,
    )

    total_trades = len(trades)
    result.total_trades = total_trades

    # Se non ci sono trade, restituisci risultato vuoto
    if total_trades == 0:
        return result

    # Estrai PnL di ogni trade
    pnls = np.array([t.pnl for t in trades])
    pnl_percents = np.array([t.pnl_percent for t in trades])

    # --- Winning/Losing trades ---
    if params.direction == "signal-only":
        # In signal-only, usa pnl_percent per determinare win/loss
        result.winning_trades = int(np.sum(pnl_percents > 0))
        result.losing_trades = int(np.sum(pnl_percents <= 0))
    else:
        result.winning_trades = int(np.sum(pnls > 0))
        result.losing_trades = int(np.sum(pnls <= 0))

    # --- Win rate ---
    result.win_rate = result.winning_trades / total_trades * 100.0 if total_trades > 0 else 0.0

    # --- Total PnL ---
    result.total_pnl = float(np.sum(pnls))
    result.total_pnl_percent = float(np.sum(pnl_percents))

    # --- Average PnL ---
    if params.direction == "signal-only":
        result.average_pnl = float(np.mean(pnl_percents))
    else:
        result.average_pnl = float(np.mean(pnls))

    # --- Best/Worst trade ---
    if params.direction == "signal-only":
        result.best_trade = float(np.max(pnl_percents))
        result.worst_trade = float(np.min(pnl_percents))
    else:
        result.best_trade = float(np.max(pnls))
        result.worst_trade = float(np.min(pnls))

    # --- Max Drawdown ---
    result.max_drawdown = _calculate_max_drawdown(pnls, params)

    # --- Profit Factor ---
    result.profit_factor = _calculate_profit_factor(pnls, pnl_percents, params)

    result.avg_mae = float(np.mean([t.mae_pct for t in trades])) if trades else 0.0
    result.avg_mfe = float(np.mean([t.mfe_pct for t in trades])) if trades else 0.0

    return result


def _calculate_max_drawdown(pnls: np.ndarray, params: BacktestParams) -> float:
    """
    Calcola il max drawdown sull'equity curve.

    Per direction != signal-only: equity curve basata su PnL cumulativo.
    Per signal-only: basata su pnl_percent cumulativo (come proxy).

    Args:
        pnls: array di PnL per trade
        params: parametri del backtest

    Returns:
        Max drawdown come valore positivo (percentuale o USDT)
    """
    if len(pnls) == 0:
        return 0.0

    # Costruisci equity curve
    if params.direction == "signal-only":
        # Per signal-only usiamo i pnl_percent come proxy
        equity = params.initial_capital + np.cumsum(pnls)
    else:
        equity = params.initial_capital + np.cumsum(pnls)

    # Calcola running maximum
    running_max = np.maximum.accumulate(equity)

    # Drawdown ad ogni punto
    drawdowns = running_max - equity

    # Max drawdown
    max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

    # Converti in percentuale rispetto al capitale iniziale
    if params.initial_capital > 0:
        max_dd_percent = max_dd / params.initial_capital * 100.0
    else:
        max_dd_percent = 0.0

    return max_dd_percent


def _calculate_profit_factor(
    pnls: np.ndarray,
    pnl_percents: np.ndarray,
    params: BacktestParams,
) -> float:
    """
    Calcola il profit factor = somma profitti / |somma perdite|.

    Args:
        pnls: array di PnL per trade
        pnl_percents: array di PnL percentuali
        params: parametri del backtest

    Returns:
        Profit factor (0 se non ci sono perdite)
    """
    if params.direction == "signal-only":
        values = pnl_percents
    else:
        values = pnls

    gross_profit = float(np.sum(values[values > 0]))
    gross_loss = float(np.abs(np.sum(values[values < 0])))

    if gross_loss == 0:
        # Nessuna perdita: profit factor infinito (usiamo 999.99 come cap)
        return 999.99 if gross_profit > 0 else 0.0

    return gross_profit / gross_loss