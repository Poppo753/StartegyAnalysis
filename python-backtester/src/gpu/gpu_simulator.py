"""
gpu_simulator.py - Simulatore GPU per screening massivo

Esegue migliaia di combinazioni X/Y/Z in parallelo sulla GPU.
NON salva trades individuali — calcola solo metriche aggregate.

Output per ogni combinazione:
- total_trades
- winning_trades
- losing_trades
- total_pnl
- gross_profit
- gross_loss
- best_trade
- worst_trade
"""

import time
import numpy as np
from typing import List, Tuple

try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False


# Kernel CUDA per simulazione batch
_GPU_KERNEL = None
_GPU_KERNEL_DYNAMIC_Y = None


def _get_kernel():
    """Lazy-load del kernel CUDA. Compilato una sola volta."""
    global _GPU_KERNEL
    if _GPU_KERNEL is not None:
        return _GPU_KERNEL
    
    _GPU_KERNEL = cp.RawKernel(r'''
    extern "C" __global__
    void simulate_batch(
        // Dati mercato (shared across all threads)
        const long long* epoch_ms,
        const double* close,
        const double* high,
        const double* low,
        const int n_candles,
        // Parametri per ogni combinazione
        const double* x_values,
        const int* y_values,
        const double* z_values,
        const int n_combinations,
        // Parametri globali
        const long long max_hold_ms,
        const double position_size,
        const double fee_rate,
        const double slippage_rate,
        const int direction,
        // Output: 8 metriche per combinazione
        double* results
    ) {
        // Ogni thread processa UNA combinazione
        int tid = blockDim.x * blockIdx.x + threadIdx.x;
        if (tid >= n_combinations) return;
        
        // Leggi parametri per questa combinazione
        double x_percent = x_values[tid];
        long long y_ms = (long long)y_values[tid] * 1000LL;
        double z_percent = z_values[tid];
        
        // Accumulatori metriche
        int total_trades = 0;
        int winning_trades = 0;
        int losing_trades = 0;
        double total_pnl = 0.0;
        double gross_profit = 0.0;
        double gross_loss = 0.0;
        double best_trade = -1e18;
        double worst_trade = 1e18;
        
        // Simulazione
        int i = 0;
        while (i < n_candles) {
            long long current_time = epoch_ms[i];
            long long target_past = current_time - y_ms;
            
            // Binary search per trovare candela passata
            int lo = 0;
            int hi = i;
            while (lo < hi) {
                int mid = (lo + hi) / 2;
                if (epoch_ms[mid] <= target_past) {
                    lo = mid + 1;
                } else {
                    hi = mid;
                }
            }
            int past_idx = lo - 1;
            
            if (past_idx < 0 || epoch_ms[past_idx] > target_past) {
                i++;
                continue;
            }
            
            double past_close = close[past_idx];
            double current_close = close[i];
            
            if (past_close == 0.0) {
                i++;
                continue;
            }
            
            double move_percent = (current_close - past_close) / past_close * 100.0;
            
            if (move_percent >= x_percent) {
                // Apri trade
                long long entry_time = epoch_ms[i];
                double raw_entry = current_close;
                double entry_price;
                
                if (direction == 1) {
                    entry_price = raw_entry * (1.0 + slippage_rate);
                } else if (direction == 2) {
                    entry_price = raw_entry * (1.0 - slippage_rate);
                } else {
                    entry_price = raw_entry;
                }
                
                double max_price = entry_price;
                double min_price = entry_price;
                int exit_idx = n_candles - 1;
                int reason = 3;
                
                for (int j = i + 1; j < n_candles; j++) {
                    double c = close[j];
                    double h = high[j];
                    double l = low[j];
                    
                    if (h > max_price) max_price = h;
                    if (l < min_price) min_price = l;
                    
                    long long elapsed = epoch_ms[j] - entry_time;
                    
                    double drop_pct = 0.0;
                    if (max_price > 0.0) {
                        drop_pct = (max_price - c) / max_price * 100.0;
                    }
                    
                    if (drop_pct >= z_percent) {
                        exit_idx = j;
                        reason = 1;
                        break;
                    }
                    
                    if (elapsed >= max_hold_ms) {
                        exit_idx = j;
                        reason = 2;
                        break;
                    }
                }
                
                // Calcola PnL
                double raw_exit = close[exit_idx];
                double exit_price;
                
                if (direction == 1) {
                    exit_price = raw_exit * (1.0 - slippage_rate);
                } else if (direction == 2) {
                    exit_price = raw_exit * (1.0 + slippage_rate);
                } else {
                    exit_price = raw_exit;
                }
                
                double pnl = 0.0;
                double fees = position_size * fee_rate * 2.0;
                
                if (direction == 0) {
                    // signal-only: pnl_percent
                    if (entry_price > 0.0) {
                        pnl = (exit_price - entry_price) / entry_price * 100.0;
                    }
                    fees = 0.0;
                } else if (direction == 1) {
                    double qty = position_size / entry_price;
                    pnl = (exit_price - entry_price) * qty - fees;
                } else {
                    double qty = position_size / entry_price;
                    pnl = (entry_price - exit_price) * qty - fees;
                }
                
                // Aggiorna metriche
                total_trades++;
                total_pnl += pnl;
                
                if (pnl > 0.0) {
                    winning_trades++;
                    gross_profit += pnl;
                } else {
                    losing_trades++;
                    gross_loss += pnl;  // negativo
                }
                
                if (pnl > best_trade) best_trade = pnl;
                if (pnl < worst_trade) worst_trade = pnl;
                
                // Salta avanti
                i = exit_idx + 1;
            } else {
                i++;
            }
        }
        
        // Scrivi risultati (8 valori per combinazione)
        int base = tid * 8;
        results[base + 0] = (double)total_trades;
        results[base + 1] = (double)winning_trades;
        results[base + 2] = (double)losing_trades;
        results[base + 3] = total_pnl;
        results[base + 4] = gross_profit;
        results[base + 5] = gross_loss;
        results[base + 6] = (total_trades > 0) ? best_trade : 0.0;
        results[base + 7] = (total_trades > 0) ? worst_trade : 0.0;
    }
    ''', 'simulate_batch')
    
    return _GPU_KERNEL


