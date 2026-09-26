"""Walk-forward F3-V06: finestre, report per-periodo, sanity flat."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src.validation.walk_forward import WalkForwardValidator


def _make_ohlc(dates, closes):
    closes = np.asarray(closes, dtype=float)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    highs = np.maximum(opens, closes) * 1.001
    lows = np.minimum(opens, closes) * 0.999
    df = pd.DataFrame(
        {
            "datetime": pd.to_datetime(dates),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": np.full(len(closes), 1000.0),
            "tradeCount": np.full(len(closes), 10),
        }
    )
    df["timestamp"] = df["datetime"]
    df["epoch_seconds"] = (df["datetime"].astype("int64") // 10**9).astype(int)
    return df


def _driftless_walk(n=425, seed=3):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0, 0.01, n)
    return 100.0 * np.exp(np.cumsum(rets))


class TestWalkForwardWindows:
    def test_14_months_gives_periods_and_embargo(self):
        dates = pd.date_range("2023-01-01", periods=425, freq="D")
        df = _make_ohlc(dates, _driftless_walk(425))
        wf = WalkForwardValidator()
        windows = wf.generate_windows(df)
        assert len(windows) >= 5
        for train_df, test_df in windows:
            tr_e = pd.to_datetime(train_df["datetime"].iloc[-1])
            te_s = pd.to_datetime(test_df["datetime"].iloc[0])
            assert (te_s - tr_e).days >= 14  # embargo 0.5m rispettato
        # Test non sovrapposti e ordinati.
        starts = [pd.to_datetime(t["datetime"].iloc[0]) for _, t in windows]
        assert starts == sorted(starts)

    def test_parametrizable(self):
        wf = WalkForwardValidator(train_months=3, test_months=1, embargo_months=0.25)
        dates = pd.date_range("2023-01-01", periods=425, freq="D")
        df = _make_ohlc(dates, _driftless_walk(425))
        assert len(wf.generate_windows(df)) >= 8


class TestWalkForwardReport:
    def test_flat_sanity_profitability_half(self):
        # Strategia piatta (sempre long) su random walk senza drift:
        # ~50% dei periodi in profitto (sanity, non edge).
        dates = pd.date_range("2023-01-01", periods=425, freq="D")
        df = _make_ohlc(dates, _driftless_walk(425, seed=3))
        wf = WalkForwardValidator()
        report = wf.run(df, evaluate_fn=lambda t: float(t["close"].pct_change().fillna(0).sum() * 100.0))
        assert report["n_periods"] >= 5
        assert len(report["per_period"]) == report["n_periods"]
        assert 0.3 <= report["profitability_rate"] <= 0.7
        assert "dsr" in report and "pbo" in report

    def test_run_strategy_fixed_params(self):
        from src.strategies.mean_reversion import MeanReversionZScore

        t = np.arange(425)
        closes = 100.0 + 5.0 * np.sin(2 * np.pi * t / 30.0)
        dates = pd.date_range("2023-01-01", periods=425, freq="D")
        df = _make_ohlc(dates, closes)
        wf = WalkForwardValidator()
        base = {
            "ma_period": 10,
            "z_threshold": 1.0,
            "max_hold_seconds": 86400 * 5,
            "initial_capital": 1000.0,
            "position_size": 100.0,
            "fee_rate": 0.0,
            "slippage_rate": 0.0,
            "direction": "long",
        }
        report = wf.run_strategy(df, MeanReversionZScore(), base, symbol="WF")
        assert report["n_periods"] >= 5
        assert report["bo_trials_per_window"] == 0
        for p in report["per_period"]:
            assert "oos_pnl" in p and "n_trades" in p

    def test_run_strategy_bo_smoke(self):
        from src.strategies.mean_reversion import MeanReversionZScore

        t = np.arange(425)
        closes = 100.0 + 5.0 * np.sin(2 * np.pi * t / 30.0)
        dates = pd.date_range("2023-01-01", periods=425, freq="D")
        df = _make_ohlc(dates, closes)
        wf = WalkForwardValidator(train_months=6, test_months=2, embargo_months=0.5)
        base = {
            "max_hold_seconds": 86400 * 5,
            "initial_capital": 1000.0,
            "position_size": 100.0,
            "fee_rate": 0.0,
            "slippage_rate": 0.0,
            "direction": "long",
        }
        report = wf.run_strategy(
            df, MeanReversionZScore(), base, symbol="WF", n_trials=3, seed=11
        )
        assert report["n_periods"] >= 1
        assert report["bo_trials_per_window"] == 3
