"""
fast_simulator.py - Simulatore accelerato con Numba JIT

La funzione core di simulazione è compilata con @numba.njit per massima velocità.
Opera esclusivamente su array numpy, senza oggetti Python.

Reason encoding (dentro numba):
    1 = drop-z
    2 = max-hold
    3 = end-of-data

Direction encoding (dentro numba):
    0 = signal-only
    1 = long
    2 = short

Output: array 2D con una riga per trade, colonne:
    [0] entry_idx
    [1] exit_idx
    [2] entry_price (con slippage)
    [3] exit_price (con slippage)
    [4] max_price_during_trade
    [5] min_price_during_trade
    [6] pnl
    [7] pnl_percent
    [8] fees
    [9] reason (1=drop-z, 2=max-hold, 3=end-of-data)

Nota: MAE/MFE NON sono colonne dell'array; vengono derivati in
fast_metrics.py da entry/max/min (direction-aware, clipped >= 0).
La variante dynamic-Y aggiunge [10] y_actual_seconds (array a 11 colonne).
"""

import numpy as np

from typing import Tuple

try:
    import numba
    from numba import njit, int64, float64
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False


class NumbaMissingError(RuntimeError):
    """Numba non installato: impossibile usare i motori fast/gpu-fallback."""
    pass


def check_numba_available() -> None:
    """
    Verifica che numba sia installato.

    Raises:
        NumbaMissingError: se numba non è disponibile, con hint sulla
            mitigazione (BACKTEST_ENGINE=standard). Il catch + exit
            avviene solo al boundary CLI.
    """
    if not NUMBA_AVAILABLE:
        raise NumbaMissingError(
            "numba non è installato. Installa con: pip install numba. "
            "Oppure usa BACKTEST_ENGINE=standard nel .env"
        )


# ============================================================
# FUNZIONE CORE NUMBA - Singola combinazione X/Y/Z
# ============================================================

