"""Test F4-G04: loop evolutivo 50x10 con F3-light + genealogia."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from src.generator.evolution import evaluate_candidate, make_synthetic_ohlc, run_evolution
from src.generator.strategy_generator import TEMPLATE_REGISTRY


class TestEvolutionLoop:
    def test_full_loop_50x10(self):
        df = make_synthetic_ohlc(n=600, seed=0)
        out = run_evolution(n_population=50, n_generations=10, seed=123, df=df)
        assert out["evaluations"] == 500  # 50 x 10 valutazioni
        assert len(out["log"]) == 500
        assert len(out["top5"]) == 5

    def test_all_logged_candidates_executable(self):
        df = make_synthetic_ohlc(n=600, seed=0)
        out = run_evolution(n_population=50, n_generations=10, seed=123, df=df)
        checked = 0
        for entry in out["log"][::5]:  # 100 voci ispezionate, mai eccezioni
            strategy = TEMPLATE_REGISTRY[entry["template"]]["strategy"]
            assert strategy.validate(entry["params"]), entry
            trades = strategy.run_backtest(df, entry["params"], "SYNTH")
            assert isinstance(trades, list)
            signals = strategy.generate_signals(df, entry["params"])
            assert isinstance(signals, list)
            checked += 1
        assert checked >= 100

    def test_top5_above_random_baseline(self):
        df = make_synthetic_ohlc(n=600, seed=0)
        out = run_evolution(n_population=50, n_generations=10, seed=123, df=df)
        assert out["top5_mean"] > out["baseline_random_mean"], (
            out["top5_mean"], out["baseline_random_mean"])

    def test_genealogy_inspectable(self):
        df = make_synthetic_ohlc(n=600, seed=0)
        out = run_evolution(n_population=50, n_generations=10, seed=123, df=df)
        by_id = {e["id"]: e for e in out["log"]}
        assert [e["id"] for e in out["log"]] == list(range(500))
        n_with_parents = 0
        for entry in out["log"]:
            assert "parents" in entry and "score" in entry
            assert "pbo" in entry and "pbo_verdict" in entry  # F3-light loggato
            if entry["generation"] == 0:
                assert entry["parents"] == []
            else:
                assert len(entry["parents"]) == 2
                for pid in entry["parents"]:
                    assert pid in by_id  # genitori risolvibili...
                    assert by_id[pid]["generation"] < entry["generation"]  # ...e passati
                n_with_parents += 1
        assert n_with_parents == 450  # 9 generazioni figlie x 50

    def test_f3_light_path_exercised_not_judgment(self):
        # Il path split+PBO gira (chiavi presenti) ma nessun rigetto: tutti
        # i 500 restano loggati indipendentemente dal verdetto PBO.
        df = make_synthetic_ohlc(n=600, seed=0)
        res = evaluate_candidate("momentum_drop",
                                 {"x_percent": 0.5, "y_seconds": 30, "z_percent": 0.3,
                                  "max_hold_seconds": 300, "position_size": 100.0,
                                  "fee_rate": 0.001, "slippage_rate": 0.0005},
                                 df)
        assert set(res) >= {"score", "train_score", "pbo", "pbo_verdict", "n_trades"}
        assert isinstance(res["score"], float)
