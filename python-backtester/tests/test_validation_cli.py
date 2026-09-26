"""CLI validation-mode + holdout F3-V07."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta

import main
from main import (
    _resolve_validation_mode,
    evaluate_holdout_once,
    parse_args,
    run_cpcv_trade_proxy,
    select_engine_df,
    split_holdout,
)
from src.metrics import calculate_metrics
from src.strategy import BacktestParams, Trade


def _daily_df(n=400, start="2023-01-01"):
    dates = pd.date_range(start, periods=n, freq="D")
    rng = np.random.default_rng(5)
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.005, n)))
    return pd.DataFrame({"datetime": dates, "close": closes})


def _results(n_trades=12, direction="long"):
    base = datetime(2023, 1, 1)
    trades = [
        Trade(
            symbol="T", entry_time=base + timedelta(days=i),
            exit_time=base + timedelta(days=i, hours=12),
            entry_price=100.0, exit_price=100.0 + v,
            max_price_during_trade=101.0, min_price_during_trade=99.0,
            pnl=v, pnl_percent=v, fees=0.0, reason="end-of-data",
            x_percent=0.5, y_seconds=30, z_percent=0.2,
        )
        for i, v in enumerate([1.0, -0.5] * (n_trades // 2))
    ]
    params = BacktestParams(
        x_percent=0.5, y_seconds=30, z_percent=0.2, max_hold_seconds=300,
        initial_capital=1000, position_size=100, fee_rate=0.0,
        slippage_rate=0.0, direction=direction,
    )
    return [calculate_metrics(trades, params, "T")]


class TestValidationModeCli:
    def test_default_off(self):
        assert _resolve_validation_mode(parse_args([])) == "off"

    def test_all_modes(self):
        for m in ("off", "purged", "cpcv", "walkforward"):
            assert _resolve_validation_mode(parse_args(["--validation-mode", m])) == m

    def test_invalid_choice_exits(self):
        with pytest.raises(SystemExit):
            parse_args(["--validation-mode", "bogus"])

    def test_env_and_cli_precedence(self, monkeypatch):
        monkeypatch.setenv("VALIDATION_MODE", "walkforward")
        assert _resolve_validation_mode(parse_args([])) == "walkforward"
        assert (
            _resolve_validation_mode(parse_args(["--validation-mode", "cpcv"]))
            == "cpcv"
        )

    def test_invalid_env_exits(self, monkeypatch):
        monkeypatch.setenv("VALIDATION_MODE", "bogus")
        with pytest.raises(SystemExit):
            _resolve_validation_mode(parse_args([]))


class TestHoldout:
    def test_off_is_identity(self):
        df = _daily_df()
        assert select_engine_df(df, "off") is df

    def test_holdout_never_touched(self):
        df = _daily_df(400)
        work, hold = split_holdout(df)
        assert len(work) > 0 and len(hold) > 0
        assert work["datetime"].max() < hold["datetime"].min()
        span_days = (df["datetime"].max() - df["datetime"].min()).days
        assert span_days - (hold["datetime"].max() - hold["datetime"].min()).days > 100

    def test_short_span_fallback(self):
        df = _daily_df(30)
        work, hold = split_holdout(df)
        assert len(hold) == 0  # span < 6 mesi: niente holdout

    def test_reuse_warns(self, capsys):
        df = _daily_df(400)
        _, hold = split_holdout(df)
        key = "T:mom:reuse-test"
        main._HOLDOUT_USED_KEYS.discard(key)
        first = evaluate_holdout_once(hold, key)
        assert first["reused"] is False
        second = evaluate_holdout_once(hold, key)
        assert second["reused"] is True
        out = capsys.readouterr().out
        assert "WARNING" in out and "INVALIDA" in out


class TestCpcvProxy:
    def test_produces_pbo_and_dsr(self, capsys):
        out = run_cpcv_trade_proxy(_results(12), n_trials=27)
        assert out["mode"] == "cpcv"
        assert out["pbo"] is not None and 0.0 <= out["pbo"] <= 1.0
        assert np.isfinite(out["dsr"])
        assert out["gate"]["decision"] in ("ACCEPT", "CONDITIONAL", "REJECT")
        assert "N_trials=27" in out["gate"]["log_line"]

    def test_too_few_trades(self):
        out = run_cpcv_trade_proxy(_results(4), n_trials=4)
        assert out["pbo"] is None
