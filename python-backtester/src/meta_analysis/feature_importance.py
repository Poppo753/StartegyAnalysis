"""feature_importance.py - RandomForest feature->success importance (F5-R01).

Gate satisfied: Fase 6 closed (consumes engineered features as a plain
DataFrame; agnostic to which factory produced them). Uses ONLY
RandomForestClassifier (scikit-learn, pinned since F5-A02) — NO
separate Bagging/Stacking meta-ensembles (forbidden §13: redundant with
CPCV/Walk-Forward, prerequisiti lontani).

"Per strategy": run once per strategy on its (features, success) pairs,
where success = 1 if the trade/params set was profitable, else 0.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np
import pandas as pd


def compute_importance(
    X: pd.DataFrame,
    y: Sequence[int],
    seed: int = 42,
    n_estimators: int = 200,
) -> pd.DataFrame:
    """Rank features by RandomForest success-prediction importance.

    Args:
        X: feature frame (n rows, feature columns, no NaN/inf allowed).
        y: binary success labels (0/1), one per row.
        seed: RNG seed (deterministic importances).
        n_estimators: number of trees.

    Returns:
        DataFrame [feature, importance] sorted desc, importances sum to 1.
    """
    from sklearn.ensemble import RandomForestClassifier

    if not isinstance(X, pd.DataFrame) or X.shape[1] == 0:
        raise ValueError("X must be a non-empty DataFrame")
    arr = np.asarray(X, dtype=float)
    if not np.all(np.isfinite(arr)):
        raise ValueError("X contains NaN/inf")
    labels = np.asarray(list(y)).ravel()
    if labels.shape[0] != len(X):
        raise ValueError(
            f"X/y length mismatch: {len(X)} != {labels.shape[0]}"
        )
    if set(np.unique(labels)) - {0, 1, 0.0, 1.0}:
        raise ValueError("y must be binary (0/1 success labels)")
    if len(np.unique(labels)) < 2:
        raise ValueError("y needs both classes (all success or all failure)")
    clf = RandomForestClassifier(
        n_estimators=int(n_estimators), random_state=int(seed)
    )
    clf.fit(arr, labels.astype(int))
    total = float(np.sum(clf.feature_importances_))
    imp = (
        np.asarray(clf.feature_importances_, dtype=float) / total
        if total > 0
        else np.full(X.shape[1], 1.0 / X.shape[1])
    )
    table = pd.DataFrame({"feature": list(X.columns), "importance": imp})
    return table.sort_values("importance", ascending=False).reset_index(drop=True)


def top_features(table: pd.DataFrame, n: int = 5) -> List[str]:
    """Top-n feature names from a compute_importance table."""
    if "feature" not in table.columns:
        raise ValueError("expected a compute_importance table")
    return [str(f) for f in table["feature"].iloc[: max(1, int(n))]]


def importance_for_labels(
    features: pd.DataFrame,
    success: Sequence[int],
    feature_names: Optional[Sequence[str]] = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Thin alias mapping raw arrays to compute_importance (per-strategy)."""
    X = pd.DataFrame(np.asarray(features, dtype=float),
                     columns=list(feature_names) if feature_names else None)
    if feature_names is not None and X.shape[1] != len(list(feature_names)):
        raise ValueError("feature_names length mismatch")
    return compute_importance(X, success, seed=seed)
