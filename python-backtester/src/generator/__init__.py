"""Generator package (Fase 4, F4-G01...G04).

Contenuto (solo file nuovi, nessun riuso modificato):
- strategy_generator.py: TEMPLATE_REGISTRY + generate_from_template (F4-G01)
- crossover.py: StrategyCrossover parametrico + strutturale (F4-G02)
- mutation.py: StrategyMutation con ampiezza parametrizzata (F4-G03)
- evolution.py: loop evolutivo 50x10 con F3-light (F4-G04)

F4-G05 (LLM-assisted) esplicitamente NON implementato (default NON fare).
"""

from src.generator.crossover import StrategyCrossover
from src.generator.evolution import make_synthetic_ohlc, run_evolution
from src.generator.mutation import StrategyMutation
from src.generator.strategy_generator import TEMPLATE_REGISTRY, generate_from_template

__all__ = [
    "TEMPLATE_REGISTRY",
    "generate_from_template",
    "StrategyCrossover",
    "StrategyMutation",
    "make_synthetic_ohlc",
    "run_evolution",
]
