"""
mean_reversion.py - Strategia MeanReversionZScore (F1-S03, logica v3 §5.3).

MA rolling, z-score, LONG-ONLY:
- entry: z_score < -z_threshold (prezzo sotto media → compra)
- exit: z_score > -0.1 (ritorno alla media → vendi)

Righe con MA/std NaN o std == 0 vengono saltate (warmup = ma_period righe).
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Union

from src.strategy import BacktestParams, Trade
from src.strategy_base import Signal, TradingStrategy

_EXIT_BAND = -0.1


class MeanReversionZScore(TradingStrategy):
    """Compra quando il prezzo è sotto media, aspetta ritorno alla media."""

    def parameter_space(self) -> Dict[str, Tuple]:
        return {
            "ma_period": (10, 200, "int"),
            "z_threshold": (0.5, 3.0, "float"),
            "max_hold_seconds": (60, 1800, "int"),
            "position_size": (10.0, 1000.0, "float"),
        }

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> List[Signal]:
        ma_period = int(params["ma_period"])
        z_threshold = float(params["z_threshold"])

        work = df.copy()
        work["ma"] = work["close"].rolling(ma_period).mean()
        work["std"] = work["close"].rolling(ma_period).std()
        work["z_score"] = (work["close"] - work["ma"]) / work["std"]

        use_datetime = "datetime" in work.columns
        signals: List[Signal] = []
        in_position = False

        for idx, row in work.iterrows():
            ma = row["ma"]
            std = row["std"]
            z = row["z_score"]
            if pd.isna(z) or pd.isna(ma) or pd.isna(std) or std == 0:
                continue
            if use_datetime:
                timestamp = pd.Timestamp(row["datetime"])
            else:
                timestamp = pd.Timestamp(idx)
            price = float(row["close"])
            if not in_position and z < -z_threshold:
                # Prezzo sotto media - compra (LONG-ONLY)
                signals.append(Signal(
                    timestamp=timestamp,
                    type="ENTRY",
                    side="LONG",
                    price=price,
                    reason=f"z_score={z:.2f}",
                ))
                in_position = True
            elif in_position and z > _EXIT_BAND:
                # Ritornato alla media - vendi
                signals.append(Signal(
                    timestamp=timestamp,
                    type="EXIT",
                    side="LONG",
                    price=price,
                    reason="mean_reversion",
                ))
                in_position = False

        return signals

    def validate(self, params: Dict) -> bool:
        try:
            return int(params["ma_period"]) >= 5 and float(params["z_threshold"]) > 0
        except (KeyError, TypeError, ValueError):
            return False

    def gpu_param_arrays(self, param_grid: List[Dict]) -> Dict[str, np.ndarray]:
        """Restituisce ma_period/z_threshold come array tipizzati."""
        return {
            "ma_period": np.array(
                [int(d["ma_period"]) for d in param_grid], dtype=np.int64
            ),
            "z_threshold": np.array(
                [float(d["z_threshold"]) for d in param_grid], dtype=np.float64
            ),
        }

    def run_backtest(
        self,
        df: pd.DataFrame,
        params: Dict,
        symbol: str,
    ) -> List[Trade]:
        """
        Esegue il backtest accoppiando i segnali ENTRY→EXIT (LONG-ONLY).

        Mappa i parametri su BacktestParams così Trade/metriche/writer restano
        riusabili: x_percent=z_threshold, y_seconds=ma_period,
        z_percent=|_EXIT_BAND|=0.1 (banda di uscita, costante).
        Rispetta max_hold_seconds (chiusura "max-hold") e chiude la posizione
        residua a fine dati ("end-of-data").
        """
        ma_period = int(params["ma_period"])
        max_hold_seconds = int(params.get("max_hold_seconds", 1800))
        position_size = float(params.get("position_size", 100.0))
        fee_rate = float(params.get("fee_rate", 0.001))
        slippage_rate = float(params.get("slippage_rate", 0.0005))

        backtest_params = BacktestParams(
            x_percent=float(params["z_threshold"]),
            y_seconds=ma_period,
            z_percent=abs(_EXIT_BAND),
            max_hold_seconds=max_hold_seconds,
            initial_capital=float(params.get("initial_capital", 1000.0)),
            position_size=position_size,
            fee_rate=fee_rate,
            slippage_rate=slippage_rate,
            direction="long",
        )

        signals = self.generate_signals(df, params)
        if not signals:
            return []

        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        datetimes = pd.to_datetime(df["datetime"]).values
        if "epoch_seconds" in df.columns:
            epoch_secs = df["epoch_seconds"].values.astype(float)
        else:
            epoch_secs = np.arange(len(df), dtype=float)

        # Indice per timestamp per ritrovare le candele di entry/exit
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
            entry_epoch = epoch_secs[entry_idx]
            raw_entry = float(closes[entry_idx])
            entry_price = raw_entry * (1.0 + slippage_rate)

            if exit_sig is not None:
                exit_idx = ts_to_idx.get(pd.Timestamp(exit_sig.timestamp), len(df) - 1)
            else:
                exit_idx = len(df) - 1

            # Impone max-hold: prima candela oltre il limite
            hold_idx = exit_idx
            for j in range(entry_idx + 1, len(df)):
                if epoch_secs[j] - entry_epoch >= max_hold_seconds:
                    hold_idx = j
                    break
            if hold_idx < exit_idx:
                exit_idx = hold_idx
                reason = "max-hold"
            elif exit_sig is not None:
                reason = "mean_reversion"
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
                x_percent=backtest_params.x_percent,
                y_seconds=backtest_params.y_seconds,
                z_percent=backtest_params.z_percent,
                mae_pct=float(mae_pct),
                mfe_pct=float(mfe_pct),
            ))
            # I segnali alternano sempre ENTRY/EXIT (flag in_position):
            # la coppia consumata è (ENTRY in k, EXIT in k+1) oppure solo ENTRY.
            k += 2 if exit_sig is not None else 1

        return trades
