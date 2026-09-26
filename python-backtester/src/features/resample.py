"""OHLC multi-timeframe resampling (F6-E04): ``resample_ohlc``.

Rules: ``1min`` / ``5min`` / ``1h`` / ``1d``.

Time source (first available wins): ``DatetimeIndex`` > ``datetime`` column
> ``timestamp`` column (ISO strings or ms ints, as written by the TS
pipeline). The frame is sorted by time; the input is never mutated.

Label/closed convention: ``label="left", closed="left"`` — each candle is
labeled with its opening time and covers ``[start, start + rule)``.
``1d`` buckets are UTC calendar days. Buckets with no trades are omitted
(no ``NaN``-open rows).

Aggregation: O = first open, H = max high, L = min low, C = last close,
V = sum of volumes (``tradeCount`` summed too when present).
"""

from __future__ import annotations

import pandas as pd

_RULES = {"1min": "1min", "5min": "5min", "1h": "1h", "1d": "1d"}

_REQUIRED = ["open", "high", "low", "close", "volume"]


def _resolve_times(df: pd.DataFrame) -> tuple[pd.DatetimeIndex, str]:
    if isinstance(df.index, pd.DatetimeIndex):
        return df.index, (df.index.name or "timestamp")
    for col in ("datetime", "timestamp"):
        if col in df.columns:
            sample = str(df[col].iloc[0]) if len(df) else ""
            if col == "timestamp" and sample.replace(".", "").replace("-", "").isdigit():
                times = pd.to_datetime(df[col].astype(int), unit="ms", utc=True)
            else:
                times = pd.to_datetime(df[col], utc=True)
            return pd.DatetimeIndex(times), col
    raise ValueError(
        "resample_ohlc needs a DatetimeIndex or a 'datetime'/'timestamp' column"
    )


def resample_ohlc(df_1s: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample base (e.g. 1s) OHLC to ``rule`` (``1min/5min/1h/1d``)."""
    if rule not in _RULES:
        raise ValueError(f"Unknown rule {rule!r}. Available: {sorted(_RULES)}")
    missing = [c for c in _REQUIRED if c not in df_1s.columns]
    if missing:
        raise ValueError(f"Missing OHLC column(s): {missing}")
    if df_1s.empty:
        cols = _REQUIRED + (["tradeCount"] if "tradeCount" in df_1s.columns else [])
        return pd.DataFrame(columns=cols)

    times, name = _resolve_times(df_1s)
    df = df_1s.copy()
    df.index = times
    df = df.sort_index()

    g = df.resample(_RULES[rule], label="left", closed="left")
    out = pd.DataFrame(
        {
            "open": g["open"].first(),
            "high": g["high"].max(),
            "low": g["low"].min(),
            "close": g["close"].last(),
            "volume": g["volume"].sum(),
        }
    )
    if "tradeCount" in df.columns:
        out["tradeCount"] = g["tradeCount"].sum()
    out = out.dropna(subset=["open"])
    out.index.name = name
    return out
