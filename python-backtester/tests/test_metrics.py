"""Test per le metriche."""
import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.metrics import (
    calculate_metrics,
    calmar_ratio,
    expectancy,
    sortino_ratio,
)
from src.strategy import BacktestParams, Trade
from datetime import datetime


SQRT_252 = float(np.sqrt(252.0))  # 15.874507866387544


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


def _long_params():
    return BacktestParams(
        x_percent=0.5, y_seconds=30, z_percent=0.2,
        max_hold_seconds=300, initial_capital=1000,
        position_size=100, fee_rate=0.001, slippage_rate=0.0005,
        direction="long",
    )


class TestPureFunctions:
    def test_sortino_mixed_known_downside(self):
        # mean=-0.25, downside=[-1,-3] std-popolazione=1.0 → -0.25*sqrt(252)
        got = sortino_ratio(np.array([2.0, 1.0, -1.0, -3.0]), 0.0)
        assert got == pytest.approx(-0.25 * SQRT_252)

    def test_sortino_empty(self):
        assert sortino_ratio(np.array([])) == 0.0

    def test_calmar(self):
        assert calmar_ratio(5.0, 2.0) == pytest.approx(2.5)
        assert calmar_ratio(5.0, 0.0) == 0.0
        assert calmar_ratio(5.0, -1.0) == 0.0

    def test_expectancy(self):
        assert expectancy(0.5, 1.5, 2.0) == pytest.approx(-0.25)
        assert expectancy(1.0, 2.0, 0.0) == pytest.approx(2.0)
        assert expectancy(0.0, 0.0, 1.0) == pytest.approx(-1.0)


class TestV3MetricsWiring:
    """3 casi hand-verified (direction long → serie pnl in USDT)."""

    def test_all_win(self):
        trades = [make_trade(pnl=1.0, pnl_percent=1.0) for _ in range(5)]
        result = calculate_metrics(trades, _long_params(), "TEST")
        # downside vuoto → downside_std=1e-9 (sketch v3): 1.0/1e-9*sqrt(252)
        assert result.sortino_ratio == pytest.approx(1.0 / 1e-9 * SQRT_252)
        assert result.expectancy == pytest.approx(1.0)  # 1.0*1.0 - 0
        assert result.max_drawdown == pytest.approx(0.0)
        assert result.calmar_ratio == pytest.approx(0.0)  # dd=0 → 0

    def test_all_loss(self):
        trades = [make_trade(pnl=-1.0, pnl_percent=-1.0) for _ in range(5)]
        result = calculate_metrics(trades, _long_params(), "TEST")
        # downside costante [-1]*5 → std=0 → 0.0 per convenzione
        assert result.sortino_ratio == pytest.approx(0.0)
        assert result.expectancy == pytest.approx(-1.0)  # 0 - 1.0*1.0
        # Include il capitale iniziale 1000: 1000 -> 995 = 0.5%.
        assert result.max_drawdown == pytest.approx(0.5)
        assert result.calmar_ratio == pytest.approx(-0.5 / 0.5)

    def test_mixed_known_downside(self):
        trades = [make_trade(pnl=v, pnl_percent=v)
                  for v in (2.0, 1.0, -1.0, -3.0)]
        result = calculate_metrics(trades, _long_params(), "TEST")
        assert result.sortino_ratio == pytest.approx(-0.25 * SQRT_252)
        assert result.expectancy == pytest.approx(-0.25)  # 0.5*1.5-0.5*2.0
        # equity 1002,1003,1002,999 → dd max 4 USDT = 0.4%; totale -1 = -0.1%
        assert result.max_drawdown == pytest.approx(0.4)
        assert result.calmar_ratio == pytest.approx(-0.1 / 0.4)

    def test_signal_only_uses_pnl_percent(self):
        # pnl USDT tutti 0 ma pct mossi → le metriche devono usare i pct.
        trades = [make_trade(pnl=0.0, pnl_percent=v)
                  for v in (4.0, 2.0, -1.0, -3.0)]
        params = _long_params()
        params.direction = "signal-only"
        result = calculate_metrics(trades, params, "TEST")
        assert result.sortino_ratio == pytest.approx(0.5 * SQRT_252)
        assert result.expectancy == pytest.approx(0.5)  # 0.5*3.0-0.5*2.0

    def test_signal_only_drawdown_uses_percent_moves_and_initial_capital(self):
        params = _long_params()
        params.direction = "signal-only"
        trades = [make_trade(pnl=0.0, pnl_percent=-2.0)]
        result = calculate_metrics(trades, params, "TEST")
        assert result.max_drawdown == pytest.approx(2.0)
