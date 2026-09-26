"""
simulator.py - Motore di simulazione del backtest (F1-S02: wrapper retrocompatibile).

La logica di entry/exit/PnL vive ora in src/strategies/momentum_drop.py
(MomentumDropStrategy). Questo modulo delega a quella implementazione così il
vecchio `run_backtest` resta identico per costruzione (stesso codice, stessi
risultati entro 1e-9).
"""

import pandas as pd
from typing import List
from src.strategy import BacktestParams, Trade
from src.strategies.momentum_drop import (
    MomentumDropStrategy,
    _calculate_pnl,
    _execute_trade,
    _find_candle_at_or_before,
    _find_exit_index_by_time,
    run_backtest as _strategy_run_backtest,
)

__all__ = [
    "run_backtest",
    "MomentumDropStrategy",
    "_find_candle_at_or_before",
    "_execute_trade",
    "_calculate_pnl",
    "_find_exit_index_by_time",
]


def run_backtest(df: pd.DataFrame, params: BacktestParams, symbol: str) -> List[Trade]:
    """
    Esegue il backtest su un DataFrame di candele OHLC 1s.

    Delega a MomentumDropStrategy (logica estratta invariata da questo file).

    Args:
        df: DataFrame con colonne timestamp, open, high, low, close, volume, tradeCount, datetime, epoch_seconds
        params: parametri del backtest
        symbol: simbolo in esame

    Returns:
        Lista di Trade eseguiti
    """
    return _strategy_run_backtest(df, params, symbol)
