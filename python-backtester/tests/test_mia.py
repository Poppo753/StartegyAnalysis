import numpy as np
import pandas as pd

from src.strategies.mia import MiaStrategy


def _df(prices):
    n = len(prices)
    return pd.DataFrame({
        "datetime": pd.date_range("2026-01-01", periods=n, freq="s"),
        "open": prices, "high": prices, "low": prices,
        "close": prices, "volume": np.ones(n),
    })


def test_validate():
    s = MiaStrategy()
    assert s.validate({"lookback": 50, "soglia": 1.5}) is True
    assert s.validate({"lookback": 2, "soglia": 1.5}) is False
    assert s.validate({"lookback": 50}) is False


def test_trend_monotono_non_genera_segnali():
    s = MiaStrategy()
    segnali = s.generate_signals(_df(np.linspace(100, 200, 400)), {"lookback": 50, "soglia": 2.0})
    assert [g for g in segnali if g.type == "ENTRY"] == []


def test_segnali_alternano_entry_exit():
    n = 600
    prices = 100 + 10 * np.sin(np.arange(n) / 12)
    s = MiaStrategy()
    segnali = s.generate_signals(_df(prices), {"lookback": 20, "soglia": 0.5})
    for a, b in zip(segnali, segnali[1:]):
        assert a.type != b.type


def test_gpu_param_arrays():
    s = MiaStrategy()
    out = s.gpu_param_arrays([{"lookback": 10, "soglia": 1.0}, {"lookback": 20, "soglia": 2.0}])
    assert set(out) == {"lookback", "soglia"}
    assert all(isinstance(v, np.ndarray) and v.dtype != object for v in out.values())
    assert len(out["lookback"]) == 2
