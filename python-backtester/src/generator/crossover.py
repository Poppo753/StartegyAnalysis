"""crossover.py - StrategyCrossover a livelli genoma v3 §4.3 (F4-G02).

- Crossover parametrico (Level 2): mean/jitter-blend per float,
  random pick per int, swap per categorici.
- Crossover strutturale (Level 0/1/3): entry+exit del donatore A
  (archetipo/variante) + filtri del donatore B.

I figli sono sempre validati con strategy.validate del template di
appartenenza; gli invalidi sono scartati e CONTATI, mai sollevati.
"""

from typing import Any, Dict, List, Tuple

import numpy as np


class StrategyCrossover:
    """Crossover parametrico + strutturale con conteggio scarti.

    Args:
        jitter_frac: frazione del range (hi-lo) usata come sigma del
            jitter gaussiano sui float dopo la media dei genitori.
    """

    def __init__(self, jitter_frac: float = 0.05) -> None:
        self.jitter_frac = float(jitter_frac)
        self.n_discarded = 0

    def blend_params(
        self,
        params_a: Dict[str, Any],
        params_b: Dict[str, Any],
        space: Dict[str, Tuple],
        rng: np.random.Generator,
    ) -> Dict[str, Any]:
        """Fonde due dict parametri sullo stesso spazio (puro, senza validare)."""
        child: Dict[str, Any] = {}
        for name, spec in space.items():
            lo, hi, kind = spec
            va, vb = params_a.get(name), params_b.get(name)
            if va is None and vb is None:
                continue
            if va is None:
                child[name] = vb
                continue
            if vb is None:
                child[name] = va
                continue
            if kind in ("float", "float_log"):
                lo_f, hi_f = float(lo), float(hi)
                mean = (float(va) + float(vb)) / 2.0
                if kind == "float_log":
                    sig = self.jitter_frac  # relativo in spazio log
                    val = float(mean) * float(np.exp(rng.normal(0.0, sig)))
                else:
                    sig = self.jitter_frac * (hi_f - lo_f)
                    val = float(mean) + float(rng.normal(0.0, sig))
                child[name] = float(np.clip(val, lo_f, hi_f))
            elif kind in ("int", "int_log"):
                pick = va if int(rng.integers(0, 2)) == 0 else vb  # random pick
                child[name] = int(np.clip(int(pick), int(lo), int(hi)))
            elif kind == "categorical":
                options = list(lo)  # type: ignore[arg-type]
                child[name] = options[int(rng.integers(0, len(options)))]
            else:
                raise ValueError(f"kind non ammesso: {kind!r}")
        return child

    def structural_child(
        self,
        entry_template: str,
        filter_template: str,
        params_entry: Dict[str, Any],
        rng: np.random.Generator,  # noqa: ARG002 - firma futura (filtri pesati)
    ) -> Dict[str, Any]:
        """Genoma figlio: entry/exit di A + filtri di B (mai eccezioni note).

        Solleva KeyError solo per nomi template ignoti (errore chiamante).
        """
        from src.generator.strategy_generator import TEMPLATE_REGISTRY

        entry_a = TEMPLATE_REGISTRY[entry_template]
        entry_b = TEMPLATE_REGISTRY[filter_template]
        return {
            "template": entry_template,  # archetipo/variante del donatore entry
            "entry_condition": entry_a["entry_condition"],
            "exit_condition": entry_a["exit_condition"],
            "filters": list(entry_b["optional_filters"]),
            "params": dict(params_entry),
        }

    def _validated_child(
        self, template: str, params: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """Valida un figlio; None (contato) se invalido o eccezione."""
        from src.generator.strategy_generator import TEMPLATE_REGISTRY

        try:
            strategy = TEMPLATE_REGISTRY[template]["strategy"]
            if strategy.validate(params):
                return {"template": template, "params": dict(params)}
        except Exception:
            pass
        self.n_discarded += 1
        return None

    def make_children(
        self,
        template_a: str,
        template_b: str,
        params_a: Dict[str, Any],
        params_b: Dict[str, Any],
        rng: np.random.Generator,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Genera figli (parametrico se stesso template + 2 strutturali).

        Returns:
            (children, n_discarded_delta): figli validi + scarti di QUESTA
            chiamata (mai eccezioni di validazione).
        """
        from src.generator.strategy_generator import TEMPLATE_REGISTRY

        before = self.n_discarded
        children: List[Dict[str, Any]] = []
        if template_a == template_b:
            try:
                space = TEMPLATE_REGISTRY[template_a]["strategy"].parameter_space()
                blended = self.blend_params(params_a, params_b, space, rng)
            except Exception:
                blended = None
            if blended is not None:
                child = self._validated_child(template_a, blended)
                if child is not None:
                    children.append(child)
        for entry_t, filt_t, p_entry in (
            (template_a, template_b, params_a),
            (template_b, template_a, params_b),
        ):
            try:
                genome = self.structural_child(entry_t, filt_t, p_entry, rng)
            except Exception:
                self.n_discarded += 1
                continue
            child = self._validated_child(genome["template"], genome["params"])
            if child is not None:
                child["filters"] = genome["filters"]
                child["entry_condition"] = genome["entry_condition"]
                children.append(child)
        return children, self.n_discarded - before
