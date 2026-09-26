"""
filters.py - Filtri intelligenti per scartare strategie deboli

Applica soglie minime su metriche chiave per eliminare:
- Strategie con troppi pochi trade (non statisticamente significative)
- Strategie con win rate troppo basso
- Strategie con profit factor insufficiente
- Strategie con drawdown eccessivo
"""

from typing import List, Dict


def apply_filters(
    strategies: List[Dict[str, object]],
    min_trades: int = 20,
    min_win_rate: float = 40.0,
    min_profit_factor: float = 1.2,
    max_drawdown: float = 30.0,
) -> List[Dict[str, object]]:
    """
    Filtra strategie che non rispettano le soglie minime.
    
    Args:
        strategies: lista di dict con metriche
        min_trades: numero minimo di trade
        min_win_rate: win rate minimo in percentuale (es. 40.0 = 40%)
        min_profit_factor: profit factor minimo
        max_drawdown: drawdown massimo accettabile in percentuale
    
    Returns:
        Lista filtrata (solo strategie che passano tutti i filtri).
    """
    filtered = []
    
    for s in strategies:
        # Filtro 1: Numero minimo trade
        if s["total_trades"] < min_trades:
            continue
        
        # Filtro 2: Win rate minimo
        if s["win_rate"] < min_win_rate:
            continue
        
        # Filtro 3: Profit factor minimo
        if s["profit_factor"] < min_profit_factor:
            continue
        
        # Filtro 4: Max drawdown
        if s["max_drawdown"] > max_drawdown:
            continue
        
        filtered.append(s)
    
    return filtered


def print_filter_summary(
    total_before: int,
    total_after: int,
    min_trades: int,
    min_win_rate: float,
    min_profit_factor: float,
    max_drawdown: float,
) -> None:
    """Stampa riepilogo dei filtri applicati."""
    eliminated = total_before - total_after
    pct = (eliminated / total_before * 100) if total_before > 0 else 0
    
    print(f"\n  🔍 Filtri applicati:")
    print(f"     MIN_TRADES >= {min_trades}")
    print(f"     MIN_WIN_RATE >= {min_win_rate}%")
    print(f"     MIN_PROFIT_FACTOR >= {min_profit_factor}")
    print(f"     MAX_DRAWDOWN <= {max_drawdown}%")
    print(f"\n  📊 Risultato filtri:")
    print(f"     Strategie iniziali:  {total_before}")
    print(f"     Eliminate:           {eliminated} ({pct:.1f}%)")
    print(f"     Sopravvissute:       {total_after}")