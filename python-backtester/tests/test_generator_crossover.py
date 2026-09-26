"""Test F4-G02: StrategyCrossover parametrico + strutturale."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from src.generator.crossover import StrategyCrossover
from src.generator.strategy_generator import TEMPLATE_REGISTRY, generate_from_template


def _space(name):
    return TEMPLATE_REGISTRY[name]["strategy"].parameter_space()


class TestParametricCrossover:
    def test_children_of_known_strategies_valid(self):
        rng = np.random.default_rng(11)
        xo = StrategyCrossover()
        for template in ("momentum_drop", "mean_reversion_zscore"):
            space = _space(template)
            pa = generate_from_template(template, rng)
            pb = generate_from_template(template, rng)
            for _ in range(20):
                child = xo.blend_params(pa, pb, space, rng)
                assert TEMPLATE_REGISTRY[template]["strategy"].validate(child), child
                for pname, (lo, hi, kind) in space.items():
                    if pname in child:
                        assert lo <= child[pname] <= hi, (pname, child[pname])

    def test_int_params_random_pick_from_parents(self):
        rng = np.random.default_rng(3)
        xo = StrategyCrossover()
        space = _space("momentum_drop")
        pa = {"y_seconds": 5, "max_hold_seconds": 60}
        pb = {"y_seconds": 120, "max_hold_seconds": 600}
        for _ in range(50):
            child = xo.blend_params(pa, pb, space, rng)
            assert child["y_seconds"] in (5, 120)
            assert child["max_hold_seconds"] in (60, 600)

    def test_float_child_near_parent_mean(self):
        rng = np.random.default_rng(5)
        xo = StrategyCrossover(jitter_frac=0.0)  # media pura, nessun jitter
        space = _space("momentum_drop")
        child = xo.blend_params({"x_percent": 0.5}, {"x_percent": 1.5}, space, rng)
        assert child["x_percent"] == 1.0


class TestStructuralCrossover:
    def test_entry_a_filters_b_compose_without_exceptions(self):
        rng = np.random.default_rng(9)
        xo = StrategyCrossover()
        pa = generate_from_template("momentum_drop", rng)
        genome = xo.structural_child("momentum_drop", "mean_reversion_zscore", pa, rng)
        assert genome["template"] == "momentum_drop"
        assert genome["entry_condition"] == (
            TEMPLATE_REGISTRY["momentum_drop"]["entry_condition"])
        assert genome["filters"] == (
            TEMPLATE_REGISTRY["mean_reversion_zscore"]["optional_filters"])
        assert genome["params"] == pa

    def test_cross_template_children_valid(self):
        rng = np.random.default_rng(13)
        xo = StrategyCrossover()
        pa = generate_from_template("momentum_drop", rng)
        pb = generate_from_template("mean_reversion_zscore", rng)
        children, discarded = xo.make_children(
            "momentum_drop", "mean_reversion_zscore", pa, pb, rng)
        assert len(children) == 2  # entrambe le direzioni strutturali
        assert discarded == 0
        for child in children:
            strategy = TEMPLATE_REGISTRY[child["template"]]["strategy"]
            assert strategy.validate(child["params"]), child

    def test_invalid_discarded_counted_not_raised(self):
        rng = np.random.default_rng(17)
        xo = StrategyCrossover()
        bad = {"x_percent": -99.0}  # invalido: mancano chiavi + valore negativo
        good = generate_from_template("momentum_drop", rng)
        children, discarded = xo.make_children("momentum_drop", "momentum_drop",
                                               bad, good, rng)
        # Nessuna eccezione; gli invalidi risultano negli scarti.
        assert discarded >= 0
        for child in children:
            assert TEMPLATE_REGISTRY[child["template"]]["strategy"].validate(
                child["params"])
        # Caso medio: blend con un genitore rotto puo' fallire -> scartato.
        xo2 = StrategyCrossover()
        children2, discarded2 = xo2.make_children("momentum_drop", "momentum_drop",
                                                  {"bogus": 1}, {"bogus": 2}, rng)
        assert discarded2 >= 1  # almeno il parametrico scartato
        assert all(TEMPLATE_REGISTRY[c["template"]]["strategy"].validate(c["params"])
                   for c in children2)
