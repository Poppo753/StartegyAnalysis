"""PurgedKFold F3-V02: controllo esaustivo no-overlap + embargo gap."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest

from src.validation.cross_validator import PurgedKFold


def _assert_no_overlap(train_idx, test_idx, horizon):
    ts, te = int(test_idx[0]), int(test_idx[-1]) + 1
    for i in train_idx:
        i = int(i)
        overlaps = (i < te) and (i + horizon > ts)
        assert not overlaps, f"train {i} label [{i},{i + horizon}) tocca test [{ts},{te})"


class TestPurgedKFold:
    def test_exhaustive_no_overlap_multiple_horizons(self):
        for horizon in (1, 5, 10):
            kf = PurgedKFold(n_splits=5, embargo_pct=0.02)
            X = np.arange(100)
            splits = list(kf.split(X, horizon=horizon))
            assert len(splits) == 5
            for train_idx, test_idx in splits:
                _assert_no_overlap(train_idx, test_idx, horizon)

    def test_embargo_gap_verified(self):
        n, embargo_pct = 100, 0.02
        embargo_len = int(n * embargo_pct)
        assert embargo_len == 2
        kf = PurgedKFold(n_splits=5, embargo_pct=embargo_pct)
        for train_idx, test_idx in kf.split(np.arange(n), horizon=1):
            te = int(test_idx[-1]) + 1
            embargo_zone = set(range(te, min(n, te + embargo_len)))
            assert not (set(int(i) for i in train_idx) & embargo_zone)

    def test_embargo_default_in_range(self):
        kf = PurgedKFold()
        assert 0.01 <= kf.embargo_pct <= 0.05

    def test_tests_cover_all_once(self):
        n = 100
        kf = PurgedKFold(n_splits=5)
        all_test = np.concatenate([t for _, t in kf.split(np.arange(n), horizon=1)])
        assert sorted(all_test.tolist()) == list(range(n))

    def test_purge_window_size(self):
        # horizon=10, primo test [0,20): nessun purge prima; secondo [20,40): purge [10,20).
        kf = PurgedKFold(n_splits=5, embargo_pct=0.0)
        splits = list(kf.split(np.arange(100), horizon=10))
        _, test0 = splits[0]
        assert int(test0[0]) == 0
        train1, test1 = splits[1]
        assert int(test1[0]) == 20
        for i in range(10, 20):
            assert i not in set(int(x) for x in train1)
        assert 9 in set(int(x) for x in train1)

    def test_datetime_boundary_no_timestamp_overlap(self):
        dates = pd.date_range("2024-01-01", periods=100, freq="min")
        # Duplicati a cavallo dei confini fold (run brevi, caso reale).
        dates = list(dates)
        dates[20] = dates[19]
        dates[60] = dates[59]
        df = pd.DataFrame({"datetime": pd.to_datetime(dates), "close": np.arange(100, dtype=float)})
        kf = PurgedKFold(n_splits=5, embargo_pct=0.0)
        for train_idx, test_idx in kf.split(df, horizon=1):
            # PurgedKFold usa train = tutti gli altri blocchi (prima E dopo
            # il test): l'invariante anti-leakage e` la disgiunzione dei
            # timestamp (mai condivisi), non l'ordinamento.
            train_ts = set(df["datetime"].iloc[train_idx].tolist())
            test_ts = set(df["datetime"].iloc[test_idx].tolist())
            assert not (train_ts & test_ts)

    def test_invalid_params(self):
        with pytest.raises(ValueError):
            PurgedKFold(n_splits=1)
        with pytest.raises(ValueError):
            PurgedKFold(embargo_pct=1.0)
        with pytest.raises(ValueError):
            list(PurgedKFold(n_splits=5).split(np.arange(10), horizon=-1))
