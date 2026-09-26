"""F5-A02: K-Means over per-strategy vectors (4 v3 archetypes)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from src.meta_analysis.strategy_clusterer import (
    ARCHETYPES,
    NUMERIC_FEATURES,
    cluster_report,
    cluster_strategies,
    vectorize,
)

PROFILES = {
    "momentum": {"win_rate": 55, "pnl_pct": 25, "sharpe": 1.8, "trades": 120, "dd": 8},
    "mean_reversion": {"win_rate": 68, "pnl_pct": 12, "sharpe": 1.2, "trades": 200, "dd": 5},
    "breakout": {"win_rate": 38, "pnl_pct": 30, "sharpe": 1.5, "trades": 60, "dd": 15},
    "grid": {"win_rate": 75, "pnl_pct": 6, "sharpe": 0.8, "trades": 400, "dd": 3},
}


@pytest.fixture(scope="module")
def strategies():
    rng = np.random.default_rng(11)
    out = []
    for arch, p in PROFILES.items():
        for i in range(4):
            out.append(
                {
                    "name": f"{arch}_{i}",
                    "archetype": arch,
                    "win_rate": p["win_rate"] + rng.normal(0, 2),
                    "pnl_pct": p["pnl_pct"] + rng.normal(0, 2),
                    "sharpe": p["sharpe"] + rng.normal(0, 0.1),
                    "trades": max(5, int(p["trades"] + rng.normal(0, 10))),
                    "dd": max(0.5, p["dd"] + rng.normal(0, 1)),
                }
            )
    return out


def _coherence(labels, strategies):
    arch = {s["name"]: s["archetype"] for s in strategies}
    names = list(labels)
    same_hit = same_tot = cross_hit = cross_tot = 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            same = arch[names[i]] == arch[names[j]]
            together = labels[names[i]] == labels[names[j]]
            if same:
                same_hit += together
                same_tot += 1
            else:
                cross_hit += together
                cross_tot += 1
    return same_hit / same_tot, cross_hit / cross_tot


class TestVectorize:
    def test_feature_columns(self, strategies):
        X, names, feats = vectorize(strategies)
        assert X.shape == (16, len(NUMERIC_FEATURES) + len(ARCHETYPES))
        assert feats == [*NUMERIC_FEATURES, *(f"arch_{a}" for a in ARCHETYPES)]
        assert names == [s["name"] for s in strategies]

    def test_bad_inputs_raise(self, strategies):
        with pytest.raises(ValueError):
            vectorize([])
        bad = dict(strategies[0])
        bad["archetype"] = "martingale"
        with pytest.raises(ValueError):
            vectorize([bad])
        bad2 = dict(strategies[0])
        del bad2["sharpe"]
        with pytest.raises(ValueError):
            vectorize([bad2])


class TestClustering:
    def test_k_selected_in_range(self, strategies):
        res = cluster_strategies(strategies)
        assert 2 <= res["k"] <= 6
        assert set(res["silhouette_scores"]) <= set(range(2, 7))
        assert res["k"] == 4  # 4 well-separated archetype groups (seed-fixed)

    def test_archetypes_cluster_coherently(self, strategies):
        res = cluster_strategies(strategies)
        same, cross = _coherence(res["labels"], strategies)
        assert same > cross
        assert same >= 0.90
        # Every archetype sits mostly in a single cluster.
        for arch in ARCHETYPES:
            members = [s["name"] for s in strategies if s["archetype"] == arch]
            top = max(
                sum(1 for m in members if res["labels"][m] == cid)
                for cid in set(res["labels"].values())
            )
            assert top / len(members) >= 0.75, arch

    def test_seed_stable_labels(self, strategies):
        a = cluster_strategies(strategies, seed=42)["labels"]
        b = cluster_strategies(strategies, seed=42)["labels"]
        assert a == b

    def test_too_few_strategies_raise(self, strategies):
        with pytest.raises(ValueError):
            cluster_strategies(strategies[:2])

    def test_report_readable(self, strategies):
        text = cluster_report(cluster_strategies(strategies))
        assert "Cluster" in text
        for arch in ARCHETYPES:
            assert arch in text
