"""Test per il simulatore."""
import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from src.strategy import BacktestParams
from src.simulator import run_backtest


def create_test_dataframe(n_candles=100):
    dates = pd.date_range('2024-01-01', periods=n_candles, freq='s', tz='UTC')
    df = pd.DataFrame({
        'timestamp': dates.strftime('%Y-%m-%dT%H:%M:%S'),
        'open': np.linspace(100, 110, n_candles),
        'high': np.linspace(101, 111, n_candles),
        'low': np.linspace(99, 109, n_candles),
        'close': np.linspace(100, 110, n_candles),
        'volume': np.ones(n_candles),
        'tradeCount': np.ones(n_candles, dtype=int),
        'datetime': dates,
        'epoch_seconds': np.arange(n_candles, dtype=float),
    })
    return df


class TestRunBacktest:
    def test_no_signals_with_low_threshold(self):
        df = create_test_dataframe(10)
        params = BacktestParams(
            x_percent=999, y_seconds=5, z_percent=0.1,
            max_hold_seconds=300, initial_capital=1000,
            position_size=100, fee_rate=0.001, slippage_rate=0.0005,
            direction="signal-only"
        )
        trades = run_backtest(df, params, "TESTUSDT")
        assert trades == []

    def test_returns_list(self):
        df = create_test_dataframe(100)
        params = BacktestParams(
            x_percent=0.001, y_seconds=5, z_percent=0.1,
            max_hold_seconds=300, initial_capital=1000,
            position_size=100, fee_rate=0.001, slippage_rate=0.0005,
            direction="signal-only"
        )
        trades = run_backtest(df, params, "TESTUSDT")
        assert isinstance(trades, list)
