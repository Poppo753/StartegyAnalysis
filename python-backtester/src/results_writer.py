"""
results_writer.py - Scrittura dei risultati su disco

Crea la struttura di output:
  backtest-results/
    {SYMBOL}/
      summary_{START_DATE}_{END_DATE}.csv
      trades_x{X}_y{Y}_z{Z}.csv
"""

import os
import pandas as pd
from typing import List
from src.config import Config
from src.strategy import BacktestResult, Trade


def write_results(
    results: List[BacktestResult],
    config: Config,
    symbol: str,
) -> str:
    """
    Scrive tutti i risultati del backtest su disco.

    Crea:
    - Un file summary CSV con una riga per combinazione
    - Un file trades CSV per ogni combinazione

    Args:
        results: lista di BacktestResult (uno per combinazione)
        config: configurazione del backtester
        symbol: simbolo testato

    Returns:
        Percorso della cartella di output
    """
    # Crea directory di output
    output_dir = os.path.join(config.output_dir, symbol)
    os.makedirs(output_dir, exist_ok=True)

    # --- Scrivi summary ---
    summary_filename = f"summary_{config.start_date}_{config.end_date}.csv"
    summary_path = os.path.join(output_dir, summary_filename)
    _write_summary(results, summary_path)

    # --- Scrivi trades per ogni combinazione ---
    for result in results:
        if result.trades:
            trades_filename = (
                f"trades_x{result.params.x_percent}_y{result.params.y_seconds}_z{result.params.z_percent}.csv"
            )
            trades_path = os.path.join(output_dir, trades_filename)
            _write_trades(result.trades, trades_path)

    return output_dir


def _write_summary(results: List[BacktestResult], filepath: str) -> None:
    """
    Scrive il file summary CSV.

    Ogni riga contiene le metriche per una combinazione X/Y/Z.

    Args:
        results: lista di BacktestResult
        filepath: percorso di output
    """
    rows = []
    for r in results:
        rows.append({
            "symbol": r.symbol,
            "x_percent": r.params.x_percent,
            "y_seconds": r.params.y_seconds,
            "z_percent": r.params.z_percent,
            "total_trades": r.total_trades,
            "winning_trades": r.winning_trades,
            "losing_trades": r.losing_trades,
            "win_rate": round(r.win_rate, 2),
            "total_pnl": round(r.total_pnl, 4),
            "total_pnl_percent": round(r.total_pnl_percent, 4),
            "max_drawdown": round(r.max_drawdown, 4),
            "average_pnl": round(r.average_pnl, 4),
            "best_trade": round(r.best_trade, 4),
            "worst_trade": round(r.worst_trade, 4),
            "profit_factor": round(r.profit_factor, 4),
        })

    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False)
    print(f"  📄 Summary salvato: {filepath}")


def _write_trades(trades: List[Trade], filepath: str) -> None:
    """
    Scrive il file trades CSV per una combinazione.

    Args:
        trades: lista di Trade
        filepath: percorso di output
    """
    rows = []
    for t in trades:
        rows.append({
            "symbol": t.symbol,
            "entry_time": t.entry_time,
            "exit_time": t.exit_time,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "max_price_during_trade": t.max_price_during_trade,
            "min_price_during_trade": t.min_price_during_trade,
            "pnl": round(t.pnl, 6),
            "pnl_percent": round(t.pnl_percent, 4),
            "fees": round(t.fees, 6),
            "reason": t.reason,
            "x_percent": t.x_percent,
            "y_seconds": t.y_seconds,
            "z_percent": t.z_percent,
        })

    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False)