if NUMBA_AVAILABLE:

    @njit(cache=True)
    def _simulate_single(
        epoch_ms: np.ndarray,
        close: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        x_percent: float,
        y_seconds: int,
        z_percent: float,
        max_hold_seconds: int,
        position_size: float,
        fee_rate: float,
        slippage_rate: float,
        direction: int,
    ) -> Tuple[np.ndarray, int]:
        """
        Simula la strategia momentum/drop su dati sparsi.

        Usa timestamps reali (millisecondi) per gestire dati non uniformi.
        Restituisce un array 2D con i dettagli di ogni trade.

        Returns:
            trades_out: float64[:, 10] - array con trade (max 10000 trade)
            n_trades: int64 - numero effettivo di trade
        """
        n = len(close)
        y_ms = y_seconds * 1000  # Converti y_seconds in millisecondi
        max_hold_ms = max_hold_seconds * 1000  # Converti max_hold in millisecondi

        # Pre-alloca array output (max 10000 trade per sicurezza)
        # 10 colonne (0-9); MAE/MFE derivati dai max/min in fast_metrics.
        max_trades = 10000
        trades_out = np.empty((max_trades, 10), dtype=np.float64)
        n_trades = 0

        # Puntatore per binary search della candela passata
        i = 0

        while i < n:
            # --- FASE 1: Trova candela Y secondi fa ---
            current_time_ms = epoch_ms[i]
            target_past_ms = current_time_ms - y_ms

            # Binary search: trova l'ultima candela con tempo <= target_past_ms
            past_idx = _searchsorted_right(epoch_ms, target_past_ms, 0, i) - 1

            if past_idx < 0:
                # Non c'è una candela abbastanza indietro
                i += 1
                continue

            # Verifica che la candela trovata sia effettivamente <= target
            if epoch_ms[past_idx] > target_past_ms:
                i += 1
                continue

            # Prezzo passato e corrente
            past_close = close[past_idx]
            current_close = close[i]

            # Evita divisione per zero
            if past_close == 0.0:
                i += 1
                continue

            # Calcola movimento percentuale
            move_percent = (current_close - past_close) / past_close * 100.0

            # --- FASE 2: Controlla segnale ---
            if move_percent >= x_percent:
                # Apri trade
                entry_epoch_ms = epoch_ms[i]
                raw_entry = current_close

                # Applica slippage all'entry
                if direction == 1:  # long
                    entry_price = raw_entry * (1.0 + slippage_rate)
                elif direction == 2:  # short
                    entry_price = raw_entry * (1.0 - slippage_rate)
                else:  # signal-only
                    entry_price = raw_entry

                # Tracking
                max_price = entry_price
                min_price = entry_price
                exit_idx = -1
                reason = 3  # default: end-of-data

                # --- FASE 3: Monitoraggio trade ---
                for j in range(i + 1, n):
                    c = close[j]
                    h = high[j]
                    l = low[j]

                    # Aggiorna max/min
                    if h > max_price:
                        max_price = h
                    if l < min_price:
                        min_price = l

                    # Tempo reale trascorso
                    elapsed_ms = epoch_ms[j] - entry_epoch_ms

                    # Drop dal massimo
                    if max_price > 0.0:
                        drop_pct = (max_price - c) / max_price * 100.0
                    else:
                        drop_pct = 0.0

                    # Condizione uscita: drop >= Z%
                    if drop_pct >= z_percent:
                        exit_idx = j
                        reason = 1  # drop-z
                        break

                    # Condizione uscita: max hold
                    if elapsed_ms >= max_hold_ms:
                        exit_idx = j
                        reason = 2  # max-hold
                        break

                # Se non è uscito, chiudi a fine dati
                if exit_idx == -1:
                    exit_idx = n - 1
                    reason = 3  # end-of-data
                    if high[exit_idx] > max_price:
                        max_price = high[exit_idx]
                    if low[exit_idx] < min_price:
                        min_price = low[exit_idx]

                # Prezzo uscita con slippage
                raw_exit = close[exit_idx]
                if direction == 1:  # long
                    exit_price = raw_exit * (1.0 - slippage_rate)
                elif direction == 2:  # short
                    exit_price = raw_exit * (1.0 + slippage_rate)
                else:  # signal-only
                    exit_price = raw_exit

                # --- FASE 4: Calcolo PnL ---
                fees = position_size * fee_rate * 2.0

                if direction == 0:  # signal-only
                    pnl = 0.0
                    if entry_price > 0.0:
                        pnl_percent = (exit_price - entry_price) / entry_price * 100.0
                    else:
                        pnl_percent = 0.0
                    fees = 0.0
                elif direction == 1:  # long
                    quantity = position_size / entry_price
                    pnl = (exit_price - entry_price) * quantity - fees
                    if position_size > 0.0:
                        pnl_percent = pnl / position_size * 100.0
                    else:
                        pnl_percent = 0.0
                else:  # short (direction == 2)
                    quantity = position_size / entry_price
                    pnl = (entry_price - exit_price) * quantity - fees
                    if position_size > 0.0:
                        pnl_percent = pnl / position_size * 100.0
                    else:
                        pnl_percent = 0.0

                # Salva trade nell'array output
                if n_trades < max_trades:
                    trades_out[n_trades, 0] = float(i)            # entry_idx
                    trades_out[n_trades, 1] = float(exit_idx)     # exit_idx
                    trades_out[n_trades, 2] = entry_price
                    trades_out[n_trades, 3] = exit_price
                    trades_out[n_trades, 4] = max_price
                    trades_out[n_trades, 5] = min_price
                    trades_out[n_trades, 6] = pnl
                    trades_out[n_trades, 7] = pnl_percent
                    trades_out[n_trades, 8] = fees
                    trades_out[n_trades, 9] = float(reason)
                    n_trades += 1

                # Salta avanti (no trade sovrapposti)
                i = exit_idx + 1
            else:
                i += 1

        return trades_out[:n_trades], n_trades


    @njit(cache=True)
    def _searchsorted_right(arr: np.ndarray, value: float, lo: int, hi: int) -> int:
        """
        Binary search: trova l'indice dove inserire value per mantenere ordine.
        Equivalente a np.searchsorted(arr[lo:hi], value, side='right') + lo

        Args:
            arr: array ordinato int64
            value: valore da cercare
            lo: indice inizio
            hi: indice fine (esclusivo)

        Returns:
            Indice di inserimento (right side)
        """
        while lo < hi:
            mid = (lo + hi) // 2
            if arr[mid] <= value:
                lo = mid + 1
            else:
                hi = mid
        return lo

    @njit(cache=True)
    def _simulate_single_dynamic_y(
        epoch_ms: np.ndarray,
        close: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        x_percent: float,
        y_max_window_sec: int,
        z_percent: float,
        max_hold_seconds: int,
        position_size: float,
        fee_rate: float,
        slippage_rate: float,
        direction: int,
    ) -> Tuple[np.ndarray, int]:
        """
        Simula la strategia con Y dinamico.
        Cerca il minimo nella finestra y_max_window e verifica se current >= X% sopra.

        Output: array 2D con colonne:
            [0] entry_idx
            [1] exit_idx
            [2] entry_price (con slippage)
            [3] exit_price (con slippage)
            [4] max_price_during_trade
            [5] min_price_during_trade
            [6] pnl
            [7] pnl_percent
            [8] fees
            [9] reason (1=drop-z, 2=max-hold, 3=end-of-data)
            [10] y_actual_seconds (quanti secondi fa era il minimo)

        Returns:
            trades_out: float64[:, 11] - array con trade
            n_trades: int64 - numero effettivo di trade
        """
        n = len(close)
        y_max_window_ms = y_max_window_sec * 1000
        max_hold_ms = max_hold_seconds * 1000

        max_trades = 10000
        trades_out = np.empty((max_trades, 11), dtype=np.float64)
        n_trades = 0

        i = 0
        while i < n:
            current_time_ms = epoch_ms[i]
            current_close = close[i]
            window_start_ms = current_time_ms - y_max_window_ms

            # Trova il minimo dei close nella finestra con binary search
            # del confine + scansione forward (O(log n + W) per candela,
            # come in gpu_fallback._cpu_screen_batch_dynamic_y).
            min_close_val = current_close
            min_close_idx = i

            lo_bs, hi_bs = 0, i
            while lo_bs < hi_bs:
                mid_bs = (lo_bs + hi_bs) // 2
                if epoch_ms[mid_bs] < window_start_ms:
                    lo_bs = mid_bs + 1
                else:
                    hi_bs = mid_bs
            window_start_idx = lo_bs

            for k in range(window_start_idx, i):
                if close[k] < min_close_val:
                    min_close_val = close[k]
                    min_close_idx = k

            if min_close_val == 0.0 or min_close_idx == i:
                i += 1
                continue

            # Calcola movimento dal minimo
            move_percent = (current_close - min_close_val) / min_close_val * 100.0

            if move_percent >= x_percent:
                # Y effettivo
                y_actual_ms = current_time_ms - epoch_ms[min_close_idx]
                y_actual_s = float(y_actual_ms) / 1000.0

                # Apri trade
                entry_epoch_ms = epoch_ms[i]
                raw_entry = current_close

                if direction == 1:
                    entry_price = raw_entry * (1.0 + slippage_rate)
                elif direction == 2:
                    entry_price = raw_entry * (1.0 - slippage_rate)
                else:
                    entry_price = raw_entry

                max_price = entry_price
                min_price = entry_price
                exit_idx = -1
                reason = 3

                for j in range(i + 1, n):
                    c = close[j]
                    h = high[j]
                    l = low[j]

                    if h > max_price:
                        max_price = h
                    if l < min_price:
                        min_price = l

                    elapsed_ms = epoch_ms[j] - entry_epoch_ms

                    if max_price > 0.0:
                        drop_pct = (max_price - c) / max_price * 100.0
                    else:
                        drop_pct = 0.0

                    if drop_pct >= z_percent:
                        exit_idx = j
                        reason = 1
                        break

                    if elapsed_ms >= max_hold_ms:
                        exit_idx = j
                        reason = 2
                        break

                if exit_idx == -1:
                    exit_idx = n - 1
                    reason = 3
                    if high[exit_idx] > max_price:
                        max_price = high[exit_idx]
                    if low[exit_idx] < min_price:
                        min_price = low[exit_idx]

                raw_exit = close[exit_idx]
                if direction == 1:
                    exit_price = raw_exit * (1.0 - slippage_rate)
                elif direction == 2:
                    exit_price = raw_exit * (1.0 + slippage_rate)
                else:
                    exit_price = raw_exit

                fees = position_size * fee_rate * 2.0

                if direction == 0:
                    pnl = 0.0
                    if entry_price > 0.0:
                        pnl_percent = (exit_price - entry_price) / entry_price * 100.0
                    else:
                        pnl_percent = 0.0
                    fees = 0.0
                elif direction == 1:
                    quantity = position_size / entry_price
                    pnl = (exit_price - entry_price) * quantity - fees
                    if position_size > 0.0:
                        pnl_percent = pnl / position_size * 100.0
                    else:
                        pnl_percent = 0.0
                else:
                    quantity = position_size / entry_price
                    pnl = (entry_price - exit_price) * quantity - fees
                    if position_size > 0.0:
                        pnl_percent = pnl / position_size * 100.0
                    else:
                        pnl_percent = 0.0

                if n_trades < max_trades:
                    trades_out[n_trades, 0] = float(i)
                    trades_out[n_trades, 1] = float(exit_idx)
                    trades_out[n_trades, 2] = entry_price
                    trades_out[n_trades, 3] = exit_price
                    trades_out[n_trades, 4] = max_price
                    trades_out[n_trades, 5] = min_price
                    trades_out[n_trades, 6] = pnl
                    trades_out[n_trades, 7] = pnl_percent
                    trades_out[n_trades, 8] = fees
                    trades_out[n_trades, 9] = float(reason)
                    trades_out[n_trades, 10] = y_actual_s
                    n_trades += 1

                i = exit_idx + 1
            else:
                i += 1

        return trades_out[:n_trades], n_trades


else:
    # Stub quando numba non è disponibile: sollevano NumbaMissingError.
    # Le firme restano tipizzate per coerenza con il ramo njit.
    def _simulate_single(*args: object, **kwargs: object) -> tuple:
        raise NumbaMissingError("Numba non disponibile. Installa con: pip install numba")

    def _simulate_single_dynamic_y(*args: object, **kwargs: object) -> tuple:
        raise NumbaMissingError("Numba non disponibile. Installa con: pip install numba")

    def _searchsorted_right(*args: object, **kwargs: object) -> int:
        raise NumbaMissingError("Numba non disponibile. Installa con: pip install numba")