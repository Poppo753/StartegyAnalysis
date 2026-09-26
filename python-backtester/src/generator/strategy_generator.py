"""strategy_generator.py - Template registry + generazione da template (F4-G01).

TEMPLATE_REGISTRY con 4 voci:
- momentum_drop, mean_reversion_zscore: spazi riusati DALLE strategie reali
  (MomentumDropStrategy / MeanReversionZScore, cfr. src/strategies/).
- breakout, grid: spazi parametrici v3 §5.4 con kind della convenzione F1
  (kind in {"float", "int", "float_log", "int_log"}, cfr. src/strategy_base.py).

generate_from_template(name, rng) -> dict parametri campionati uniformemente
dallo spazio e validati via strategy.validate (retry limitati, mai eccezioni
di validazione verso il chiamante per nomi noti).
"""

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from src.strategy import BacktestParams, Trade
from src.strategy_base import ALLOWED_PARAM_KINDS, Signal, TradingStrategy
from src.strategies.mean_reversion import MeanReversionZScore
from src.strategies.momentum_drop import MomentumDropStrategy

_MAX_GENERATE_ATTEMPTS = 50


def _sample_value(lo: float, hi: float, kind: str, rng: np.random.Generator) -> Any:
    """Campiona un valore in [lo, hi] secondo il kind F1 (clip sempre)."""
    if kind == "float":
        return float(np.clip(float(rng.uniform(lo, hi)), lo, hi))
    if kind == "int":
        return int(np.clip(int(rng.integers(int(lo), int(hi) + 1)), lo, hi))
    if kind == "float_log":
        if float(lo) <= 0:
            raise ValueError(f"float_log richiede lo>0 (lo={lo})")
        val = float(np.exp(rng.uniform(np.log(float(lo)), np.log(float(hi)))))
        return float(np.clip(val, lo, hi))
    if kind == "int_log":
        if int(lo) <= 0:
            raise ValueError(f"int_log richiede lo>0 (lo={lo})")
        val = int(round(float(np.exp(rng.uniform(np.log(float(lo)), np.log(float(hi)))))))
        return int(np.clip(val, lo, hi))
    if kind == "categorical":
        # Spazio non standard: lo = sequenza di opzioni, hi ignorato.
        options = list(lo)  # type: ignore[arg-type]
        return options[int(rng.integers(0, len(options)))]
    raise ValueError(f"kind non ammesso: {kind!r}")


def sample_from_space(space: Dict[str, Tuple], rng: np.random.Generator) -> Dict[str, Any]:
    """Campiona un dict parametri dallo spazio (uniforme per kind)."""
    sampled: Dict[str, Any] = {}
    for name, spec in space.items():
        lo, hi, kind = spec
        sampled[name] = _sample_value(lo, hi, kind, rng)
    return sampled


def _pair_signals_to_long_trades(
    df: pd.DataFrame,
    signals: List[Signal],
    symbol: str,
    position_size: float,
    fee_rate: float,
    slippage_rate: float,
    max_hold_seconds: int,
    x: float,
    y: int,
    z: float,
) -> List[Trade]:
    """Accoppia segnali ENTRY->EXIT in trade LONG (stessa contabilita' ovunque)."""
    datetimes = pd.to_datetime(df["datetime"]).values
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    if "epoch_seconds" in df.columns:
        epoch_secs = df["epoch_seconds"].values.astype(float)
    else:
        epoch_secs = np.arange(len(df), dtype=float)
    ts_to_idx = {pd.Timestamp(t): k for k, t in enumerate(datetimes)}

    trades: List[Trade] = []
    k = 0
    while k < len(signals):
        entry = signals[k]
        if entry.type != "ENTRY":
            k += 1
            continue
        exit_sig = signals[k + 1] if k + 1 < len(signals) else None
        if exit_sig is not None and exit_sig.type != "EXIT":
            exit_sig = None
        entry_idx = ts_to_idx.get(pd.Timestamp(entry.timestamp), 0)
        entry_epoch = float(epoch_secs[entry_idx])
        raw_entry = float(closes[entry_idx])
        entry_price = raw_entry * (1.0 + slippage_rate)
        if exit_sig is not None:
            exit_idx = ts_to_idx.get(pd.Timestamp(exit_sig.timestamp), len(df) - 1)
        else:
            exit_idx = len(df) - 1
        hold_idx = exit_idx
        for j in range(entry_idx + 1, len(df)):
            if float(epoch_secs[j]) - entry_epoch >= max_hold_seconds:
                hold_idx = j
                break
        if hold_idx < exit_idx:
            exit_idx = hold_idx
            reason = "max-hold"
        elif exit_sig is not None:
            reason = "signal-exit"
        else:
            reason = "end-of-data"
        raw_exit = float(closes[exit_idx])
        exit_price = raw_exit * (1.0 - slippage_rate)
        window_high = np.concatenate(([entry_price], highs[entry_idx:exit_idx + 1]))
        window_low = np.concatenate(([entry_price], lows[entry_idx:exit_idx + 1]))
        max_price = float(np.max(window_high))
        min_price = float(np.min(window_low))
        fees = position_size * fee_rate * 2.0
        quantity = position_size / entry_price if entry_price > 0 else 0.0
        pnl = quantity * exit_price - position_size - fees
        pnl_percent = pnl / position_size * 100.0 if position_size > 0 else 0.0
        mae_pct = (entry_price - min_price) / entry_price * 100.0 if entry_price > 0 else 0.0
        mfe_pct = (max_price - entry_price) / entry_price * 100.0 if entry_price > 0 else 0.0
        trades.append(Trade(
            symbol=symbol,
            entry_time=pd.Timestamp(datetimes[entry_idx]),
            exit_time=pd.Timestamp(datetimes[exit_idx]),
            entry_price=entry_price,
            exit_price=exit_price,
            max_price_during_trade=max_price,
            min_price_during_trade=min_price,
            pnl=float(pnl),
            pnl_percent=float(pnl_percent),
            fees=float(fees),
            reason=reason,
            x_percent=float(x),
            y_seconds=int(y),
            z_percent=float(z),
            mae_pct=float(mae_pct),
            mfe_pct=float(mfe_pct),
        ))
        k += 2 if exit_sig is not None else 1
    return trades


