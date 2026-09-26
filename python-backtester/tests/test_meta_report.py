"""F5-A04: golden-dataset markdown report with expected key phrases."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src.meta_analysis.report import build_report, main

PROFILES = {
    "momentum_drop": {"win_rate": 55, "pnl_pct": 25, "sharpe": 1.8,
                      "trades": 120, "dd": 8},
    "mean_reversion_zscore": {"win_rate": 68, "pnl_pct": 12, "sharpe": 1.2,
                              "trades": 200, "dd": 5},
    "breakout": {"win_rate": 38, "pnl_pct": 30, "sharpe": 1.5,
                 "trades": 60, "dd": 15},
    "grid": {"win_rate": 75, "pnl_pct": 6, "sharpe": 0.8,
             "trades": 400, "dd": 3},
}


def _golden_dir(tmp_path):
    rng = np.random.default_rng(7)
    rows = []
    for name, p in PROFILES.items():
        for i in range(2):
            rows.append(
                {
                    "name": f"{name}_{i}",
                    "archetype": "",
                    "win_rate": p["win_rate"] + rng.normal(0, 1),
                    "pnl_pct": p["pnl_pct"] + rng.normal(0, 1),
                    "sharpe": p["sharpe"] + rng.normal(0, 0.05),
                    "trades": max(5, int(p["trades"] + rng.normal(0, 5))),
                    "dd": max(0.5, p["dd"] + rng.normal(0, 0.5)),
                }
            )
    # archetype left blank on purpose: report must infer it from names.
    pd.DataFrame(rows).to_csv(tmp_path / "strategies.csv", index=False)
    n = 500
    u = np.zeros(n)
    for t in range(1, n):
        u[t] = 0.4 * u[t - 1] + rng.normal(0, 0.001)
    close = 100 * np.exp(np.cumsum(0.002 + u))
    pd.DataFrame(
        {
            "datetime": pd.date_range("2026-01-01", periods=n, freq="min"),
            "open": close,
            "high": close * 1.001,
            "low": close * 0.999,
            "close": close,
            "volume": 10.0,
        }
    ).to_csv(tmp_path / "ohlc.csv", index=False)
    return str(tmp_path)


class TestGoldenReport:
    def test_key_phrases(self, tmp_path):
        d = _golden_dir(tmp_path)
        text = build_report(d)
        assert "Current regime: TRENDING" in text
        assert "Cluster" in text
        assert "momentum" in text
        assert "Top strategies" in text
        assert "Recommended allocation" in text
        assert "momentum_drop" in text

    def test_main_writes_out_file(self, tmp_path):
        d = _golden_dir(tmp_path)
        out = str(tmp_path / "report.md")
        text = main(["--results", d, "--out", out])
        assert os.path.isfile(out)
        with open(out, encoding="utf-8") as fh:
            assert fh.read() == text
        assert "Current regime" in text

    def test_missing_ohlc_degrades_gracefully(self, tmp_path):
        rng = np.random.default_rng(3)
        rows = [
            {"name": f"s{i}", "archetype": "momentum",
             "win_rate": 55, "pnl_pct": 10 + i, "sharpe": 1.0,
             "trades": 50, "dd": 5}
            for i in range(4)
        ]
        pd.DataFrame(rows).to_csv(tmp_path / "strategies.csv", index=False)
        text = build_report(str(tmp_path))
        assert "Current regime: UNKNOWN" in text
        assert "Recommended allocation" in text
