"""focus_allocator.py - cluster x regime -> budget ricerca (F5-A03).

Table (current_regime x cluster -> quota trial/generation) consumable by
F2 (n_trials per strategy via `strategy_trials`) and F4 (which template
to mutate via `preferred_templates`).

Integration is import-clean by design: this module imports ONLY the
stdlib and consumes duck-typed dicts (it also accepts the cluster dicts
produced by `strategy_clusterer.cluster_strategies`, reading
``dominant_archetype`` as fallback for ``archetype``). It never imports
src.searcher / src.generator, so no import cycle is possible in either
direction.

Weight rule (documented prior from v3 §4.1 + §5.7: momentum wins when
trending, mean-reversion/grid when ranging, breakout on volatility
expansion)::

    weight(cluster) = AFFINITY[regime][archetype] * size
"""

from __future__ import annotations

from typing import Dict, List, Sequence

REGIMES = ("TRENDING", "RANGING", "HIGH_VOL", "NORMAL")

ARCHETYPES = ("momentum", "mean_reversion", "breakout", "grid")

# Template registry names (F4-G01) per archetype, for F4 consumption.
TEMPLATE_FOR_ARCHETYPE = {
    "momentum": "momentum_drop",
    "mean_reversion": "mean_reversion_zscore",
    "breakout": "breakout",
    "grid": "grid",
}

AFFINITY: Dict[str, Dict[str, float]] = {
    "TRENDING": {"momentum": 1.6, "breakout": 1.2, "mean_reversion": 0.5, "grid": 0.4},
    "RANGING": {"mean_reversion": 1.6, "grid": 1.3, "breakout": 0.6, "momentum": 0.5},
    "HIGH_VOL": {"breakout": 1.5, "momentum": 1.0, "mean_reversion": 0.7, "grid": 0.6},
    "NORMAL": {"momentum": 1.0, "mean_reversion": 1.0, "breakout": 1.0, "grid": 1.0},
}


def _norm_cluster(c: Dict) -> Dict:
    cid = c.get("cluster_id", c.get("id"))
    if cid is None:
        raise ValueError(f"cluster entry missing 'cluster_id': {c!r}")
    arch = c.get("archetype", c.get("dominant_archetype"))
    if arch not in ARCHETYPES:
        raise ValueError(f"cluster {cid!r}: unknown archetype {arch!r}")
    size = int(c.get("size", c.get("n_strategies", 1)))
    if size < 1:
        raise ValueError(f"cluster {cid!r}: size must be >= 1, got {size}")
    return {"cluster_id": cid, "archetype": arch, "size": size,
            "members": list(c.get("members", []))}


def _check_regime(regime: str) -> str:
    if regime not in AFFINITY:
        raise ValueError(f"unknown regime {regime!r} (expected one of {list(AFFINITY)})")
    return regime


def allocation_table(current_regime: str, clusters: Sequence[Dict]) -> Dict:
    """Normalized weight per cluster_id (weights sum to 1.0)."""
    _check_regime(current_regime)
    norm = [_norm_cluster(c) for c in clusters]
    if not norm:
        raise ValueError("allocation_table: empty cluster list")
    raw = {c["cluster_id"]: AFFINITY[current_regime][c["archetype"]] * c["size"]
           for c in norm}
    total = sum(raw.values())
    if total <= 0:
        raise ValueError("allocation_table: non-positive total weight")
    return {cid: w / total for cid, w in raw.items()}


def _largest_remainder(weights: Dict, total: int) -> Dict:
    order = sorted(weights)  # deterministic tie-break
    exact = {cid: weights[cid] * total for cid in order}
    out = {cid: int(v) for cid, v in exact.items()}
    rest = int(total) - sum(out.values())
    remainders = sorted(
        ((exact[cid] - out[cid], cid) for cid in order), reverse=True
    )
    for i in range(rest):
        out[remainders[i % len(remainders)][1]] += 1
    return out


def allocate_trials(
    current_regime: str, clusters: Sequence[Dict], total_trials: int = 100
) -> Dict:
    """Cluster_id -> integer trial quota (sums exactly to total_trials)."""
    if int(total_trials) < 1:
        raise ValueError(f"total_trials must be >= 1, got {total_trials}")
    weights = allocation_table(current_regime, clusters)
    return _largest_remainder(weights, int(total_trials))


def strategy_trials(
    current_regime: str, clusters: Sequence[Dict], total_trials: int = 100
) -> Dict[str, int]:
    """Strategy name -> n_trials for F2 (cluster quota split evenly inside).

    Clusters without a member list fall back to one anonymous slot named
    after the cluster_id (still sums to total_trials).
    """
    norm = [_norm_cluster(c) for c in clusters]
    if not norm:
        raise ValueError("strategy_trials: empty cluster list")
    quota = allocate_trials(current_regime, norm, total_trials)
    per_strategy: Dict[str, float] = {}
    for c in norm:
        members = c["members"] or [f"cluster_{c['cluster_id']}"]
        each = quota[c["cluster_id"]] / len(members)
        for m in members:
            per_strategy[str(m)] = each
    scale = int(total_trials) / sum(per_strategy.values())
    weights = {k: v * scale / int(total_trials) for k, v in per_strategy.items()}
    return _largest_remainder(weights, int(total_trials))


def preferred_templates(
    current_regime: str, clusters: Sequence[Dict], top_n: int = 2
) -> List[str]:
    """Template names (F4 registry) ranked for the current regime."""
    weights = allocation_table(current_regime, clusters)
    norm = {c.get("cluster_id", c.get("id")): _norm_cluster(c) for c in clusters}
    ranked = sorted(weights, key=lambda cid: (-weights[cid], str(cid)))
    return [
        TEMPLATE_FOR_ARCHETYPE[norm[cid]["archetype"]]
        for cid in ranked[: max(1, int(top_n))]
    ]
