"""Test per MeanReversionZScore (F1-S03, logica v3 §5.3, LONG-ONLY)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src.strategies.mean_reversion import MeanReversionZScore


def _make_df(close):
    n = len(close)
    close = np.asarray(close, dtype=float)
    dates = pd.date_range("2024-01-01", periods=n, freq="s", tz="UTC")
    return pd.DataFrame({
        "timestamp": dates.strftime("%Y-%m-%dT%H:%M:%S"),
        "open": close,
        "high": close * 1.0005,
        "low": close * 0.9995,
        "close": close,
        "volume": np.ones(n),
        "tradeCount": np.ones(n, dtype=int),
        "datetime": dates,
        "epoch_seconds": np.arange(n, dtype=float),
    })


class TestMeanReversionZScore:
    def test_validate_rejects(self):
        s = MeanReversionZScore()
        assert s.validate({"ma_period": 10, "z_threshold": 1.0}) is True
        assert s.validate({"ma_period": 4, "z_threshold": 1.0}) is False
        assert s.validate({"ma_period": 10, "z_threshold": 0.0}) is False
        assert s.validate({"ma_period": 10, "z_threshold": -1.0}) is False

    def test_monotone_rising_trend_zero_trades(self):
        # Trend monotono crescente: z-score resta positivo → nessun ENTRY long-only.
        df = _make_df(np.linspace(100.0, 200.0, 300))
        signals = MeanReversionZScore().generate_signals(
            df, {"ma_period": 20, "z_threshold": 1.0}
        )
        assert signals == []

    def test_sine_wave_entry_and_exit(self):
        # Sinusoide: discese sotto media (entry) + ritorni alla media (exit).
        t = np.arange(400)
        close = 100.0 + 5.0 * np.sin(2 * np.pi * t / 40.0)
        df = _make_df(close)
        signals = MeanReversionZScore().generate_signals(
            df, {"ma_period": 20, "z_threshold": 1.0}
        )
        entries = [s for s in signals if s.type == "ENTRY"]
        exits = [s for s in signals if s.type == "EXIT"]
        assert len(entries) >= 1
        assert len(exits) >= 1
        assert all(s.side == "LONG" for s in signals)

    def test_run_backtest_pairs_trades(self):
        t = np.arange(400)
        close = 100.0 + 5.0 * np.sin(2 * np.pi * t / 40.0)
        df = _make_df(close)
        trades = MeanReversionZScore().run_backtest(
            df,
            {"ma_period": 20, "z_threshold": 1.0, "max_hold_seconds": 1800,
             "position_size": 100.0, "fee_rate": 0.001, "slippage_rate": 0.0005},
            "TESTUSDT",
        )
        assert len(trades) >= 1
        for tr in trades:
            assert tr.exit_time >= tr.entry_time
