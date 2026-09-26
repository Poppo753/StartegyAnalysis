"""bayesian_optimizer.py - Ottimizzatore Bayesiano Optuna TPE (Fase 2, F2-B01/B02/B05).

Uso esclusivo TPE (checklist §13 forbisce EI/PI/UCB/GP: non implementati qui).

Percorso motore standard (stesso di main.py):
  trades = strategy.run_backtest(df, full_params, symbol)
  result = calculate_metrics(trades, metrics_params, symbol)
  score  = strategy.score(result)

Thread-safety (F2-B05): l'ottimizzatore non ha stato mutabile condiviso tra
trial (solo locals); le strategie reali sono stateless (solo variabili locali,
nessun globale). DataFrame `df` condiviso in sola lettura; MeanReversion fa
`df.copy()` internamente. `study.optimize(..., n_jobs=N)` usa thread Optuna.
`njit` (motori fast/gpu, non usati qui) rilascia il GIL solo con
`nogil=True`/parallel — verificare con `numba` (vedi nota F2-B05 nel messaggio
di chiusura): lo path standard qui e' Python+pandas/numpy (GIL tenuto nei loop
Python, rilasciato nelle op C), quindi speedup sublineare atteso.
"""

from typing import Any, Dict, Optional, Tuple

import optuna
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner

from src.strategy import BacktestParams
from src.metrics import calculate_metrics

# Silenzia i log rumorosi di Optuna (restano errori/warning).
optuna.logging.set_verbosity(optuna.logging.WARNING)

_MEAN_REVERSION_EXIT_Z = 0.1

_ALLOWED_KINDS = ("float", "int", "float_log", "int_log")


def suggest_params(trial: optuna.Trial, space: Dict[str, Tuple]) -> Dict[str, Any]:
    """Campiona un dict parametri da `parameter_space()`.

    Mappatura kind -> suggest (F2-B02):
      float     -> suggest_float(name, lo, hi)
      int       -> suggest_int(name, lo, hi)
      float_log -> suggest_float(name, lo, hi, log=True)
      int_log   -> suggest_int(name, lo, hi, log=True)
    """
    sampled: Dict[str, Any] = {}
    for name, spec in space.items():
        lo, hi, kind = spec
        if kind not in _ALLOWED_KINDS:
            raise ValueError(f"kind non ammesso per {name!r}: {kind!r}")
        if lo == hi:
            sampled[name] = int(lo) if kind in ("int", "int_log") else float(lo)
            continue
        if kind == "float":
            sampled[name] = trial.suggest_float(name, float(lo), float(hi))
        elif kind == "int":
            sampled[name] = trial.suggest_int(name, int(lo), int(hi))
        elif kind == "float_log":
            if float(lo) <= 0:
                raise ValueError(f"float_log richiede lo>0 per {name!r} (lo={lo})")
            sampled[name] = trial.suggest_float(name, float(lo), float(hi), log=True)
        elif kind == "int_log":
            if int(lo) <= 0:
                raise ValueError(f"int_log richiede lo>0 per {name!r} (lo={lo})")
            sampled[name] = trial.suggest_int(name, int(lo), int(hi), log=True)
    return sampled


def build_metrics_params(
    strategy: Any,
    full_params: Dict[str, Any],
    base_params: Optional[Dict[str, Any]] = None,
) -> BacktestParams:
    """Costruisce BacktestParams per calculate_metrics (stessa mappa di main.py).

    - momentum_drop (x_percent/y_seconds/z_percent presenti): uso diretto.
    - mean_reversion (ma_period/z_threshold): x=z_threshold, y=ma_period,
      z=|exit_band|=0.1 (come run_standard_engine_mean_reversion).
    - generico: fallback x<-x_percent|z_threshold, y<-y_seconds|ma_period,
      z<-z_percent|0.1.
    """
    base = base_params or {}

    def _pick(*keys: str, default: Any = None) -> Any:
        for k in keys:
            if k in full_params:
                return full_params[k]
        return base.get(keys[0], default) if keys else default

    if "x_percent" in full_params and "y_seconds" in full_params and "z_percent" in full_params:
        x = float(full_params["x_percent"])
        y = int(full_params["y_seconds"])
        z = float(full_params["z_percent"])
    elif "ma_period" in full_params and "z_threshold" in full_params:
        x = float(full_params["z_threshold"])
        y = int(full_params["ma_period"])
        z = float(_MEAN_REVERSION_EXIT_Z)
    else:
        x = float(_pick("x_percent", "z_threshold", default=0.5))
        y = int(_pick("y_seconds", "ma_period", default=10))
        z = float(_pick("z_percent", default=_MEAN_REVERSION_EXIT_Z))

    # direction: base_params vince; default long per mean-reversion (long-only),
    # signal-only altrimenti (come config DIRECTION default).
    if "direction" in full_params:
        direction = str(full_params["direction"])
    elif "direction" in base:
        direction = str(base["direction"])
    else:
        cls_name = type(strategy).__name__
        direction = "long" if "MeanReversion" in cls_name else "signal-only"

    return BacktestParams(
        x_percent=x,
        y_seconds=y,
        z_percent=z,
        max_hold_seconds=int(_pick("max_hold_seconds", default=300)),
        initial_capital=float(_pick("initial_capital", default=1000.0)),
        position_size=float(_pick("position_size", default=100.0)),
        fee_rate=float(_pick("fee_rate", default=0.001)),
        slippage_rate=float(_pick("slippage_rate", default=0.0005)),
        direction=direction,
    )