def _get_kernel_dynamic_y():
    """Lazy-load del kernel CUDA per Y dinamico. Compilato una sola volta."""
    global _GPU_KERNEL_DYNAMIC_Y
    if _GPU_KERNEL_DYNAMIC_Y is not None:
        return _GPU_KERNEL_DYNAMIC_Y
    
    _GPU_KERNEL_DYNAMIC_Y = cp.RawKernel(r'''
    extern "C" __global__
    void simulate_batch_dynamic_y(
        // Dati mercato
        const long long* epoch_ms,
        const double* close,
        const double* high,
        const double* low,
        const int n_candles,
        // Parametri per ogni combinazione (solo X e Z, Y è la finestra max)
        const double* x_values,
        const double* z_values,
        const int n_combinations,
        // Parametri globali
        const long long y_max_window_ms,
        const long long max_hold_ms,
        const double position_size,
        const double fee_rate,
        const double slippage_rate,
        const int direction,
        // Output: 9 metriche per combinazione
        double* results
    ) {
        int tid = blockDim.x * blockIdx.x + threadIdx.x;
        if (tid >= n_combinations) return;
        
        double x_percent = x_values[tid];
        double z_percent = z_values[tid];
        
        // Accumulatori
        int total_trades = 0;
        int winning_trades = 0;
        int losing_trades = 0;
        double total_pnl = 0.0;
        double gross_profit = 0.0;
        double gross_loss = 0.0;
        double best_trade = -1e18;
        double worst_trade = 1e18;
        double sum_y_actual = 0.0;
        
        int i = 0;
        while (i < n_candles) {
            long long current_time = epoch_ms[i];
            double current_close = close[i];
            long long window_start_time = current_time - y_max_window_ms;
            
            // Trova il minimo dei close nella finestra [window_start_time, current_time)
            double min_close_in_window = current_close;
            int min_close_idx = i;
            
            // Binary search for the window start boundary
            int lo_bs = 0;
            int hi_bs = i;
            while (lo_bs < hi_bs) {
                int mid_bs = (lo_bs + hi_bs) / 2;
                if (epoch_ms[mid_bs] < window_start_time) {
                    lo_bs = mid_bs + 1;
                } else {
                    hi_bs = mid_bs;
                }
            }
            int window_start_idx = lo_bs;

            // Iterate forward from window_start_idx to i-1 (O(window_size) per candle)
            for (int k = window_start_idx; k < i; k++) {
                if (close[k] < min_close_in_window) {
                    min_close_in_window = close[k];
                    min_close_idx = k;
                }
            }
            
            if (min_close_in_window == 0.0 || min_close_idx == i) {
                i++;
                continue;
            }
            
            // Calcola movimento dal minimo
            double move_percent = (current_close - min_close_in_window) / min_close_in_window * 100.0;
            
            if (move_percent >= x_percent) {
                // Y effettivo (quanti secondi fa era il minimo)
                double y_actual_s = (double)(current_time - epoch_ms[min_close_idx]) / 1000.0;
                sum_y_actual += y_actual_s;
                
                // Apri trade
                long long entry_time = epoch_ms[i];
                double raw_entry = current_close;
                double entry_price;
                
                if (direction == 1) {
                    entry_price = raw_entry * (1.0 + slippage_rate);
                } else if (direction == 2) {
                    entry_price = raw_entry * (1.0 - slippage_rate);
                } else {
                    entry_price = raw_entry;
                }
                
                double max_price = entry_price;
                double min_price = entry_price;
                int exit_idx = n_candles - 1;
                
                for (int j = i + 1; j < n_candles; j++) {
                    double c = close[j];
                    double h = high[j];
                    double l = low[j];
                    
                    if (h > max_price) max_price = h;
                    if (l < min_price) min_price = l;
                    
                    long long elapsed = epoch_ms[j] - entry_time;
                    
                    double drop_pct = 0.0;
                    if (max_price > 0.0) {
                        drop_pct = (max_price - c) / max_price * 100.0;
                    }
                    
                    if (drop_pct >= z_percent) {
                        exit_idx = j;
                        break;
                    }
                    
                    if (elapsed >= max_hold_ms) {
                        exit_idx = j;
                        break;
                    }
                }
                
                // Calcola PnL
                double raw_exit = close[exit_idx];
                double exit_price;
                
                if (direction == 1) {
                    exit_price = raw_exit * (1.0 - slippage_rate);
                } else if (direction == 2) {
                    exit_price = raw_exit * (1.0 + slippage_rate);
                } else {
                    exit_price = raw_exit;
                }
                
                double pnl = 0.0;
                double fees = position_size * fee_rate * 2.0;
                
                if (direction == 0) {
                    if (entry_price > 0.0) {
                        pnl = (exit_price - entry_price) / entry_price * 100.0;
                    }
                    fees = 0.0;
                } else if (direction == 1) {
                    double qty = position_size / entry_price;
                    pnl = (exit_price - entry_price) * qty - fees;
                } else {
                    double qty = position_size / entry_price;
                    pnl = (entry_price - exit_price) * qty - fees;
                }
                
                total_trades++;
                total_pnl += pnl;
                
                if (pnl > 0.0) {
                    winning_trades++;
                    gross_profit += pnl;
                } else {
                    losing_trades++;
                    gross_loss += pnl;
                }
                
                if (pnl > best_trade) best_trade = pnl;
                if (pnl < worst_trade) worst_trade = pnl;
                
                i = exit_idx + 1;
            } else {
                i++;
            }
        }
        
        // Scrivi risultati (9 valori per combinazione)
        int base = tid * 9;
        results[base + 0] = (double)total_trades;
        results[base + 1] = (double)winning_trades;
        results[base + 2] = (double)losing_trades;
        results[base + 3] = total_pnl;
        results[base + 4] = gross_profit;
        results[base + 5] = gross_loss;
        results[base + 6] = (total_trades > 0) ? best_trade : 0.0;
        results[base + 7] = (total_trades > 0) ? worst_trade : 0.0;
        results[base + 8] = (total_trades > 0) ? (sum_y_actual / (double)total_trades) : 0.0;
    }
    ''', 'simulate_batch_dynamic_y')
    
    return _GPU_KERNEL_DYNAMIC_Y


