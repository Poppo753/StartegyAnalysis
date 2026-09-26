"""
screening_metrics.py - Calcolo metriche derivate dai risultati GPU/screening

Partendo dalle 8 metriche raw (output del kernel GPU o fallback CPU),
calcola metriche avanzate e scoring per ranking strategie.
"""

import numpy as np
from typing import Dict, List, Tuple


def compute_derived_metrics(
    raw_results: np.ndarray,
    combinations: List[Tuple[float, int, float]],
    initial_capital: float,
    y_dynamic: bool = False,
) -> List[Dict[str, object]]:
    """
    Calcola metriche derivate dalle metriche raw del screening.
    
    Args:
        raw_results: array (n, 8) o (n, 9) dal GPU/CPU screening
            [total_trades, winning, losing, total_pnl,
             gross_profit, gross_loss, best_trade, worst_trade,
             (avg_y_actual se y_dynamic)]
        combinations: lista di tuple (x, y, z)
        initial_capital: capitale iniziale
        y_dynamic: se True, la colonna 8 contiene avg_y_actual
    
    Returns:
        Lista di dict con tutte le metriche per ogni combinazione.
    """
    results = []
    
    for idx in range(len(combinations)):
        x, y, z = combinations[idx]
        row = raw_results[idx]
        
        total_trades = int(row[0])
        winning_trades = int(row[1])
        losing_trades = int(row[2])
        total_pnl = row[3]
        gross_profit = row[4]
        gross_loss = row[5]  # Negativo!
        best_trade = row[6]
        worst_trade = row[7]
        avg_y_actual = row[8] if y_dynamic and raw_results.shape[1] > 8 else 0.0
        
        # Metriche base
        win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0
        
        # Profit factor
        abs_gross_loss = abs(gross_loss)
        if abs_gross_loss > 0:
            profit_factor = gross_profit / abs_gross_loss
        else:
            profit_factor = 999.99 if gross_profit > 0 else 0.0
        
        # Average win / loss
        avg_win = (gross_profit / winning_trades) if winning_trades > 0 else 0.0
        avg_loss = (gross_loss / losing_trades) if losing_trades > 0 else 0.0  # negativo
        
        # Expectancy = (win_rate * avg_win) + ((1-win_rate) * avg_loss)
        win_rate_dec = win_rate / 100.0
        expectancy = (win_rate_dec * avg_win) + ((1 - win_rate_dec) * abs(avg_loss) * -1)
        
        # Max drawdown stimato (approssimazione dallo screening)
        # Senza la equity curve completa, usiamo worst_trade come proxy
        max_drawdown = abs(worst_trade) / initial_capital * 100.0 if initial_capital > 0 else 0.0
        
        # Sharpe ratio semplificato (PnL medio / stima volatilità)
        # Approssimazione: assumiamo distribuzione uniforme tra best e worst
        if total_trades > 1:
            avg_pnl = total_pnl / total_trades
            # Stima std come range / 4 (regola empirica)
            pnl_range = best_trade - worst_trade
            std_estimate = pnl_range / 4.0 if pnl_range > 0 else 1.0
            sharpe_ratio = avg_pnl / std_estimate if std_estimate > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        entry = {
            "x_percent": x,
            "y_seconds": y,
            "z_percent": z,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 6),
            "gross_profit": round(gross_profit, 6),
            "gross_loss": round(gross_loss, 6),
            "profit_factor": round(profit_factor, 4),
            "best_trade": round(best_trade, 6),
            "worst_trade": round(worst_trade, 6),
            "avg_win": round(avg_win, 6),
            "avg_loss": round(avg_loss, 6),
            "expectancy": round(expectancy, 6),
            "max_drawdown": round(max_drawdown, 4),
            "sharpe_ratio": round(sharpe_ratio, 4),
        }
        if y_dynamic:
            entry["avg_y_actual"] = round(avg_y_actual, 2)
        results.append(entry)
    
    return results


def compute_score(strategy: Dict[str, object]) -> float:
    """
    Calcola lo score composito per ranking di una strategia.
    
    Formula:
        score = total_pnl * 0.4 
              + profit_factor * 0.3 
              + (win_rate / 100) * 0.2 
              - max_drawdown * 0.3
    
    Normalizzazione: pnl è normalizzato per evitare che un singolo
    componente domini lo score.
    """
    pnl = strategy["total_pnl"]
    pf = min(strategy["profit_factor"], 10.0)  # Cap PF a 10 per evitare outliers
    wr = strategy["win_rate"] / 100.0
    dd = strategy["max_drawdown"]
    
    score = (
        pnl * 0.4
        + pf * 0.3
        + wr * 0.2
        - dd * 0.3
    )
    
    return round(score, 6)


def rank_strategies(strategies: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """
    Calcola lo score per ogni strategia e ordina per score decrescente.
    
    Returns:
        Lista ordinata per score (migliore primo).
    """
    for s in strategies:
        s["score"] = compute_score(s)
    
    return sorted(strategies, key=lambda s: s["score"], reverse=True)