"""report.py - Markdown meta report, "il cervello" (F5-A04).

Usage:
    python -m src.meta_analysis.report --results <dir> [--out report.md]

<dir> holds CSVs (column-tolerant):
- strategy results: either clusterer-style
  (name, archetype, win_rate, pnl_pct, sharpe, trades, dd) or
  results_writer summaries (strategy, win_rate, total_pnl_percent,
  total_trades, max_drawdown, ...; archetype inferred from the strategy
  name, sharpe defaults to 0.0 when absent);
- OHLC: any CSV with high/low/close columns (used for the current
  regime via the last full window; "UNKNOWN" when absent).
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import Dict, List, Optional

import pandas as pd

from src.meta_analysis.focus_allocator import (
    AFFINITY,
    allocate_trials,
    preferred_templates,
)
from src.meta_analysis.regime_detector import detect_current_regime
from src.meta_analysis.strategy_clusterer import (
    ARCHETYPES,
    cluster_report,
    cluster_strategies,
)

STRATEGY_FROM_NAME = {
    "momentum_drop": "momentum",
    "mean_reversion": "mean_reversion",
    "meanreversion": "mean_reversion",
    "breakout": "breakout",
    "grid": "grid",
}


def _infer_archetype(name: str) -> str:
    low = str(name).strip().lower()
    for key, arch in STRATEGY_FROM_NAME.items():
        if key in low:
            return arch
    return "unknown"


def _f(row: Dict, *keys: str, default: float = 0.0) -> float:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            try:
                return float(row[k])
            except (TypeError, ValueError):
                continue
    return float(default)


def load_strategies(results_dir: str) -> List[Dict]:
    """Collect strategy dicts from every CSV carrying strategy metrics."""
    out: List[Dict] = []
    for path in sorted(glob.glob(os.path.join(results_dir, "*.csv"))):
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        cols = set(df.columns)
        if not ({"high", "low", "close"} <= cols):
            # Strategy file if it has a name-ish + metric-ish column.
            if {"win_rate", "total_trades", "trades", "pnl_pct",
                    "total_pnl_percent"} & cols:
                for i, row in df.iterrows():
                    d = dict(row)
                    name = str(d.get("name", d.get("strategy", f"row{i}")))
                    arch = str(d.get("archetype", "")).strip().lower()
                    if arch not in ARCHETYPES:
                        arch = _infer_archetype(name)
                    out.append(
                        {
                            "name": name,
                            "archetype": arch,
                            "win_rate": _f(d, "win_rate"),
                            "pnl_pct": _f(d, "pnl_pct", "total_pnl_percent"),
                            "sharpe": _f(d, "sharpe", "sharpe_ratio"),
                            "trades": _f(d, "trades", "total_trades"),
                            "dd": abs(_f(d, "dd", "max_drawdown")),
                        }
                    )
    # Unknown archetypes cannot cluster: keep them out of the table but
    # count them (reported as unclassified).
    known = [s for s in out if s["archetype"] in ARCHETYPES]
    return known


def load_current_regime(results_dir: str, window: int = 100) -> str:
    """Regime of the last OHLC window found in <dir> (else UNKNOWN)."""
    for path in sorted(glob.glob(os.path.join(results_dir, "*.csv"))):
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if {"high", "low", "close"} <= set(df.columns) and len(df) >= window:
            try:
                return detect_current_regime(df, window=window)
            except ValueError:
                continue
    return "UNKNOWN"


def top_per_regime(
    strategies: List[Dict], regimes: Optional[List[str]] = None, top_n: int = 3
) -> Dict[str, List[Dict]]:
    """Top strategies per regime by pnl_pct * regime affinity."""
    regimes = list(regimes) if regimes else [r for r in AFFINITY if r != "NORMAL"]
    table: Dict[str, List[Dict]] = {}
    for regime in regimes:
        scored = sorted(
            strategies,
            key=lambda s: s["pnl_pct"] * AFFINITY[regime].get(s["archetype"], 0.0)
            + s["sharpe"],
            reverse=True,
        )
        table[regime] = scored[: max(1, int(top_n))]
    return table


def build_report(results_dir: str) -> str:
    """Assemble the markdown report from <results_dir>."""
    strategies = load_strategies(results_dir)
    regime = load_current_regime(results_dir)
    lines = ["# Meta-Analysis Report", "", f"Current regime: {regime}", ""]
    if len(strategies) >= 3:
        try:
            res = cluster_strategies(strategies)
            lines += ["## Strategy Clusters", "", cluster_report(res), ""]
            anchor = regime if regime in AFFINITY else "NORMAL"
            quota = allocate_trials(anchor, res["clusters"], total_trials=100)
            templates = preferred_templates(anchor, res["clusters"], top_n=2)
            tops = top_per_regime(strategies)
            lines += ["## Top Strategies per Regime", ""]
            for r, rows in tops.items():
                names = ", ".join(
                    f"{s['name']} (pnl={s['pnl_pct']:.2f}%)" for s in rows
                )
                lines += [f"Top strategies ({r}): {names}"]
            lines += ["", "## Allocation Recommendation", ""]
            alloc = ", ".join(
                f"cluster {cid}: {n} trials" for cid, n in sorted(quota.items())
            )
            lines += [
                f"Recommended allocation for regime {anchor}: {alloc}.",
                f"Mutate templates first: {', '.join(templates)}.",
                "",
            ]
        except Exception as exc:  # graceful degradation, never crash
            lines += [f"Clustering unavailable: {exc}", ""]
    else:
        lines += [
            "Clustering unavailable: "
            f"only {len(strategies)} classifiable strategies found (need >= 3).",
            "",
        ]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> str:
    """CLI entry: parse args, emit markdown to stdout and/or --out file."""
    parser = argparse.ArgumentParser(description="Meta-analysis markdown report")
    parser.add_argument("--results", required=True, help="results directory with CSVs")
    parser.add_argument("--out", default=None, help="output markdown file")
    args = parser.parse_args(argv)
    text = build_report(args.results)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        print(text)
    return text


if __name__ == "__main__":
    main()
