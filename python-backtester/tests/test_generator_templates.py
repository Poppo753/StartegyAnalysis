"""Test F4-G01: TEMPLATE_REGISTRY + generate_from_template."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from src.generator.strategy_generator import TEMPLATE_REGISTRY, generate_from_template
from src.strategies.mean_reversion import MeanReversionZScore
from src.strategies.momentum_drop import MomentumDropStrategy
from src.strategy_base import ALLOWED_PARAM_KINDS


class TestTemplateRegistry:
    def test_four_templates_registered(self):
        assert set(TEMPLATE_REGISTRY) == {
            "momentum_drop", "mean_reversion_zscore", "breakout", "grid"}

    def test_real_strategies_spaces_reused(self):
        # Gli spazi dei due template noti sono IDENTICI a quelli reali.
        assert (TEMPLATE_REGISTRY["momentum_drop"]["parameters"]
                == MomentumDropStrategy().parameter_space())
        assert (TEMPLATE_REGISTRY["mean_reversion_zscore"]["parameters"]
                == MeanReversionZScore().parameter_space())

    def test_breakout_grid_spaces_match_v3_54(self):
        # Valori esatti da masterplan v3 §5.4 (breakout/grid_trading).
        assert TEMPLATE_REGISTRY["breakout"]["parameters"] == {
            "lookback_period": (5, 60, "int"),
            "stop_loss_pct": (0.5, 5.0, "float"),
        }
        assert TEMPLATE_REGISTRY["grid"]["parameters"] == {
            "grid_levels": (5, 20, "int"),
            "grid_spacing_pct": (0.1, 2.0, "float"),
        }

    def test_all_kinds_follow_f1_convention(self):
        for name, entry in TEMPLATE_REGISTRY.items():
            for pname, (lo, hi, kind) in entry["parameters"].items():
                assert kind in ALLOWED_PARAM_KINDS, f"{name}.{pname}: {kind!r}"
                assert lo <= hi, f"{name}.{pname}: range invertito"


class TestGenerateFromTemplate:
    def test_100_generations_all_valid(self):
        rng = np.random.default_rng(7)
        names = list(TEMPLATE_REGISTRY)
        for i in range(100):
            name = names[i % len(names)]
            params = generate_from_template(name, rng)
            assert TEMPLATE_REGISTRY[name]["strategy"].validate(params), (name, params)

    def test_fixed_seed_reproducible(self):
        a = generate_from_template("momentum_drop", np.random.default_rng(42))
        b = generate_from_template("momentum_drop", np.random.default_rng(42))
        assert a == b

    def test_unknown_template_raises_keyerror(self):
        import pytest
        with pytest.raises(KeyError):
            generate_from_template("nope", np.random.default_rng(0))
