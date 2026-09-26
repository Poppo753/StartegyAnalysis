"""Test per il data_splitter."""
import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from src.gpu.data_splitter import split_train_validation


class TestSplitTrainValidation:
    def test_basic_split(self):
        dates = pd.date_range('2024-01-01', periods=10, freq='s', tz='UTC')
        df = pd.DataFrame({'datetime': dates, 'close': range(10)})
        train, val = split_train_validation(df, train_ratio=0.7)
        assert len(train) == 7
        assert len(val) == 3
        assert train['datetime'].max() < val['datetime'].min()

    def test_no_overlap(self):
        dates = pd.date_range('2024-01-01', periods=100, freq='s', tz='UTC')
        df = pd.DataFrame({'datetime': dates, 'close': range(100)})
        train, val = split_train_validation(df, train_ratio=0.7)
        assert len(train) > 0
        assert len(val) > 0
        assert train['datetime'].max() < val['datetime'].min()

    def test_small_dataframe(self):
        dates = pd.date_range('2024-01-01', periods=2, freq='s', tz='UTC')
        df = pd.DataFrame({'datetime': dates, 'close': [1, 2]})
        train, val = split_train_validation(df, train_ratio=0.7)
        assert len(train) >= 1

    def test_empty_dataframe(self):
        with pytest.raises(ValueError):
            split_train_validation(pd.DataFrame(), train_ratio=0.7)

    def test_sorted_chronologically(self):
        dates = pd.to_datetime(['2024-01-02', '2024-01-01', '2024-01-03'])
        df = pd.DataFrame({'datetime': dates, 'close': [2, 1, 3]})
        train, val = split_train_validation(df, train_ratio=0.5)
        assert train['datetime'].is_monotonic_increasing
        assert val['datetime'].is_monotonic_increasing

    # --- F0-01 regression: split must be datetime-based, never index-based ---
    def test_datetime_based_month_year_boundary(self):
        # Spans month AND year boundary: Dec 2023 -> Jan 2024
        dates = pd.date_range('2023-12-28', periods=20, freq='D', tz='UTC')
        df = pd.DataFrame({'datetime': dates, 'close': range(20)})
        # Shuffle input: index-based split without sort would leak
        df_shuffled = df.sample(frac=1, random_state=7).reset_index(drop=True)
        train, val = split_train_validation(df_shuffled, train_ratio=0.7)
        assert len(train) > 0 and len(val) > 0
        assert train['datetime'].max() < val['datetime'].min()
        assert len(train) + len(val) == len(df)
        assert set(train['datetime']).isdisjoint(set(val['datetime']))

    def test_datetime_based_with_time_gaps(self):
        # Two blocks with a ~1-month gap (missing data / market halt)
        block1 = pd.date_range('2024-01-01', periods=10, freq='D', tz='UTC')
        block2 = pd.date_range('2024-03-01', periods=10, freq='D', tz='UTC')
        dates = block1.append(block2)
        df = pd.DataFrame({'datetime': dates, 'close': range(len(dates))})
        df_shuffled = df.sample(frac=1, random_state=11).reset_index(drop=True)
        train, val = split_train_validation(df_shuffled, train_ratio=0.7)
        assert len(train) > 0 and len(val) > 0
        assert train['datetime'].max() < val['datetime'].min()
        assert len(train) + len(val) == len(df)
        assert set(train['datetime']).isdisjoint(set(val['datetime']))

    def test_regression_duplicate_timestamp_at_boundary(self):
        # n=10, ratio=0.7 -> split_idx=7. Duplicate t6 at positions 6 and 7
        # so a naive iloc[:7]/iloc[7:] split would put the same timestamp
        # in both sets (max == min -> leakage). Data-based split must move
        # the whole run into VALIDATION (train ends at t5).
        base = pd.date_range('2024-03-01', periods=10, freq='s', tz='UTC')
        dts = list(base)
        dts[7] = dts[6]
        df = pd.DataFrame({'datetime': dts, 'close': range(10)})
        df_sorted = df.sort_values('datetime').reset_index(drop=True)
        # Prove the test is sensitive: naive index split DOES leak here
        naive_train = df_sorted.iloc[:7]
        naive_val = df_sorted.iloc[7:]
        assert naive_train['datetime'].max() == naive_val['datetime'].min()
        # Shuffled input must still split by datetime, not by position
        df_shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)
        train, val = split_train_validation(df_shuffled, train_ratio=0.7)
        assert train['datetime'].max() < val['datetime'].min()
        assert set(train['datetime']).isdisjoint(set(val['datetime']))
        assert len(train) + len(val) == len(df)
