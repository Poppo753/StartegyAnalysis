"""
trade_profile.py - Analisi diagnostica approfondita dei trades

Risponde alle domande chiave:
  1. Quanti trade escono per max-hold vs drop-z?
  2. MAE/MFE: nel tempo che il trade era aperto, di quanto è andato
     contro di noi (Max Adverse Excursion) e di quanto a favore (Max
     Favorable Excursion)?
  3. Cosa succede DOPO un uscita max-hold? Avremmo guadagnato aspettando di
     più? (usando i dati OHLC originali)
  4. Simulazione "extended hold": con 4h, 8h, 24h cosa sarebbe successo?
  5. Time-to-MFE: quanto tempo ci vuole prima che il prezzo scenda del X%
     dall'entry (tesi di reversal)?

DIREZIONE ASSUNTA: SHORT (dopo un pump → si shorta aspettando il reversal).
Cambia la costante DIRECTION se stai testando LONG.

Utilizzo:
    python trade_profile.py                          # tutti i trades_*.csv in backtest-results
    python trade_profile.py backtest-results/UNIUSDT/gpu/trades_train_001_x20.0_y86400_z12.4.csv
    python trade_profile.py --ohlc ../data/UNIUSDT/ohlc/ohlc_1s_2026-01-01_2026-05-05.csv ...
    python trade_profile.py --extended-hold 7200 14400 28800 86400 ...  (secondi)
"""

import os
import sys
import glob
import argparse
import numpy as np
import pandas as pd
from typing import List, Optional

from src.utils.trade_utils import load_trades

# ─────────────────────────────────────────────────────────────────────────────
DIRECTION = "short"          # "long" o "short"
DEFAULT_POSITION_SIZE = 100.0
DEFAULT_FEE_RATE = 0.001
DEFAULT_SLIPPAGE = 0.0005
DEFAULT_EXT_HOLDS = [7200, 14400, 28800, 86400]   # 2h 4h 8h 24h in secondi
# ─────────────────────────────────────────────────────────────────────────────


# ════════════════════════════════════════════════════════════════════════
# 1.  CARICAMENTO
# ════════════════════════════════════════════════════════════════════════

