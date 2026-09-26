"""mutation.py - StrategyMutation con ampiezza parametrizzata (F4-G03).

- float: jitter gaussiano sigma = sigma_frac * (hi-lo), clip ai bounds.
- float_log: jitter moltiplicativo exp(N(0, sigma_frac)), clip.
- int/int_log: step ±1, clip ai bounds.
- categorical: swap verso un'opzione (diversa se possibile).
- rate default 0.05 per parametro (probabilita' indipendente).
"""

from typing import Any, Dict, Tuple

import numpy as np


class StrategyMutation:
    """Mutazione parametrica con ampiezza configurabile.

    Args:
        rate: probabilita' di mutare ciascun parametro (default 0.05).
        sigma_frac: ampiezza jitter continuo come frazione del range.
    """

    def __init__(self, rate: float = 0.05, sigma_frac: float = 0.10) -> None:
        self.rate = float(rate)
        self.sigma_frac = float(sigma_frac)

    def mutate(
        self,
        params: Dict[str, Any],
        space: Dict[str, Tuple],
        rng: np.random.Generator,
    ) -> Dict[str, Any]:
        """Restituisce un NUOVO dict mutato (input mai toccato)."""
        child = dict(params)
        for name, spec in space.items():
            if name not in child:
                continue
            if float(rng.random()) >= self.rate:
                continue
            lo, hi, kind = spec
            val = child[name]
            if kind == "float":
                lo_f, hi_f = float(lo), float(hi)
                child[name] = float(np.clip(
                    float(val) + float(rng.normal(0.0, self.sigma_frac * (hi_f - lo_f))),
                    lo_f, hi_f))
            elif kind == "float_log":
                lo_f, hi_f = float(lo), float(hi)
                child[name] = float(np.clip(
                    float(val) * float(np.exp(rng.normal(0.0, self.sigma_frac))),
                    lo_f, hi_f))
            elif kind in ("int", "int_log"):
                step = 1 if int(rng.integers(0, 2)) == 0 else -1  # ±1 step
                child[name] = int(np.clip(int(val) + step, int(lo), int(hi)))
            elif kind == "categorical":
                options = list(lo)  # type: ignore[arg-type]
                others = [o for o in options if o != val]
                pool = others if others else options
                child[name] = pool[int(rng.integers(0, len(pool)))]
            # kind ignoto: parametro lasciato invariato (nessuna eccezione)
        return child