class BreakoutStrategy(TradingStrategy):
    """Template breakout v3 §5.4 (LONG-ONLY): entry sopra max N periodi, stop %."""

    def parameter_space(self) -> Dict[str, Tuple]:
        return {
            "lookback_period": (5, 60, "int"),
            "stop_loss_pct": (0.5, 5.0, "float"),
        }

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> List[Signal]:
        lookback = int(params["lookback_period"])
        stop_pct = float(params["stop_loss_pct"])
        closes = df["close"]
        prev_high = closes.rolling(lookback, min_periods=lookback).max().shift(1)
        use_datetime = "datetime" in df.columns
        signals: List[Signal] = []
        in_position = False
        entry_price = 0.0
        for i in range(len(df)):
            ref = prev_high.iloc[i]
            if pd.isna(ref):
                continue
            price = float(closes.iloc[i])
            ts = pd.Timestamp(df["datetime"].iloc[i]) if use_datetime else pd.Timestamp(i)
            if not in_position and price > float(ref):
                signals.append(Signal(timestamp=ts, type="ENTRY", side="LONG",
                                      price=price, reason="breakout_high"))
                in_position = True
                entry_price = price
            elif in_position and price <= entry_price * (1.0 - stop_pct / 100.0):
                signals.append(Signal(timestamp=ts, type="EXIT", side="LONG",
                                      price=price, reason="stop-loss"))
                in_position = False
        return signals

    def validate(self, params: Dict) -> bool:
        try:
            return int(params["lookback_period"]) >= 1 and float(params["stop_loss_pct"]) > 0
        except (KeyError, TypeError, ValueError):
            return False

    def gpu_param_arrays(self, param_grid: List[Dict]) -> Dict[str, np.ndarray]:
        return {
            "lookback_period": np.array([int(d["lookback_period"]) for d in param_grid],
                                        dtype=np.int64),
            "stop_loss_pct": np.array([float(d["stop_loss_pct"]) for d in param_grid],
                                      dtype=np.float64),
        }

    def run_backtest(self, df: pd.DataFrame, params: Dict, symbol: str) -> List[Trade]:
        lookback = int(params["lookback_period"])
        stop_pct = float(params["stop_loss_pct"])
        signals = self.generate_signals(df, params)
        if not signals:
            return []
        return _pair_signals_to_long_trades(
            df, signals, symbol,
            position_size=float(params.get("position_size", 100.0)),
            fee_rate=float(params.get("fee_rate", 0.001)),
            slippage_rate=float(params.get("slippage_rate", 0.0005)),
            max_hold_seconds=int(params.get("max_hold_seconds", 600)),
            x=stop_pct, y=lookback, z=stop_pct,
        )


