"""
gpu_runner.py - Orchestratore del motore GPU/screening (Fase 3)

Pipeline completa:
1. Split dati in TRAIN / VALIDATION
2. GPU screening su TRAIN (o fallback CPU)
3. Filtri intelligenti
4. Scoring e ranking
5. Validazione CPU delle migliori strategie su TRAIN + VALIDATION
6. Output risultati e insight
"""

import os
import time
import numpy as np
import pandas as pd
from itertools import product
from typing import List, Tuple

from src.config import Config
from src.gpu.gpu_detector import check_gpu_available, print_gpu_status
from src.gpu.data_splitter import split_train_validation, print_split_info
from src.gpu.screening_metrics import compute_derived_metrics, rank_strategies
from src.gpu.filters import apply_filters, print_filter_summary
from src.fast.fast_simulator import _simulate_single, _simulate_single_dynamic_y, check_numba_available, NumbaMissingError
from src.fast.fast_metrics import calculate_fast_metrics


# Mapping direction stringa -> intero
DIRECTION_MAP = {
    "signal-only": 0,
    "long": 1,
    "short": 2,
}

REASON_MAP = {
    1: "drop-z",
    2: "max-hold",
    3: "end-of-data",
}


def run_gpu_pipeline(df: pd.DataFrame, config: Config, symbol: str) -> str:
    """
    Esegue la pipeline completa Fase 3 per un simbolo.
    
    Args:
        df: DataFrame completo con dati OHLC
        config: configurazione
        symbol: simbolo in esame
    
    Returns:
        Percorso directory output
    """
    # --- Setup ---
    direction_int = DIRECTION_MAP[config.direction]
    output_dir = os.path.join(config.output_dir, symbol, "gpu")
    os.makedirs(output_dir, exist_ok=True)
    
    # Genera griglia
    if config.y_dynamic:
        # Y dinamico: griglia solo X × Z
        combinations = [(x, config.y_max_window, z) for x, z in product(config.x_values, config.z_values)]
        n_combinations = len(combinations)
        print(f"\n  🚀 Engine: GPU SCREENING (Fase 3) — Y DINAMICO")
        print(f"  🔢 Combinazioni X×Z: {n_combinations} (Y_MAX_WINDOW={config.y_max_window}s)")
    else:
        combinations = list(product(config.x_values, config.y_values, config.z_values))
        n_combinations = len(combinations)
        print(f"\n  🚀 Engine: GPU SCREENING (Fase 3)")
        print(f"  🔢 Combinazioni totali: {n_combinations}")
    print_gpu_status()
    
    # --- STEP 1: Split temporale ---
    train_ratio = config.train_ratio
    df_train, df_validation = split_train_validation(df, train_ratio)
    print_split_info(df, df_train, df_validation)
    
    # Prepara array numpy per TRAIN
    train_epoch_ms = (df_train["epoch_seconds"].values * 1000).astype(np.int64)
    train_close = df_train["close"].values.astype(np.float64)
    train_high = df_train["high"].values.astype(np.float64)
    train_low = df_train["low"].values.astype(np.float64)
    
    # --- STEP 2: Screening su TRAIN ---
    print(f"\n  ⚡ STEP 1: Screening {n_combinations} combinazioni su TRAIN...")
    screen_start = time.time()
    
    use_gpu = check_gpu_available()
    
    if config.y_dynamic:
        # Y dinamico: griglia X×Z, cerca minimo nella finestra
        xz_combinations = [(c[0], c[2]) for c in combinations]  # (x, z) pairs
        
        if use_gpu:
            from src.gpu.gpu_simulator import gpu_screen_combinations_dynamic_y
            print(f"  🎮 Usando GPU (Y dinamico, finestra max {config.y_max_window}s)")
            raw_results = gpu_screen_combinations_dynamic_y(
                train_epoch_ms, train_close, train_high, train_low,
                xz_combinations,
                config.y_max_window,
                config.max_hold_seconds,
                config.position_size,
                config.fee_rate,
                config.slippage_rate,
                direction_int,
                batch_size=config.gpu_batch_size,
            )
        else:
            from src.gpu.gpu_fallback import cpu_screen_combinations_dynamic_y
            print(f"  ⚠️  GPU non disponibile → uso fast CPU (Y dinamico, finestra max {config.y_max_window}s)")
            raw_results = cpu_screen_combinations_dynamic_y(
                train_epoch_ms, train_close, train_high, train_low,
                xz_combinations,
                config.y_max_window,
                config.max_hold_seconds,
                config.position_size,
                config.fee_rate,
                config.slippage_rate,
                direction_int,
                batch_size=config.gpu_batch_size,
            )
    else:
        # Modalità classica: griglia X×Y×Z
        if use_gpu:
            from src.gpu.gpu_simulator import gpu_screen_combinations
            print(f"  🎮 Usando GPU")
            raw_results = gpu_screen_combinations(
                train_epoch_ms, train_close, train_high, train_low,
                combinations,
                config.max_hold_seconds,
                config.position_size,
                config.fee_rate,
                config.slippage_rate,
                direction_int,
                batch_size=config.gpu_batch_size,
            )
        else:
            from src.gpu.gpu_fallback import cpu_screen_combinations
            print(f"  ⚠️  GPU non disponibile → uso fast CPU per screening")
            raw_results = cpu_screen_combinations(
                train_epoch_ms, train_close, train_high, train_low,
                combinations,
                config.max_hold_seconds,
                config.position_size,
                config.fee_rate,
                config.slippage_rate,
                direction_int,
            )
    
    screen_elapsed = time.time() - screen_start
    print(f"  ⏱️  Screening completato in {screen_elapsed:.2f}s")
    
    # --- STEP 3: Calcola metriche derivate ---
    strategies = compute_derived_metrics(raw_results, combinations, config.initial_capital, y_dynamic=config.y_dynamic)
    
    # --- STEP 4: Filtri intelligenti ---
    total_before = len(strategies)
    
    if config.skip_filters:
        print(f"\n  ⏭️  SKIP_FILTERS=true → filtri disabilitati, uso tutte le {total_before} strategie")
        filtered = strategies
    else:
        filtered = apply_filters(
            strategies,
            min_trades=config.min_trades,
            min_win_rate=config.min_win_rate,
            min_profit_factor=config.min_profit_factor,
            max_drawdown=config.max_drawdown_filter,
        )
        print_filter_summary(
            total_before, len(filtered),
            config.min_trades, config.min_win_rate,
            config.min_profit_factor, config.max_drawdown_filter,
        )
    
    if len(filtered) == 0:
        print("\n  ⚠️  Nessuna strategia ha superato i filtri. Pipeline terminata.")
        print("  💡 Suggerimento: prova SKIP_FILTERS=true o abbassa i valori MIN_* nel .env")
        # Salva comunque summary vuoto
        _save_summary_csv(strategies, output_dir, "summary_train.csv")
        return output_dir
    
    # --- STEP 5: Scoring e ranking ---
    ranked = rank_strategies(filtered)
    
    # Top N per validazione
    top_n = min(config.fast_top_n, len(ranked))
    best_strategies = ranked[:top_n]
    
    print(f"\n  🏆 Top {top_n} strategie (TRAIN) per score:")
    _print_top_table(best_strategies[:10], config.direction)
    
    # --- STEP 6: Validazione CPU su TRAIN e VALIDATION ---
    print(f"\n  🔬 STEP 2: Validazione dettagliata top {top_n} su TRAIN + VALIDATION...")

    try:
        check_numba_available()
    except NumbaMissingError as e:
        raise NumbaMissingError(
            f"{e} (validazione CPU del pipeline gpu richiesta ma numba assente)"
        ) from e
    
    # Prepara array VALIDATION
    val_epoch_ms = (df_validation["epoch_seconds"].values * 1000).astype(np.int64)
    val_close = df_validation["close"].values.astype(np.float64)
    val_high = df_validation["high"].values.astype(np.float64)
    val_low = df_validation["low"].values.astype(np.float64)
    
    train_results = []
    validation_results = []
    
    for rank, strategy in enumerate(best_strategies, 1):
        x = strategy["x_percent"]
        y = strategy["y_seconds"]
        z = strategy["z_percent"]
        avg_y_actual = strategy.get("avg_y_actual", 0)
        
        # --- TRAIN dettagliato ---
        if config.y_dynamic:
            trades_train, n_train = _simulate_single_dynamic_y(
                train_epoch_ms, train_close, train_high, train_low,
                np.float64(x), np.int64(config.y_max_window), np.float64(z),
                np.int64(config.max_hold_seconds),
                np.float64(config.position_size),
                np.float64(config.fee_rate),
                np.float64(config.slippage_rate),
                np.int64(direction_int),
            )
        else:
            trades_train, n_train = _simulate_single(
                train_epoch_ms, train_close, train_high, train_low,
                np.float64(x), np.int64(y), np.float64(z),
                np.int64(config.max_hold_seconds),
                np.float64(config.position_size),
                np.float64(config.fee_rate),
                np.float64(config.slippage_rate),
                np.int64(direction_int),
            )
        metrics_train = calculate_fast_metrics(trades_train, n_train, direction_int, config.initial_capital)
        metrics_train.update({"x_percent": x, "y_seconds": y, "z_percent": z, "rank": rank})
        if config.y_dynamic:
            metrics_train["avg_y_actual"] = round(avg_y_actual, 2)
            # Calcola avg_y_actual dal dettaglio trade se disponibile
            if n_train > 0 and trades_train.shape[1] > 10:
                metrics_train["avg_y_actual"] = round(float(np.mean(trades_train[:n_train, 10])), 2)
        
        # Metriche avanzate
        _add_advanced_metrics(metrics_train, trades_train, n_train, direction_int)
        
        n_cols = trades_train.shape[1] if n_train > 0 else 10
        train_results.append({
            "metrics": metrics_train,
            "trades_array": trades_train.copy() if n_train > 0 else np.empty((0, n_cols)),
            "n_trades": n_train,
        })
        
        # --- VALIDATION ---
        if config.y_dynamic:
            trades_val, n_val = _simulate_single_dynamic_y(
                val_epoch_ms, val_close, val_high, val_low,
                np.float64(x), np.int64(config.y_max_window), np.float64(z),
                np.int64(config.max_hold_seconds),
                np.float64(config.position_size),
                np.float64(config.fee_rate),
                np.float64(config.slippage_rate),
                np.int64(direction_int),
            )
        else:
            trades_val, n_val = _simulate_single(
                val_epoch_ms, val_close, val_high, val_low,
                np.float64(x), np.int64(y), np.float64(z),
                np.int64(config.max_hold_seconds),
                np.float64(config.position_size),
                np.float64(config.fee_rate),
                np.float64(config.slippage_rate),
                np.int64(direction_int),
            )
        metrics_val = calculate_fast_metrics(trades_val, n_val, direction_int, config.initial_capital)
        metrics_val.update({"x_percent": x, "y_seconds": y, "z_percent": z, "rank": rank})
        if config.y_dynamic and n_val > 0 and trades_val.shape[1] > 10:
            metrics_val["avg_y_actual"] = round(float(np.mean(trades_val[:n_val, 10])), 2)
        
        _add_advanced_metrics(metrics_val, trades_val, n_val, direction_int)
        
        n_cols_val = trades_val.shape[1] if n_val > 0 else 10
        validation_results.append({
            "metrics": metrics_val,
            "trades_array": trades_val.copy() if n_val > 0 else np.empty((0, n_cols_val)),
            "n_trades": n_val,
        })
    
    # --- STEP 7: Stampa confronto TRAIN vs VALIDATION ---
    print(f"\n  📊 Confronto TRAIN vs VALIDATION (top 10):")
    _print_comparison_table(train_results[:10], validation_results[:10], config.direction)
    
    # --- STEP 8: Salva output ---
    print(f"\n  💾 Salvataggio risultati...")
    
    # Summary CSV
    _save_summary_csv(strategies, output_dir, "summary_train.csv")
    _save_filtered_csv(ranked, output_dir, "filtered_strategies.csv")
    _save_best_csv(train_results, validation_results, output_dir, "best_strategies.csv")
    
    # Trades CSV per top strategie
    _save_trades_files(train_results, df_train, output_dir, "train")
    _save_trades_files(validation_results, df_validation, output_dir, "validation")
    
    # --- STEP 9: Insight finale ---
    _print_final_insight(strategies, filtered, train_results, validation_results)
    
    return output_dir


