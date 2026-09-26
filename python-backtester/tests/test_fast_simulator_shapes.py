"""Regression test per bug audit: width array fast_simulator + NumbaMissingError."""
import numpy as np
import pytest

from src.fast.fast_simulator import (
    NUMBA_AVAILABLE,
    NumbaMissingError,
    _simulate_single,
    _simulate_single_dynamic_y,
)

pytestmark = pytest.mark.skipif(not NUMBA_AVAILABLE, reason="numba non installato")


def _toy_data(n: int = 600):
    epoch_ms = (np.arange(n, dtype=np.int64) * 1000) + 1_700_000_000_000
    # pump lineare + rumore deterministico: garantisce almeno un segnale con X bassa
    close = 100.0 + np.linspace(0, 8, n) + np.sin(np.arange(n) * 0.3) * 0.2
    high = close + 0.15
    low = close - 0.15
    return epoch_ms, close.astype(np.float64), high.astype(np.float64), low.astype(np.float64)


def test_numba_missing_error_is_runtime_error():
    assert issubclass(NumbaMissingError, RuntimeError)


def test_simulate_single_width_10():
    epoch_ms, close, high, low = _toy_data()
    trades, n_trades = _simulate_single(
        epoch_ms, close, high, low,
        np.float64(0.5), np.int64(60), np.float64(5.0),
        np.int64(3600),
        np.float64(100.0), np.float64(0.001), np.float64(0.0005),
        np.int64(1),
    )
    assert trades.shape[1] == 10
    assert n_trades >= 0
    if n_trades > 0:
        # reason code valido
        assert set(np.unique(trades[:n_trades, 9])).issubset({1.0, 2.0, 3.0})


def test_dynamic_width_11_and_y_actual_nonnegative():
    epoch_ms, close, high, low = _toy_data()
    trades, n_trades = _simulate_single_dynamic_y(
        epoch_ms, close, high, low,
        np.float64(0.5), np.int64(300), np.float64(5.0),
        np.int64(3600),
        np.float64(100.0), np.float64(0.001), np.float64(0.0005),
        np.int64(1),
    )
    assert trades.shape[1] == 11
    if n_trades > 0:
        assert bool(np.all(trades[:n_trades, 10] >= 0.0))