class GridStrategy(TradingStrategy):
    """Template grid v3 §5.4 (LONG-ONLY): compra -1 step, vendi +1 step di griglia."""

    def parameter_space(self) -> Dict[str, Tuple]:
        return {
            "grid_levels": (5, 20, "int"),
            "grid_spacing_pct": (0.1, 2.0, "float"),
        }

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> List[Signal]:
        spacing_pct = float(params["grid_spacing_pct"])
        closes = df["close"]
        if len(closes) == 0:
            return []
        anchor = float(closes.iloc[0])
        if anchor <= 0 or spacing_pct <= 0:
            return []
        step = anchor * spacing_pct / 100.0
        use_datetime = "datetime" in df.columns
        signals: List[Signal] = []
        in_position = False
        ref_k = 0
        entry_k = 0
        for i in range(len(df)):
            price = float(closes.iloc[i])
            k = int(round((price - anchor) / step))
            ts = pd.Timestamp(df["datetime"].iloc[i]) if use_datetime else pd.Timestamp(i)
            if not in_position and k <= ref_k - 1:
                signals.append(Signal(timestamp=ts, type="ENTRY", side="LONG",
                                      price=price, reason="grid_buy"))
                in_position = True
                entry_k = k
            elif in_position and k >= entry_k + 1:
                signals.append(Signal(timestamp=ts, type="EXIT", side="LONG",
                                      price=price, reason="grid_sell"))
                in_position = False
                ref_k = k
        return signals

    def validate(self, params: Dict) -> bool:
        try:
            return int(params["grid_levels"]) >= 2 and float(params["grid_spacing_pct"]) > 0
        except (KeyError, TypeError, ValueError):
            return False

    def gpu_param_arrays(self, param_grid: List[Dict]) -> Dict[str, np.ndarray]:
        return {
            "grid_levels": np.array([int(d["grid_levels"]) for d in param_grid],
                                    dtype=np.int64),
            "grid_spacing_pct": np.array([float(d["grid_spacing_pct"]) for d in param_grid],
                                         dtype=np.float64),
        }

    def run_backtest(self, df: pd.DataFrame, params: Dict, symbol: str) -> List[Trade]:
        signals = self.generate_signals(df, params)
        if not signals:
            return []
        spacing = float(params["grid_spacing_pct"])
        return _pair_signals_to_long_trades(
            df, signals, symbol,
            position_size=float(params.get("position_size", 100.0)),
            fee_rate=float(params.get("fee_rate", 0.001)),
            slippage_rate=float(params.get("slippage_rate", 0.0005)),
            max_hold_seconds=int(params.get("max_hold_seconds", 600)),
            x=spacing, y=int(params["grid_levels"]), z=spacing,
        )


def _entry(strategy: TradingStrategy, entry_condition: str, exit_condition: str,
           optional_filters: List[str], archetype: str, variant: str) -> Dict[str, Any]:
    """Voce di registry: spazio riusato dalla strategia (mai duplicato a mano)."""
    return {
        "strategy": strategy,
        "parameters": strategy.parameter_space(),
        "entry_condition": entry_condition,
        "exit_condition": exit_condition,
        "optional_filters": list(optional_filters),
        "archetype": archetype,  # genoma v3 §4.3, Level 0
        "variant": variant,      # genoma v3 §4.3, Level 1
    }


TEMPLATE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "momentum_drop": _entry(
        MomentumDropStrategy(),
        entry_condition="price_rose_X_pct_in_Y_seconds",
        exit_condition="price_dropped_Z_pct_from_high",
        optional_filters=["min_volume", "time_filter"],
        archetype="momentum", variant="threshold",
    ),
    "mean_reversion_zscore": _entry(
        MeanReversionZScore(),
        entry_condition="price_below_Z_std_of_MA",
        exit_condition="price_returned_to_MA",
        optional_filters=["trend_filter", "volume_filter"],
        archetype="mean_reversion", variant="zscore",
    ),
    "breakout": _entry(
        BreakoutStrategy(),
        entry_condition="price_above_N_period_high",
        exit_condition="price_below_entry_minus_Z_pct",
        optional_filters=["confirmation_candles", "volume_spike"],
        archetype="breakout", variant="donchian",
    ),
    "grid": _entry(
        GridStrategy(),
        entry_condition="price_at_grid_level",
        exit_condition="price_reached_opposite_grid",
        optional_filters=["trend_filter", "volatility_filter"],
        archetype="grid", variant="fixed_spacing",
    ),
}


def generate_from_template(name: str, rng: np.random.Generator) -> Dict[str, Any]:
    """Genera un dict parametri valido per il template (KeyError se ignoto).

    Campiona uniformemente dallo spazio del template e valida via
    strategy.validate; riprova fino a _MAX_GENERATE_ATTEMPTS (il sampling
    resta nei bounds, quindi il primo tentativo passa quasi sempre).
    Seed fissato su rng -> output riproducibile.
    """
    entry = TEMPLATE_REGISTRY[name]  # KeyError intenzionale per nomi ignoti
    strategy: TradingStrategy = entry["strategy"]
    space = strategy.parameter_space()
    for _ in range(_MAX_GENERATE_ATTEMPTS):
        params = sample_from_space(space, rng)
        try:
            if strategy.validate(params):
                return params
        except Exception:
            continue
    raise RuntimeError(f"generate_from_template({name!r}): nessun params valido "
                       f"in {_MAX_GENERATE_ATTEMPTS} tentativi")
