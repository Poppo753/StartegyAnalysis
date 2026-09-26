"""Test per il modulo config del backtester."""
import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config, _parse_range, load_config, ConfigError


class TestParseRange:
    def test_float_range(self):
        result = _parse_range("0.5:2.0:0.1", cast_type="float", param_name="X_RANGE")
        assert len(result) > 0
        assert all(isinstance(v, float) for v in result)

    def test_int_range(self):
        result = _parse_range("10:60:10", cast_type="int", param_name="Y_RANGE")
        assert len(result) > 0
        assert all(isinstance(v, int) for v in result)

    def test_invalid_format(self):
        with pytest.raises(ConfigError):
            _parse_range("invalid", param_name="TEST")

    def test_step_zero(self):
        with pytest.raises(ConfigError):
            _parse_range("1:10:0", param_name="TEST")


class TestConfigDefaults:
    def test_config_dataclass_defaults(self):
        c = Config()
        assert c.timeframe == "1s"
        assert c.max_hold_seconds == 300
        assert c.initial_capital == 1000.0
        assert c.position_size == 100.0
        assert c.fee_rate == 0.001
        assert c.direction == "signal-only"
        assert c.backtest_engine == "standard"
