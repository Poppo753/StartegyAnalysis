"""Test per le metriche."""
import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.metrics import calculate_metrics
from src.strategy import BacktestParams, Trade
from datetime import datetime


def make_trade(pnl=0.0, pnl_percent=0.0, reason="end-of-data"):
    return Trade(
        symbol="TEST", entry_time=datetime.now(), exit_time=datetime.now(),
        entry_price=100.0, exit_price=101.0, max_price_during_trade=102.0,
        min_price_during_trade=99.0, pnl=pnl, pnl_percent=pnl_percent,
        fees=0.2, reason=reason, x_percent=0.5, y_seconds=30, z_percent=0.2
    )


class TestCalculateMetrics:
    def test_empty_trades(self):
        result = calculate_metrics([], BacktestParams(
            x_percent=0.5, y_seconds=30, z_percent=0.2,
            max_hold_seconds=300, initial_capital=1000,
            position_size=100, fee_rate=0.001, slippage_rate=0.0005,
            direction="signal-only"
        ), "TEST")
        assert result.total_trades == 0
        assert result.win_rate == 0.0

    def test_all_winning(self):
        trades = [make_trade(pnl=1.0, pnl_percent=1.0) for _ in range(5)]
        result = calculate_metrics(trades, BacktestParams(
            x_percent=0.5, y_seconds=30, z_percent=0.2,
            max_hold_seconds=300, initial_capital=1000,
            position_size=100, fee_rate=0.001, slippage_rate=0.0005,
            direction="long"
        ), "TEST")
        assert result.win_rate == 100.0
        assert result.total_pnl > 0

    def test_all_losing(self):
        trades = [make_trade(pnl=-1.0, pnl_percent=-1.0) for _ in range(5)]
        result = calculate_metrics(trades, BacktestParams(
            x_percent=0.5, y_seconds=30, z_percent=0.2,
            max_hold_seconds=300, initial_capital=1000,
            position_size=100, fee_rate=0.001, slippage_rate=0.0005,
            direction="long"
        ), "TEST")
        assert result.win_rate == 0.0
