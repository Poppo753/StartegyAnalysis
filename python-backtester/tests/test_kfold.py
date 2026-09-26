"""Test enterprise per k_fold_split (finestra espandente, anti-leakage)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest

from src.gpu.data_splitter import k_fold_split


def make_df(n=21):
    dates = pd.date_range("2024-01-01", periods=n, freq="s", tz="UTC")
    return pd.DataFrame({"datetime": dates, "close": range(n)})


def test_kfold_returns_k_splits():
    df = make_df(21)
    k = 3
    folds = k_fold_split(df, k=k)
    assert len(folds) == k
    for train, val in folds:
        assert len(train) > 0
        assert len(val) > 0


def test_kfold_no_leakage():
    df = make_df(21)
    folds = k_fold_split(df, k=3)
    for train, val in folds:
        assert train["datetime"].max() < val["datetime"].min()


def test_kfold_expanding():
    df = make_df(21)
    folds = k_fold_split(df, k=3)
    # primo train non vuoto
    assert len(folds[0][0]) > 0
    # train cresce ad ogni fold
    sizes = [len(train) for train, _ in folds]
    for i in range(1, len(sizes)):
        assert sizes[i] > sizes[i - 1]


def test_kfold_invalid_k():
    df = make_df(21)
    with pytest.raises(ValueError):
        k_fold_split(df, k=1)
    with pytest.raises(ValueError):
        k_fold_split(df, k=0)
    with pytest.raises(ValueError):
        k_fold_split(df, k=-3)


def test_kfold_duplicate_timestamps():
    # Duplicato a cavallo di un possibile confine di fold:
    # stesso timestamp mai diviso tra train e val.
    df = make_df(21)
    # Forza un duplicato: riga 5 = stesso timestamp di riga 4
    df.loc[5, "datetime"] = df.loc[4, "datetime"]
    df = df.sort_values("datetime").reset_index(drop=True)
    folds = k_fold_split(df, k=3)
    assert len(folds) == 3
    for train, val in folds:
        assert train["datetime"].max() < val["datetime"].min()
        assert set(train["datetime"]).isdisjoint(set(val["datetime"]))
    # Il timestamp duplicato compare interamente in un solo lato per fold
    dup_ts = df.loc[4, "datetime"]
    for train, val in folds:
        in_train = (train["datetime"] == dup_ts).sum()
        in_val = (val["datetime"] == dup_ts).sum()
        assert not (in_train > 0 and in_val > 0)
