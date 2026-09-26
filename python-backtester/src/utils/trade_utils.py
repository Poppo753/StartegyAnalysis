"""
trade_utils.py - Funzioni di utilità condivise per analisi post-hoc dei trades.

Single source of truth per:
- load_trades: caricamento CSV trades con validazione colonne
- calc_metrics: metriche aggregate da array pnl
- format_metrics / diagnose: reporting testuale condiviso
- load_ohlc_data: caricamento OHLC generati dalla pipeline TypeScript

Pattern errori:
- Solleva ValueError / DataLoadError, MAI sys.exit().
  L'exit è consentito solo al boundary CLI (main / trade_profile.__main__).
"""

import os
from typing import List, Dict, Any

import numpy as np
import pandas as pd

from src.config import Config


class DataLoadError(ValueError):
    """Errore di caricamento/validazione di un file dati (trades o OHLC)."""
    pass


def load_trades(filepath: str, required_columns: List[str]) -> pd.DataFrame:
    """
    Carica un CSV trades e valida le colonne richieste.

    Normalizza i nomi legacy max_price/min_price -> max_price_during_trade /
    min_price_during_trade. Se presenti entry_time/exit_time calcola hold_seconds.

    Args:
        filepath: percorso CSV trades.
        required_columns: colonne che devono esistere dopo la normalizzazione.

    Returns:
        DataFrame validato.

    Raises:
        DataLoadError: se file mancante, illeggibile o con colonne mancanti.
    """
    if not os.path.exists(filepath):
        raise DataLoadError(f"File non trovato: {filepath}")

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise DataLoadError(f"Impossibile leggere il CSV trades: {filepath}: {e}") from e

    df = df.rename(columns={
        "max_price": "max_price_during_trade",
        "min_price": "min_price_during_trade",
    })

    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise DataLoadError(f"Colonne mancanti in {filepath}: {missing}")

    if "entry_time" in df.columns and "exit_time" in df.columns:
        df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)
        df["exit_time"] = pd.to_datetime(df["exit_time"], utc=True)
        df["hold_seconds"] = (df["exit_time"] - df["entry_time"]).dt.total_seconds()

    return df


def calc_metrics(pnls: np.ndarray, capital: float) -> Dict[str, Any]:
    """
    Calcola metriche aggregate da un array di pnl.

    Args:
        pnls: array 1D di pnl per trade.
        capital: capitale iniziale per drawdown percentuale.

    Returns:
        Dict con n, nw, nl, wr, avg_w, avg_l, gp, gl, pf, total,
        best, worst, dd_u, dd_p, expect. {} se nessun trade.
    """
    pnls = np.asarray(pnls, dtype=float)
    if pnls.size == 0:
        return {}

    win_mask = pnls > 0
    winning = pnls[win_mask]
    losing = pnls[~win_mask]
    n, nw, nl = int(pnls.size), int(winning.size), int(losing.size)
    wr = nw / n * 100.0
    avg_w = float(np.mean(winning)) if nw > 0 else 0.0
    avg_l = float(np.mean(losing)) if nl > 0 else 0.0
    gp = float(np.sum(winning)) if nw > 0 else 0.0
    gl = float(np.sum(losing)) if nl > 0 else 0.0
    pf = gp / abs(gl) if gl < 0 else (999.0 if gp > 0 else 0.0)
    equity = capital + np.cumsum(pnls)
    rmax = np.maximum.accumulate(np.concatenate(([capital], equity)))[1:]
    dd_u = float(np.max(rmax - equity))
    dd_p = dd_u / capital * 100.0 if capital > 0 else 0.0
    expect = wr / 100.0 * avg_w + (1 - wr / 100.0) * avg_l

    return dict(
        n=n, nw=nw, nl=nl, wr=wr, avg_w=avg_w, avg_l=avg_l,
        gp=gp, gl=gl, pf=pf,
        total=float(np.sum(pnls)),
        best=float(np.max(pnls)), worst=float(np.min(pnls)),
        dd_u=dd_u, dd_p=dd_p, expect=expect,
    )


def format_metrics(m: Dict[str, Any]) -> str:
    """Ritorna (non stampa) il blocco metriche formattato."""
    lines = [
        f"    Trades: {m['n']}  Win: {m['wr']:.1f}%  "
        f"AvgWin: {m['avg_w']:.3f}  AvgLoss: {m['avg_l']:.3f}",
        f"    PF: {m['pf']:.3f}  TotalPnL: {m['total']:+.2f}  "
        f"MaxDD: {m['dd_p']:.2f}%  Worst: {m['worst']:.2f}",
        f"    Expectancy/trade: {m['expect']:.4f}",
    ]
    return "\n".join(lines)


