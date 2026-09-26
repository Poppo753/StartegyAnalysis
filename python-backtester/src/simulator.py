"""
simulator.py - Motore di simulazione del backtest

Implementa la logica core della strategia:
1. Scorre le candele OHLC 1s
2. Cerca segnali di ingresso (salita >= X% in Y secondi)
3. Monitora i trade aperti fino a chiusura (drop >= Z%, max_hold, end-of-data)
4. Calcola PnL con commissioni e slippage
"""

import numpy as np
import pandas as pd
from typing import List
from src.strategy import BacktestParams, Trade


def run_backtest(df: pd.DataFrame, params: BacktestParams, symbol: str) -> List[Trade]:
    """
    Esegue il backtest su un DataFrame di candele OHLC 1s.

    Logica:
    - Per ogni candela i, cerca la candela più recente che dista almeno y_seconds
    - Se il movimento >= x_percent, apre un trade
    - Monitora il trade fino a chiusura per drop-z, max-hold o end-of-data
    - Non apre trade sovrapposti (un trade alla volta)

    NOTA: I dati sono sparsi (solo candele con trade), quindi la logica
    temporale usa epoch_seconds invece degli indici.

    Args:
        df: DataFrame con colonne timestamp, open, high, low, close, volume, tradeCount, datetime, epoch_seconds
        params: parametri del backtest
        symbol: simbolo in esame

    Returns:
        Lista di Trade eseguiti
    """
    trades: List[Trade] = []
    n = len(df)

    if n == 0:
        return trades

    # Pre-calcolo array numpy per velocità
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    timestamps = df["datetime"].values  # numpy datetime64
    epoch_secs = df["epoch_seconds"].values  # float64, secondi epoch

    # Puntatore per la ricerca della candela passata (scorre in avanti)
    past_ptr = 0

    # Stato: indice da cui riprendere la scansione dopo un trade
    i = 0

    while i < n:
        # --- FASE 1: Cerca segnale di ingresso ---

        current_time = epoch_secs[i]
        target_past_time = current_time - params.y_seconds

        # Trova la candela più recente con tempo <= target_past_time
        # Usa binary search per efficienza
        past_idx = _find_candle_at_or_before(epoch_secs, target_past_time, 0, i)

        if past_idx is None:
            # Non c'è una candela abbastanza indietro nel tempo
            i += 1
            continue

        # Prezzo passato e corrente
        past_close = closes[past_idx]
        current_close = closes[i]

        # Evita divisione per zero
        if past_close == 0:
            i += 1
            continue

        # Calcola movimento percentuale
        move_percent = (current_close - past_close) / past_close * 100.0

        # Controlla se il segnale è attivo
        if move_percent >= params.x_percent:
            # --- FASE 2: Apri trade ---
            trade = _execute_trade(
                entry_idx=i,
                params=params,
                symbol=symbol,
                closes=closes,
                highs=highs,
                lows=lows,
                timestamps=timestamps,
                epoch_secs=epoch_secs,
                n=n,
            )

            if trade is not None:
                trades.append(trade)

                # Trova l'indice di uscita per saltare avanti
                # (non aprire trade sovrapposti)
                exit_idx = _find_exit_index_by_time(epoch_secs, trade.exit_time, timestamps)
                if exit_idx is not None:
                    i = exit_idx + 1
                else:
                    i += 1
            else:
                i += 1
        else:
            i += 1

    return trades


def _find_candle_at_or_before(
    epoch_secs: np.ndarray,
    target_time: float,
    start: int,
    end: int,
) -> int:
    """
    Trova l'indice della candela più recente con epoch_seconds <= target_time.
    Usa numpy searchsorted per efficienza.

    Args:
        epoch_secs: array ordinato di epoch seconds
        target_time: tempo target in epoch seconds
        start: indice di partenza per la ricerca
        end: indice di fine (esclusivo)

    Returns:
        Indice trovato o None se non esiste
    """
    if start >= end:
        return None

    # searchsorted trova dove inserire target_time per mantenere l'ordine
    # 'right' restituisce l'indice dopo l'ultimo elemento <= target_time
    idx = np.searchsorted(epoch_secs[start:end], target_time, side="right") + start

    # L'elemento a idx-1 è l'ultimo con valore <= target_time
    if idx > start:
        return idx - 1
    return None


