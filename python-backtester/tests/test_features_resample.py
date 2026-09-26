"""F6-E04: resample_ohlc on a hand-verified synthetic 1s fixture.

PRIMARY DoD (no external deps): O=first open, H=max high, L=min low,
C=last close, V=sum volumes, exact candle count.

CONDITIONAL DoD (TypeScript 1m CSVs): applied only if Lane C outputs exist;
currently NOT produced (only ohlc_1s_*.csv in data/) -> test skips with a
note instead of failing.
"""
import glob
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.features.resample import resample_ohlc

START = pd.Timestamp("2026-01-01T00:00:00Z")


def make_1s(n=300, start=START, drop=None, iso=True):
    idx = pd.date_range(start, periods=n, freq="s", tz="UTC")
    i = pd.Series(range(n), index=idx)
    df = pd.DataFrame({
        "timestamp": idx.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%S.000Z") if iso else idx,
        "open": i.values.astype(float),
        "high": (i + 10).values.astype(float),
        "low": (i - 10).values.astype(float),
        "close": (i + 1).values.astype(float),
        "volume": 1.0,
        "tradeCount": 2,
    })
    if drop is not None:
        df = df.drop(df.index[drop]).reset_index(drop=True)
    return df


def bucket(j, width):
    lo = j * width
    hi = lo + width - 1
    return {"open": float(lo), "high": float(hi + 10), "low": float(lo - 10),
            "close": float(hi + 1), "volume": float(width)}


class TestResamplePrimary:
    def test_1min_exact(self):
        got = resample_ohlc(make_1s(300), "1min")
        assert len(got) == 5  # exact candle count
        for j in range(5):
            row = got.iloc[j]
            exp = bucket(j, 60)
            assert row["open"] == exp["open"]
            assert row["high"] == exp["high"]
            assert row["low"] == exp["low"]
            assert row["close"] == exp["close"]
            assert row["volume"] == exp["volume"]
            assert row["tradeCount"] == 120
        # label/closed convention: labeled with opening time
        assert got.index[0] == START
        assert list(got.index) == list(pd.date_range(START, periods=5, freq="min", tz="UTC"))

    def test_counts_5min_1h_1d(self):
        assert len(resample_ohlc(make_1s(300), "5min")) == 1
        assert len(resample_ohlc(make_1s(300), "1h")) == 1
        assert len(resample_ohlc(make_1s(300), "1d")) == 1
        row = resample_ohlc(make_1s(300), "5min").iloc[0]
        exp = bucket(0, 300)
        assert (row["open"], row["high"], row["low"], row["close"],
                row["volume"]) == (exp["open"], exp["high"], exp["low"],
                                   exp["close"], exp["volume"])

    def test_gap_drops_empty_bucket(self):
        df = make_1s(300, drop=range(60, 120))  # whole 2nd minute missing
        got = resample_ohlc(df, "1min")
        assert len(got) == 4
        assert got["open"].notna().all()

    def test_datetime_index_input(self):
        df = make_1s(120, iso=False).set_index("timestamp")
        got = resample_ohlc(df, "1min")
        assert len(got) == 2
        assert got.iloc[0]["open"] == 0.0

    def test_input_not_mutated(self):
        df = make_1s(120)
        before = df.copy(deep=True)
        resample_ohlc(df, "1min")
        pd.testing.assert_frame_equal(df, before)

    def test_bad_rule_and_missing_cols(self):
        with pytest.raises(ValueError, match="Unknown rule"):
            resample_ohlc(make_1s(10), "15min")
        with pytest.raises(ValueError, match="Missing OHLC"):
            resample_ohlc(pd.DataFrame({"close": [1.0]}), "1min")


class TestResampleConditionalTS:
    def test_vs_typescript_1m_csvs(self):
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        found = glob.glob(os.path.join(repo, "..", "data", "*", "ohlc",
                                        "ohlc_1m_*.csv"))
        if not found:
            pytest.skip(
                "CONDITIONAL DoD N/A: no TypeScript ohlc_1m_*.csv in data/ "
                "(Lane C has not produced multi-timeframe CSVs yet); "
                "PRIMARY synthetic-fixture DoD above governs."
            )
        pytest.fail("TS 1m CSVs now exist: implement the comparison vs "
                    f"{found[0]} (F6-E04 conditional DoD).")
