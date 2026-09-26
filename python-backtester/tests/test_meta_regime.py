"""F5-A01: regime_detector on synthetic series (v3 §5.7 thresholds).

Constructions (documented, deterministic):
- TRENDING: drift + AR(1) returns (persistent, positively autocorrelated:
  ADX > 25, Hurst > 0.5, VR > 1). A pure arithmetic drift would give
  VR ~= 1 (no return autocorrelation) and flake on the v3 AND-rule.
- RANGING: short-period sine (period 16 << window 100, several cycles per
  window: ADX < 20, Hurst < 0.5). A long-period sine looks trending to
  any short-horizon estimator (within-cycle persistence).
- RANDOM WALK: iid Gaussian returns (Hurst ~= 0.5 ON the threshold, so a
  deterministic threshold rule misfires sometimes -- acknowledged v3
  fragility; expectation is the non-directional set {NORMAL, RANGING}).
- HIGH_VOL: flat series + one jump strictly inside a window (volatility
  >> 2x mean). Precedence matters: the shock window has ADX=55 /
  Hurst=0.75 / VR=1.01, i.e. v3-order would call it TRENDING; HIGH_VOL
  first (same thresholds) is what makes it HIGH_VOL.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest

from src.meta_analysis.regime_detector import (
    ADX_RANGE,
    ADX_TREND,
    HURST_MID,
    VARIANCE_RATIO_TREND,
    VOL_SPIKE_MULT,
    compute_adx,
    detect_current_regime,
    detect_regime,
    detect_regimes,
    hurst_exponent,
    realized_volatility,
    regime_features,
    variance_ratio,
)

N = 2000
WINDOW = 100


def _ohlc(close) -> pd.DataFrame:
    close = pd.Series(np.asarray(close, dtype=float))
    return pd.DataFrame(
        {
            "datetime": pd.date_range("2026-01-01", periods=len(close), freq="min"),
            "open": close.values,
            "high": close.values * 1.001,
            "low": close.values * 0.999,
            "close": close.values,
            "volume": 10.0,
        }
    )


@pytest.fixture(scope="module")
def series():
    # Independent stream per series (each construction reproducible alone).
    rng = np.random.default_rng(7)
    u = np.zeros(N)
    for t in range(1, N):
        u[t] = 0.4 * u[t - 1] + rng.normal(0, 0.001)
    trend = 100 * np.exp(np.cumsum(0.002 + u))
    rng = np.random.default_rng(7)
    sine = 100 + 5 * np.sin(2 * np.pi * np.arange(N) / 16) + rng.normal(0, 0.2, N)
    rng = np.random.default_rng(123)
    rw = 100 * np.exp(np.cumsum(rng.normal(0, 0.005, N)))
    rng = np.random.default_rng(7)
    shock = 100 + rng.normal(0, 0.05, N)
    shock[550:] += 15.0  # strictly inside window [500, 600)
    return {
        "trend": _ohlc(trend),
        "sine": _ohlc(sine),
        "rw": _ohlc(rw),
        "shock": _ohlc(shock),
    }


def _frac(table: pd.DataFrame, label: str) -> float:
    return float((table["regime"] == label).mean())


class TestThresholdsAreV3:
    def test_threshold_constants_verbatim_v3_57(self):
        assert ADX_TREND == 25.0
        assert ADX_RANGE == 20.0
        assert HURST_MID == 0.5
        assert VARIANCE_RATIO_TREND == 1.0
        assert VOL_SPIKE_MULT == 2.0

    def test_no_ml_dependencies(self):
        import pathlib

        src = pathlib.Path(__file__).resolve().parent.parent.joinpath(
            "src", "meta_analysis", "regime_detector.py"
        ).read_text()
        for token in ("sklearn", "hmmlearn", "HiddenMarkov", "CUSUM", "cusum"):
            assert token not in src, f"forbidden/ML token {token!r} in regime_detector"


class TestSyntheticRegimes:
    def test_linear_trend_is_trending(self, series):
        table = detect_regimes(series["trend"], window=WINDOW)
        assert _frac(table, "TRENDING") >= 0.90

    def test_sine_is_ranging(self, series):
        table = detect_regimes(series["sine"], window=WINDOW)
        assert _frac(table, "RANGING") >= 0.90

    def test_random_walk_is_non_directional(self, series):
        table = detect_regimes(series["rw"], window=WINDOW)
        frac = float(table["regime"].isin(["NORMAL", "RANGING"]).mean())
        assert frac >= 0.90

    def test_shock_window_is_high_vol(self, series):
        table = detect_regimes(series["shock"], window=WINDOW)
        shock_row = table[table["window_start"] == 500].iloc[0]
        assert shock_row["regime"] == "HIGH_VOL"
        assert (table["regime"] == "TRENDING").sum() == 0
        correct = table["regime"].isin(["NORMAL", "RANGING", "HIGH_VOL"]).mean()
        assert float(correct) >= 0.90


class TestApiShape:
    def test_features_keys(self, series):
        feats = regime_features(series["trend"].iloc[:WINDOW])
        assert set(feats) == {"adx", "hurst", "volatility", "variance_ratio"}
        assert all(np.isfinite(v) for v in feats.values())

    def test_single_window_label(self, series):
        assert detect_regime(series["trend"].iloc[:WINDOW]) == "TRENDING"
        assert detect_regime(series["sine"].iloc[:WINDOW]) == "RANGING"

    def test_current_regime_is_last_window(self, series):
        table = detect_regimes(series["trend"], window=WINDOW)
        assert detect_current_regime(series["trend"], window=WINDOW) == table["regime"].iloc[-1]

    def test_indicators_degenerate_inputs(self):
        flat = pd.Series([100.0] * 60)
        assert hurst_exponent(flat) == 0.5
        assert realized_volatility(flat) == 0.0
        assert variance_ratio(flat) == 1.0
        assert compute_adx(flat, flat, flat) == 0.0

    def test_bad_inputs_raise(self, series):
        with pytest.raises(ValueError):
            detect_regimes(series["trend"].iloc[:10], window=WINDOW)
        with pytest.raises(ValueError):
            detect_regimes(series["trend"], window=10)
        with pytest.raises(ValueError):
            regime_features(pd.DataFrame({"close": [1.0, 2.0]}))
        with pytest.raises(ValueError):
            variance_ratio(pd.Series([1.0, 2.0, 3.0]), k=1)
