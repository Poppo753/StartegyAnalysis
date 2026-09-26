"""
utils.py - Funzioni di utilità generiche

Contiene:
- Formattazione output console
- Timer per performance
- Utility di stampa
"""

import time
from types import TracebackType
from typing import List, Optional, Type

from src.strategy import BacktestResult


class Timer:
    """Context manager per misurare il tempo di esecuzione."""

    def __init__(self, label: str = "") -> None:
        self.label = label
        self.start_time = 0.0
        self.elapsed = 0.0

    def __enter__(self) -> "Timer":
        self.start_time = time.time()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.elapsed = time.time() - self.start_time
        if self.label:
            print(f"  ⏱️  {self.label}: {self.elapsed:.2f}s")


def print_header() -> None:
    """Stampa l'header del backtester."""
    print()
    print("=" * 60)
    print("  🚀 PYTHON BACKTESTER - Strategia Momentum/Drop")
    print("=" * 60)
    print()


def print_config_summary(
    symbols: List[str],
    start_date: str,
    end_date: str,
    n_combinations: int,
    direction: str,
) -> None:
    """Stampa un riepilogo della configurazione."""
    print("📋 Configurazione:")
    print(f"   Simboli:       {', '.join(symbols)}")
    print(f"   Date:          {start_date} -> {end_date}")
    print(f"   Direzione:     {direction}")
    print(f"   Combinazioni:  {n_combinations}")
    print()


def print_top_results(results: List[BacktestResult], top_n: int = 10) -> None:
    """
    Stampa le top N combinazioni ordinate per total_pnl (o total_pnl_percent in signal-only).

    Args:
        results: lista di BacktestResult
        top_n: numero di risultati da mostrare
    """
    if not results:
        print("  ⚠️  Nessun risultato da mostrare")
        return

    # Determina se siamo in signal-only
    is_signal_only = results[0].params.direction == "signal-only"

    # Ordina per total_pnl o total_pnl_percent
    if is_signal_only:
        sorted_results = sorted(results, key=lambda r: r.total_pnl_percent, reverse=True)
    else:
        sorted_results = sorted(results, key=lambda r: r.total_pnl, reverse=True)

    top = sorted_results[:top_n]

    print(f"\n🏆 Top {min(top_n, len(top))} combinazioni:")
    print("-" * 90)

    if is_signal_only:
        print(f"  {'#':<3} {'X%':<6} {'Y(s)':<6} {'Z%':<6} {'Trades':<8} {'Win%':<7} {'PnL%':<10} {'Avg%':<8} {'PF':<6}")
        print("-" * 90)
        for idx, r in enumerate(top, 1):
            print(
                f"  {idx:<3} "
                f"{r.params.x_percent:<6.1f} "
                f"{r.params.y_seconds:<6} "
                f"{r.params.z_percent:<6.1f} "
                f"{r.total_trades:<8} "
                f"{r.win_rate:<7.1f} "
                f"{r.total_pnl_percent:<10.4f} "
                f"{r.average_pnl:<8.4f} "
                f"{r.profit_factor:<6.2f}"
            )
    else:
        print(f"  {'#':<3} {'X%':<6} {'Y(s)':<6} {'Z%':<6} {'Trades':<8} {'Win%':<7} {'PnL($)':<10} {'MaxDD%':<8} {'PF':<6}")
        print("-" * 90)
        for idx, r in enumerate(top, 1):
            print(
                f"  {idx:<3} "
                f"{r.params.x_percent:<6.1f} "
                f"{r.params.y_seconds:<6} "
                f"{r.params.z_percent:<6.1f} "
                f"{r.total_trades:<8} "
                f"{r.win_rate:<7.1f} "
                f"{r.total_pnl:<10.4f} "
                f"{r.max_drawdown:<8.4f} "
                f"{r.profit_factor:<6.2f}"
            )

    print("-" * 90)
    print()


def print_completion(output_dir: str, elapsed: float) -> None:
    """Stampa il messaggio di completamento."""
    print(f"✅ Backtest completato in {elapsed:.2f} secondi")
    print(f"📁 Risultati salvati in: {output_dir}")
    print()
