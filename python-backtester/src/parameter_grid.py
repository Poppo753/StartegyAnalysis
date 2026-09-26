"""
parameter_grid.py - Generazione della griglia di parametri

Genera tutte le combinazioni X/Y/Z dalla configurazione .env
e crea gli oggetti BacktestParams corrispondenti.
"""

from itertools import product
from typing import List
from src.config import Config
from src.strategy import BacktestParams


def generate_parameter_grid(config: Config) -> List[BacktestParams]:
    """
    Genera tutte le combinazioni di parametri X, Y, Z dalla configurazione.

    Args:
        config: configurazione caricata dal .env

    Returns:
        Lista di BacktestParams, una per ogni combinazione X/Y/Z
    """
    # Stampa informazioni sulla griglia generata
    n_x = len(config.x_values)
    n_y = len(config.y_values)
    n_z = len(config.z_values)

    if config.y_dynamic:
        total = n_x * n_z
        print(f"  [GRID] X values: {n_x} | Z values: {n_z} | Y: DINAMICO (max {config.y_max_window}s)")
        print(f"  [GRID] Combinazioni totali: {total} (solo X × Z)")
    else:
        total = n_x * n_y * n_z
        print(f"  [GRID] X values: {n_x} | Y values: {n_y} | Z values: {n_z}")
        print(f"  [GRID] Combinazioni totali: {total}")

    if total > 10000:
        print(f"  ⚠️  [WARNING] Numero di combinazioni elevato ({total} > 10000). L'esecuzione potrebbe richiedere molto tempo.")

    combinations = list(product(config.x_values, config.y_values, config.z_values))

    params_list: List[BacktestParams] = []

    for x, y, z in combinations:
        params = BacktestParams(
            x_percent=x,
            y_seconds=y,
            z_percent=z,
            max_hold_seconds=config.max_hold_seconds,
            initial_capital=config.initial_capital,
            position_size=config.position_size,
            fee_rate=config.fee_rate,
            slippage_rate=config.slippage_rate,
            direction=config.direction,
        )
        params_list.append(params)

    return params_list