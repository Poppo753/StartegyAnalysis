"""CPCV + PBO + semaforo F3-V03/V04 (incl. verifica critica v3)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from src.validation.cross_validator import (
    CombinatorialPurgedCV,
    calculate_pbo,
    evaluate_pbo,
)


class TestCalculatePbo:
    def test_arithmetic(self):
        assert calculate_pbo([1.0, 2.0, -1.0]) == pytest.approx(1.0 / 3.0)
        assert calculate_pbo([1.0, 2.0]) == pytest.approx(0.0)
        assert calculate_pbo([-1.0, -2.0]) == pytest.approx(1.0)
        assert calculate_pbo([0.0, 1.0]) == pytest.approx(0.0)  # zero non negativo

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            calculate_pbo([])


class TestEvaluatePboMapping:
    """DoD F3-V04: mapping deterministico + N_trials + nota confini."""

    def test_deterministic_boundaries_percent(self):
        assert evaluate_pbo(9.9, n_trials=100)["verdict"] == "SOLID"
        assert evaluate_pbo(10.1, n_trials=100)["verdict"] == "POTENTIALLY_VALID"
        assert evaluate_pbo(49.9, n_trials=100)["verdict"] == "POTENTIALLY_VALID"
        assert evaluate_pbo(50.1, n_trials=100)["verdict"] == "OVERFITTED"

    def test_fraction_inputs(self):
        assert evaluate_pbo(0.099)["verdict"] == "SOLID"
        assert evaluate_pbo(0.10)["verdict"] == "POTENTIALLY_VALID"
        assert evaluate_pbo(0.50)["verdict"] == "POTENTIALLY_VALID"
        assert evaluate_pbo(0.501)["verdict"] == "OVERFITTED"

    def test_actions(self):
        assert evaluate_pbo(5.0)["action"] == "ACCEPT"
        assert evaluate_pbo(30.0)["action"] == "WALK_FORWARD_HOLDOUT"
        assert evaluate_pbo(80.0)["action"] == "REJECT"

    def test_n_trials_always_logged(self):
        for pbo in (5.0, 30.0, 80.0):
            line = evaluate_pbo(pbo, n_trials=250)["log_line"]
            assert "N_trials=250" in line
            assert "PBO=" in line
        assert "N_trials=unknown" in evaluate_pbo(5.0)["log_line"]

    def test_boundary_note_yellow(self):
        # Entro ±2pp dai confini → nota operatore gialla.
        for pbo in (9.9, 10.1, 8.5, 11.9, 48.5, 51.9):
            assert evaluate_pbo(pbo)["boundary_note"] != ""
        for pbo in (5.0, 30.0, 70.0):
            assert evaluate_pbo(pbo)["boundary_note"] == ""


class TestCpcvSplits:
    def test_no_overlap_exhaustive(self):
        cpcv = CombinatorialPurgedCV(n_partitions=6, n_test_groups=2)
        n, horizon = 600, 5
        for train_idx, test_idx in cpcv.splits(n, horizon):
            test_set = set(int(t) for t in test_idx)
            for i in train_idx:
                i = int(i)
                assert not (set(range(i, i + horizon)) & test_set)

    def test_embargo_gap(self):
        cpcv = CombinatorialPurgedCV(n_partitions=6, n_test_groups=2, embargo_pct=0.02)
        n = 600
        embargo_len = int(n * 0.02)
        bounds = cpcv._bounds(n)
        for train_idx, _ in cpcv.splits(n):
            train_set = set(int(t) for t in train_idx)
            for g in range(6):
                s, e = bounds[g], bounds[g + 1]
                # Se il gruppo g e` nel test di questo split, l'embargo dopo
                # di esso non deve essere nel train: verifica mirata sotto.
            assert train_set.isdisjoint(set())  # placeholder strutturale
        # Verifica diretta: per ogni split, nessun train in [e, e+embargo)
        # di un intervallo di test dello stesso split.
        combos = cpcv.test_group_combos()
        for (train_idx, _), combo in zip(cpcv.splits(n), combos):
            train_set = set(int(t) for t in train_idx)
            for g in combo:
                e = bounds[g + 1]
                assert train_set.isdisjoint(set(range(e, min(n, e + embargo_len))))

    def test_split_count(self):
        cpcv = CombinatorialPurgedCV(n_partitions=6, n_test_groups=2)
        assert len(cpcv.splits(600)) == 15  # C(6,2)
        assert len(cpcv.test_group_combos()) == 15


class TestCpcvPaths:
    def test_full_coverage(self):
        cpcv = CombinatorialPurgedCV(n_partitions=6, n_test_groups=2)
        n = 600
        splits = cpcv.splits(n)
        paths = cpcv.get_paths(n)
        assert len(paths) == 15
        for path in paths:
            union = np.concatenate([splits[i][1] for i in path])
            assert sorted(union.tolist()) == list(range(n))
            assert len(union) == n  # disgiunti: copertura esatta

    def test_cap_deterministic(self):
        cpcv = CombinatorialPurgedCV(n_partitions=6, n_test_groups=2, max_paths=5, seed=42)
        n = 600
        p1 = cpcv.get_paths(n)
        p2 = cpcv.get_paths(n)
        assert len(p1) == 5
        assert p1 == p2

    def test_big_enumeration_capped(self):
        cpcv = CombinatorialPurgedCV(n_partitions=8, n_test_groups=2, max_paths=10, seed=7)
        assert cpcv.n_paths_theoretical() == 105
        assert len(cpcv.get_paths(800)) == 10


class TestPboCriticalV3:
    """Verifica critica v3: random → PBO > 50%; edge iniettato → PBO < 50%.

    Se fallisce: bug nel calcolo, NON procedere (checklist F3-V03).
    """

    def test_random_signals_high_pbo(self):
        cpcv = CombinatorialPurgedCV(n_partitions=6, n_test_groups=2, seed=42)
        n = 600
        rng_ret = np.random.default_rng(11)
        rets = rng_ret.normal(0.0, 0.01, n)  # drift nullo
        pbos = []
        for seed in range(10):
            rng = np.random.default_rng(seed)
            signals = rng.choice([-1.0, 1.0], size=n)
            oos = cpcv.split_oos_pnl(rets, signals, cost=0.001)
            pbos.append(calculate_pbo(oos))
        assert float(np.mean(pbos)) > 0.50

    def test_injected_edge_low_pbo(self):
        cpcv = CombinatorialPurgedCV(n_partitions=6, n_test_groups=2, seed=42)
        n = 600
        rng_ret = np.random.default_rng(7)
        rets = rng_ret.normal(0.003, 0.01, n)  # drift positivo iniettato
        signals = np.ones(n)  # edge: sempre long sul drift
        oos = cpcv.split_oos_pnl(rets, signals, cost=0.001)
        assert calculate_pbo(oos) < 0.50
