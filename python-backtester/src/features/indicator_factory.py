"""Indicator factory (F6-E01 + F6-E02).

Pure vectorized functions (pandas/numpy, no Python loops).

Leading-NaN convention: SMA/BB/RSI/ATR emit ``NaN`` for the first
``period - 1`` rows (``min_periods=period``); EMA/MACD are seeded on the
first observation (no leading ``NaN``); OBV is seeded at ``0.0``; VWAP is
``NaN`` while the session cumulative volume is ``0``. Warmup for any
consumer is ``max(periods)`` rows (see ``src.features`` docstring).

Conventions:
- RSI: Wilder smoothing via ``ewm(alpha=1/period, adjust=False)`` on gains
  (``NaN`` deltas treated as flat/``0``). ``avg_loss == 0`` with
  ``avg_gain > 0`` -> ``100.0``; flat series (``0/0``) -> ``NaN``.
- Bollinger Bands: sample std (``ddof=1``, pandas ``rolling.std`` default).
- ATR: Wilder smoothing (``alpha=1/period``) of the true range
  ``max(H-L, |H-prevC|, |L-prevC|)``.
- MACD: ``EMA(fast) - EMA(slow)``, signal = ``EMA(line, signal)``,
  histogram = ``line - signal`` (all ``adjust=False``).
- OBV: ``cumsum(sign(close.diff()) * volume)``; first bar contributes ``0``.
- VWAP: typical price ``(H+L+C)/3``; ``cumsum(TP*V)/cumsum(V)`` reset per
  session label when ``session`` is given, else cumulative over the frame.
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd


def _series(x: pd.Series, name: str) -> pd.Series:
    s = pd.Series(x)
    s.name = name
    return s


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple moving average (``min_periods=period`` -> leading ``NaN``)."""
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")
    s = _series(series, getattr(series, "name", None) or "value")
    return s.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average, ``span=period``, ``adjust=False``.

    Seeded on the first observation: no leading ``NaN`` (first ``period``
    rows are still warmup).
    """
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")
    s = _series(series, getattr(series, "name", None) or "value")
    return s.ewm(span=period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index with Wilder smoothing (``alpha=1/period``)."""
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")
    c = _series(close, "rsi")
    delta = c.diff()
    gain = delta.clip(lower=0.0).fillna(0.0)
    loss = (-delta.clip(upper=0.0)).fillna(0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    out = 100.0 - (100.0 / (1.0 + rs))
    out.name = f"rsi_{period}"
    return out


def bollinger_bands(
    close: pd.Series, period: int = 20, num_std: float = 2.0
) -> pd.DataFrame:
    """Bollinger Bands: SMA middle, ``+/- num_std`` sample-std (``ddof=1``)."""
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")
    c = _series(close, "close")
    middle = c.rolling(window=period, min_periods=period).mean()
    sd = c.rolling(window=period, min_periods=period).std(ddof=1)
    return pd.DataFrame(
        {
            "bb_middle": middle,
            f"bb_upper": middle + num_std * sd,
            f"bb_lower": middle - num_std * sd,
        },
        index=c.index,
    )


def atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """Average True Range with Wilder smoothing (``alpha=1/period``)."""
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")
    h, l, c = (pd.Series(x) for x in (high, low, close))
    prev_close = c.shift(1)
    tr = pd.concat(
        [(h - l), (h - prev_close).abs(), (l - prev_close).abs()], axis=1
    ).max(axis=1)
    out = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    out.name = f"atr_{period}"
    return out


def macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """MACD line / signal / histogram (all EMAs ``adjust=False``)."""
    if not (1 <= fast < slow):
        raise ValueError(f"require 1 <= fast < slow, got fast={fast} slow={slow}")
    if signal < 1:
        raise ValueError(f"signal must be >= 1, got {signal}")
    c = _series(close, "close")
    line = ema(c, fast) - ema(c, slow)
    sig = ema(line, signal)
    hist = line - sig
    return pd.DataFrame(
        {"macd_line": line, "macd_signal": sig, "macd_hist": hist}, index=c.index
    )


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume; seeded at ``0.0`` on the first bar."""
    c, v = pd.Series(close), pd.Series(volume)
    if len(c) != len(v):
        raise ValueError(f"close/volume length mismatch: {len(c)} != {len(v)}")
    direction = np.sign(c.diff().fillna(0.0))
    out = (direction * v).cumsum()
    out.name = "obv"
    return out


def vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    session: Optional[Sequence] = None,
) -> pd.Series:
    """Volume-Weighted Average Price; cumulative per session if given.

    ``session``: array-like of labels (same length, e.g. calendar dates);
    cumulative sums reset at each label change. ``None`` -> cumulative over
    the whole frame. ``NaN`` while session cumulative volume is ``0``.
    """
    h, l, c, v = (pd.Series(x) for x in (high, low, close, volume))
    n = len(c)
    if not (len(h) == len(l) == len(v) == n):
        raise ValueError("high/low/close/volume must have equal length")
    tp = (h + l + c) / 3.0
    pv = tp * v
    if session is None:
        cum_pv = pv.cumsum()
        cum_v = v.cumsum()
    else:
        keys = np.asarray(list(session))
        if len(keys) != n:
            raise ValueError(f"session length {len(keys)} != data length {n}")
        cum_pv = pv.groupby(keys).cumsum()
        cum_v = v.groupby(keys).cumsum()
    out = cum_pv / cum_v
    out.name = "vwap"
    return out
