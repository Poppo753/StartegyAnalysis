"""Test F4-G03: StrategyMutation (ampiezza parametrizzata, rate default 0.05)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from src.generator.mutation import StrategyMutation
from src.generator.strategy_generator import TEMPLATE_REGISTRY


def _space(name):
    return TEMPLATE_REGISTRY[name]["strategy"].parameter_space()


class TestMutationDistribution:
    def test_float_mean_zero_within_bounds_1000_samples(self):
        space = {"x_percent": (0.01, 2.0, "float")}
        mut = StrategyMutation(rate=1.0, sigma_frac=0.10)
        rng = np.random.default_rng(21)
        deltas = []
        for _ in range(1000):
            out = mut.mutate({"x_percent": 1.0}, space, rng)
            assert 0.01 <= out["x_percent"] <= 2.0  # supporto nei bounds
            deltas.append(out["x_percent"] - 1.0)
        mean = float(np.mean(deltas))
        # sigma = 0.1*1.99 ~= 0.2; SE media ~= 0.006 -> |mean| < 0.05 larghissimo.
        assert abs(mean) < 0.05, mean

    def test_int_step_pm1_clipped(self):
        space = {"y_seconds": (5, 120, "int")}
        mut = StrategyMutation(rate=1.0)
        rng = np.random.default_rng(23)
        seen = set()
        for _ in range(500):
            out = mut.mutate({"y_seconds": 60}, space, rng)
            assert out["y_seconds"] in (59, 61), out
            seen.add(out["y_seconds"])
        assert seen == {59, 61}  # entrambe le direzioni occorrono
        # Clip al bordo: da 5 si puo' solo salire, da 120 solo scendere.
        assert mut.mutate({"y_seconds": 5}, space,
                          np.random.default_rng(0))["y_seconds"] in (5, 6)
        assert mut.mutate({"y_seconds": 120}, space,
                          np.random.default_rng(1))["y_seconds"] in (119, 120)

    def test_categorical_swap(self):
        space = {"direction": (("long", "short", "signal-only"), None, "categorical")}
        mut = StrategyMutation(rate=1.0)
        rng = np.random.default_rng(29)
        outs = {mut.mutate({"direction": "long"}, space, rng)["direction"]
                for _ in range(50)}
        assert outs <= {"short", "signal-only"}  # swap: mai identico
        assert outs == {"short", "signal-only"}

    def test_default_rate_005(self):
        assert StrategyMutation().rate == 0.05
        space = {"x_percent": (0.01, 2.0, "float")}
        mut = StrategyMutation()  # rate default
        rng = np.random.default_rng(31)
        n_mut = sum(
            mut.mutate({"x_percent": 1.0}, space, rng)["x_percent"] != 1.0
            for _ in range(2000))
        frac = n_mut / 2000
        assert 0.02 <= frac <= 0.08, frac  # ~=5% (intervallo largo ma vincolante)

    def test_input_not_mutated_in_place(self):
        space = _space("momentum_drop")
        mut = StrategyMutation(rate=1.0)
        orig = {"x_percent": 1.0, "y_seconds": 60, "z_percent": 0.5,
                "max_hold_seconds": 300, "position_size": 100.0,
                "fee_rate": 0.001, "slippage_rate": 0.0005}
        snapshot = dict(orig)
        mut.mutate(orig, space, np.random.default_rng(33))
        assert orig == snapshot
