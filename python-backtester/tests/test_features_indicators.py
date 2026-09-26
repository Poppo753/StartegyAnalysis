"""F6-E01 + F6-E02: indicators vs second independent implementations (tol 1e-8).

Reference implementations below use explicit loops / cumsum / convolve and
never pandas rolling/ewm, so agreement validates the factory formulas.
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.features.indicator_factory import sma, ema, rsi, bollinger_bands, atr
from src.features.indicator_factory import macd, obv, vwap

TOL = 1e-8


@pytest.fixture(scope="module")
def ohlc():
    rng = np.random.RandomState(7)
    n = 150
    close = pd.Series(100.0 + np.cumsum(rng.randn(n) * 0.5))
    spread = np.abs(rng.randn(n)) * 0.2 + 0.01
    high = close + spread
    low = close - spread
    open_ = close.shift(1).fillna(close.iloc[0] - 0.1)
    volume = pd.Series(np.abs(rng.randn(n)) * 10.0 + 1.0)
    return {"open": open_, "high": high, "low": low, "close": close,
            "volume": volume}


# ---- independent references (loops / cumsum, no rolling/ewm) ----

def ref_sma(x, n):
    x = np.asarray(x, float)
    out = np.full_like(x, np.nan)
    c = np.cumsum(np.insert(x, 0, 0.0))
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def ref_ema(x, n):
    x = np.asarray(x, float)
    a = 2.0 / (n + 1)
    out = np.empty_like(x)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def _ref_wilder(x, n):
    """Wilder recursion seeded at x[0]=0, NaN-masked for first n-1 rows."""
    x = np.asarray(x, float)
    a = 1.0 / n
    out = np.empty_like(x)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = (1 - a) * out[i - 1] + a * x[i]
    out[: n - 1] = np.nan
    return out


def ref_rsi(close, n):
    x = np.asarray(close, float)
    d = np.empty_like(x)
    d[0] = 0.0
    d[1:] = np.diff(x)
    g = np.where(d > 0, d, 0.0)
    loss = np.where(d < 0, -d, 0.0)
    ag, al = _ref_wilder(g, n), _ref_wilder(loss, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 100.0 - (100.0 / (1.0 + ag / al))
    return out


def ref_bb(x, n, k):
    x = np.asarray(x, float)
    mid = ref_sma(x, n)
    up = np.full_like(x, np.nan)
    lo = np.full_like(x, np.nan)
    for i in range(n - 1, len(x)):
        sd = x[i - n + 1:i + 1].std(ddof=1)
        up[i], lo[i] = mid[i] + k * sd, mid[i] - k * sd
    return mid, up, lo


def ref_atr(h, l, c, n):
    h, l, c = (np.asarray(v, float) for v in (h, l, c))
    pc = np.empty_like(c)
    pc[0] = np.nan
    pc[1:] = c[:-1]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    return _ref_wilder(tr, n)


def ref_obv(close, volume):
    c = np.asarray(close, float)
    v = np.asarray(volume, float)
    out = np.zeros_like(c)
    for i in range(1, len(c)):
        if c[i] > c[i - 1]:
            out[i] = out[i - 1] + v[i]
        elif c[i] < c[i - 1]:
            out[i] = out[i - 1] - v[i]
        else:
            out[i] = out[i - 1]
    return out


def ref_vwap(h, l, c, v, session=None):
    h, l, c, v = (np.asarray(a, float) for a in (h, l, c, v))
    tp = (h + l + c) / 3.0
    out = np.full_like(c, np.nan)
    acc_pv, acc_v, cur = 0.0, 0.0, object()
    for i in range(len(c)):
        key = session[i] if session is not None else None
        if key != cur:
            acc_pv, acc_v, cur = 0.0, 0.0, key
        acc_pv += tp[i] * v[i]
        acc_v += v[i]
        out[i] = acc_pv / acc_v if acc_v != 0 else np.nan
    return out


def assert_close(a, b, tol=TOL):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    assert a.shape == b.shape, f"shape {a.shape} != {b.shape}"
    assert np.array_equal(np.isnan(a), np.isnan(b)), "NaN mask differs"
    m = ~np.isnan(a)
    assert np.allclose(a[m], b[m], rtol=tol, atol=tol), \
        f"max abs diff: {np.max(np.abs(a[m] - b[m]))}"


# ---- F6-E01 ----

class TestIndicatorsE01:
    def test_sma(self, ohlc):
        for n in (5, 20):
            assert_close(sma(ohlc["close"], n), ref_sma(ohlc["close"], n))

    def test_ema(self, ohlc):
        for n in (5, 12):
            assert_close(ema(ohlc["close"], n), ref_ema(ohlc["close"], n))

    def test_rsi_14(self, ohlc):
        assert_close(rsi(ohlc["close"], 14), ref_rsi(ohlc["close"], 14))

    def test_rsi_other_period(self, ohlc):
        assert_close(rsi(ohlc["close"], 7), ref_rsi(ohlc["close"], 7))

    def test_bollinger(self, ohlc):
        got = bollinger_bands(ohlc["close"], 20, 2.0)
        mid, up, lo = ref_bb(ohlc["close"], 20, 2.0)
        assert_close(got["bb_middle"], mid)
        assert_close(got["bb_upper"], up)
        assert_close(got["bb_lower"], lo)

    def test_atr(self, ohlc):
        got = atr(ohlc["high"], ohlc["low"], ohlc["close"], 14)
        ref = ref_atr(ohlc["high"], ohlc["low"], ohlc["close"], 14)
        assert_close(got, ref)

    def test_leading_nan_convention(self, ohlc):
        n = 14
        for got in (sma(ohlc["close"], n), rsi(ohlc["close"], n),
                    atr(ohlc["high"], ohlc["low"], ohlc["close"], n),
                    bollinger_bands(ohlc["close"], n)["bb_middle"]):
            assert got.iloc[: n - 1].isna().all()
            assert got.iloc[n - 1:].notna().all()

    def test_invalid_period(self, ohlc):
        with pytest.raises(ValueError):
            sma(ohlc["close"], 0)
        with pytest.raises(ValueError):
            rsi(ohlc["close"], -3)


# ---- F6-E02 ----

class TestIndicatorsE02:
    def test_macd(self, ohlc):
        c = np.asarray(ohlc["close"], float)
        line = ref_ema(c, 12) - ref_ema(c, 26)
        sig = ref_ema(line, 9)
        got = macd(ohlc["close"], 12, 26, 9)
        assert_close(got["macd_line"], line)
        assert_close(got["macd_signal"], sig)
        assert_close(got["macd_hist"], line - sig)

    def test_macd_invalid(self, ohlc):
        with pytest.raises(ValueError):
            macd(ohlc["close"], 26, 12, 9)

    def test_obv(self, ohlc):
        got = obv(ohlc["close"], ohlc["volume"])
        assert_close(got, ref_obv(ohlc["close"], ohlc["volume"]))
        assert got.iloc[0] == 0.0

    def test_obv_length_mismatch(self, ohlc):
        with pytest.raises(ValueError):
            obv(ohlc["close"].iloc[:10], ohlc["volume"])

    def test_vwap_no_session(self, ohlc):
        got = vwap(ohlc["high"], ohlc["low"], ohlc["close"], ohlc["volume"])
        ref = ref_vwap(ohlc["high"], ohlc["low"], ohlc["close"], ohlc["volume"])
        assert_close(got, ref)
        tp0 = (ohlc["high"].iloc[0] + ohlc["low"].iloc[0]
               + ohlc["close"].iloc[0]) / 3.0
        assert got.iloc[0] == pytest.approx(tp0, abs=1e-12)

    def test_vwap_per_session(self, ohlc):
        n = len(ohlc["close"])
        session = ["A"] * (n // 2) + ["B"] * (n - n // 2)
        got = vwap(ohlc["high"], ohlc["low"], ohlc["close"],
                   ohlc["volume"], session)
        ref = ref_vwap(ohlc["high"], ohlc["low"], ohlc["close"],
                       ohlc["volume"], session)
        assert_close(got, ref)
        # session B restarts: first B value == its own typical price
        j = n // 2
        tp_j = (ohlc["high"].iloc[j] + ohlc["low"].iloc[j]
                + ohlc["close"].iloc[j]) / 3.0
        assert got.iloc[j] == pytest.approx(tp_j, abs=1e-12)

    def test_vwap_zero_volume_nan(self):
        h = pd.Series([10.0, 10.0, 11.0])
        l = pd.Series([9.0, 9.0, 10.0])
        c = pd.Series([9.5, 9.5, 10.5])
        v = pd.Series([0.0, 0.0, 2.0])
        got = vwap(h, l, c, v)
        assert got.iloc[:2].isna().all()
        assert got.iloc[2] == pytest.approx((11.0 + 10.0 + 10.5) / 3.0)
