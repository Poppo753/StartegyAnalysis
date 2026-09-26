"""
profiling.py - Profiler integrato per il backtester (caso #25).

Fornisce:
- Profiler: context manager basato su cProfile + pstats (top-N per cumtime/tottime).
- profile(): decoratore per profilare singole funzioni.
- Timer esteso: misura wall-time (riuso di src.utils.Timer quando possibile).
- tracemalloc snapshot: picco memoria allocata dal Python allocator.

Tutto stdlib: nessun extra in requirements. Output su stdout, mai su file
dati. Pensato per sviluppo/ottimizzazione, non per il path hot del motore.

Uso:
    from src.profiling import Profiler, profile

    with Profiler("screening", top_n=15, track_memory=True):
        run_gpu_pipeline(df, config, symbol)

    @profile(top_n=10)
    def run_fast_backtest(...): ...

    PROFILING=1 python main.py   # abilita Profiler globale se integrato nel runner
"""

from __future__ import annotations

import cProfile
import functools
import io
import os
import pstats
import time
import tracemalloc
from types import TracebackType
from typing import Any, Callable, Optional, Type


def _profiling_enabled_by_default() -> bool:
    return os.getenv("PROFILING", "false").strip().lower() in ("true", "1", "yes")


class Profiler:
    """
    Context manager per profilare un blocco di codice.

    Args:
        label: etichetta stampata nel report.
        top_n: righe mostrate per cumtime e tottime.
        track_memory: se True, misura il picco tracemalloc del blocco.
        enabled: se False, misura solo wall-time (zero overhead cProfile).
        min_print_seconds: sotto questa soglia stampa solo wall-time compatto.
    """

    def __init__(
        self,
        label: str = "",
        top_n: int = 15,
        track_memory: bool = False,
        enabled: Optional[bool] = None,
        min_print_seconds: float = 0.0,
    ) -> None:
        self.label = label or "profiled block"
        self.top_n = max(1, int(top_n))
        self.track_memory = bool(track_memory)
        self.enabled = _profiling_enabled_by_default() if enabled is None else bool(enabled)
        self.min_print_seconds = float(min_print_seconds)
        self.elapsed = 0.0
        self.peak_memory_mb = 0.0
        self._profiler: Optional[cProfile.Profile] = None
        self._start = 0.0
        self._tracemalloc_started_here = False

    def __enter__(self) -> "Profiler":
        self._start = time.perf_counter()
        if self.track_memory and not tracemalloc.is_tracing():
            tracemalloc.start()
            self._tracemalloc_started_here = True
        if self.enabled:
            self._profiler = cProfile.Profile()
            self._profiler.enable()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        if self._profiler is not None:
            self._profiler.disable()
        self.elapsed = time.perf_counter() - self._start

        if self.track_memory and tracemalloc.is_tracing():
            _, peak = tracemalloc.get_traced_memory()
            self.peak_memory_mb = peak / (1024 * 1024)
            if self._tracemalloc_started_here:
                tracemalloc.stop()

        if self.elapsed < self.min_print_seconds and self._profiler is None:
            print(f"  [time] {self.label}: {self.elapsed:.2f}s")
            return

        # Nota: niente emoji qui dentro. Questo modulo è codice libreria e
        # print() non deve mai sollevare UnicodeEncodeError su console
        # Windows cp1252 (main.py forza UTF-8 solo per il proprio flusso CLI).
        print(f"\n  [Profiler] {self.label}: {self.elapsed:.2f}s wall"
              + (f" | peak mem {self.peak_memory_mb:.1f} MB" if self.track_memory else ""))

        if self._profiler is None:
            print("     (cProfile disabilitato - imposta PROFILING=1 per il dettaglio funzioni)")
            return

        stream = io.StringIO()
        stats = pstats.Stats(self._profiler, stream=stream).strip_dirs().sort_stats("cumulative")
        stats.print_stats(self.top_n)
        print("     --- top per cumtime ---")
        for line in stream.getvalue().splitlines()[-self.top_n:]:
            print(f"     {line}")

        stream2 = io.StringIO()
        stats2 = pstats.Stats(self._profiler, stream=stream2).strip_dirs().sort_stats("tottime")
        stats2.print_stats(self.top_n)
        print("     --- top per tottime (self) ---")
        for line in stream2.getvalue().splitlines()[-self.top_n:]:
            print(f"     {line}")

    def report_dict(self) -> dict[str, Any]:
        """Report sintetico machine-readable."""
        return {
            "label": self.label,
            "elapsed_seconds": round(self.elapsed, 4),
            "peak_memory_mb": round(self.peak_memory_mb, 2),
            "cprofile_enabled": self._profiler is not None,
        }


def profile(
    _func: Optional[Callable] = None,
    *,
    label: Optional[str] = None,
    top_n: int = 15,
    track_memory: bool = False,
    enabled: Optional[bool] = None,
) -> Callable:
    """
    Decoratore per profilare una funzione con Profiler.

    Uso:
        @profile
        def f(...): ...

        @profile(label="fast", top_n=10, track_memory=True)
        def g(...): ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with Profiler(
                label or f"{func.__module__}.{func.__qualname__}",
                top_n=top_n,
                track_memory=track_memory,
                enabled=enabled,
            ):
                return func(*args, **kwargs)
        return wrapper

    if _func is not None and callable(_func):
        return decorator(_func)
    return decorator
