"""
mia.py - Strategia Mia.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

from src.strategy import BacktestParams, Trade
from src.strategy_base import Signal, TradingStrategy


class MiaStrategy(TradingStrategy):
    """Una riga di descrizione: cosa compra e cosa vende."""

    def parameter_space(self) -> Dict[str, Tuple]:
        return {
            "lookback": (10, 200, "int"),
            "soglia": (0.5, 3.0, "float"),
            "max_hold_seconds": (60, 1800, "int"),
            "position_size": (10.0, 1000.0, "float"),
        }

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> List[Signal]:
        lookback = int(params["lookback"])
        soglia = float(params["soglia"])

        work = df.copy()
        work["ma"] = work["close"].rolling(lookback).mean()
        work["std"] = work["close"].rolling(lookback).std()
        work["z"] = (work["close"] - work["ma"]) / work["std"]

        use_datetime = "datetime" in work.columns
        signals: List[Signal] = []
        in_position = False

        for idx, row in work.iterrows():
            z = row["z"]
            # salta il warmup: MA/std NaN o std == 0
            if pd.isna(z) or row["std"] == 0:
                continue
            timestamp = pd.Timestamp(row["datetime"]) if use_datetime else pd.Timestamp(idx)
            price = float(row["close"])

            if not in_position and z < -soglia:
                signals.append(Signal(
                    timestamp=timestamp, type="ENTRY", side="LONG",
                    price=price, reason=f"z={z:.2f}",
                ))
                in_position = True
            elif in_position and z > -0.1:
                signals.append(Signal(
                    timestamp=timestamp, type="EXIT", side="LONG",
                    price=price, reason="uscita",
                ))
                in_position = False

        return signals

    def validate(self, params: Dict) -> bool:
        try:
            return int(params["lookback"]) >= 5 and float(params["soglia"]) > 0
        except (KeyError, TypeError, ValueError):
            return False

    def gpu_param_arrays(self, param_grid: List[Dict]) -> Dict[str, np.ndarray]:
        """Opzionale ma raccomandato: parametri come array per il path GPU."""
        return {
            "lookback": np.array([int(d["lookback"]) for d in param_grid], dtype=np.int64),
            "soglia": np.array([float(d["soglia"]) for d in param_grid], dtype=np.float64),
        }