def _fmt_metrics(m: Dict[str, Any]) -> str:
    """Alias legacy per compatibilità con import esistenti."""
    return format_metrics(m)


def diagnose(m: Dict[str, Any], position_size: float) -> str:
    """Ritorna (non stampa) la diagnosi break-even / worst-trade."""
    ratio = abs(m["avg_l"]) / m["avg_w"] if m["avg_w"] > 0 else float("inf")
    be_wr = ratio / (1.0 + ratio) * 100.0 if ratio != float("inf") else 100.0
    gap = m["wr"] - be_wr
    lines = [
        "",
        "  --- DIAGNOSI ---",
        f"    |AvgLoss|/AvgWin = {ratio:.2f}x  ->  break-even WR: {be_wr:.1f}%",
        f"    WR attuale: {m['wr']:.1f}%  ->  gap: {gap:+.1f}%  "
        + ("(PERDENTE)" if gap < 0 else "(PROFITTEVOLE))"),
        f"    Worst trade: {m['worst']:.2f} USDT  "
        f"({abs(m['worst']) / position_size * 100:.1f}% della posizione)"
        if position_size > 0 else f"    Worst trade: {m['worst']:.2f} USDT",
    ]
    return "\n".join(lines)


def _diagnose(m: Dict[str, Any], position_size: float) -> str:
    """Alias legacy per compatibilità."""
    return diagnose(m, position_size)


def load_ohlc_data(config: Config, symbol: str) -> pd.DataFrame:
    """
    Carica l'OHLC 1s generato dalla pipeline TypeScript.

    Path: {data_dir}/{symbol}/ohlc/ohlc_{timeframe}_{start}_{end}.csv

    Raises:
        DataLoadError: se file mancante, vuoto, illeggibile o con colonne mancanti.
    """
    filename = f"ohlc_{config.timeframe}_{config.start_date}_{config.end_date}.csv"
    filepath = os.path.normpath(os.path.join(config.data_dir, symbol, "ohlc", filename))

    if not os.path.exists(filepath):
        raise DataLoadError(
            f"File non trovato: {filepath}. "
            f"Genera i dati con la pipeline TypeScript per {symbol} "
            f"({config.start_date} -> {config.end_date})."
        )
    if os.path.getsize(filepath) == 0:
        raise DataLoadError(f"File vuoto: {filepath}")

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise DataLoadError(f"Impossibile leggere il CSV OHLC: {filepath}: {e}") from e

    required_columns = ["timestamp", "open", "high", "low", "close", "volume", "tradeCount"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise DataLoadError(
            f"Colonne mancanti nel CSV {filepath}: {missing_columns}. "
            f"Trovate: {list(df.columns)}"
        )
    if df.empty:
        raise DataLoadError(f"Nessuna riga nel file: {filepath}")

    sample_ts = str(df["timestamp"].iloc[0])
    if sample_ts.replace(".", "").replace("-", "").isdigit():
        df["datetime"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms", utc=True)
    else:
        df["datetime"] = pd.to_datetime(df["timestamp"], utc=True)

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["tradeCount"] = pd.to_numeric(df["tradeCount"], errors="coerce").fillna(0).astype(int)

    df = df.sort_values("datetime").reset_index(drop=True)

    try:
        df["epoch_seconds"] = (
            df["datetime"] - pd.Timestamp("1970-01-01", tz="UTC")
        ).dt.total_seconds()
    except Exception:
        df["epoch_seconds"] = (
            pd.to_datetime(df["datetime"], utc=True) - pd.Timestamp("1970-01-01", tz="UTC")
        ).dt.total_seconds()

    if df["epoch_seconds"].isna().all():
        raise DataLoadError(f"Timestamp non convertibili in epoch_seconds: {filepath}")

    return df


def expected_candles(df: pd.DataFrame) -> int:
    """Secondi coperti dal DataFrame (ultima - prima datetime)."""
    if len(df) < 2:
        return len(df)
    total_seconds = (df["datetime"].iloc[-1] - df["datetime"].iloc[0]).total_seconds()
    return int(total_seconds)


def _expected_candles(df: pd.DataFrame) -> int:
    """Alias legacy."""
    return expected_candles(df)
