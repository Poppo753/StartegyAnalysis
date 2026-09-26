"""F0-07 regression: _warmup_numba guard (len(close) < 100 -> return).

- datasets of 10/50/99/100/101 rows must not crash
- results identical with/without warmup (warmup is JIT-only, no side effects)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from src.config import Config
from src.fast.fast_runner import _warmup_numba
from src.fast.fast_simulator import NUMBA_AVAILABLE, _simulate_single

pytestmark = pytest.mark.skipif(not NUMBA_AVAILABLE, reason="numba non installato")


def _toy_arrays(n: int):
    epoch_ms = (np.arange(n, dtype=np.int64) * 1000) + 1_700_000_000_000
    close = 100.0 + np.linspace(0, 8, n) + np.sin(np.arange(n) * 0.3) * 0.2
    high = close + 0.15
    low = close - 0.15
    return (
        epoch_ms,
        close.astype(np.float64),
        high.astype(np.float64),
        low.astype(np.float64),
    )


def _test_config():
    return Config(
        x_values=[0.5],
        y_values=[10],
        z_values=[5.0],
        max_hold_seconds=3600,
        position_size=100.0,
        fee_rate=0.001,
        slippage_rate=0.0005,
    )


@pytest.mark.parametrize("n", [10, 50, 99, 100, 101])
def test_warmup_does_not_crash(n):
    epoch_ms, close, high, low = _toy_arrays(n)
    config = _test_config()
    # Must return None and never raise, on both sides of the <100 guard.
    assert _warmup_numba(epoch_ms, close, high, low, 1, config) is None


@pytest.mark.parametrize("n", [10, 50, 99, 100, 101])
def test_results_identical_with_without_warmup(n):
    epoch_ms, close, high, low = _toy_arrays(n)
    config = _test_config()
    kwargs = dict(
        x_percent=np.float64(config.x_values[0]),
        y_seconds=np.int64(config.y_values[0]),
        z_percent=np.float64(config.z_values[0]),
        max_hold_seconds=np.int64(config.max_hold_seconds),
        position_size=np.float64(config.position_size),
        fee_rate=np.float64(config.fee_rate),
        slippage_rate=np.float64(config.slippage_rate),
        direction=np.int64(1),
    )
    before_trades, before_n = _simulate_single(epoch_ms, close, high, low, **kwargs)
    _warmup_numba(epoch_ms, close, high, low, 1, config)
    after_trades, after_n = _simulate_single(epoch_ms, close, high, low, **kwargs)
    assert before_n == after_n
    np.testing.assert_array_equal(np.asarray(before_trades), np.asarray(after_trades))
