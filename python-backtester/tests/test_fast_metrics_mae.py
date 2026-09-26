"""Test enterprise per calculate_fast_metrics: avg_mae/avg_mfe direction-aware."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from src.fast.fast_metrics import calculate_fast_metrics


def make_trades_array():
    """2 trade asimmetrici: entry=100, max/min noti."""
    trades = np.zeros((2, 10), dtype=np.float64)
    # Trade 1: entry 100, max 105 (+5%), min 90 (-10% long)
    trades[0] = [0, 10, 100.0, 102.0, 105.0, 90.0, 5.0, 5.0, 0.0, 0]
    # Trade 2: entry 100, max 120 (+20%), min 98 (-2% long)
    trades[1] = [11, 20, 100.0, 110.0, 120.0, 98.0, 8.0, 8.0, 0.0, 1]
    return trades


def test_long_mae_mfe():
    trades = make_trades_array()
    m = calculate_fast_metrics(trades, 2, direction=1, initial_capital=10000.0)
    # long: MAE=(entry-min)/entry -> [10.0, 2.0]; MFE=(max-entry)/entry -> [5.0, 20.0]
    assert m["avg_mae"] == pytest.approx(6.0)
    assert m["max_mae"] == pytest.approx(10.0)
    assert m["avg_mfe"] == pytest.approx(12.5)
    assert m["max_mfe"] == pytest.approx(20.0)


def test_short_mae_mfe_swapped():
    trades = make_trades_array()
    m = calculate_fast_metrics(trades, 2, direction=2, initial_capital=10000.0)
    # short: MAE=(max-entry)/entry -> [5.0, 20.0]; MFE=(entry-min)/entry -> [10.0, 2.0]
    assert m["avg_mae"] == pytest.approx(12.5)
    assert m["max_mae"] == pytest.approx(20.0)
    assert m["avg_mfe"] == pytest.approx(6.0)
    assert m["max_mfe"] == pytest.approx(10.0)


def test_direction_aware_symmetry():
    trades = make_trades_array()
    m_long = calculate_fast_metrics(trades, 2, direction=1, initial_capital=10000.0)
    m_short = calculate_fast_metrics(trades, 2, direction=2, initial_capital=10000.0)
    assert m_long["avg_mae"] == pytest.approx(m_short["avg_mfe"])
    assert m_long["avg_mfe"] == pytest.approx(m_short["avg_mae"])


def test_drawdown_includes_first_loss_and_signal_only_move():
    trades = np.zeros((1, 10), dtype=np.float64)
    trades[0, 2] = 100.0
    trades[0, 4] = 100.0
    trades[0, 5] = 100.0
    trades[0, 6] = -10.0
    trades[0, 7] = -2.0
    assert calculate_fast_metrics(trades, 1, direction=1, initial_capital=1000.0)["max_drawdown"] == pytest.approx(1.0)
    assert calculate_fast_metrics(trades, 1, direction=0, initial_capital=1000.0)["max_drawdown"] == pytest.approx(2.0)
