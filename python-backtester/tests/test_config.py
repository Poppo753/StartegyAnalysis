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


def _set_valid_env(monkeypatch):
    """Baseline .env valido; i singoli test ne invalidano una chiave."""
    monkeypatch.setenv("SYMBOLS", "BTCUSDT")
    monkeypatch.setenv("START_DATE", "2024-01-01")
    monkeypatch.setenv("END_DATE", "2024-01-02")
    monkeypatch.setenv("X_VALUES", "0.5,1.0")
    monkeypatch.setenv("Y_VALUES", "10,30")
    monkeypatch.setenv("Z_VALUES", "0.5,1.0")
    monkeypatch.setenv("X_RANGE", "")
    monkeypatch.setenv("Y_RANGE", "")
    monkeypatch.setenv("Z_RANGE", "")
    monkeypatch.setenv("MAX_HOLD_SECONDS", "300")
    monkeypatch.setenv("INITIAL_CAPITAL", "1000")
    monkeypatch.setenv("POSITION_SIZE", "100")
    monkeypatch.setenv("FEE_RATE", "0.001")
    monkeypatch.setenv("SLIPPAGE_RATE", "0.0005")
    monkeypatch.setenv("DIRECTION", "long")
    monkeypatch.setenv("BACKTEST_ENGINE", "standard")
    monkeypatch.setenv("FAST_TOP_N", "20")
    monkeypatch.setenv("GPU_BATCH_SIZE", "2048")
    monkeypatch.setenv("TRAIN_RATIO", "0.7")
    monkeypatch.setenv("VALIDATION_RATIO", "0.3")
    monkeypatch.setenv("MIN_TRADES", "20")
    monkeypatch.setenv("MIN_WIN_RATE", "40.0")
    monkeypatch.setenv("MIN_PROFIT_FACTOR", "1.2")
    monkeypatch.setenv("MAX_DRAWDOWN_FILTER", "30.0")
    monkeypatch.setenv("SKIP_FILTERS", "false")
    monkeypatch.setenv("Y_DYNAMIC", "false")
    monkeypatch.setenv("Y_MAX_WINDOW", "600")


def _assert_raises_config_error_never_exits(monkeypatch):
    """load_config() deve sollevare ConfigError, mai chiamare sys.exit."""
    monkeypatch.setattr(
        sys, "exit", lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("sys.exit called instead of raising ConfigError"))
    )
    with pytest.raises(ConfigError):
        load_config()
    # Prova esplicita che non sia SystemExit travestito
    try:
        load_config()
    except ConfigError:
        pass
    except SystemExit:
        pytest.fail("load_config() exited instead of raising ConfigError")


class TestLoadConfigInvalidEnv:
    def test_missing_symbols_raises_never_exits(self, monkeypatch):
        _set_valid_env(monkeypatch)
        monkeypatch.setenv("SYMBOLS", "")
        _assert_raises_config_error_never_exits(monkeypatch)

    def test_bad_date_format_raises_never_exits(self, monkeypatch):
        _set_valid_env(monkeypatch)
        monkeypatch.setenv("START_DATE", "01-01-2024")
        _assert_raises_config_error_never_exits(monkeypatch)

    def test_non_numeric_x_values_raises_never_exits(self, monkeypatch):
        _set_valid_env(monkeypatch)
        monkeypatch.setenv("X_VALUES", "abc,1.0")
        _assert_raises_config_error_never_exits(monkeypatch)

    def test_invalid_direction_raises_never_exits(self, monkeypatch):
        _set_valid_env(monkeypatch)
        monkeypatch.setenv("DIRECTION", "sideways")
        _assert_raises_config_error_never_exits(monkeypatch)

    def test_config_error_is_value_error_not_system_exit(self):
        assert issubclass(ConfigError, ValueError)
        assert not issubclass(ConfigError, SystemExit)


class TestStrategiesEnv:
    def test_default_is_momentum_drop(self, monkeypatch):
        _set_valid_env(monkeypatch)
        monkeypatch.delenv("STRATEGIES", raising=False)
        assert load_config().strategies == ["momentum_drop"]

    def test_two_strategies_parsed(self, monkeypatch):
        _set_valid_env(monkeypatch)
        monkeypatch.setenv("STRATEGIES", "momentum_drop, mean_reversion")
        assert load_config().strategies == ["momentum_drop", "mean_reversion"]

    def test_empty_strategies_falls_back_to_default(self, monkeypatch):
        _set_valid_env(monkeypatch)
        monkeypatch.setenv("STRATEGIES", "  ")
        assert load_config().strategies == ["momentum_drop"]


class TestMeanReversionGridEnv:
    def test_grid_values_are_configurable(self, monkeypatch):
        _set_valid_env(monkeypatch)
        monkeypatch.setenv("MA_PERIODS", "12,24,48")
        monkeypatch.setenv("Z_THRESHOLDS", "0.75,1.5")
        config = load_config()
        assert config.ma_periods == [12, 24, 48]
        assert config.z_thresholds == [0.75, 1.5]

    def test_invalid_grid_values_fail(self, monkeypatch):
        _set_valid_env(monkeypatch)
        monkeypatch.setenv("MA_PERIODS", "1,20")
        with pytest.raises(ConfigError, match="MA_PERIODS"):
            load_config()
