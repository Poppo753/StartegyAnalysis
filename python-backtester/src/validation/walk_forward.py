"""walk_forward.py - Walk-Forward con purging (F3-V06).

Finestre parametrizzabili train(6m)/test(1m)/embargo(0.5m) su colonna
'datetime' (logica a confini datetime, come data_splitter). Per finestra:
BO opzionale sul train (riuso `src.searcher.BayesianOptimizer`, fallback
parametri fissi), backtest OOS sul test. Output: PnL per periodo +
profitability-rate + DSR + PBO.

ESCLUSIONE v3 vincolante (checklist §13): NESSUN t-test / Shapiro sui PnL
di periodo — le finestre di train sovrapposte violano l'assunzione i.i.d.
dei test parametrici; bastano i criteri v3 (profitability-rate, DSR, PBO).
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.metrics import calculate_metrics, sharpe_ratio
from src.validation.cross_validator import calculate_pbo
from src.validation.dsr import calculate_dsr

logger = logging.getLogger(__name__)

# Mese medio in giorni per convertire i parametri in mesi in Timedelta
# (DateOffset non accetta mesi frazionari come 0.5).
AVG_MONTH_DAYS = 365.25 / 12.0  # ≈ 30.44


class WalkForwardValidator:
    """Validatore walk-forward a finestre mobili (F3-V06).

    Args:
        train_months: ampiezza finestra train (default 6).
        test_months: ampiezza finestra test OOS (default 1).
        embargo_months: gap tra train e test (default 0.5).
    """

    def __init__(
        self,
        train_months: float = 6,
        test_months: float = 1,
        embargo_months: float = 0.5,
    ) -> None:
        for name, v in (
            ("train_months", train_months),
            ("test_months", test_months),
            ("embargo_months", embargo_months),
        ):
            if float(v) <= 0:
                raise ValueError(f"{name} must be > 0, got {v}")
        self.train_months = float(train_months)
        self.test_months = float(test_months)
        self.embargo_months = float(embargo_months)

    def generate_windows(
        self, df: pd.DataFrame
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """Genera (train_df, test_df) con embargo tra le due.

        Le finestre di test sono contigue e non sovrapposte (avanzamento =
        test_months); i train si sovrappongono per costruzione — da qui il
        divieto di t-test/Shapiro (§13).
        """
        if "datetime" not in df.columns:
            raise ValueError("walk-forward richiede colonna 'datetime'")
        dts = pd.to_datetime(df["datetime"])
        if dts.isna().any():
            raise ValueError("colonna 'datetime' con NaT")
        order = np.argsort(dts.values)
        df_sorted = df.iloc[order].reset_index(drop=True)
        dts = pd.to_datetime(df_sorted["datetime"]).reset_index(drop=True)

        train_d = pd.Timedelta(days=self.train_months * AVG_MONTH_DAYS)
        embargo_d = pd.Timedelta(days=self.embargo_months * AVG_MONTH_DAYS)
        test_d = pd.Timedelta(days=self.test_months * AVG_MONTH_DAYS)
        start, end = dts.iloc[0], dts.iloc[-1]

        windows: List[Tuple[pd.DataFrame, pd.DataFrame]] = []
        w = start
        while True:
            tr_e = w + train_d
            te_s = tr_e + embargo_d
            te_e = te_s + test_d
            if te_e > end:
                break
            train_df = df_sorted[(dts >= w) & (dts < tr_e)].reset_index(drop=True)
            test_df = df_sorted[(dts >= te_s) & (dts < te_e)].reset_index(drop=True)
            if len(train_df) == 0 or len(test_df) == 0:
                break
            windows.append((train_df, test_df))
            nxt = w + test_d
            if nxt <= w:  # pragma: no cover - guardia DateOffset degeneri
                break
            w = nxt
        return windows

    def run(
        self,
        df: pd.DataFrame,
        evaluate_fn: Callable[[pd.DataFrame], float],
        fit_fn: Optional[Callable[[pd.DataFrame], Any]] = None,
    ) -> Dict[str, Any]:
        """Esegue il walk-forward con funzioni generiche.

        Args:
            df: OHLC con colonna 'datetime' (12+ mesi per DoD).
            evaluate_fn: test_df -> PnL OOS del periodo.
            fit_fn: train_df -> stato/parametri (es. BO sul train);
                chiamato per finestra, ignorato se None (parametri fissi).

        Returns:
            report {n_periods, per_period[{window, train_start/end,
            test_start/end, oos_pnl}], total_oos_pnl, profitability_rate,
            sharpe_oos, pbo, pbo_percent, dsr}.
        """
        windows = self.generate_windows(df)
        if not windows:
            raise ValueError("walk-forward: nessuna finestra generata (dati insufficienti?)")
        per_period: List[Dict[str, Any]] = []
        for i, (train_df, test_df) in enumerate(windows):
            if fit_fn is not None:
                fit_fn(train_df)
            pnl = float(evaluate_fn(test_df))
            per_period.append(
                {
                    "window": i,
                    "train_start": str(pd.to_datetime(train_df["datetime"].iloc[0])),
                    "train_end": str(pd.to_datetime(train_df["datetime"].iloc[-1])),
                    "test_start": str(pd.to_datetime(test_df["datetime"].iloc[0])),
                    "test_end": str(pd.to_datetime(test_df["datetime"].iloc[-1])),
                    "oos_pnl": pnl,
                }
            )
        return self._report(per_period)

    def run_strategy(
        self,
        df: pd.DataFrame,
        strategy,
        base_params: Dict[str, Any],
        symbol: str = "WF",
        n_trials: int = 0,
        seed: int = 42,
    ) -> Dict[str, Any]:
        """Walk-forward di una TradingStrategy (BO-opzionale sul train).

        Args:
            strategy: istanza con run_backtest(df, params, symbol).
            base_params: parametri fissi (fallback quando n_trials=0).
            n_trials: se > 0, BO TPE sul train per finestra via
                src.searcher (riuso Fase 2); altrimenti parametri fissi.
        """
        from src.searcher.bayesian_optimizer import (  # import locale: riuso opzionale
            build_metrics_params,
        )

        use_bo = int(n_trials) > 0
        optimizer_cls = None
        if use_bo:
            from src.searcher import BayesianOptimizer

            optimizer_cls = BayesianOptimizer

        direction = str(base_params.get("direction", "signal-only"))
        per_period: List[Dict[str, Any]] = []
        for i, (train_df, test_df) in enumerate(self.generate_windows(df)):
            if use_bo:
                opt = optimizer_cls(
                    strategy,
                    base_params={k: v for k, v in base_params.items()},
                    symbol=symbol,
                    seed=int(seed) + i,
                )
                out = opt.optimize(train_df, n_trials=int(n_trials))
                params_dict = {**base_params, **out["best_params"]}
            else:
                params_dict = dict(base_params)
            trades = strategy.run_backtest(test_df, params_dict, symbol)
            metrics_params = build_metrics_params(strategy, params_dict, base_params)
            result = calculate_metrics(trades, metrics_params, symbol)
            if metrics_params.direction == "signal-only":
                oos = float(result.total_pnl_percent)
            else:
                oos = float(result.total_pnl)
            per_period.append(
                {
                    "window": i,
                    "train_start": str(pd.to_datetime(train_df["datetime"].iloc[0])),
                    "train_end": str(pd.to_datetime(train_df["datetime"].iloc[-1])),
                    "test_start": str(pd.to_datetime(test_df["datetime"].iloc[0])),
                    "test_end": str(pd.to_datetime(test_df["datetime"].iloc[-1])),
                    "oos_pnl": oos,
                    "n_trades": int(result.total_trades),
                }
            )
            logger.info(
                f"WF window {i}: OOS pnl={oos:.4f} trades={result.total_trades} "
                f"(BO={'on' if use_bo else 'off'})"
            )
        _ = direction
        report = self._report(per_period)
        report["bo_trials_per_window"] = int(n_trials) if use_bo else 0
        return report

    @staticmethod
    def _report(per_period: List[Dict[str, Any]]) -> Dict[str, Any]:
        pnls = np.array([p["oos_pnl"] for p in per_period], dtype=float)
        n = len(pnls)
        profitability_rate = float(np.sum(pnls > 0) / n) if n else 0.0
        pbo = calculate_pbo(pnls) if n else 0.0
        sh = sharpe_ratio(pnls, 0.0) if n else 0.0
        return {
            "n_periods": n,
            "per_period": per_period,
            "total_oos_pnl": float(np.sum(pnls)) if n else 0.0,
            "profitability_rate": profitability_rate,
            "sharpe_oos": float(sh),
            "pbo": float(pbo),
            "pbo_percent": float(pbo * 100.0),
            "dsr": float(calculate_dsr(sh, pbo)),
        }
