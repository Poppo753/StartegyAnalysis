"""Report executable strategies to the local dashboard as JSON."""

import json

from src.strategies import STRATEGY_REGISTRY


def main() -> None:
    seen = set()
    entries = []
    for name, strategy_class in STRATEGY_REGISTRY.items():
        if strategy_class in seen:
            continue  # An alias is not a separate strategy.
        seen.add(strategy_class)
        instance = strategy_class()
        has_runner = callable(getattr(instance, "run_backtest", None))
        entries.append({
            "name": name,
            "runnable": has_runner,
            "grid": name in ("momentum_drop", "mean_reversion"),
            "optuna": has_runner,
            "fast": name == "momentum_drop",
            "gpu": name == "momentum_drop",
            "parameters": list(instance.parameter_space()),
            "parameterSpace": {key: list(value) for key, value in instance.parameter_space().items()},
        })
    print(json.dumps(entries))


if __name__ == "__main__":
    main()
