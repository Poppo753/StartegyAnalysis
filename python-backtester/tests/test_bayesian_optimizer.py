"""Test BayesianOptimizer TPE (Fase 2, F2-B04).

Criterio onesto per ottimizzatore stocastico (mai "deve sempre"):
- Spazio enumerabile 3x3x3=27 (int 0..2 su a/b/c), ottimo noto (1,2,0).
- BO budget 30 (>=27) ritrova l'ottimo grid entro tolleranza score 1e-9
  in >=4 seed su 5. Seed fissi: [0, 1, 2, 3, 4].
  n_startup_trials=5 (ridotto dal default produzione 20 perche' il budget
  test e' piccolo; con 20 il TPE non partirebbe mai entro 10-30 trial).
- Budget 10: media best BO su 5 seed batte media best random su 5 seed
  (stessi seed, 10 campioni uniformi con replacement).

Tolleranza: |best_BO - best_grid| <= 1e-9 sullo score (spazio discreto:
equivale al ritrovamento esatto dell'ottimo).
Seed: [0, 1, 2, 3, 4] per entrambi i test (documentati qui).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import itertools

import numpy as np
import pandas as pd

from src.strategy_base import TradingStrategy
from src.strategy import Trade
from src.searcher import BayesianOptimizer

SEEDS = [0, 1, 2, 3, 4]
SCORE_TOL = 1e-9
BASE_PARAMS = {
    "max_hold_seconds": 300,
    "initial_capital": 1000.0,
    "position_size": 100.0,
    "fee_rate": 0.0,
    "slippage_rate": 0.0,
    "direction": "long",
}


class TinyGridStrategy(TradingStrategy):
    """Spazio 3x3x3=27, ottimo sintetico in (a=1, b=2, c=0), stateless."""

    def parameter_space(self):
        return {"a": (0, 2, "int"), "b": (0, 2, "int"), "c": (0, 2, "int")}

    def generate_signals(self, df, params):
        return []

    def validate(self, params):
        try:
            return (
                0 <= int(params["a"]) <= 2
                and 0 <= int(params["b"]) <= 2
                and 0 <= int(params["c"]) <= 2
            )
        except (KeyError, TypeError, ValueError):
            return False

    def run_backtest(self, df, params, symbol):
        a, b, c = int(params["a"]), int(params["b"]), int(params["c"])
        dist = (a - 1) ** 2 + (b - 2) ** 2 + (c - 0) ** 2
        pnl = 10.0 - 5.0 * dist
        t0 = pd.Timestamp("2024-01-01")
        return [
            Trade(
                symbol=symbol,
                entry_time=t0,
                exit_time=t0,
                entry_price=100.0,
                exit_price=100.0 + pnl,
                max_price_during_trade=100.0 + max(pnl, 0.0),
                min_price_during_trade=100.0 + min(pnl, 0.0),
                pnl=float(pnl),
                pnl_percent=float(pnl),
                fees=0.0,
                reason="synthetic",
                x_percent=0.5,
                y_seconds=10,
                z_percent=0.5,
            )
            for _ in range(5)
        ]


def _dummy_df():
    return pd.DataFrame({"close": [1.0, 2.0]})


def _grid_optimum():
    ref = BayesianOptimizer(TinyGridStrategy(), base_params=BASE_PARAMS)
    df = _dummy_df()
    best = -1e18
    for a, b, c in itertools.product([0, 1, 2], repeat=3):
        score, _ = ref._evaluate({"a": a, "b": b, "c": c}, df)
        best = max(best, score)
    return best


class TestBayesianOptimizerParity:
    def test_budget_ge_space_finds_grid_optimum_4_of_5_seeds(self):
        grid_best = _grid_optimum()
        df = _dummy_df()
        hits = 0
        for seed in SEEDS:
            opt = BayesianOptimizer(
                TinyGridStrategy(),
                n_startup_trials=5,
                base_params=BASE_PARAMS,
                seed=seed,
            )
            out = opt.optimize(df, n_trials=30)
            assert out["best_params"] is not None
            # Nessun trial deve fallire come errore (pruned ok, FAIL no).
            states = [t.state.name for t in out["study"].trials]
            assert "FAIL" not in states, f"seed={seed} states={states}"
            if abs(out["best_value"] - grid_best) <= SCORE_TOL:
                hits += 1
        assert hits >= 4, f"solo {hits}/5 seed trovano l'ottimo (tol={SCORE_TOL})"

    def test_budget_10_beats_random_mean_over_5_seeds(self):
        combos = list(itertools.product([0, 1, 2], repeat=3))
        ref = BayesianOptimizer(TinyGridStrategy(), base_params=BASE_PARAMS)
        df = _dummy_df()
        grid_scores = {}
        for a, b, c in combos:
            s, _ = ref._evaluate({"a": a, "b": b, "c": c}, df)
            grid_scores[(a, b, c)] = s
        bo_bests = []
        rnd_bests = []
        for seed in SEEDS:
            opt = BayesianOptimizer(
                TinyGridStrategy(),
                n_startup_trials=5,
                base_params=BASE_PARAMS,
                seed=seed,
            )
            out = opt.optimize(df, n_trials=10)
            bo_bests.append(out["best_value"])
            rng = np.random.default_rng(seed)
            idx = rng.integers(0, len(combos), size=10)
            rnd_bests.append(max(grid_scores[combos[i]] for i in idx))
        assert float(np.mean(bo_bests)) > float(np.mean(rnd_bests)), (
            f"BO mean {np.mean(bo_bests):.4f} non batte random mean {np.mean(rnd_bests):.4f}"
        )


def _small_ohlc(n=300, seed=0):
    rng = np.random.RandomState(seed)
    close = np.linspace(100.0, 105.0, n) + rng.randn(n) * 0.5
    dates = pd.date_range("2024-01-01", periods=n, freq="s", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": dates.strftime("%Y-%m-%dT%H:%M:%S"),
            "open": close,
            "high": close * 1.001,
            "low": close * 0.999,
            "close": close,
            "volume": np.ones(n),
            "tradeCount": np.ones(n, dtype=int),
            "datetime": dates,
            "epoch_seconds": np.arange(n, dtype=float),
        }
    )


class TestBayesianOptimizerSmoke:
    def test_momentum_small_budget_completes_no_fail(self):
        from src.strategies.momentum_drop import MomentumDropStrategy

        df = _small_ohlc()
        opt = BayesianOptimizer(
            MomentumDropStrategy(),
            n_startup_trials=5,
            base_params={
                "max_hold_seconds": 300,
                "initial_capital": 1000.0,
                "position_size": 100.0,
                "fee_rate": 0.001,
                "slippage_rate": 0.0005,
                "direction": "signal-only",
            },
            symbol="TESTUSDT",
            seed=0,
        )
        out = opt.optimize(df, n_trials=5)
        states = [t.state.name for t in out["study"].trials]
        assert "FAIL" not in states
        assert out["best_params"]

    def test_mean_reversion_small_budget_completes_no_fail(self):
        from src.strategies.mean_reversion import MeanReversionZScore

        t = np.arange(300)
        close = 100.0 + 5.0 * np.sin(2 * np.pi * t / 40.0)
        n = len(close)
        dates = pd.date_range("2024-01-01", periods=n, freq="s", tz="UTC")
        df = pd.DataFrame(
            {
                "timestamp": dates.strftime("%Y-%m-%dT%H:%M:%S"),
                "open": close,
                "high": close * 1.0005,
                "low": close * 0.9995,
                "close": close,
                "volume": np.ones(n),
                "tradeCount": np.ones(n, dtype=int),
                "datetime": dates,
                "epoch_seconds": np.arange(n, dtype=float),
            }
        )
        opt = BayesianOptimizer(
            MeanReversionZScore(),
            n_startup_trials=5,
            base_params={
                "initial_capital": 1000.0,
                "fee_rate": 0.001,
                "slippage_rate": 0.0005,
                "direction": "long",
            },
            symbol="TESTUSDT",
            seed=0,
        )
        out = opt.optimize(df, n_trials=5)
        states = [t.state.name for t in out["study"].trials]
        assert "FAIL" not in states
        assert out["best_params"]

    def test_suggest_kinds_mapping(self):
        from src.searcher.bayesian_optimizer import suggest_params
        import optuna

        space = {
            "a": (0.1, 10.0, "float"),
            "b": (1, 10, "int"),
            "c": (0.01, 10.0, "float_log"),
            "d": (1, 100, "int_log"),
        }
        study = optuna.create_study(direction="maximize")
        trial = study.ask()
        vals = suggest_params(trial, space)
        assert isinstance(vals["a"], float) and 0.1 <= vals["a"] <= 10.0
        assert isinstance(vals["b"], int) and 1 <= vals["b"] <= 10
        assert isinstance(vals["c"], float) and 0.01 <= vals["c"] <= 10.0
        assert isinstance(vals["d"], int) and 1 <= vals["d"] <= 100
        study.tell(trial, 0.0)
