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
