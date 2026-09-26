"""F6-E03: add_features copy-on-write, registry, idempotency, errors."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.features.feature_pipeline import FEATURE_REGISTRY, add_features

ALL = ["sma_20", "ema_12", "rsi_14", "bb_20", "atr_14", "macd", "obv", "vwap"]


@pytest.fixture()
def df():
    rng = np.random.RandomState(11)
    n = 60
    close = pd.Series(50.0 + np.cumsum(rng.randn(n) * 0.2))
    spread = np.abs(rng.randn(n)) * 0.1 + 0.01
    out = pd.DataFrame({
        "datetime": pd.date_range("2026-01-01", periods=n, freq="1min", tz="UTC"),
        "open": close.shift(1).fillna(close.iloc[0]),
        "high": close + spread,
        "low": close - spread,
        "close": close,
        "volume": np.abs(rng.randn(n)) * 5 + 0.5,
    })
    return out


def test_registry_names_stable():
    assert sorted(FEATURE_REGISTRY) == sorted(ALL)


def test_add_all_columns(df):
    got = add_features(df, ALL)
    for col in ["sma_20", "ema_12", "rsi_14", "bb_middle_20", "bb_upper_20",
                "bb_lower_20", "atr_14", "macd_line", "macd_signal",
                "macd_hist", "obv", "vwap"]:
        assert col in got.columns
    assert len(got) == len(df)


def test_copy_on_write(df):
    before = df.copy(deep=True)
    got = add_features(df, ALL)
    pd.testing.assert_frame_equal(df, before)  # input untouched
    assert got is not df
    got["sma_20"] = -1.0  # mutating output must not leak back
    assert (df["close"] == before["close"]).all()


def test_idempotency(df):
    once = add_features(df, ALL)
    twice = add_features(once, ALL)
    assert list(twice.columns) == list(once.columns)  # no duplicates
    pd.testing.assert_frame_equal(twice, once)


def test_empty_list(df):
    got = add_features(df, [])
    pd.testing.assert_frame_equal(got, df)
    assert got is not df


def test_unknown_indicator(df):
    with pytest.raises(ValueError, match="Unknown feature"):
        add_features(df, ["sma_20", "nope_99"])


def test_single_subset(df):
    got = add_features(df, ["rsi_14"])
    assert "rsi_14" in got.columns
    assert "sma_20" not in got.columns
