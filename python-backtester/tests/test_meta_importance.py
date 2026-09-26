"""F5-R01: RF importance finds the single true signal among noise."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest

from src.meta_analysis.feature_importance import (
    compute_importance,
    importance_for_labels,
    top_features,
)


@pytest.fixture(scope="module")
def synthetic():
    # 1 true signal + 5 noise (fixed seed, deterministic).
    rng = np.random.default_rng(9)
    n = 600
    signal = rng.normal(0, 1, n)
    noise = rng.normal(0, 1, (n, 5))
    X = pd.DataFrame(
        np.column_stack([signal, noise]),
        columns=["true_signal", *[f"noise_{i}" for i in range(5)]],
    )
    y = (signal > 0).astype(int)
    return X, y


class TestImportance:
    def test_true_signal_is_top1(self, synthetic):
        X, y = synthetic
        table = compute_importance(X, y)
        assert table["feature"].iloc[0] == "true_signal"
        assert top_features(table, 1) == ["true_signal"]

    def test_importances_sum_to_one(self, synthetic):
        X, y = synthetic
        table = compute_importance(X, y)
        assert table["importance"].sum() == pytest.approx(1.0)
        assert len(table) == 6

    def test_seed_deterministic(self, synthetic):
        X, y = synthetic
        a = compute_importance(X, y, seed=42)
        b = compute_importance(X, y, seed=42)
        pd.testing.assert_frame_equal(a, b)

    def test_alias_matches(self, synthetic):
        X, y = synthetic
        table = importance_for_labels(
            X.values, y, feature_names=list(X.columns), seed=42
        )
        assert table["feature"].iloc[0] == "true_signal"

    def test_bad_inputs_raise(self, synthetic):
        X, y = synthetic
        with pytest.raises(ValueError):
            compute_importance(X, np.ones(len(X), dtype=int))  # single class
        with pytest.raises(ValueError):
            compute_importance(X, [0, 1])  # length mismatch
        with pytest.raises(ValueError):
            compute_importance(X.iloc[:, :0], y)  # no columns
        bad = X.copy()
        bad.iloc[0, 0] = np.nan
        with pytest.raises(ValueError):
            compute_importance(bad, y)
        with pytest.raises(ValueError):
            compute_importance(X, (y * 2).tolist())  # not binary

    def test_no_bagging_stacking(self):
        src = pathlib.Path(__file__).resolve().parent.parent.joinpath(
            "src", "meta_analysis", "feature_importance.py"
        ).read_text()
        assert "BaggingClassifier" not in src
        assert "StackingClassifier" not in src
        assert "RandomForestClassifier" in src