def _add_advanced_metrics(metrics: dict, trades_array: np.ndarray, n_trades: int, direction: int) -> None:
    """Aggiunge metriche avanzate (Sezione 6) al dict metriche."""
    if n_trades == 0:
        metrics["sharpe_ratio"] = 0.0
        metrics["expectancy"] = 0.0
        metrics["avg_win"] = 0.0
        metrics["avg_loss"] = 0.0
        metrics["max_consecutive_losses"] = 0
        return
    
    # Usa pnl_percent per signal-only, pnl per long/short
    if direction == 0:
        pnls = trades_array[:n_trades, 7]  # pnl_percent
    else:
        pnls = trades_array[:n_trades, 6]  # pnl
    
    # Sharpe ratio semplificato (annualizzato non serve per confronto relativo)
    mean_pnl = np.mean(pnls)
    std_pnl = np.std(pnls)
    metrics["sharpe_ratio"] = round(float(mean_pnl / std_pnl) if std_pnl > 0 else 0.0, 4)
    
    # Avg win / Avg loss
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    metrics["avg_win"] = round(float(np.mean(wins)) if len(wins) > 0 else 0.0, 6)
    metrics["avg_loss"] = round(float(np.mean(losses)) if len(losses) > 0 else 0.0, 6)
    
    # Expectancy
    win_rate = len(wins) / n_trades
    metrics["expectancy"] = round(
        (win_rate * metrics["avg_win"]) + ((1 - win_rate) * metrics["avg_loss"]), 6
    )
    
    # Max consecutive losses
    max_consec = 0
    current_consec = 0
    for p in pnls:
        if p <= 0:
            current_consec += 1
            if current_consec > max_consec:
                max_consec = current_consec
        else:
            current_consec = 0
    metrics["max_consecutive_losses"] = max_consec
    
    # MAE (Maximum Adverse Excursion) - quanto è sceso sotto entry
    # Colonna [5] = min_price, colonna [2] = entry_price
    entry_prices = trades_array[:n_trades, 2]
    min_prices = trades_array[:n_trades, 5]
    
    with np.errstate(divide='ignore', invalid='ignore'):
        mae_per_trade = np.where(
            entry_prices > 0,
            (entry_prices - min_prices) / entry_prices * 100.0,
            0.0
        )
    metrics["avg_mae"] = round(float(np.mean(mae_per_trade)), 4)
    metrics["max_mae"] = round(float(np.max(mae_per_trade)), 4)


