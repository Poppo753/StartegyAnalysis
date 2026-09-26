"""DataFrame integration (F6-E03): ``add_features`` + ``FEATURE_REGISTRY``.

Stable column names: ``sma_20``, ``ema_12``, ``rsi_14``,
``bb_middle_20``/``bb_upper_20``/``bb_lower_20``, ``atr_14``,
``macd_line``/``macd_signal``/``macd_hist``, ``obv``, ``vwap``.

``add_features`` is copy-on-write (never mutates the input) and idempotent
(re-applying the same list overwrites the same columns, no duplicates).
Unknown names raise an explicit ``ValueError`` listing what is available.

``vwap`` resets per calendar day when the frame carries a ``datetime``
column (or a ``DatetimeIndex``), else it is cumulative over the frame.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Union

import pandas as pd

from src.features.indicator_factory import (
    atr,
    bollinger_bands,
    ema,
    macd,
    obv,
    rsi,
    sma,
    vwap,
)

FeatureFn = Callable[[pd.DataFrame], Union[pd.Series, pd.DataFrame]]


def _sma_20(df: pd.DataFrame) -> pd.Series:
    return sma(df["close"], 20).rename("sma_20")


def _ema_12(df: pd.DataFrame) -> pd.Series:
    return ema(df["close"], 12).rename("ema_12")


def _rsi_14(df: pd.DataFrame) -> pd.Series:
    return rsi(df["close"], 14)


def _bb_20(df: pd.DataFrame) -> pd.DataFrame:
    bb = bollinger_bands(df["close"], 20, 2.0)
    return bb.rename(
        columns={
            "bb_middle": "bb_middle_20",
            "bb_upper": "bb_upper_20",
            "bb_lower": "bb_lower_20",
        }
    )


def _atr_14(df: pd.DataFrame) -> pd.Series:
    return atr(df["high"], df["low"], df["close"], 14)


def _macd(df: pd.DataFrame) -> pd.DataFrame:
    return macd(df["close"], 12, 26, 9)


def _obv(df: pd.DataFrame) -> pd.Series:
    return obv(df["close"], df["volume"])


def _vwap(df: pd.DataFrame) -> pd.Series:
    session = None
    if "datetime" in df.columns:
        session = pd.to_datetime(df["datetime"], utc=True).dt.date
    elif isinstance(df.index, pd.DatetimeIndex):
        session = df.index.date
    return vwap(df["high"], df["low"], df["close"], df["volume"], session).rename(
        "vwap"
    )


FEATURE_REGISTRY: Dict[str, FeatureFn] = {
    "sma_20": _sma_20,
    "ema_12": _ema_12,
    "rsi_14": _rsi_14,
    "bb_20": _bb_20,
    "atr_14": _atr_14,
    "macd": _macd,
    "obv": _obv,
    "vwap": _vwap,
}


def add_features(df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
    """Return a copy of ``df`` with one column group per requested feature."""
    if isinstance(features, str):
        features = [features]
    unknown = [f for f in features if f not in FEATURE_REGISTRY]
    if unknown:
        raise ValueError(
            f"Unknown feature(s): {unknown}. Available: {sorted(FEATURE_REGISTRY)}"
        )
    out = df.copy()
    for name in features:
        result = FEATURE_REGISTRY[name](df)
        if isinstance(result, pd.DataFrame):
            for col in result.columns:
                out[col] = result[col].values
        else:
            out[result.name] = result.values
    return out
