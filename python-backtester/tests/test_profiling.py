"""Test enterprise per profiling (Profiler / profile)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time

from src.profiling import Profiler, profile


def test_profiler_measures_elapsed():
    with Profiler("elapsed-test", top_n=2, enabled=True) as p:
        time.sleep(0.05)
    assert p.elapsed >= 0.02
    assert p.report_dict()["elapsed_seconds"] >= 0.02
    assert p.report_dict()["cprofile_enabled"] is True


def test_profiler_disabled_still_times():
    with Profiler("disabled-test", enabled=False) as p:
        time.sleep(0.02)
    assert p.elapsed >= 0.0
    assert p._profiler is None
    assert p.report_dict()["cprofile_enabled"] is False


def test_profile_decorator_preserves_result():
    @profile(label="sample-add", enabled=False)
    def sample_add(a, b):
        return a + b

    assert sample_add(2, 3) == 5
    assert sample_add.__name__ == "sample_add"
