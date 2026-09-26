"""Feature engineering package (Fase 6, Lane B).

Leading-NaN / warmup convention (F6-E01, applies to every indicator here):
- ``SMA`` / ``Bollinger Bands`` / ``RSI`` / ``ATR``: the first ``period - 1``
  values are ``NaN`` (``min_periods=period``); the first valid value is at
  zero-based position ``period - 1``. Consumers must treat the first
  ``max(periods)`` rows as warmup.
- ``EMA`` / ``MACD``: seeded on the first observation (pandas ``ewm`` with
  ``adjust=False``), so no leading ``NaN``; the first ``period``
  (resp. ``slow + signal``) rows are still warmup/unstable and must not be
  used for signals.
- ``OBV``: seeded at ``0.0`` on the first bar, no ``NaN``.
- ``VWAP``: defined from the first bar of each session; ``NaN`` wherever the
  cumulative volume of the session is still ``0``.

All functions are pure (no input mutation) and vectorized (pandas/numpy, no
Python loops). Only ``pandas``/``numpy`` are used.
"""

from src.features.indicator_factory import (
    sma,
    ema,
    rsi,
    bollinger_bands,
    atr,
    macd,
    obv,
    vwap,
)
from src.features.feature_pipeline import FEATURE_REGISTRY, add_features
from src.features.resample import resample_ohlc

__all__ = [
    "sma",
    "ema",
    "rsi",
    "bollinger_bands",
    "atr",
    "macd",
    "obv",
    "vwap",
    "FEATURE_REGISTRY",
    "add_features",
    "resample_ohlc",
]
