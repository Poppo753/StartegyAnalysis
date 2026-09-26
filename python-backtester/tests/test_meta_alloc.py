"""F5-A03: regime x cluster -> trial quota + template ranking."""
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src.meta_analysis.focus_allocator import (
    AFFINITY,
    allocate_trials,
    allocation_table,
    preferred_templates,
    strategy_trials,
)

CLUSTERS = [
    {"cluster_id": 0, "archetype": "momentum", "size": 4,
     "members": ["momentum_0", "momentum_1"]},
    {"cluster_id": 1, "archetype": "mean_reversion", "size": 4,
     "members": ["mr_0", "mr_1"]},
]


class TestAllocation:
    def test_trending_favors_momentum(self):
        quota = allocate_trials("TRENDING", CLUSTERS, total_trials=100)
        assert quota[0] > quota[1]
        assert sum(quota.values()) == 100

    def test_ranging_favors_mean_reversion(self):
        quota = allocate_trials("RANGING", CLUSTERS, total_trials=100)
        assert quota[1] > quota[0]
        assert sum(quota.values()) == 100

    def test_weights_sum_to_one(self):
        w = allocation_table("HIGH_VOL", CLUSTERS)
        assert sum(w.values()) == pytest.approx(1.0)

    def test_accepts_clusterer_output_shape(self):
        # clusterer.py emits dominant_archetype/size/members (no 'archetype').
        clusterer_shaped = [
            {"cluster_id": 2, "dominant_archetype": "breakout", "size": 3,
             "members": ["b_0"]},
            {"cluster_id": 3, "dominant_archetype": "grid", "size": 3,
             "members": ["g_0"]},
        ]
        quota = allocate_trials("HIGH_VOL", clusterer_shaped, total_trials=50)
        assert quota[2] > quota[3]
        assert sum(quota.values()) == 50

    def test_strategy_trials_for_f2(self):
        per = strategy_trials("TRENDING", CLUSTERS, total_trials=100)
        assert sum(per.values()) == 100
        assert per["momentum_0"] + per["momentum_1"] > per["mr_0"] + per["mr_1"]

    def test_preferred_templates_for_f4(self):
        assert preferred_templates("TRENDING", CLUSTERS, top_n=1) == ["momentum_drop"]
        assert preferred_templates("RANGING", CLUSTERS, top_n=1) == [
            "mean_reversion_zscore"
        ]

    def test_bad_inputs_raise(self):
        with pytest.raises(ValueError):
            allocate_trials("CRASH", CLUSTERS)
        with pytest.raises(ValueError):
            allocate_trials("TRENDING", [])
        with pytest.raises(ValueError):
            allocate_trials("TRENDING", [{"cluster_id": 0, "archetype": "nope"}])
        with pytest.raises(ValueError):
            allocate_trials("TRENDING", CLUSTERS, total_trials=0)

    def test_no_searcher_generator_imports(self):
        import ast

        src = pathlib.Path(__file__).resolve().parent.parent.joinpath(
            "src", "meta_analysis", "focus_allocator.py"
        ).read_text()
        imported = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        assert not any("searcher" in m or "generator" in m for m in imported)
        assert set(AFFINITY) == {"TRENDING", "RANGING", "HIGH_VOL", "NORMAL"}