def _print_top_table(strategies: List[dict], direction: str) -> None:
    """Stampa tabella top strategie."""
    has_y_actual = "avg_y_actual" in strategies[0] if strategies else False
    
    if has_y_actual:
        print("  " + "-" * 105)
        print(f"    {'#':<3} {'X%':<6} {'Z%':<6} {'AvgY':<7} {'Trades':<8} {'Win%':<7} {'PnL':<10} {'PF':<7} {'DD%':<7} {'Score':<8}")
        print("  " + "-" * 105)
    else:
        print("  " + "-" * 95)
        print(f"    {'#':<3} {'X%':<6} {'Y(s)':<6} {'Z%':<6} {'Trades':<8} {'Win%':<7} {'PnL':<10} {'PF':<7} {'DD%':<7} {'Score':<8}")
        print("  " + "-" * 95)
    
    for idx, s in enumerate(strategies, 1):
        if has_y_actual:
            print(
                f"    {idx:<3} "
                f"{s['x_percent']:<6.1f} "
                f"{s['z_percent']:<6.1f} "
                f"{s['avg_y_actual']:<7.1f} "
                f"{s['total_trades']:<8} "
                f"{s['win_rate']:<7.1f} "
                f"{s['total_pnl']:<10.4f} "
                f"{s['profit_factor']:<7.2f} "
                f"{s['max_drawdown']:<7.2f} "
                f"{s['score']:<8.3f}"
            )
        else:
            print(
                f"    {idx:<3} "
                f"{s['x_percent']:<6.1f} "
                f"{s['y_seconds']:<6} "
                f"{s['z_percent']:<6.1f} "
                f"{s['total_trades']:<8} "
                f"{s['win_rate']:<7.1f} "
                f"{s['total_pnl']:<10.4f} "
                f"{s['profit_factor']:<7.2f} "
                f"{s['max_drawdown']:<7.2f} "
                f"{s['score']:<8.3f}"
            )
    
    print("  " + "-" * (105 if has_y_actual else 95))


