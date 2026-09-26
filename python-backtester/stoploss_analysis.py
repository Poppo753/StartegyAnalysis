"""
stoploss_analysis.py - Analisi post-hoc dell impatto di uno stop loss fisso

DIREZIONE:
  --direction long  (default): stop SOTTO entry, triggerato se min_price <= entry*(1-sl%)
  --direction short:            stop SOPRA entry, triggerato se max_price >= entry*(1+sl%)

Limiti:
  1. Sequential bias: chiudendo prima un trade, la strategia avrebbe
     potuto aprirne altri (sottostima del beneficio).
  2. Stop-and-recover: se il trade avrebbe poi recuperato, il SL viene
     contato come peggioramento (corretto).
"""

import os
import sys
import glob
import argparse
import numpy as np
import pandas as pd
from typing import List, Dict, Any

from src.utils.trade_utils import load_trades, calc_metrics, _fmt_metrics, _diagnose


DEFAULT_SL_LEVELS: List[float] = [1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0]
DEFAULT_POSITION_SIZE: float = 100.0
DEFAULT_CAPITAL: float = 1000.0
DEFAULT_DIRECTION: str = "short"  # "long" o "short"


def simulate_stoploss(df: pd.DataFrame, sl_pct: float, position_size: float, direction: str = "short") -> pd.DataFrame:
    """
    direction="short": stop SOPRA entry (protegge da pump continuo dopo entry short)
      stop_price = entry * (1 + sl_pct/100)
      triggered  = max_price >= stop_price
      pnl_sl     = -(sl_pct% della posizione) - fees  [perdita su short]

    direction="long": stop SOTTO entry (protegge da caduta dopo entry long)
      stop_price = entry * (1 - sl_pct/100)
      triggered  = min_price <= stop_price
      pnl_sl     = -(sl_pct% della posizione) - fees  [perdita su long]
    """
    sl_dec = sl_pct / 100.0
    result = df.copy()

    if direction == "short":
        stop_px = result["entry_price"] * (1.0 + sl_dec)
        trig    = result["max_price_during_trade"] >= stop_px
        # Short: perdi quando il prezzo SALE oltre lo stop
        qty     = position_size / result["entry_price"]
        pnl_sl  = position_size - qty * stop_px - result["fees"]  # negativo
    else:  # long
        stop_px = result["entry_price"] * (1.0 - sl_dec)
        trig    = result["min_price_during_trade"] <= stop_px
        qty     = position_size / result["entry_price"]
        pnl_sl  = qty * stop_px - position_size - result["fees"]  # negativo

    pct_sl = pnl_sl / position_size * 100.0

    result["sl_triggered"]    = trig
    result["new_pnl"]         = result["pnl"].copy()
    result["new_pnl_percent"] = result["pnl_percent"].copy()
    result.loc[trig, "new_pnl"]         = pnl_sl[trig]
    result.loc[trig, "new_pnl_percent"] = pct_sl[trig]
    return result