def load_ohlc(filepath: str) -> pd.DataFrame:
    print(f"  [OHLC] Caricamento {os.path.basename(filepath)}...", end="", flush=True)
    df = pd.read_csv(filepath)
    df["dt"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("dt").reset_index(drop=True)
    df["epoch_s"] = df["dt"].astype(np.int64) // 10**9
    print(f" {len(df):,} candele.")
    return df


# ════════════════════════════════════════════════════════════════════════
# 2.  MAE / MFE
# ════════════════════════════════════════════════════════════════════════

def compute_mae_mfe(df: pd.DataFrame) -> pd.DataFrame:
    """
    MAE = Max Adverse Excursion = quanto va contro di noi
    MFE = Max Favorable Excursion = quanto va a favore

    Per SHORT:
       MAE% = (max_price - entry) / entry * 100   (prezzo salito → avverso)
       MFE% = (entry - min_price) / entry * 100   (prezzo sceso → favorevole)

    Per LONG:
       MAE% = (entry - min_price) / entry * 100
       MFE% = (max_price - entry) / entry * 100
    """
    e = df["entry_price"]
    mx = df["max_price_during_trade"]
    mn = df["min_price_during_trade"]

    if DIRECTION == "short":
        df = df.copy()
        df["mae_pct"] = ((mx - e) / e * 100).clip(lower=0)
        df["mfe_pct"] = ((e - mn) / e * 100).clip(lower=0)
    else:
        df = df.copy()
        df["mae_pct"] = ((e - mn) / e * 100).clip(lower=0)
        df["mfe_pct"] = ((mx - e) / e * 100).clip(lower=0)

    df["mfe_gt_mae"] = df["mfe_pct"] > df["mae_pct"]
    # Quality: quanta parte del movimento era a favore?  0=tutto contro, 1=tutto a favore
    total = df["mfe_pct"] + df["mae_pct"]
    df["quality"] = np.where(total > 0, df["mfe_pct"] / total, 0.5)
    return df


# ════════════════════════════════════════════════════════════════════════
# 3.  FORWARD ANALYSIS SU OHLC
# ════════════════════════════════════════════════════════════════════════

def forward_pnl(ohlc: pd.DataFrame, entry_epoch: float, entry_price: float,
                hold_seconds: float, fee_rate: float, position_size: float) -> Optional[float]:
    """
    Simula un trade esteso: parti da entry_epoch, esci dopo hold_seconds.
    Restituisce pnl_percent, oppure None se non ci sono dati sufficienti.
    """
    exit_epoch = entry_epoch + hold_seconds
    # Trova la candela di uscita più vicina
    idx = np.searchsorted(ohlc["epoch_s"].values, exit_epoch, side="left")
    if idx >= len(ohlc):
        return None
    exit_price_raw = ohlc["close"].iloc[idx]
    # Slippage
    if DIRECTION == "short":
        exit_price = exit_price_raw * (1.0 + DEFAULT_SLIPPAGE)
        pnl = position_size - (position_size / entry_price) * exit_price - fee_rate * position_size * 2
    else:
        exit_price = exit_price_raw * (1.0 - DEFAULT_SLIPPAGE)
        pnl = (position_size / entry_price) * exit_price - position_size - fee_rate * position_size * 2
    return pnl / position_size * 100.0


def simulate_extended_hold(df: pd.DataFrame, ohlc: pd.DataFrame,
                           hold_values: List[float],
                           fee_rate: float = DEFAULT_FEE_RATE,
                           position_size: float = DEFAULT_POSITION_SIZE) -> pd.DataFrame:
    """
    Per ogni trade testa diversi valori di max_hold sull'OHLC reale.
    Restituisce tabella con medie pnl% per ogni hold time.
    """
    results: Dict[float, List[float]] = {}
    epoch_arr = ohlc["epoch_s"].values

    for h in hold_values:
        pnls: List[float] = []
        for _, row in df.iterrows():
            entry_epoch = row["entry_time"].timestamp()
            ep = forward_pnl(ohlc, entry_epoch, row["entry_price"],
                             h, fee_rate, position_size)
            pnls.append(ep)
        results[h] = pnls

    out = df[["entry_time", "entry_price", "pnl_percent", "reason"]].copy()
    for h in hold_values:
        label = _fmt_hold(h)
        out[f"pnl@{label}"] = results[h]
    return out


def _fmt_hold(seconds: float) -> str:
    if seconds >= 86400:
        return f"{seconds/86400:.0f}d"
    elif seconds >= 3600:
        return f"{seconds/3600:.0f}h"
    else:
        return f"{seconds/60:.0f}m"


# ════════════════════════════════════════════════════════════════════════
# 4.  TIME-TO-REVERSAL
# ════════════════════════════════════════════════════════════════════════

def time_to_reversal(df: pd.DataFrame, ohlc: pd.DataFrame,
                      target_pct: float = 1.0,
                      max_look_seconds: float = 86400 * 3) -> pd.Series:
    """
    Per ogni trade, cerca quanti secondi ci vogliono (dall'entry)
    perché il prezzo scenda di target_pct% sotto l'entry (per SHORT).
    Restituisce Serie con i secondi, NaN se non avviene entro max_look_seconds.
    """
    epoch_arr = ohlc["epoch_s"].values
    close_arr = ohlc["close"].values
    times: List[Optional[float]] = []
    for _, row in df.iterrows():
        entry_epoch = row["entry_time"].timestamp()
        entry_price = row["entry_price"]
        if DIRECTION == "short":
            target_price = entry_price * (1 - target_pct / 100.0)
            compare = lambda p: p <= target_price
        else:
            target_price = entry_price * (1 + target_pct / 100.0)
            compare = lambda p: p >= target_price

        start_idx = np.searchsorted(epoch_arr, entry_epoch, side="left")
        end_epoch = entry_epoch + max_look_seconds
        end_idx = np.searchsorted(epoch_arr, end_epoch, side="right")

        found: Optional[float] = None
        for k in range(start_idx, min(end_idx, len(epoch_arr))):
            if compare(close_arr[k]):
                found = epoch_arr[k] - entry_epoch
                break
        times.append(found)
    return pd.Series(times, name=f"secs_to_{target_pct:.1f}pct")


# ════════════════════════════════════════════════════════════════════════
# 5.  REPORTING
# ════════════════════════════════════════════════════════════════════════

def report(df: pd.DataFrame, ohlc: Optional[pd.DataFrame],
           ext_holds: List[float],
           position_size: float, fee_rate: float,
           filename: str) -> None:

    df = compute_mae_mfe(df)
    n = len(df)

    print(f"\n{'═'*72}")
    print(f"  {filename}  ({n} trades, direzione={DIRECTION})")
    print(f"{'═'*72}")

    # ── A. Exit reason breakdown ──────────────────────────────────
    print(f"\n  {'─'*30} A. Exit reason {'─'*20}")
    reasons = df["reason"].value_counts()
    for r, cnt in reasons.items():
        pct = cnt / n * 100
        sub = df[df["reason"] == r]
        avg_pnl = sub["pnl_percent"].mean()
        print(f"    {r:<15} {cnt:>4} ({pct:5.1f}%)   avg pnl_pct={avg_pnl:+.3f}%")

    # ── B. MAE / MFE globale ──────────────────────────────────────
    print(f"\n  {'─'*30} B. MAE / MFE {'─'*22}")
    print(f"    {'':20}  {'Tutti':>8}  {'Vincenti':>10}  {'Perdenti':>10}")
    for col, label in [("mae_pct", "Max Adverse (%)"),
                       ("mfe_pct", "Max Favorable (%)")]:
        vals_all  = df[col]
        vals_win  = df[df["pnl_percent"] > 0][col]
        vals_lose = df[df["pnl_percent"] <= 0][col]
        def s(v: pd.Series) -> str:
            return f"{v.mean():+.2f} ± {v.std():.2f}" if len(v) > 0 else "N/A"
        print(f"    {label:<20}  {s(vals_all):>20}  {s(vals_win):>18}  {s(vals_lose):>18}")

    n_mfe_gt = df["mfe_gt_mae"].sum()
    print(f"\n    Trade in cui MFE > MAE (prezzo è andato più a favore che contro): "
          f"{n_mfe_gt}/{n} ({n_mfe_gt/n*100:.0f}%)")
    print(f"    Quality medio (MFE/totale movimento):  {df['quality'].mean():.2f}  "
          f"(>0.5 = prevalentemente a favore)")

    # ── C. MAE/MFE per exit reason ────────────────────────────────
    print(f"\n  {'─'*30} C. MAE/MFE per exit reason {'─'*8}")
    for r in reasons.index:
        sub = df[df["reason"] == r]
        print(f"    {r:<15}  MAE={sub['mae_pct'].mean():.2f}%  "
              f"MFE={sub['mfe_pct'].mean():.2f}%  "
              f"quality={sub['quality'].mean():.2f}  "
              f"n={len(sub)}")

    # ── D. Distribuzione MAE per i MAX-HOLD ───────────────────────
    mh = df[df["reason"] == "max-hold"]
    if len(mh) > 0:
        print(f"\n  {'─'*30} D. Max-hold: distribuzione MAE e MFE {'─'*1}")
        print(f"    n={len(mh)}  MAE medio={mh['mae_pct'].mean():.2f}%  "
              f"MFE medio={mh['mfe_pct'].mean():.2f}%")
        # Quanti max-hold avevano MFE > 0 ma ancora perso?
        mh_had_mfe = (mh["mfe_pct"] > 0.1).sum()
        mh_zero_mfe = (mh["mfe_pct"] <= 0.1).sum()
        print(f"    Con MFE > 0.1% (prezzo è sceso almeno un po'): {mh_had_mfe} ({mh_had_mfe/len(mh)*100:.0f}%)")
        print(f"    Con MFE ≈ 0 (prezzo NON è mai andato a favore): {mh_zero_mfe} ({mh_zero_mfe/len(mh)*100:.0f}%)")
        # Percentili MAE
        p = mh["mae_pct"].quantile([0.25, 0.5, 0.75, 0.9, 1.0]).to_dict()
        print(f"    MAE percentili: p25={p[0.25]:.2f}%  p50={p[0.5]:.2f}%  "
              f"p75={p[0.75]:.2f}%  p90={p[0.9]:.2f}%  max={p[1.0]:.2f}%")

    # ── E. Extended hold su OHLC ──────────────────────────────────
    if ohlc is not None and len(ext_holds) > 0:
        print(f"\n  {'─'*30} E. Simulazione extended hold (su OHLC reale) {'─'*0}")
        print(f"    (Sostituisce il max-hold fisso —  stessa Z% non applicata, "
              "uscita time-based pura)")
        ext_df = simulate_extended_hold(df, ohlc, ext_holds, fee_rate, position_size)

        labels = [_fmt_hold(h) for h in ext_holds]
        header = f"    {'':>22}" + "".join(f"  {l:>7}" for l in labels)
        print(header)

        # Avg PnL per hold
        row_avg  = "    avg pnl_pct          "
        row_win  = "    win rate             "
        row_best = "    best trade           "
        row_wrst = "    worst trade          "
        for h, lbl in zip(ext_holds, labels):
            col = f"pnl@{lbl}"
            v = ext_df[col].dropna()
            if len(v) == 0:
                row_avg  += f"  {'N/A':>7}"
                row_win  += f"  {'N/A':>7}"
                row_best += f"  {'N/A':>7}"
                row_wrst += f"  {'N/A':>7}"
            else:
                row_avg  += f"  {v.mean():>+7.2f}"
                row_win  += f"  {(v>0).mean()*100:>7.1f}"
                row_best += f"  {v.max():>+7.2f}"
                row_wrst += f"  {v.min():>+7.2f}"
        print(row_avg + "%")
        print(row_win + "%")
        print(row_best + "%")
        print(row_wrst + "%")

        # Solo i max-hold originali
        mh_ext = ext_df[ext_df["reason"] == "max-hold"]
        if len(mh_ext) > 0:
            print(f"\n    Solo trades che erano usciti per max-hold (n={len(mh_ext)}):")
            r2 = "    avg pnl_pct (mh)     "
            r3 = "    win rate  (mh)       "
            for h, lbl in zip(ext_holds, labels):
                col = f"pnl@{lbl}"
                v = mh_ext[col].dropna()
                if len(v) == 0:
                    r2 += f"  {'N/A':>7}"; r3 += f"  {'N/A':>7}"
                else:
                    r2 += f"  {v.mean():>+7.2f}"; r3 += f"  {(v>0).mean()*100:>7.1f}"
            print(r2 + "%")
            print(r3 + "%")

    # ── F. Time-to-reversal ───────────────────────────────────────
    if ohlc is not None:
        print(f"\n  {'─'*30} F. Time-to-reversal (quanto ci vuole per tornare a favore) ──")
        for target in [0.5, 1.0, 2.0, 3.0]:
            t = time_to_reversal(df, ohlc, target_pct=target)
            reached = t.notna().sum()
            if reached > 0:
                med = t.median() / 3600
                p90 = t.quantile(0.9) / 3600
                print(f"    price -{target:.1f}% dall'entry: "
                      f"{reached}/{n} trades ({reached/n*100:.0f}%) lo raggiungono  "
                      f"[mediana={med:.1f}h  p90={p90:.1f}h]")
            else:
                print(f"    price -{target:.1f}% dall'entry: 0/{n} trades lo raggiungono entro 3 giorni")

    # ── G. Diagnosi finale ────────────────────────────────────────
    _diagnose(df)


def _diagnose(df: pd.DataFrame) -> None:
    print(f"\n  {'─'*30} G. Diagnosi {'─'*24}")
    mh_pct = (df["reason"] == "max-hold").mean() * 100
    mfe = df["mfe_pct"].mean()
    mae = df["mae_pct"].mean()
    q   = df["quality"].mean()

    print(f"    {mh_pct:.0f}% dei trade escono per max-hold (il prezzo non si muove abbastanza "
          "nella finestra temporale).")
    print(f"    Movimento medio a favore (MFE): {mfe:.2f}%")
    print(f"    Movimento medio contro  (MAE): {mae:.2f}%")

    if q < 0.3:
        print(f"\n  ⚠  PROBLEMA PRINCIPALE: il prezzo va prevalentemente CONTRO (quality={q:.2f}).")
        print(f"     → La tesi di reversal è debole. Shortiamo durante un uptrend, non al top.")
        print(f"     Cosa considerare:")
        print(f"       - Aggiungere un filtro di 'raffreddamento': aspetta N minuti dopo il picco")
        print(f"       - Cambiare il segnale: X% in Y secondi → cercare pattern di double-top o volume spike")
        print(f"       - Aumentare X% molto: solo pump estremi tendono a revertare")
    elif q < 0.5:
        print(f"\n  ⚠  Il prezzo va contro più di quanto va a favore (quality={q:.2f}).")
        print(f"     → Il timing dell'entry è sbagliato — si entra troppo presto.")
        print(f"     Cosa considerare:")
        print(f"       - Ritardare l'entry: aspetta un primo 'lower high' prima di shortare")
        print(f"       - Ridurre Y per prendere solo pump rapidi (già esauriti)")
        print(f"       - Entry in zone di prezzo specifiche (resistenze note)")
    else:
        print(f"\n  ✓  Il prezzo va prevalentemente a favore (quality={q:.2f}).")
        print(f"     Il problema è l'exit, non l'entry. Considera:")
        print(f"       - Estendere max_hold (vedi sezione E)")
        print(f"       - Ridurre Z% per uscire più velocemente sui vincenti")


# ════════════════════════════════════════════════════════════════════════
# 6.  MAIN
# ════════════════════════════════════════════════════════════════════════

def main() -> int:
    """Entry point CLI. Ritorna l'exit code; sys.exit solo nel blocco __main__."""
    global DIRECTION
    p = argparse.ArgumentParser(description="Profilazione MAE/MFE e extended-hold dei trades")
    p.add_argument("files", nargs="*", help="File CSV trades (default: auto-discover)")
    p.add_argument("--ohlc",  help="File OHLC 1s (necessario per extended-hold e time-to-reversal)")
    p.add_argument("--extended-hold", nargs="+", type=float, default=DEFAULT_EXT_HOLDS,
                   dest="ext_holds", metavar="SECONDS",
                   help="Hold times in secondi per la simulazione (default: 7200 14400 28800 86400)")
    p.add_argument("--direction", default=DIRECTION, choices=["long", "short"],
                   help="Direzione delle posizioni (default: short)")
    p.add_argument("--position-size", type=float, default=DEFAULT_POSITION_SIZE)
    p.add_argument("--fee-rate", type=float, default=DEFAULT_FEE_RATE)
    args = p.parse_args()

    # override direzione globale (evita import circolare fragile)
    DIRECTION = args.direction

    if args.files:
        trade_files = args.files
    else:
        trade_files = sorted(glob.glob(
            "./backtest-results/**/trades_*.csv", recursive=True
        ))
    trade_files = [f for f in trade_files if os.path.basename(f).startswith("trades_")]

    if not trade_files:
        print("Nessun file trades trovato.", file=sys.stderr)
        return 2

    ohlc = None
    if args.ohlc:
        ohlc = load_ohlc(args.ohlc)

    print(f"\n{'═'*72}")
    print(f"  TRADE PROFILER — MAE/MFE + Extended Hold Analysis")
    print(f"  Direzione: {DIRECTION}  |  Files: {len(trade_files)}")
    if ohlc is not None:
        labels = [_fmt_hold(h) for h in args.ext_holds]
        print(f"  Extended holds: {labels}")
    print(f"{'═'*72}")

    for f in trade_files:
        try:
            df = load_trades(f, ["entry_time", "exit_time", "entry_price", "exit_price",
                                 "max_price_during_trade", "min_price_during_trade",
                                 "pnl", "pnl_percent", "fees", "reason"])
            report(df, ohlc, args.ext_holds, args.position_size, args.fee_rate,
                   os.path.basename(f))
        except Exception as e:
            print(f"\n  [SKIP] {f}: {e}")

    print(f"\n{'═'*72}")
    print(f"  Fine analisi.")
    print(f"{'═'*72}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
