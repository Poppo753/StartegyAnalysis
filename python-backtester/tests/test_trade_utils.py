"""Test enterprise per trade_utils (load_trades / calc_metrics)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest

from src.utils.trade_utils import DataLoadError, calc_metrics, load_trades


def test_load_trades_missing_file():
    with pytest.raises(DataLoadError):
        load_trades("non_existent_trades_xyz.csv", ["pnl"])


def test_load_trades_missing_columns(tmp_path):
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    path = tmp_path / "trades.csv"
    df.to_csv(path, index=False)
    with pytest.raises(DataLoadError):
        load_trades(str(path), ["a", "missing_col"])


def test_calc_metrics_empty():
    assert calc_metrics(np.array([]), 1000.0) == {}


def test_calc_metrics_basic():
    pnls = np.array([10.0, -5.0, 20.0])
    m = calc_metrics(pnls, 1000.0)
    assert m["n"] == 3
    assert m["nw"] == 2
    assert m["nl"] == 1
    assert m["wr"] == pytest.approx(2 / 3 * 100.0)
    assert m["total"] == pytest.approx(25.0)
