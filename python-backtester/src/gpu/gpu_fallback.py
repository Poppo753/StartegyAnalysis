"""
gpu_fallback.py - Fallback CPU per screening quando GPU non disponibile

Replica la stessa logica del kernel GPU ma usando Numba su CPU.
Output identico: array (n_combinations, 8) con metriche aggregate.
"""

import time
import numpy as np
from typing import List, Tuple

try:
    from numba import njit, prange
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False


if NUMBA_AVAILABLE:

    @njit(cache=True, parallel=True)
    def _cpu_screen_batch(
        epoch_ms,       # int64[:]
        close,          # float64[:]
        high,           # float64[:]
        low,            # float64[:]
        x_values,       # float64[:]
        y_values,       # int64[:]
        z_values,       # float64[:]
        max_hold_ms,    # int64
        position_size,  # float64
        fee_rate,       # float64
        slippage_rate,  # float64
        direction,      # int64
    ):
        """
        Screening CPU parallelo con Numba.
        Ogni combinazione è processata da un thread separato.
        
        Returns:
            results: float64[:, 8] - metriche per ogni combinazione
        """
        n_combinations = len(x_values)
        n_candles = len(close)
        results = np.zeros((n_combinations, 8), dtype=np.float64)
        
        for tid in prange(n_combinations):
            x_percent = x_values[tid]
            y_ms = y_values[tid] * 1000
            z_percent = z_values[tid]
            
            # Accumulatori
            total_trades = 0
            winning_trades = 0
            losing_trades = 0
            total_pnl = 0.0
            gross_profit = 0.0
            gross_loss = 0.0
            best_trade = -1e18
            worst_trade = 1e18
            
            i = 0
            while i < n_candles:
                current_time = epoch_ms[i]
                target_past = current_time - y_ms
                
                # Binary search
                lo = 0
                hi = i
                while lo < hi:
                    mid = (lo + hi) // 2
                    if epoch_ms[mid] <= target_past:
                        lo = mid + 1
                    else:
                        hi = mid
                past_idx = lo - 1
                
                if past_idx < 0 or epoch_ms[past_idx] > target_past:
                    i += 1
                    continue
                
                past_close = close[past_idx]
                current_close = close[i]
                
                if past_close == 0.0:
                    i += 1
                    continue
                
                move_percent = (current_close - past_close) / past_close * 100.0
                
                if move_percent >= x_percent:
                    entry_time = epoch_ms[i]
                    raw_entry = current_close
                    
                    if direction == 1:
                        entry_price = raw_entry * (1.0 + slippage_rate)
                    elif direction == 2:
                        entry_price = raw_entry * (1.0 - slippage_rate)
                    else:
                        entry_price = raw_entry
                    
                    max_price = entry_price
                    min_price = entry_price
                    exit_idx = n_candles - 1
                    
                    for j in range(i + 1, n_candles):
                        c = close[j]
                        h = high[j]
                        l = low[j]
                        
                        if h > max_price:
                            max_price = h
                        if l < min_price:
                            min_price = l
                        
                        elapsed = epoch_ms[j] - entry_time
                        
                        drop_pct = 0.0
                        if max_price > 0.0:
                            drop_pct = (max_price - c) / max_price * 100.0
                        
                        if drop_pct >= z_percent:
                            exit_idx = j
                            break
                        
                        if elapsed >= max_hold_ms:
                            exit_idx = j
                            break
                    
                    # Calcola PnL
                    raw_exit = close[exit_idx]
                    if direction == 1:
                        exit_price = raw_exit * (1.0 - slippage_rate)
                    elif direction == 2:
                        exit_price = raw_exit * (1.0 + slippage_rate)
                    else:
                        exit_price = raw_exit
                    
                    pnl = 0.0
                    fees = position_size * fee_rate * 2.0
                    
                    if direction == 0:
                        if entry_price > 0.0:
                            pnl = (exit_price - entry_price) / entry_price * 100.0
                        fees = 0.0
                    elif direction == 1:
                        qty = position_size / entry_price
                        pnl = (exit_price - entry_price) * qty - fees
                    else:
                        qty = position_size / entry_price
                        pnl = (entry_price - exit_price) * qty - fees
                    
                    total_trades += 1
                    total_pnl += pnl
                    
                    if pnl > 0.0:
                        winning_trades += 1
                        gross_profit += pnl
                    else:
                        losing_trades += 1
                        gross_loss += pnl
                    
                    if pnl > best_trade:
                        best_trade = pnl
                    if pnl < worst_trade:
                        worst_trade = pnl
                    
                    i = exit_idx + 1
                else:
                    i += 1
            
            # Scrivi risultati
            results[tid, 0] = float(total_trades)
            results[tid, 1] = float(winning_trades)
            results[tid, 2] = float(losing_trades)
            results[tid, 3] = total_pnl
            results[tid, 4] = gross_profit
            results[tid, 5] = gross_loss
            results[tid, 6] = best_trade if total_trades > 0 else 0.0
            results[tid, 7] = worst_trade if total_trades > 0 else 0.0
        
        return results