def _print_comparison_table(
    train_results: List[dict],
    val_results: List[dict],
    direction: str,
) -> None:
    """Stampa confronto TRAIN vs VALIDATION."""
    has_y_actual = "avg_y_actual" in train_results[0]["metrics"] if train_results else False
    
    if has_y_actual:
        print("  " + "-" * 120)
        print(f"    {'#':<3} {'X%':<5} {'Z%':<5} {'AvgY':<6} {'|':<2} {'Tr.T':<6} {'Tr.WR':<7} {'Tr.PnL':<10} {'Tr.PF':<6} {'|':<2} {'V.T':<6} {'V.WR':<7} {'V.PnL':<10} {'V.PF':<6} {'|':<2} {'Status':<10}")
        print("  " + "-" * 120)
    else:
        print("  " + "-" * 110)
        print(f"    {'#':<3} {'X%':<5} {'Y':<4} {'Z%':<5} {'|':<2} {'Tr.T':<6} {'Tr.WR':<7} {'Tr.PnL':<10} {'Tr.PF':<6} {'|':<2} {'V.T':<6} {'V.WR':<7} {'V.PnL':<10} {'V.PF':<6} {'|':<2} {'Status':<10}")
        print("  " + "-" * 110)
    
    for i in range(len(train_results)):
        mt = train_results[i]["metrics"]
        mv = val_results[i]["metrics"]
        
        # Determina status
        train_profitable = mt["total_pnl"] > 0 if direction != "signal-only" else mt["total_pnl_percent"] > 0
        val_profitable = mv["total_pnl"] > 0 if direction != "signal-only" else mv["total_pnl_percent"] > 0
        
        if train_profitable and val_profitable:
            status = "✅ ROBUST"
        elif train_profitable and not val_profitable:
            status = "⚠️  OVERFIT"
        elif not train_profitable:
            status = "❌ WEAK"
        else:
            status = "🔄 CHECK"
        
        pnl_key = "total_pnl" if direction != "signal-only" else "total_pnl_percent"
        
        if has_y_actual:
            avg_y = mt.get('avg_y_actual', 0)
            print(
                f"    {i+1:<3} "
                f"{mt['x_percent']:<5.1f} "
                f"{mt['z_percent']:<5.1f} "
                f"{avg_y:<6.1f} "
                f"{'|':<2} "
                f"{mt['total_trades']:<6} "
                f"{mt['win_rate']:<7.1f} "
                f"{mt[pnl_key]:<10.4f} "
                f"{mt['profit_factor']:<6.2f} "
                f"{'|':<2} "
                f"{mv['total_trades']:<6} "
                f"{mv['win_rate']:<7.1f} "
                f"{mv[pnl_key]:<10.4f} "
                f"{mv['profit_factor']:<6.2f} "
                f"{'|':<2} "
                f"{status:<10}"
            )
        else:
            print(
                f"    {i+1:<3} "
                f"{mt['x_percent']:<5.1f} "
                f"{mt['y_seconds']:<4} "
                f"{mt['z_percent']:<5.1f} "
                f"{'|':<2} "
                f"{mt['total_trades']:<6} "
                f"{mt['win_rate']:<7.1f} "
                f"{mt[pnl_key]:<10.4f} "
                f"{mt['profit_factor']:<6.2f} "
                f"{'|':<2} "
                f"{mv['total_trades']:<6} "
                f"{mv['win_rate']:<7.1f} "
                f"{mv[pnl_key]:<10.4f} "
                f"{mv['profit_factor']:<6.2f} "
                f"{'|':<2} "
                f"{status:<10}"
            )
    
    print("  " + "-" * (120 if has_y_actual else 110))


