"""Sharpe ratio F3-V01 (file separato: test_metrics.py non toccabile per scope).

Valori verificati a mano: Sharpe = mean/std_pop * sqrt(252).
Serie [2,1,-1,-3]: mean=-0.25, std_pop=sqrt(3.6875)≈1.920286, shelve.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest
from datetime import datetime

from src.metrics import sharpe_ratio, calculate_metrics
from src.strategy import BacktestParams, Trade

SQRT_252 = float(np.sqrt(252.0))


def make_trade(pnl=0.0, pnl_percent=0.0):
    return Trade(
        symbol="TEST", entry_time=datetime.now(), exit_time=datetime.now(),
        entry_price=100.0, exit_price=101.0, max_price_during_trade=102.0,
        min_price_during_trade=99.0, pnl=pnl, pnl_percent=pnl_percent,
        fees=0.2, reason="end-of-data", x_percent=0.5, y_seconds=30, z_percent=0.2,
    )


def _long_params():
    return BacktestParams(
        x_percent=0.5, y_seconds=30, z_percent=0.2,
        max_hold_seconds=300, initial_capital=1000,
        position_size=100, fee_rate=0.001, slippage_rate=0.0005,
        direction="long",
    )


class TestSharpePure:
    def test_known_series(self):
        # mean=-0.25, std_pop=sqrt(3.6875) → -0.25/sqrt(3.6875)*sqrt(252)
        v = np.array([2.0, 1.0, -1.0, -3.0])
        expected = -0.25 / float(np.std(v)) * SQRT_252
        assert sharpe_ratio(v, 0.0) == pytest.approx(expected)
        assert sharpe_ratio(v, 0.0) == pytest.approx(-2.0666848914815166, rel=1e-9)

    def test_risk_free(self):
        v = np.array([3.0, 2.0, 0.0, -2.0])
        excess = v - 1.0
        expected = float(np.mean(excess)) / float(np.std(excess)) * SQRT_252
        assert sharpe_ratio(v, 1.0) == pytest.approx(expected)

    def test_empty(self):
        assert sharpe_ratio(np.array([])) == 0.0

    def test_constant_series(self):
        assert sharpe_ratio(np.array([1.0, 1.0, 1.0])) == 0.0

    def test_all_zero(self):
        assert sharpe_ratio(np.array([0.0, 0.0])) == 0.0


class TestSharpeWiring:
    def test_wired_long_uses_pnl(self):
        trades = [make_trade(pnl=v, pnl_percent=999.0) for v in (2.0, 1.0, -1.0, -3.0)]
        result = calculate_metrics(trades, _long_params(), "TEST")
        assert result.sharpe_ratio == pytest.approx(-2.0666848914815166, rel=1e-9)

    def test_wired_signal_only_uses_pnl_percent(self):
        trades = [make_trade(pnl=999.0, pnl_percent=v) for v in (2.0, 1.0, -1.0, -3.0)]
        params = _long_params()
        params.direction = "signal-only"
        result = calculate_metrics(trades, params, "TEST")
        assert result.sharpe_ratio == pytest.approx(-2.0666848914815166, rel=1e-9)
        # E la convenzione deve coincidere con sortino: pnl USDT ignorato.
        trades2 = [make_trade(pnl=0.0, pnl_percent=v) for v in (2.0, 1.0, -1.0, -3.0)]
        result2 = calculate_metrics(trades2, params, "TEST")
        assert result.sharpe_ratio == pytest.approx(result2.sharpe_ratio)

    def test_empty_trades_zero(self):
        result = calculate_metrics([], _long_params(), "TEST")
        assert result.sharpe_ratio == 0.0