if NUMBA_AVAILABLE:

    @njit(cache=True, parallel=True)
    def _cpu_screen_batch_dynamic_y(
        epoch_ms,       # int64[:]
        close,          # float64[:]
        high,           # float64[:]
        low,            # float64[:]
        x_values,       # float64[:]
        z_values,       # float64[:]
        y_max_window_ms,  # int64
        max_hold_ms,    # int64
        position_size,  # float64
        fee_rate,       # float64
        slippage_rate,  # float64
        direction,      # int64
    ):
        """
        Screening CPU con Y dinamico.
        Per ogni candela cerca il minimo nella finestra y_max_window.
        Se current è X% sopra il minimo → trade.
        Output: 9 metriche (le 8 standard + avg_y_actual).
        """
        n_combinations = len(x_values)
        n_candles = len(close)
        results = np.zeros((n_combinations, 9), dtype=np.float64)
        
        for tid in prange(n_combinations):
            x_percent = x_values[tid]
            z_percent = z_values[tid]
            
            total_trades = 0
            winning_trades = 0
            losing_trades = 0
            total_pnl = 0.0
            gross_profit = 0.0
            gross_loss = 0.0
            best_trade = -1e18
            worst_trade = 1e18
            sum_y_actual = 0.0
            
            i = 0
            while i < n_candles:
                current_time = epoch_ms[i]
                current_close = close[i]
                window_start_time = current_time - y_max_window_ms
                
                # Trova minimo close nella finestra
                min_close_val = current_close
                min_close_idx = i
                
                # Binary search for the window start boundary
                lo_bs = 0
                hi_bs = i
                while lo_bs < hi_bs:
                    mid_bs = (lo_bs + hi_bs) // 2
                    if epoch_ms[mid_bs] < window_start_time:
                        lo_bs = mid_bs + 1
                    else:
                        hi_bs = mid_bs
                window_start_idx = lo_bs

                # Iterate forward from window_start_idx to i-1
                for k in range(window_start_idx, i):
                    if close[k] < min_close_val:
                        min_close_val = close[k]
                        min_close_idx = k
                
                if min_close_val == 0.0 or min_close_idx == i:
                    i += 1
                    continue
                
                move_percent = (current_close - min_close_val) / min_close_val * 100.0
                
                if move_percent >= x_percent:
                    # Y effettivo
                    y_actual_s = float(current_time - epoch_ms[min_close_idx]) / 1000.0
                    sum_y_actual += y_actual_s
                    
                    entry_time = epoch_ms[i]
                    raw_entry = current_close
                    
                    if direction == 1:
                        entry_price = raw_entry * (1.0 + slippage_rate)
                    elif direction == 2:
                        entry_price = raw_entry * (1.0 - slippage_rate)
                    else:
                        entry_price = raw_entry
                    
                    max_price = entry_price
                    min_price = entry_price
                    exit_idx = n_candles - 1
                    
                    for j in range(i + 1, n_candles):
                        c = close[j]
                        h = high[j]
                        l = low[j]
                        
                        if h > max_price:
                            max_price = h
                        if l < min_price:
                            min_price = l
                        
                        elapsed = epoch_ms[j] - entry_time
                        
                        drop_pct = 0.0
                        if max_price > 0.0:
                            drop_pct = (max_price - c) / max_price * 100.0
                        
                        if drop_pct >= z_percent:
                            exit_idx = j
                            break
                        
                        if elapsed >= max_hold_ms:
                            exit_idx = j
                            break
                    
                    raw_exit = close[exit_idx]
                    if direction == 1:
                        exit_price = raw_exit * (1.0 - slippage_rate)
                    elif direction == 2:
                        exit_price = raw_exit * (1.0 + slippage_rate)
                    else:
                        exit_price = raw_exit
                    
                    pnl = 0.0
                    fees = position_size * fee_rate * 2.0
                    
                    if direction == 0:
                        if entry_price > 0.0:
                            pnl = (exit_price - entry_price) / entry_price * 100.0
                        fees = 0.0
                    elif direction == 1:
                        qty = position_size / entry_price
                        pnl = (exit_price - entry_price) * qty - fees
                    else:
                        qty = position_size / entry_price
                        pnl = (entry_price - exit_price) * qty - fees
                    
                    total_trades += 1
                    total_pnl += pnl
                    
                    if pnl > 0.0:
                        winning_trades += 1
                        gross_profit += pnl
                    else:
                        losing_trades += 1
                        gross_loss += pnl
                    
                    if pnl > best_trade:
                        best_trade = pnl
                    if pnl < worst_trade:
                        worst_trade = pnl
                    
                    i = exit_idx + 1
                else:
                    i += 1
            
            results[tid, 0] = float(total_trades)
            results[tid, 1] = float(winning_trades)
            results[tid, 2] = float(losing_trades)
            results[tid, 3] = total_pnl
            results[tid, 4] = gross_profit
            results[tid, 5] = gross_loss
            results[tid, 6] = best_trade if total_trades > 0 else 0.0
            results[tid, 7] = worst_trade if total_trades > 0 else 0.0
            results[tid, 8] = (sum_y_actual / float(total_trades)) if total_trades > 0 else 0.0
        
        return results


