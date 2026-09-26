"""
data_loader.py - Caricamento dei file OHLC CSV generati dalla pipeline TypeScript

Re-exports load_ohlc_data from src.utils.trade_utils.
"""

from src.utils.trade_utils import load_ohlc_data, DataLoadError
from src.utils.trade_utils import _expected_candles, expected_candles

__all__ = ["load_ohlc_data", "DataLoadError", "_expected_candles", "expected_candles"]
