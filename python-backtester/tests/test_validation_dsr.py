"""DSR + protocol gate F3-V04/V05."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest
from scipy.stats import norm

from src.validation.dsr import calculate_dsr, calculate_dsr_exact
from src.validation.protocol import apply_pbo_gate


class TestDsrOperational:
    def test_equals_sr_when_pbo_zero(self):
        assert calculate_dsr(1.5, 0.0) == pytest.approx(1.5)
        assert calculate_dsr(1.5, 0.01) == pytest.approx(1.5 * 0.98)

    def test_negative_for_high_pbo_random(self):
        # Strategia random ad alto PBO → DSR negativo → rigetta.
        assert calculate_dsr(1.2, 0.90) == pytest.approx(1.2 * (1 - 1.8))
        assert calculate_dsr(1.2, 0.90) < 0

    def test_zero_at_pbo_half(self):
        assert calculate_dsr(2.0, 0.5) == pytest.approx(0.0)
        assert calculate_dsr(2.0, 50.0) == pytest.approx(0.0)  # percentuale

    def test_percent_and_fraction_agree(self):
        assert calculate_dsr(1.0, 20.0) == pytest.approx(calculate_dsr(1.0, 0.20))


class TestDsrExact:
    def test_known_phi_over_Phi(self):
        # z=1: phi=0.2419707245, Phi=0.8413447461 → 1*phi/Phi ≈ 0.28759993.
        expected = float(norm.pdf(1.0)) / float(norm.cdf(1.0))
        assert calculate_dsr_exact(1.0, 1.0) == pytest.approx(expected)
        assert calculate_dsr_exact(1.0, 1.0) == pytest.approx(0.28759993, rel=1e-6)

    def test_zero_sharpe(self):
        assert calculate_dsr_exact(0.0, 2.0) == pytest.approx(0.0)

    def test_scaling_with_years(self):
        # z = SR*sqrt(T): T=4 → z=2.
        expected = 1.0 * float(norm.pdf(2.0)) / float(norm.cdf(2.0))
        assert calculate_dsr_exact(1.0, 4.0) == pytest.approx(expected)

    def test_invalid_years(self):
        assert calculate_dsr_exact(1.0, 0.0) == 0.0
        assert calculate_dsr_exact(1.0, -1.0) == 0.0


class TestProtocolGate:
    def test_solid_accept(self):
        out = apply_pbo_gate(5.0, n_trials=100, dsr=0.8)
        assert out["decision"] == "ACCEPT"
        assert out["required_steps"] == []

    def test_yellow_conditional(self):
        out = apply_pbo_gate(30.0, n_trials=100, dsr=0.4)
        assert out["decision"] == "CONDITIONAL"
        assert out["required_steps"] == ["walk_forward", "holdout_final"]

    def test_overfitted_reject(self):
        out = apply_pbo_gate(80.0, n_trials=100, dsr=0.4)
        assert out["decision"] == "REJECT"

    def test_negative_dsr_overrides(self):
        out = apply_pbo_gate(5.0, n_trials=100, dsr=-0.2)
        assert out["decision"] == "REJECT"
        assert "DSR" in out["reason"]

    def test_log_line_has_pbo_and_trials(self):
        out = apply_pbo_gate(30.0, n_trials=77, dsr=0.1)
        assert "PBO=" in out["log_line"] and "N_trials=77" in out["log_line"]
