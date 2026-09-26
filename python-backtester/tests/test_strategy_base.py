"""Test per l'interfaccia TradingStrategy (F1-S01) + contratto GPU (F1-G01)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest

from src.strategy_base import (
    ALLOWED_PARAM_KINDS,
    GPU_METRIC_NAMES,
    Signal,
    TradingStrategy,
)


class _CompleteStrategy(TradingStrategy):
    def parameter_space(self):
        return {
            "x_percent": (0.01, 2.0, "float"),
            "y_seconds": (5, 120, "int"),
        }

    def generate_signals(self, df, params):
        return []

    def validate(self, params):
        return True


class _MissingValidateStrategy(TradingStrategy):
    """Classe fittizia senza un metodo astratto (validate) → non istanziabile."""

    def parameter_space(self):
        return {"x_percent": (0.01, 2.0, "float")}

    def generate_signals(self, df, params):
        return []


class TestTradingStrategyBase:
    def test_missing_abstract_method_not_instantiable(self):
        with pytest.raises(TypeError):
            _MissingValidateStrategy()

    def test_parameter_space_uses_only_allowed_kinds(self):
        space = _CompleteStrategy().parameter_space()
        assert isinstance(space, dict) and len(space) > 0
        for name, spec in space.items():
            assert isinstance(spec, tuple) and len(spec) == 3, name
            lo, hi, kind = spec
            assert kind in ALLOWED_PARAM_KINDS, f"{name}: kind {kind!r} non ammesso"
            assert kind in ("float", "int", "float_log", "int_log")
            assert lo <= hi

    def test_score_default_no_trades(self):
        class _R:
            total_trades = 0

        assert _CompleteStrategy().score(_R()) == -999.0


def _sample_grid(strategy, n=4):
    """Costruisce una griglia valida alternando lo/hi dello spazio dichiarato."""
    space = strategy.parameter_space()
    grid = []
    for i in range(n):
        row = {}
        for name, (lo, hi, kind) in space.items():
            bound = lo if i % 2 == 0 else hi
            row[name] = int(bound) if kind in ("int", "int_log") else float(bound)
        grid.append(row)
    return grid


class TestGpuContract:
    @pytest.mark.parametrize("strategy_name", ["momentum_drop", "mean_reversion"])
    def test_gpu_param_arrays_typed_and_sized(self, strategy_name):
        from src.strategies import STRATEGY_REGISTRY

        cls = STRATEGY_REGISTRY[strategy_name]
        strategy = cls()
        grid = _sample_grid(strategy, n=4)
        arrays = strategy.gpu_param_arrays(grid)
        assert isinstance(arrays, dict) and len(arrays) > 0
        for key, arr in arrays.items():
            assert isinstance(arr, np.ndarray), key
            assert arr.dtype.kind in ("f", "i", "u"), f"{key}: dtype {arr.dtype} non tipizzato"
            assert arr.dtype.kind != "O", f"{key}: dtype object non ammesso nel path GPU"
            assert len(arr) == len(grid), f"{key}: lunghezza {len(arr)} != {len(grid)}"

    @pytest.mark.parametrize("strategy_name", ["momentum_drop", "mean_reversion"])
    def test_gpu_metric_names_fixed_length_8(self, strategy_name):
        from src.strategies import STRATEGY_REGISTRY

        cls = STRATEGY_REGISTRY[strategy_name]
        names = cls().gpu_metric_names()
        assert isinstance(names, list)
        assert len(names) == 8
        assert names == GPU_METRIC_NAMES