def cpu_screen_combinations_dynamic_y(
    epoch_ms: np.ndarray,
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    combinations: List[Tuple[float, float]],  # (x, z) pairs
    y_max_window: int,
    max_hold_seconds: int,
    position_size: float,
    fee_rate: float,
    slippage_rate: float,
    direction: int,
    batch_size: int = 2048,
) -> np.ndarray:
    """
    Screening CPU con Y dinamico (fallback).
    
    Returns:
        Array numpy (n_combinations, 9) con metriche.
        Colonna [8] = avg_y_actual (media secondi del pump)
    """
    if not NUMBA_AVAILABLE:
        raise RuntimeError("Numba non disponibile. Installa con: pip install numba")
    
    n_combinations = len(combinations)
    
    x_all = np.array([c[0] for c in combinations], dtype=np.float64)
    z_all = np.array([c[1] for c in combinations], dtype=np.float64)
    
    y_max_window_ms = np.int64(y_max_window * 1000)
    max_hold_ms = np.int64(max_hold_seconds * 1000)
    
    epoch_ms_i64 = epoch_ms.astype(np.int64)
    close_f64 = close.astype(np.float64)
    high_f64 = high.astype(np.float64)
    low_f64 = low.astype(np.float64)
    
    all_results = np.zeros((n_combinations, 9), dtype=np.float64)
    
    total_batches = (n_combinations + batch_size - 1) // batch_size
    last_progress_time = time.time()
    progress_interval = 15
    screen_start_time = last_progress_time
    
    for batch_idx, batch_start in enumerate(range(0, n_combinations, batch_size)):
        batch_end = min(batch_start + batch_size, n_combinations)
        
        batch_results = _cpu_screen_batch_dynamic_y(
            epoch_ms_i64,
            close_f64,
            high_f64,
            low_f64,
            x_all[batch_start:batch_end],
            z_all[batch_start:batch_end],
            y_max_window_ms,
            max_hold_ms,
            np.float64(position_size),
            np.float64(fee_rate),
            np.float64(slippage_rate),
            np.int64(direction),
        )
        
        all_results[batch_start:batch_end] = batch_results
        
        now = time.time()
        if now - last_progress_time >= progress_interval:
            completed = batch_end
            pct = completed / n_combinations * 100
            elapsed = now - screen_start_time
            rate = completed / elapsed if elapsed > 0 else 0
            eta = (n_combinations - completed) / rate if rate > 0 else 0
            print(f"  📊 [CPU] Progresso: {completed}/{n_combinations} ({pct:.1f}%) | "
                  f"Batch {batch_idx+1}/{total_batches} | "
                  f"Velocità: {rate:.0f} comb/s | ETA: {eta:.0f}s")
            last_progress_time = now
    
    return all_results