def gpu_screen_combinations_dynamic_y(
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
    Screening GPU con Y dinamico.
    Cerca il minimo nella finestra y_max_window e verifica se current è X% sopra.
    
    Args:
        combinations: lista di tuple (x_percent, z_percent) — Y non è nella griglia
        y_max_window: finestra massima di lookback in secondi
    
    Returns:
        Array numpy (n_combinations, 9) con metriche.
        Colonna [8] = avg_y_actual (media secondi del pump)
    """
    if not CUPY_AVAILABLE:
        raise RuntimeError("CuPy non disponibile")
    
    n_combinations = len(combinations)
    n_candles = len(close)
    
    # Prepara array parametri (solo X e Z)
    x_all = np.array([c[0] for c in combinations], dtype=np.float64)
    z_all = np.array([c[1] for c in combinations], dtype=np.float64)
    
    # Trasferisci dati mercato su GPU
    d_epoch_ms = cp.asarray(epoch_ms.astype(np.int64))
    d_close = cp.asarray(close.astype(np.float64))
    d_high = cp.asarray(high.astype(np.float64))
    d_low = cp.asarray(low.astype(np.float64))
    
    y_max_window_ms = np.int64(y_max_window * 1000)
    max_hold_ms = np.int64(max_hold_seconds * 1000)
    
    # Array risultati (9 valori per combinazione)
    all_results = np.zeros((n_combinations, 9), dtype=np.float64)
    
    # Processa in batch
    kernel = _get_kernel_dynamic_y()
    
    total_batches = (n_combinations + batch_size - 1) // batch_size
    last_progress_time = time.time()
    progress_interval = 15
    screen_start_time = last_progress_time
    
    for batch_idx, batch_start in enumerate(range(0, n_combinations, batch_size)):
        batch_end = min(batch_start + batch_size, n_combinations)
        batch_n = batch_end - batch_start
        
        d_x = cp.asarray(x_all[batch_start:batch_end])
        d_z = cp.asarray(z_all[batch_start:batch_end])
        
        d_results = cp.zeros(batch_n * 9, dtype=cp.float64)
        
        threads_per_block = 256
        blocks = (batch_n + threads_per_block - 1) // threads_per_block
        
        kernel(
            (blocks,), (threads_per_block,),
            (
                d_epoch_ms, d_close, d_high, d_low,
                np.int32(n_candles),
                d_x, d_z,
                np.int32(batch_n),
                y_max_window_ms,
                max_hold_ms,
                np.float64(position_size),
                np.float64(fee_rate),
                np.float64(slippage_rate),
                np.int32(direction),
                d_results,
            )
        )
        
        batch_results = cp.asnumpy(d_results).reshape(batch_n, 9)
        all_results[batch_start:batch_end] = batch_results
        
        # Progress report
        now = time.time()
        if now - last_progress_time >= progress_interval:
            completed = batch_end
            pct = completed / n_combinations * 100
            elapsed = now - screen_start_time
            rate = completed / elapsed if elapsed > 0 else 0
            eta = (n_combinations - completed) / rate if rate > 0 else 0
            print(f"  📊 [GPU] Progresso: {completed}/{n_combinations} ({pct:.1f}%) | "
                  f"Batch {batch_idx+1}/{total_batches} | "
                  f"Velocità: {rate:.0f} comb/s | ETA: {eta:.0f}s")
            last_progress_time = now
    
    # Libera memoria GPU
    del d_epoch_ms, d_close, d_high, d_low
    cp.get_default_memory_pool().free_all_blocks()
    
    return all_results


def gpu_screen_combinations(
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
    Esegue screening GPU di tutte le combinazioni in batch.
    
    Args:
        epoch_ms: timestamps in millisecondi (int64)
        close: prezzi close (float64)
        high: prezzi high (float64)
        low: prezzi low (float64)
        combinations: lista di tuple (x, y, z)
        max_hold_seconds: timeout max
        position_size: size posizione
        fee_rate: commissione
        slippage_rate: slippage
        direction: 0=signal-only, 1=long, 2=short
        batch_size: combinazioni per batch GPU
    
    Returns:
        Array numpy (n_combinations, 8) con metriche per ogni combinazione.
        Colonne: [total_trades, winning, losing, total_pnl, 
                  gross_profit, gross_loss, best_trade, worst_trade]
    """
    if not CUPY_AVAILABLE:
        raise RuntimeError("CuPy non disponibile")
    
    n_combinations = len(combinations)
    n_candles = len(close)
    
    # Prepara array parametri
    x_all = np.array([c[0] for c in combinations], dtype=np.float64)
    y_all = np.array([c[1] for c in combinations], dtype=np.int32)
    z_all = np.array([c[2] for c in combinations], dtype=np.float64)
    
    # Trasferisci dati mercato su GPU (una volta sola)
    d_epoch_ms = cp.asarray(epoch_ms.astype(np.int64))
    d_close = cp.asarray(close.astype(np.float64))
    d_high = cp.asarray(high.astype(np.float64))
    d_low = cp.asarray(low.astype(np.float64))
    
    max_hold_ms = np.int64(max_hold_seconds * 1000)
    
    # Array risultati completo
    all_results = np.zeros((n_combinations, 8), dtype=np.float64)
    
    # Processa in batch
    kernel = _get_kernel()
    
    # Progress tracking
    total_batches = (n_combinations + batch_size - 1) // batch_size
    last_progress_time = time.time()
    progress_interval = 15  # secondi
    screen_start_time = last_progress_time
    
    for batch_idx, batch_start in enumerate(range(0, n_combinations, batch_size)):
        batch_end = min(batch_start + batch_size, n_combinations)
        batch_n = batch_end - batch_start
        
        # Trasferisci parametri batch su GPU
        d_x = cp.asarray(x_all[batch_start:batch_end])
        d_y = cp.asarray(y_all[batch_start:batch_end])
        d_z = cp.asarray(z_all[batch_start:batch_end])
        
        # Output buffer
        d_results = cp.zeros(batch_n * 8, dtype=cp.float64)
        
        # Lancia kernel
        threads_per_block = 256
        blocks = (batch_n + threads_per_block - 1) // threads_per_block
        
        kernel(
            (blocks,), (threads_per_block,),
            (
                d_epoch_ms, d_close, d_high, d_low,
                np.int32(n_candles),
                d_x, d_y, d_z,
                np.int32(batch_n),
                max_hold_ms,
                np.float64(position_size),
                np.float64(fee_rate),
                np.float64(slippage_rate),
                np.int32(direction),
                d_results,
            )
        )
        
        # Copia risultati batch da GPU a CPU
        batch_results = cp.asnumpy(d_results).reshape(batch_n, 8)
        all_results[batch_start:batch_end] = batch_results
        
        # Progress report ogni 15 secondi
        now = time.time()
        if now - last_progress_time >= progress_interval:
            completed = batch_end
            pct = completed / n_combinations * 100
            elapsed = now - screen_start_time
            rate = completed / elapsed if elapsed > 0 else 0
            eta = (n_combinations - completed) / rate if rate > 0 else 0
            print(f"  📊 [GPU] Progresso: {completed}/{n_combinations} ({pct:.1f}%) | "
                  f"Batch {batch_idx+1}/{total_batches} | "
                  f"Velocità: {rate:.0f} comb/s | ETA: {eta:.0f}s")
            last_progress_time = now
    
    # Libera memoria GPU
    del d_epoch_ms, d_close, d_high, d_low
    cp.get_default_memory_pool().free_all_blocks()
    
    return all_results