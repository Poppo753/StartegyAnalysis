"""strategy_clusterer.py - K-Means su vettori risultato (F5-A02).

Vector per strategy: (win_rate, pnl_pct, sharpe, trades, dd, archetype
one-hot over the 4 v3 archetypes). Features are standardized
(StandardScaler) before K-Means; k is selected by silhouette over
k=2..6; labels are seed-stable (random_state + n_init=10).

Requires scikit-learn (pinned in requirements.txt, added by this task
and reused by F5-R01).
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np

ARCHETYPES: Tuple[str, ...] = ("momentum", "mean_reversion", "breakout", "grid")

NUMERIC_FEATURES: Tuple[str, ...] = ("win_rate", "pnl_pct", "sharpe", "trades", "dd")

K_MIN = 2
K_MAX = 6


def _require_strategy(s: Dict) -> None:
    missing = [k for k in ("name", *NUMERIC_FEATURES, "archetype") if k not in s]
    if missing:
        raise ValueError(f"strategy {s.get('name', '?')!r} missing keys: {missing}")
    if s["archetype"] not in ARCHETYPES:
        raise ValueError(
            f"strategy {s['name']!r}: unknown archetype {s['archetype']!r} "
            f"(expected one of {list(ARCHETYPES)})"
        )


def vectorize(strategies: Sequence[Dict]) -> Tuple[np.ndarray, List[str], List[str]]:
    """Build the feature matrix (numeric + archetype one-hot).

    Returns (X, names, feature_names) with X float, one row per strategy.
    """
    strategies = list(strategies)
    if not strategies:
        raise ValueError("vectorize: empty strategy list")
    for s in strategies:
        _require_strategy(s)
    feature_names = [*NUMERIC_FEATURES, *(f"arch_{a}" for a in ARCHETYPES)]
    rows = []
    for s in strategies:
        rows.append(
            [float(s[f]) for f in NUMERIC_FEATURES]
            + [1.0 if s["archetype"] == a else 0.0 for a in ARCHETYPES]
        )
    return np.asarray(rows, dtype=float), [str(s["name"]) for s in strategies], feature_names


def cluster_strategies(
    strategies: Sequence[Dict],
    k_min: int = K_MIN,
    k_max: int = K_MAX,
    seed: int = 42,
) -> Dict:
    """Cluster strategies, selecting k by silhouette.

    Args:
        strategies: list of dicts (see vectorize).
        k_min/k_max: silhouette search range (defaults 2..6 per checklist).
        seed: RNG seed (labels stable across calls with the same seed).

    Returns:
        dict {k, labels, silhouette_scores, clusters, feature_names} where
        labels maps strategy name -> cluster id and clusters lists
        {cluster_id, size, members, dominant_archetype, mean_<metric>}.
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    strategies = list(strategies)
    n = len(strategies)
    if n < 3:
        raise ValueError(f"need >= 3 strategies to cluster, got {n}")
    k_min, k_max = int(k_min), int(k_max)
    if not 2 <= k_min <= k_max:
        raise ValueError(f"require 2 <= k_min <= k_max, got {k_min}/{k_max}")
    X, names, feature_names = vectorize(strategies)
    Xs = StandardScaler().fit_transform(X)

    hi = min(k_max, n - 1)  # silhouette requires k < n
    scores: Dict[int, float] = {}
    labelings: Dict[int, np.ndarray] = {}
    for k in range(k_min, hi + 1):
        km = KMeans(n_clusters=k, random_state=int(seed), n_init=10)
        lab = km.fit_predict(Xs)
        try:
            scores[k] = float(silhouette_score(Xs, lab))
        except ValueError:
            continue  # degenerate labeling (e.g. singleton-heavy): skip k
        labelings[k] = lab
    if not scores:
        raise RuntimeError("silhouette failed for every k in range")
    best_k = max(scores, key=lambda k: (scores[k], -k))
    labels = {name: int(lab) for name, lab in zip(names, labelings[best_k])}

    by_arch = {s["name"]: s["archetype"] for s in strategies}
    clusters = []
    for cid in range(best_k):
        members = [nm for nm in names if labels[nm] == cid]
        archs = [by_arch[m] for m in members]
        dom = max(sorted(set(archs)), key=archs.count)
        entry: Dict = {
            "cluster_id": cid,
            "size": len(members),
            "members": members,
            "dominant_archetype": dom,
        }
        for f in NUMERIC_FEATURES:
            vals = [float(s[f]) for s in strategies if s["name"] in set(members)]
            entry[f"mean_{f}"] = float(np.mean(vals)) if vals else 0.0
        clusters.append(entry)
    return {
        "k": int(best_k),
        "labels": labels,
        "silhouette_scores": scores,
        "clusters": clusters,
        "feature_names": feature_names,
    }


def cluster_report(result: Dict) -> str:
    """Readable multi-line cluster summary."""
    lines = [
        f"Strategy clusters: k={result['k']} "
        f"(silhouette={result['silhouette_scores'][result['k']]:.3f})"
    ]
    for c in result["clusters"]:
        metrics = ", ".join(
            f"{f}={c[f'mean_{f}']:.2f}" for f in NUMERIC_FEATURES
        )
        lines.append(
            f"Cluster {c['cluster_id']} (n={c['size']}, "
            f"archetype={c['dominant_archetype']}): {metrics} "
            f"| members={', '.join(c['members'])}"
        )
    return "\n".join(lines)