def _print_final_insight(
    all_strategies: List[dict],
    filtered: List[dict],
    train_results: List[dict],
    validation_results: List[dict],
) -> None:
    """Stampa insight finale."""
    n_validated = len(train_results)
    n_robust = 0
    n_overfit = 0
    
    for tr, vr in zip(train_results, validation_results):
        train_pnl = tr["metrics"]["total_pnl"] + tr["metrics"]["total_pnl_percent"]
        val_pnl = vr["metrics"]["total_pnl"] + vr["metrics"]["total_pnl_percent"]
        
        if train_pnl > 0 and val_pnl > 0:
            n_robust += 1
        elif train_pnl > 0 and val_pnl <= 0:
            n_overfit += 1
    
    print(f"\n  {'='*60}")
    print(f"  📈 INSIGHT FINALE")
    print(f"  {'='*60}")
    print(f"     Strategie totali screened:    {len(all_strategies)}")
    print(f"     Dopo filtri:                  {len(filtered)}")
    print(f"     Validate su TRAIN+VALIDATION: {n_validated}")
    print(f"     ✅ Robuste (profitto su entrambi): {n_robust}")
    print(f"     ⚠️  Overfitted (solo TRAIN):       {n_overfit}")
    print(f"     ❌ Deboli:                         {n_validated - n_robust - n_overfit}")
    
    if n_robust > 0:
        print(f"\n     💡 {n_robust} strategie hanno confermato profitto out-of-sample!")
    elif n_overfit > 0:
        print(f"\n     ⚠️  Attenzione: tutte le strategie profittevoli sono overfitted.")
        print(f"        Considera parametri meno aggressivi o più dati.")
    print()


