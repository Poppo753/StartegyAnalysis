"""Test per il modulo strategy del backtester."""
import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategy import BacktestParams, Trade, BacktestResult


class TestBacktestParams:
    def test_create_params(self):
        params = BacktestParams(
            x_percent=0.5, y_seconds=30, z_percent=0.2,
            max_hold_seconds=300, initial_capital=1000,
            position_size=100, fee_rate=0.001, slippage_rate=0.0005,
            direction="signal-only"
        )
        assert params.x_percent == 0.5
        assert params.y_seconds == 30
        assert params.z_percent == 0.2

    def test_signal_only_direction(self):
        params = BacktestParams(
            x_percent=0.5, y_seconds=30, z_percent=0.2,
            max_hold_seconds=300, initial_capital=1000,
            position_size=100, fee_rate=0.001, slippage_rate=0.0005,
            direction="signal-only"
        )
        assert params.direction == "signal-only"


class TestTrade:
    def test_create_trade(self):
        trade = Trade(
            symbol="BTCUSDT",
            entry_time="2024-01-01T00:00:00",
            exit_time="2024-01-01T00:00:30",
            entry_price=100.0, exit_price=101.0,
            max_price_during_trade=102.0, min_price_during_trade=99.0,
            pnl=1.0, pnl_percent=1.0, fees=0.2,
            reason="drop-z", x_percent=0.5, y_seconds=30, z_percent=0.2
        )
        assert trade.pnl == 1.0
        assert trade.reason == "drop-z"


class TestBacktestResult:
    def test_empty_result(self):
        result = BacktestResult(symbol="BTCUSDT", params=BacktestParams(
            x_percent=0.5, y_seconds=30, z_percent=0.2,
            max_hold_seconds=300, initial_capital=1000,
            position_size=100, fee_rate=0.001, slippage_rate=0.0005,
            direction="signal-only"
        ))
        assert result.total_trades == 0
        assert result.trades == []
