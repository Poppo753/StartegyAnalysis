"""evolution.py - Loop evolutivo 50x10 con F3-light + genealogia (F4-G04).

Protocollo per candidato (F3-light come ESERCIZIO del path, mai giudizio):
1. split temporale train/val via src/gpu/data_splitter (riuso, no duplicati);
2. backtest train + val, fitness = strategy.score su VAL (OOS);
3. PBO su sample ridotto via src/validation (PurgedKFold k=2 sul val +
   calculate_pbo/evaluate_pbo), solo loggato.

Valutazione a parametri fissi (fallback esplicitamente ammesso dal checklist:
BayesianOptimizer riusabile in linea di principio — stesso path
run_backtest/calculate_metrics/score — ma Optuna per-candidato costerebbe
un ordine di grandezza in piu' per un milestone di correttezza).
"""

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.gpu.data_splitter import split_train_validation
from src.metrics import calculate_metrics
from src.strategy import BacktestParams
from src.validation.cross_validator import PurgedKFold, calculate_pbo, evaluate_pbo

_DEFAULT_SYMBOL = "SYNTH"


def make_synthetic_ohlc(n: int = 600, seed: int = 0) -> pd.DataFrame:
    """OHLC 1s sintetico piccolo: random walk + drift + seno (trade garantiti)."""
    rng = np.random.default_rng(seed)
    n = int(n)
    rets = 0.0002 + 0.0005 * rng.standard_normal(n)
    trend = 100.0 * np.exp(np.cumsum(rets))
    wave = 1.5 * np.sin(2.0 * np.pi * np.arange(n) / 120.0)
    close = trend + wave
    open_ = np.concatenate(([close[0]], close[:-1]))
    noise = 0.0002 * close * np.abs(rng.standard_normal(n))
    high = np.maximum(open_, close) + noise
    low = np.minimum(open_, close) - noise
    start = pd.Timestamp("2024-01-01")
    datetimes = pd.date_range(start, periods=n, freq="s")
    return pd.DataFrame({
        "timestamp": (datetimes.astype("int64") // 10 ** 9).astype(int),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.integers(1, 100, size=n).astype(float),
        "tradeCount": rng.integers(1, 10, size=n).astype(int),
        "datetime": datetimes,
        "epoch_seconds": (datetimes.astype("int64") // 10 ** 9).astype(float),
    })


def _metrics_params(template: str, params: Dict[str, Any]) -> BacktestParams:
    """Mappa params template -> BacktestParams per calculate_metrics."""
    if template == "momentum_drop":
        return BacktestParams(
            x_percent=float(params["x_percent"]), y_seconds=int(params["y_seconds"]),
            z_percent=float(params["z_percent"]),
            max_hold_seconds=int(params.get("max_hold_seconds", 300)),
            initial_capital=1000.0, position_size=float(params.get("position_size", 100.0)),
            fee_rate=float(params.get("fee_rate", 0.001)),
            slippage_rate=float(params.get("slippage_rate", 0.0005)),
            direction=str(params.get("direction", "signal-only")),
        )
    if template == "mean_reversion_zscore":
        return BacktestParams(
            x_percent=float(params["z_threshold"]), y_seconds=int(params["ma_period"]),
            z_percent=0.1, max_hold_seconds=int(params.get("max_hold_seconds", 1800)),
            initial_capital=1000.0, position_size=float(params.get("position_size", 100.0)),
            fee_rate=float(params.get("fee_rate", 0.001)),
            slippage_rate=float(params.get("slippage_rate", 0.0005)),
            direction="long",
        )
    if template == "breakout":
        stop = float(params["stop_loss_pct"])
        return BacktestParams(
            x_percent=stop, y_seconds=int(params["lookback_period"]), z_percent=stop,
            max_hold_seconds=600, initial_capital=1000.0, position_size=100.0,
            fee_rate=0.001, slippage_rate=0.0005, direction="long",
        )
    # grid
    spacing = float(params["grid_spacing_pct"])
    return BacktestParams(
        x_percent=spacing, y_seconds=int(params["grid_levels"]), z_percent=spacing,
        max_hold_seconds=600, initial_capital=1000.0, position_size=100.0,
        fee_rate=0.001, slippage_rate=0.0005, direction="long",
    )


def evaluate_candidate(
    template: str,
    params: Dict[str, Any],
    df: pd.DataFrame,
    symbol: str = _DEFAULT_SYMBOL,
) -> Dict[str, Any]:
    """F3-light: split + score VAL + PBO-light (path exercise, non giudizio)."""
    from src.generator.strategy_generator import TEMPLATE_REGISTRY

    strategy = TEMPLATE_REGISTRY[template]["strategy"]
    df_train, df_val = split_train_validation(df, train_ratio=0.7)
    metrics_params = _metrics_params(template, params)
    train_trades = strategy.run_backtest(df_train, params, symbol)
    val_trades = strategy.run_backtest(df_val, params, symbol)
    train_score = float(strategy.score(calculate_metrics(train_trades, metrics_params, symbol)))
    val_result = calculate_metrics(val_trades, metrics_params, symbol)
    val_score = float(strategy.score(val_result))

    # PBO su sample ridotto: 2 fold purged sul VAL, score per fold.
    pbo: float | None = None
    verdict = "SKIPPED"
    try:
        fold_scores: List[float] = []
        splitter = PurgedKFold(n_splits=2, embargo_pct=0.01)
        for _, test_idx in splitter.split(df_val, horizon=1):
            fold_df = df_val.iloc[test_idx]
            fold_trades = strategy.run_backtest(fold_df, params, symbol)
            fold_scores.append(float(strategy.score(
                calculate_metrics(fold_trades, metrics_params, symbol))))
        if fold_scores:
            pbo = float(calculate_pbo(fold_scores))
            verdict = str(evaluate_pbo(pbo, n_trials=len(fold_scores))["verdict"])
    except Exception:
        pbo, verdict = None, "SKIPPED"
    return {
        "score": val_score,          # fitness OOS
        "train_score": train_score,
        "pbo": pbo,
        "pbo_verdict": verdict,      # loggato, MAI usato per accettare/rigettare
        "n_trades": int(val_result.total_trades),
    }


def run_evolution(
    n_population: int = 50,
    n_generations: int = 10,
    seed: int = 123,
    df: pd.DataFrame | None = None,
    symbol: str = _DEFAULT_SYMBOL,
) -> Dict[str, Any]:
    """Loop evolutivo: 50 x 10 = 500 valutazioni, genealogia completa in log."""
    from src.generator.crossover import StrategyCrossover
    from src.generator.mutation import StrategyMutation
    from src.generator.strategy_generator import TEMPLATE_REGISTRY, generate_from_template

    rng = np.random.default_rng(seed)
    df = make_synthetic_ohlc() if df is None else df
    names = list(TEMPLATE_REGISTRY)
    crossover = StrategyCrossover()
    mutation = StrategyMutation()  # rate default 0.05
    log: List[Dict[str, Any]] = []
    next_id = 0

    def _evaluate(template: str, params: Dict[str, Any], generation: int,
                  parents: List[int]) -> Dict[str, Any]:
        nonlocal next_id
        res = evaluate_candidate(template, params, df, symbol)
        entry = {"id": next_id, "generation": generation, "template": template,
                 "params": dict(params), "parents": list(parents), **res}
        next_id += 1
        log.append(entry)
        return entry

    population: List[Dict[str, Any]] = []
    for _ in range(n_population):
        name = names[int(rng.integers(0, len(names)))]
        population.append({"template": name, "params": generate_from_template(name, rng)})
    for cand in population:
        _evaluate(cand["template"], cand["params"], generation=0, parents=[])
    baseline_random_mean = float(np.mean([e["score"] for e in log]))

    for gen in range(1, n_generations):
        prev = [e for e in log if e["generation"] == gen - 1]
        prev_sorted = sorted(prev, key=lambda e: e["score"], reverse=True)
        pool = prev_sorted[:max(2, n_population // 2)]  # selezione: top 50%
        population = []
        for _ in range(n_population):
            ia, ib = rng.integers(0, len(pool), size=2)
            pa, pb = pool[int(ia)], pool[int(ib)]
            children, _ = crossover.make_children(
                pa["template"], pb["template"], pa["params"], pb["params"], rng)
            if children:
                child = children[0]
            else:  # fallback: rigenerazione fresca (sempre valida)
                t = pa["template"]
                child = {"template": t, "params": generate_from_template(t, rng)}
            space = TEMPLATE_REGISTRY[child["template"]]["strategy"].parameter_space()
            mutated = mutation.mutate(child["params"], space, rng)
            try:
                valid = bool(TEMPLATE_REGISTRY[child["template"]]["strategy"].validate(mutated))
            except Exception:
                valid = False
            if not valid:  # fallback: params pre-mutazione (gia' validati)
                mutated = dict(child["params"])
            cand = {"template": child["template"], "params": mutated}
            population.append(cand)
            _evaluate(cand["template"], cand["params"], generation=gen,
                      parents=[pa["id"], pb["id"]])

    last_gen = [e for e in log if e["generation"] == n_generations - 1]
    top5 = sorted(last_gen, key=lambda e: e["score"], reverse=True)[:5]
    best = max(log, key=lambda e: e["score"])
    return {
        "log": log,
        "evaluations": len(log),
        "n_population": n_population,
        "n_generations": n_generations,
        "baseline_random_mean": baseline_random_mean,
        "top5": top5,
        "top5_mean": float(np.mean([e["score"] for e in top5])),
        "best": best,
    }