def analyze_file(filepath: str, sl_levels: List[float], position_size: float, capital: float, direction: str = "short") -> None:
    print(f"\n{'='*72}")
    print(f"  FILE: {os.path.relpath(filepath)}")
    print(f"{'='*72}")
    try:
        df = load_trades(filepath, ["entry_price", "exit_price",
                                     "min_price_during_trade", "max_price_during_trade",
                                     "pnl", "pnl_percent", "fees"])
    except Exception as e:
        print(f"  [SKIP] {e}")
        return
    if len(df) == 0:
        print("  [SKIP] Nessun trade.")
        return

    orig = calc_metrics(df["pnl"].values, capital)
    print(f"\n  Trades: {orig['n']}  (direction={direction})")
    print(f"\n  --- BASELINE (nessuno stop loss) ---")
    print(_fmt_metrics(orig))

    rows = []
    for sl in sl_levels:
        df_sl      = simulate_stoploss(df, sl, position_size, direction)
        n_trig     = int(df_sl["sl_triggered"].sum())
        n_cut_win  = int((df_sl["sl_triggered"] & (df["pnl"] > 0)).sum())
        n_save_los = int((df_sl["sl_triggered"] & (df["pnl"] <= 0)).sum())
        m          = calc_metrics(df_sl["new_pnl"].values, capital)
        rows.append({
            "SL%":       f"{sl:.1f}%",
            "Triggered": n_trig,
            "SaveLos":   n_save_los,
            "CutWin":    n_cut_win,
            "Win%":      f"{m['wr']:.1f}%",
            "TotalPnL":  f"{m['total']:+.2f}",
            "dPnL":      f"{m['total'] - orig['total']:+.2f}",
            "AvgWin":    f"{m['avg_w']:.3f}",
            "AvgLoss":   f"{m['avg_l']:.3f}",
            "PF":        f"{m['pf']:.3f}",
            "MaxDD%":    f"{m['dd_p']:.2f}%",
            "dMaxDD":    f"{m['dd_p'] - orig['dd_p']:+.2f}%",
            "Worst":     f"{m['worst']:.2f}",
        })

    print(f"\n  --- IMPATTO STOP LOSS ---")
    print(pd.DataFrame(rows).to_string(index=False))

    best_i  = int(np.argmax([float(r["dPnL"]) for r in rows]))
    best_dd = int(np.argmin([float(r["MaxDD%"].rstrip("%")) for r in rows]))
    print(f"\n  * Miglior SL per PnL: {rows[best_i]['SL%']}"
          f"  (dPnL={rows[best_i]['dPnL']}, MaxDD={rows[best_i]['MaxDD%']})")
    print(f"  * Minor MaxDD:        {rows[best_dd]['SL%']}"
          f"  (MaxDD={rows[best_dd]['MaxDD%']}, dPnL={rows[best_dd]['dPnL']})")

    print(_diagnose(orig, position_size))


def main() -> int:
    """Entry point CLI. Ritorna l'exit code; sys.exit solo nel blocco __main__."""
    parser = argparse.ArgumentParser(
        description="Analisi post-hoc stop loss su trades del backtest"
    )
    parser.add_argument("files", nargs="*",
                        help="File CSV trades. Ometti per ricerca automatica.")
    parser.add_argument("--sl", nargs="+", type=float, default=DEFAULT_SL_LEVELS,
                        metavar="PCT",
                        help="Stop loss levels in pct")
    parser.add_argument("--direction", default=DEFAULT_DIRECTION, choices=["long", "short"],
                        help="long: stop sotto entry | short: stop sopra entry (default: short)")
    parser.add_argument("--position-size", type=float, default=DEFAULT_POSITION_SIZE)
    parser.add_argument("--capital", type=float, default=DEFAULT_CAPITAL)
    args = parser.parse_args()

    if args.files:
        trade_files = args.files
    else:
        trade_files = sorted(
            glob.glob("./backtest-results/**/trades_*.csv", recursive=True)
        )
    trade_files = [f for f in trade_files
                   if os.path.basename(f).startswith("trades_")]

    if not trade_files:
        print("Nessun file trades_*.csv trovato. Specifica i file come argomenti.", file=sys.stderr)
        return 2

    print(f"\n{'='*72}")
    print(f"  STOP LOSS ANALYSIS")
    print(f"  Direction: {args.direction}  (SL {'sopra' if args.direction == 'short' else 'sotto'} entry)")
    print(f"  SL levels: {[f'{s:.1f}%' for s in args.sl]}")
    print(f"  Position: {args.position_size:.0f} USDT | Capital: {args.capital:.0f} USDT")
    print(f"  Files: {len(trade_files)}")
    print(f"{'='*72}")

    for f in trade_files:
        analyze_file(f, args.sl, args.position_size, args.capital, args.direction)

    print(f"\n{'='*72}")
    print("  Fine analisi.")
    print(f"{'='*72}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