def _save_summary_csv(strategies: List[dict], output_dir: str, filename: str) -> None:
    """Salva CSV con tutte le strategie screened."""
    if not strategies:
        return
    df = pd.DataFrame(strategies)
    path = os.path.join(output_dir, filename)
    df.to_csv(path, index=False)
    print(f"  📄 {filename}: {len(strategies)} righe")


def _save_filtered_csv(strategies: List[dict], output_dir: str, filename: str) -> None:
    """Salva CSV con strategie filtrate e ranked."""
    if not strategies:
        return
    df = pd.DataFrame(strategies)
    path = os.path.join(output_dir, filename)
    df.to_csv(path, index=False)
    print(f"  📄 {filename}: {len(strategies)} righe")


def _save_best_csv(
    train_results: List[dict],
    val_results: List[dict],
    output_dir: str,
    filename: str,
):
    """Salva CSV confronto TRAIN vs VALIDATION per le migliori."""
    rows = []
    for tr, vr in zip(train_results, val_results):
        mt = tr["metrics"]
        mv = vr["metrics"]
        row_data = {
            "rank": mt["rank"],
            "x_percent": mt["x_percent"],
            "y_seconds": mt["y_seconds"],
            "z_percent": mt["z_percent"],
        }
        if "avg_y_actual" in mt:
            row_data["train_avg_y_actual"] = mt["avg_y_actual"]
        if "avg_y_actual" in mv:
            row_data["val_avg_y_actual"] = mv["avg_y_actual"]
        row_data.update({
            "train_trades": mt["total_trades"],
            "train_win_rate": mt["win_rate"],
            "train_pnl": round(mt["total_pnl"], 6),
            "train_pnl_percent": round(mt["total_pnl_percent"], 4),
            "train_profit_factor": round(mt["profit_factor"], 4),
            "train_max_drawdown": round(mt["max_drawdown"], 4),
            "train_sharpe": mt.get("sharpe_ratio", 0),
            "train_expectancy": mt.get("expectancy", 0),
            "train_max_consec_losses": mt.get("max_consecutive_losses", 0),
            "val_trades": mv["total_trades"],
            "val_win_rate": mv["win_rate"],
            "val_pnl": round(mv["total_pnl"], 6),
            "val_pnl_percent": round(mv["total_pnl_percent"], 4),
            "val_profit_factor": round(mv["profit_factor"], 4),
            "val_max_drawdown": round(mv["max_drawdown"], 4),
            "val_sharpe": mv.get("sharpe_ratio", 0),
            "val_expectancy": mv.get("expectancy", 0),
            "val_max_consec_losses": mv.get("max_consecutive_losses", 0),
        })
        # Aggiungi metriche MAE se disponibili
        if "avg_mae" in mt:
            row_data["train_avg_mae"] = mt["avg_mae"]
            row_data["train_max_mae"] = mt["max_mae"]
        if "avg_mae" in mv:
            row_data["val_avg_mae"] = mv["avg_mae"]
            row_data["val_max_mae"] = mv["max_mae"]
        
        rows.append(row_data)
    
    df = pd.DataFrame(rows)
    path = os.path.join(output_dir, filename)
    df.to_csv(path, index=False)
    print(f"  📄 {filename}: {len(rows)} righe")


