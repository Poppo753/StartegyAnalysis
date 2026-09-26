"""
strategies/__init__.py - Registry delle strategie disponibili (Fase 1).

Nomi registrati:
- "momentum_drop"  → MomentumDropStrategy (strategia storica, default)
- "mean_reversion" (+ alias "mean_reversion_zscore") → MeanReversionZScore
"""

from src.strategies.momentum_drop import MomentumDropStrategy
from src.strategies.mean_reversion import MeanReversionZScore

STRATEGY_REGISTRY = {
    "momentum_drop": MomentumDropStrategy,
    "mean_reversion": MeanReversionZScore,
    "mean_reversion_zscore": MeanReversionZScore,
}

__all__ = ["MomentumDropStrategy", "MeanReversionZScore", "STRATEGY_REGISTRY"]
