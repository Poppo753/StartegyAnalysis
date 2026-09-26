"""
strategies/__init__.py - Registry delle strategie disponibili (Fase 1).

Nomi registrati:
- "momentum_drop"  → MomentumDropStrategy (strategia storica, default)
- "mean_reversion" (+ alias "mean_reversion_zscore") → MeanReversionZScore
- "mia"            → MiaStrategy (esempio di procedura, vedi
                      docs/COME_AGGIUNGERE_UNA_STRATEGIA.md)
"""

from src.strategies.mia import MiaStrategy
from src.strategies.momentum_drop import MomentumDropStrategy
from src.strategies.mean_reversion import MeanReversionZScore

STRATEGY_REGISTRY = {
    "momentum_drop": MomentumDropStrategy,
    "mean_reversion": MeanReversionZScore,
    "mean_reversion_zscore": MeanReversionZScore,
    "mia": MiaStrategy,
}

__all__ = [
    "MiaStrategy",
    "MomentumDropStrategy",
    "MeanReversionZScore",
    "STRATEGY_REGISTRY",
]
