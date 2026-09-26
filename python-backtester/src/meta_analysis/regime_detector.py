"""regime_detector.py - Regime detection via soglie v3 §5.7 (F5-A01).

Pure functions on DataFrame -> per-window label in
``TRENDING / RANGING / HIGH_VOL / NORMAL`` from ADX + Hurst exponent +
realized volatility + variance ratio. No ML dependencies (only
numpy/pandas). Online state-space and change-point detectors are excluded
here (forbidden §13, production-only per v3 §5.7-nota-v3).

Thresholds (masterplan v3 §5.7, verbatim)::

    TRENDING if adx > 25 and hurst > 0.5 and variance_ratio > 1
    RANGING  if adx < 20 and hurst < 0.5
    HIGH_VOL if volatility > 2 * mean_volatility
    NORMAL   otherwise

Precedence note: HIGH_VOL is evaluated FIRST (same thresholds, only the
order differs from the v3 sketch). Rationale: a volatility spike must
not be masked by the fragile deterministic ADX/Hurst pair that v3
itself calls fragile (v3 §5.7-nota-v3); a shock window can otherwise
leak into TRENDING/RANGING on a single Wilder-smoothed DM print.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# v3 §5.7 thresholds (verbatim values).
ADX_TREND = 25.0
ADX_RANGE = 20.0
HURST_MID = 0.5
VARIANCE_RATIO_TREND = 1.0
VOL_SPIKE_MULT = 2.0

ADX_PERIOD = 14
MIN_WINDOW = 30

LABELS = ("TRENDING", "RANGING", "HIGH_VOL", "NORMAL")


def compute_adx(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = ADX_PERIOD
) -> float:
    """Wilder ADX, last value (0.0 when undefined: flat/too-short series)."""
    if period < 1:
        raise ValueError(f"period must be >= 1, got {period}")
    h = pd.Series(np.asarray(high, dtype=float))
    l = pd.Series(np.asarray(low, dtype=float))
    c = pd.Series(np.asarray(close, dtype=float))
    n = len(c)
    if not (len(h) == len(l) == n) or n < period + 1:
        return 0.0
    up = h.diff()
    dn = -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0))
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0))
    prev_close = c.shift(1)
    tr = pd.concat(
        [(h - l), (h - prev_close).abs(), (l - prev_close).abs()], axis=1
    ).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        plus_di = 100.0 * (
            plus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
            / atr
        )
        minus_di = 100.0 * (
            minus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
            / atr
        )
        di_sum = plus_di + minus_di
        dx = 100.0 * (plus_di - minus_di).abs() / di_sum
    dx = dx.where(di_sum.fillna(0.0) != 0.0, 0.0).fillna(0.0)
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    finite = adx[np.isfinite(adx.values)]
    return float(finite.iloc[-1]) if len(finite) else 0.0


def hurst_exponent(close: pd.Series) -> float:
    """Hurst via rescaled-range (R/S): >0.5 trending, <0.5 mean-reverting.

    Returns 0.5 when undefined (constant or < 20 observations).
    """
    x = np.asarray(close, dtype=float).ravel()
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 20 or float(np.std(x)) == 0.0:
        return 0.5
    max_lag = min(n // 2, 100)
    lags = list(range(10, max_lag + 1))
    if len(lags) < 2:
        return 0.5
    log_lags: List[float] = []
    log_rs: List[float] = []
    for lag in lags:
        n_chunks = n // lag
        if n_chunks < 1:
            continue
        rs_vals: List[float] = []
        for k in range(n_chunks):
            chunk = x[k * lag:(k + 1) * lag]
            s = float(np.std(chunk, ddof=1))
            if s == 0.0 or not np.isfinite(s):
                continue
            dev = np.cumsum(chunk - chunk.mean())
            r = float(dev.max() - dev.min())
            rs_vals.append(r / s)
        if not rs_vals:
            continue
        log_lags.append(float(np.log(lag)))
        log_rs.append(float(np.log(np.mean(rs_vals))))
    if len(log_lags) < 2:
        return 0.5
    slope = float(np.polyfit(np.asarray(log_lags), np.asarray(log_rs), 1)[0])
    if not np.isfinite(slope):
        return 0.5
    return float(np.clip(slope, 0.0, 1.0))


def realized_volatility(close: pd.Series) -> float:
    """Std of log-returns (ddof=1); 0.0 when undefined."""
    x = np.asarray(close, dtype=float).ravel()
    x = x[np.isfinite(x)]
    x = x[x > 0]
    if len(x) < 3:
        return 0.0
    r = np.diff(np.log(x))
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return 0.0
    return float(np.std(r, ddof=1))


def variance_ratio(close: pd.Series, k: int = 2) -> float:
    """Lo-MacKinlay variance ratio on log-returns (k=2 default).

    VR = Var(k-period returns) / (k * Var(1-period returns)).
    >1 trending, <1 mean-reverting, ~=1 random walk. Returns 1.0 when
    undefined (constant or too-short series).
    """
    if int(k) < 2:
        raise ValueError(f"k must be >= 2, got {k}")
    x = np.asarray(close, dtype=float).ravel()
    x = x[np.isfinite(x)]
    x = x[x > 0]
    if len(x) < 2 * int(k) + 1:
        return 1.0
    r1 = np.diff(np.log(x))
    r1 = r1[np.isfinite(r1)]
    m = (len(r1) // int(k)) * int(k)
    if m < 2 * int(k):
        return 1.0
    rk = r1[:m].reshape(-1, int(k)).sum(axis=1)
    v1 = float(np.var(r1[:m], ddof=1))
    vk = float(np.var(rk, ddof=1))
    if v1 <= 0.0 or not (np.isfinite(v1) and np.isfinite(vk)):
        return 1.0
    return float(vk / (int(k) * v1))


def regime_features(df: pd.DataFrame) -> Dict[str, float]:
    """The four v3 §5.7 numbers for one window (requires high/low/close)."""
    for col in ("high", "low", "close"):
        if col not in df.columns:
            raise ValueError(f"regime detection requires column {col!r}")
        if len(df) == 0:
            raise ValueError("regime detection on empty frame")
    return {
        "adx": compute_adx(df["high"], df["low"], df["close"]),
        "hurst": hurst_exponent(df["close"]),
        "volatility": realized_volatility(df["close"]),
        "variance_ratio": variance_ratio(df["close"]),
    }


def detect_regime(df: pd.DataFrame, baseline_vol: Optional[float] = None) -> str:
    """Label one window (v3 §5.7 thresholds; HIGH_VOL precedence, see note).

    Args:
        df: OHLC window with high/low/close columns.
        baseline_vol: mean volatility reference for the HIGH_VOL rule
            (vol > 2 * baseline). None disables the HIGH_VOL rule.
    """
    feats = regime_features(df)
    vol = feats["volatility"]
    if (
        baseline_vol is not None
        and np.isfinite(float(baseline_vol))
        and float(baseline_vol) > 0
        and vol > VOL_SPIKE_MULT * float(baseline_vol)
    ):
        return "HIGH_VOL"
    if (
        feats["adx"] > ADX_TREND
        and feats["hurst"] > HURST_MID
        and feats["variance_ratio"] > VARIANCE_RATIO_TREND
    ):
        return "TRENDING"
    if feats["adx"] < ADX_RANGE and feats["hurst"] < HURST_MID:
        return "RANGING"
    return "NORMAL"


def detect_regimes(
    df: pd.DataFrame,
    window: int = 100,
    step: Optional[int] = None,
    baseline_vol: Optional[float] = None,
) -> pd.DataFrame:
    """Label consecutive windows (non-overlapping by default).

    Args:
        df: OHLC frame with high/low/close columns (row 0 = oldest).
        window: rows per window (must be >= MIN_WINDOW = 30 for ADX warmup).
        step: window stride (default = window, i.e. non-overlapping).
            A partial tail shorter than `window` is dropped.
        baseline_vol: explicit HIGH_VOL reference; default = mean of the
            per-window volatilities.

    Returns:
        DataFrame with columns [window_start, window_end, regime, adx,
        hurst, volatility, variance_ratio], one row per full window.
    """
    window = int(window)
    if window < MIN_WINDOW:
        raise ValueError(f"window must be >= {MIN_WINDOW} (ADX warmup), got {window}")
    step = int(step) if step is not None else window
    if step < 1:
        raise ValueError(f"step must be >= 1, got {step}")
    if len(df) < window:
        raise ValueError(f"need >= {window} rows, got {len(df)}")
    starts = list(range(0, len(df) - window + 1, step))
    feats = [regime_features(df.iloc[s:s + window]) for s in starts]
    base = (
        float(baseline_vol)
        if baseline_vol is not None
        else float(np.mean([f["volatility"] for f in feats]))
    )
    rows = []
    for s, f in zip(starts, feats):
        rows.append(
            {
                "window_start": int(s),
                "window_end": int(s + window),
                "regime": detect_regime(df.iloc[s:s + window], baseline_vol=base),
                "adx": f["adx"],
                "hurst": f["hurst"],
                "volatility": f["volatility"],
                "variance_ratio": f["variance_ratio"],
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "window_start",
            "window_end",
            "regime",
            "adx",
            "hurst",
            "volatility",
            "variance_ratio",
        ],
    )


def detect_current_regime(df: pd.DataFrame, window: int = 100) -> str:
    """Regime of the last full window (the "current" regime for allocation)."""
    window = int(window)
    if window < MIN_WINDOW:
        raise ValueError(f"window must be >= {MIN_WINDOW}, got {window}")
    if len(df) < window:
        raise ValueError(f"need >= {window} rows, got {len(df)}")
    table = detect_regimes(df, window=window)
    return str(table["regime"].iloc[-1])