class BayesianOptimizer:
    """Ottimizzatore Bayesiano TPE sopra una TradingStrategy.

    Args:
        strategy: istanza TradingStrategy (deve esporre parameter_space(),
            validate(), score() e run_backtest(df, params, symbol)).
        n_startup_trials: trial casuali prima che TPE modelli (default 20,
            da checklist F2-B01/B02). Test piccoli possono passare un valore
            minore (es. 5) per budget ridotti.
        base_params: parametri fissi non campionati (es. initial_capital,
            fee_rate, slippage_rate, direction, max_hold_seconds se non in
            spazio). I campionati sovrascrivono la base.
        symbol: simbolo passato a run_backtest/calculate_metrics.
        seed: seed RNG per TPESampler (riproducibilita' test).
        storage: URL storage Optuna (es. "sqlite:///optimization_study_optuna.db")
            per persistenza/resume. None = in-memory.
        study_name: nome study (obbligatorio con storage per resume).
        n_jobs: default job paralleli per optimize().
    """

    def __init__(
        self,
        strategy: Any,
        n_startup_trials: int = 20,
        base_params: Optional[Dict[str, Any]] = None,
        symbol: str = "BACKTEST",
        seed: Optional[int] = None,
        storage: Optional[str] = None,
        study_name: Optional[str] = None,
        n_jobs: int = 1,
    ) -> None:
        self.strategy = strategy
        self.n_startup_trials = int(n_startup_trials)
        self.base_params = dict(base_params or {})
        self.symbol = symbol
        self.seed = seed
        self.storage = storage
        self.study_name = study_name
        self.n_jobs = int(n_jobs)
        self.study: Optional[optuna.Study] = None

    def _evaluate(
        self, sampled: Dict[str, Any], df: Any
    ) -> Tuple[float, Any]:
        """Esegue lo path motore standard e restituisce (score, result)."""
        full_params = {**self.base_params, **sampled}
        validate = getattr(self.strategy, "validate", None)
        if callable(validate):
            try:
                ok = validate(full_params)
            except Exception:
                ok = False
            if not ok:
                raise optuna.TrialPruned(f"invalid params: {sampled}")
        run_bt = getattr(self.strategy, "run_backtest", None)
        if not callable(run_bt):
            raise TypeError(
                f"{type(self.strategy).__name__} non espone run_backtest(df, params, symbol)"
            )
        trades = run_bt(df, full_params, self.symbol)
        metrics_params = build_metrics_params(self.strategy, full_params, self.base_params)
        result = calculate_metrics(trades, metrics_params, self.symbol)
        score = float(self.strategy.score(result))
        return score, result

    def _objective(self, df: Any):
        def _fn(trial: optuna.Trial) -> float:
            space = self.strategy.parameter_space()
            sampled = suggest_params(trial, space)
            # TrialPruned (parametri invalidi) si propaga: Optuna lo registra
            # come PRUNED, mai come FAIL/errore.
            score, _ = self._evaluate(sampled, df)
            # Report + prune ogni valutazione (F2-B02). Step singolo: con
            # MedianPruner(n_warmup_steps=5) il prune scatta raramente, ma il
            # protocollo resta corretto e i pruned restano TrialPruned.
            trial.report(score, step=0)
            if trial.should_prune():
                raise optuna.TrialPruned()
            return score

        return _fn

    def optimize(
        self,
        df: Any,
        n_trials: int,
        n_jobs: Optional[int] = None,
        show_progress: bool = False,
    ) -> Dict[str, Any]:
        """Esegue l'ottimizzazione TPE.

        Args:
            df: DataFrame OHLC (condiviso read-only tra i thread).
            n_trials: budget trial.
            n_jobs: job paralleli (thread Optuna). Default self.n_jobs.
                Thread-safe se la strategia e' stateless (le strategie reali
                usano solo locals; non condividere stato mutabile).
            show_progress: mostra progress bar Optuna.

        Returns:
            dict {best_params, best_value, study, n_trials}.
            study e' anche in self.study per resume/ispezione.
        """
        jobs = self.n_jobs if n_jobs is None else int(n_jobs)
        sampler = TPESampler(n_startup_trials=self.n_startup_trials, seed=self.seed)
        pruner = MedianPruner(n_warmup_steps=5)
        self.study = optuna.create_study(
            direction="maximize",
            sampler=sampler,
            pruner=pruner,
            storage=self.storage,
            study_name=self.study_name,
            load_if_exists=True,
        )
        self.study.optimize(
            self._objective(df),
            n_trials=int(n_trials),
            n_jobs=jobs,
            show_progress_bar=show_progress,
        )
        return {
            "best_params": dict(self.study.best_params),
            "best_value": float(self.study.best_value),
            "study": self.study,
            "n_trials": int(n_trials),
        }