def _execute_trade(
    entry_idx: int,
    params: BacktestParams,
    symbol: str,
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    timestamps: np.ndarray,
    epoch_secs: np.ndarray,
    n: int,
) -> Trade:
    """
    Esegue un singolo trade dall'indice di ingresso.

    Applica slippage all'entry, poi monitora fino a chiusura.
    Usa epoch_secs per calcolare il tempo reale trascorso.

    Args:
        entry_idx: indice della candela di ingresso
        params: parametri del backtest
        symbol: simbolo
        closes/highs/lows/timestamps/epoch_secs: array numpy pre-calcolati
        n: lunghezza totale del dataset

    Returns:
        Trade completato, o None se impossibile eseguire
    """
    raw_entry_price = closes[entry_idx]
    entry_time = pd.Timestamp(timestamps[entry_idx])
    entry_epoch = epoch_secs[entry_idx]

    # Applica slippage all'entry
    if params.direction == "long":
        # Long: entry peggiorato verso l'alto
        entry_price = raw_entry_price * (1.0 + params.slippage_rate)
    elif params.direction == "short":
        # Short: entry peggiorato verso il basso
        entry_price = raw_entry_price * (1.0 - params.slippage_rate)
    else:
        # signal-only: nessuno slippage
        entry_price = raw_entry_price

    # Inizializza tracking
    max_price = entry_price
    min_price = entry_price
    exit_idx = None
    reason = ""

    # --- FASE 3: Monitoraggio trade ---
    for j in range(entry_idx + 1, n):
        current_close = closes[j]
        current_high = highs[j]
        current_low = lows[j]

        # Aggiorna max/min durante il trade
        max_price = max(max_price, current_high)
        min_price = min(min_price, current_low)

        # Calcola tempo trascorso in SECONDI REALI
        seconds_elapsed = epoch_secs[j] - entry_epoch

        # Controlla drop dal massimo
        if max_price > 0:
            drop_percent = (max_price - current_close) / max_price * 100.0
        else:
            drop_percent = 0.0

        # Condizione di uscita: drop >= Z%
        if drop_percent >= params.z_percent:
            exit_idx = j
            reason = "drop-z"
            break

        # Condizione di uscita: max hold raggiunto (tempo reale)
        if seconds_elapsed >= params.max_hold_seconds:
            exit_idx = j
            reason = "max-hold"
            break

    # Se non è uscito nel loop, chiudi a fine dati
    if exit_idx is None:
        exit_idx = n - 1
        reason = "end-of-data"
        # Aggiorna max/min con l'ultima candela se non già fatto
        max_price = max(max_price, highs[exit_idx])
        min_price = min(min_price, lows[exit_idx])

    # Prezzo di uscita
    raw_exit_price = closes[exit_idx]
    exit_time = pd.Timestamp(timestamps[exit_idx])

    # Applica slippage all'exit
    if params.direction == "long":
        # Long: exit peggiorato verso il basso
        exit_price = raw_exit_price * (1.0 - params.slippage_rate)
    elif params.direction == "short":
        # Short: exit peggiorato verso l'alto
        exit_price = raw_exit_price * (1.0 + params.slippage_rate)
    else:
        # signal-only: nessuno slippage
        exit_price = raw_exit_price

    # --- FASE 4: Calcolo PnL ---
    fees, pnl, pnl_percent = _calculate_pnl(
        entry_price=entry_price,
        exit_price=exit_price,
        params=params,
    )

    mae_pct = 0.0
    mfe_pct = 0.0
    if entry_price > 0:
        if params.direction == "short":
            mae_pct = (max_price - entry_price) / entry_price * 100.0
            mfe_pct = (entry_price - min_price) / entry_price * 100.0
        else:
            mae_pct = (entry_price - min_price) / entry_price * 100.0
            mfe_pct = (max_price - entry_price) / entry_price * 100.0

    return Trade(
        symbol=symbol,
        entry_time=entry_time,
        exit_time=exit_time,
        entry_price=entry_price,
        exit_price=exit_price,
        max_price_during_trade=max_price,
        min_price_during_trade=min_price,
        pnl=pnl,
        pnl_percent=pnl_percent,
        fees=fees,
        reason=reason,
        x_percent=params.x_percent,
        y_seconds=params.y_seconds,
        z_percent=params.z_percent,
        mae_pct=mae_pct,
        mfe_pct=mfe_pct,
    )


def _calculate_pnl(
    entry_price: float,
    exit_price: float,
    params: BacktestParams,
) -> tuple:
    """
    Calcola commissioni, PnL e PnL percentuale.

    Args:
        entry_price: prezzo di ingresso (con slippage applicato)
        exit_price: prezzo di uscita (con slippage applicato)
        params: parametri del backtest

    Returns:
        Tupla (fees, pnl, pnl_percent)
    """
    # Commissioni: fee su entry + exit
    fees = params.position_size * params.fee_rate * 2.0

    # Quantità acquistata/venduta
    quantity = params.position_size / entry_price

    if params.direction == "signal-only":
        # Solo segnale: PnL = 0, pnl_percent = movimento teorico
        pnl = 0.0
        if entry_price > 0:
            pnl_percent = (exit_price - entry_price) / entry_price * 100.0
        else:
            pnl_percent = 0.0
        fees = 0.0  # Nessuna fee in signal-only

    elif params.direction == "long":
        # Long: guadagno se exit > entry
        exit_value = quantity * exit_price
        entry_value = params.position_size  # = quantity * entry_price
        pnl = exit_value - entry_value - fees
        if entry_value > 0:
            pnl_percent = pnl / entry_value * 100.0
        else:
            pnl_percent = 0.0

    elif params.direction == "short":
        # Short: guadagno se exit < entry
        entry_value = params.position_size  # = quantity * entry_price
        exit_value = quantity * exit_price
        pnl = entry_value - exit_value - fees
        if entry_value > 0:
            pnl_percent = pnl / entry_value * 100.0
        else:
            pnl_percent = 0.0

    else:
        pnl = 0.0
        pnl_percent = 0.0
        fees = 0.0

    return fees, pnl, pnl_percent


def _find_exit_index_by_time(
    epoch_secs: np.ndarray,
    exit_time: pd.Timestamp,
    timestamps: np.ndarray,
) -> int:
    """
    Trova l'indice nell'array timestamps corrispondente a exit_time.

    Args:
        epoch_secs: array epoch seconds
        exit_time: timestamp di uscita (pd.Timestamp)
        timestamps: array numpy datetime64

    Returns:
        Indice trovato o None
    """
    # Converti exit_time in numpy datetime64 per confronto
    exit_np = np.datetime64(exit_time)
    matches = np.where(timestamps == exit_np)[0]
    if len(matches) > 0:
        return int(matches[0])
    return None