def cpu_screen_combinations(
    epoch_ms: np.ndarray,
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    combinations: List[Tuple[float, int, float]],
    max_hold_seconds: int,
    position_size: float,
    fee_rate: float,
    slippage_rate: float,
    direction: int,
    batch_size: int = 2048,
) -> np.ndarray:
    """
    Screening CPU parallelo (fallback per GPU).
    Stessa interfaccia di gpu_screen_combinations.
    Processa in batch per mostrare progresso ogni 15 secondi.
    
    Returns:
        Array numpy (n_combinations, 8) con metriche.
    """
    if not NUMBA_AVAILABLE:
        raise RuntimeError("Numba non disponibile. Installa con: pip install numba")
    
    n_combinations = len(combinations)
    
    # Prepara array parametri
    x_all = np.array([c[0] for c in combinations], dtype=np.float64)
    y_all = np.array([c[1] for c in combinations], dtype=np.int64)
    z_all = np.array([c[2] for c in combinations], dtype=np.float64)
    
    max_hold_ms = np.int64(max_hold_seconds * 1000)
    
    # Prepara dati mercato (cast una volta sola)
    epoch_ms_i64 = epoch_ms.astype(np.int64)
    close_f64 = close.astype(np.float64)
    high_f64 = high.astype(np.float64)
    low_f64 = low.astype(np.float64)
    
    # Array risultati completo
    all_results = np.zeros((n_combinations, 8), dtype=np.float64)
    
    # Progress tracking
    total_batches = (n_combinations + batch_size - 1) // batch_size
    last_progress_time = time.time()
    progress_interval = 15  # secondi
    screen_start_time = last_progress_time
    
    for batch_idx, batch_start in enumerate(range(0, n_combinations, batch_size)):
        batch_end = min(batch_start + batch_size, n_combinations)
        
        # Esegui batch con Numba
        batch_results = _cpu_screen_batch(
            epoch_ms_i64,
            close_f64,
            high_f64,
            low_f64,
            x_all[batch_start:batch_end],
            y_all[batch_start:batch_end],
            z_all[batch_start:batch_end],
            max_hold_ms,
            np.float64(position_size),
            np.float64(fee_rate),
            np.float64(slippage_rate),
            np.int64(direction),
        )
        
        all_results[batch_start:batch_end] = batch_results
        
        # Progress report ogni 15 secondi
        now = time.time()
        if now - last_progress_time >= progress_interval:
            completed = batch_end
            pct = completed / n_combinations * 100
            elapsed = now - screen_start_time
            rate = completed / elapsed if elapsed > 0 else 0
            eta = (n_combinations - completed) / rate if rate > 0 else 0
            print(f"  📊 [CPU] Progresso: {completed}/{n_combinations} ({pct:.1f}%) | "
                  f"Batch {batch_idx+1}/{total_batches} | "
                  f"Velocità: {rate:.0f} comb/s | ETA: {eta:.0f}s")
            last_progress_time = now
    
    return all_results