def _save_trades_files(
    results: List[dict],
    df_source: pd.DataFrame,
    output_dir: str,
    prefix: str,  # "train" o "validation"
) -> None:
    """Salva trades CSV per ogni strategia validata."""
    timestamps_dt = df_source["datetime"].values
    
    for rank, r in enumerate(results, 1):
        if r["n_trades"] == 0:
            continue
        
        m = r["metrics"]
        filename = f"trades_{prefix}_{rank:03d}_x{m['x_percent']}_y{m['y_seconds']}_z{m['z_percent']}.csv"
        filepath = os.path.join(output_dir, filename)
        
        rows = []
        for t in range(r["n_trades"]):
            entry_idx = int(r["trades_array"][t, 0])
            exit_idx = int(r["trades_array"][t, 1])
            
            # Clamp agli indici validi
            entry_idx = min(entry_idx, len(timestamps_dt) - 1)
            exit_idx = min(exit_idx, len(timestamps_dt) - 1)
            
            entry_time = pd.Timestamp(timestamps_dt[entry_idx])
            exit_time = pd.Timestamp(timestamps_dt[exit_idx])
            reason_code = int(r["trades_array"][t, 9])
            reason_str = REASON_MAP.get(reason_code, f"unknown-{reason_code}")
            
            entry_price = r["trades_array"][t, 2]
            min_price = r["trades_array"][t, 5]
            
            # MAE: Maximum Adverse Excursion (quanto è sceso sotto entry)
            if entry_price > 0:
                mae_percent = round((entry_price - min_price) / entry_price * 100.0, 4)
            else:
                mae_percent = 0.0
            
            trade_row = {
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": entry_price,
                "exit_price": r["trades_array"][t, 3],
                "max_price": r["trades_array"][t, 4],
                "min_price": min_price,
                "mae_percent": mae_percent,
                "pnl": round(r["trades_array"][t, 6], 6),
                "pnl_percent": round(r["trades_array"][t, 7], 4),
                "fees": round(r["trades_array"][t, 8], 6),
                "reason": reason_str,
            }
            # Aggiungi y_actual se presente (colonna 10, dynamic Y mode)
            if r["trades_array"].shape[1] > 10:
                trade_row["y_actual_seconds"] = round(r["trades_array"][t, 10], 2)
            rows.append(trade_row)
        
        trades_df = pd.DataFrame(rows)
        trades_df.to_csv(filepath, index=False)
    
    n_saved = sum(1 for r in results if r["n_trades"] > 0)
    print(f"  📄 trades_{prefix}_*.csv: {n_saved} file")