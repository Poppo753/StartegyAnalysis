"""
strategy_base.py - Interfaccia base per tutte le strategie (Fase 1, F1-S01).

Contratto vincolante da IMPLEMENTATION_CHECKLIST §4 + masterplan v3 §5.3:
- parameter_space(): Dict[nome, (lo, hi, kind)] con
  kind in {"float", "int", "float_log", "int_log"} (i *_log servono a F2-B02).
- generate_signals(df, params): cuore della strategia, restituisce Signal.
- validate(params): validazione dei parametri.
- score(result): default v3 (pesi invariati, cfr. masterplan v3 §5.3).
- gpu_param_arrays(param_grid): parametri come array tipizzati (vincolo §6.1-nota-v3:
  CPU seleziona / GPU valuta; niente oggetti Python nel path GPU).
- gpu_metric_names(): nomi delle 8 metriche aggregate del kernel attuale
  (cfr. src/gpu/gpu_simulator.py + screening_metrics.py):
  ["total_trades", "winning_trades", "losing_trades", "total_pnl",
   "gross_profit", "gross_loss", "best_trade", "worst_trade"].
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


ALLOWED_PARAM_KINDS = ("float", "int", "float_log", "int_log")

GPU_METRIC_NAMES = [
    "total_trades",
    "winning_trades",
    "losing_trades",
    "total_pnl",
    "gross_profit",
    "gross_loss",
    "best_trade",
    "worst_trade",
]


@dataclass
class Signal:
    """Un segnale di ingresso o uscita (masterplan v3 §5.3)."""

    timestamp: pd.Timestamp
    type: str  # "ENTRY" or "EXIT"
    side: str  # "LONG" or "SHORT"
    price: float
    reason: str
    metadata: Dict = field(default_factory=dict)


class TradingStrategy(ABC):
    """
    Interfaccia base per TUTTE le strategie.

    Ogni strategia implementa:
    1. parameter_space() — dove cercare i parametri ottimali
    2. generate_signals(df, params) — il cuore della strategia
    3. validate(params) — validazione dei parametri
    """

    @abstractmethod
    def parameter_space(self) -> Dict[str, Tuple]:
        """
        Restituisce lo spazio di ricerca dei parametri.

        Convenzione v3: tupla (lo, hi, kind) con
        kind in {"float", "int", "float_log", "int_log"}.
        Esempio: {"x_percent": (0.01, 2.0, "float"), "y_seconds": (5, 120, "int")}
        """
        ...

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, params: Dict) -> List[Signal]:
        """
        Genera segnali dai dati con i parametri dati.
        """
        ...

    @abstractmethod
    def validate(self, params: Dict) -> bool:
        """Validazione parametri."""
        ...

    def score(self, result: Any) -> float:
        """
        Score composto per ranking (default v3, pesi invariati).

        Accetta BacktestResult (o StrategyResult): usa duck typing così resta
        compatibile con F3-V01 (campo sharpe_ratio aggiunto dopo).
        """
        total_trades = getattr(result, "total_trades", 0) or 0
        if total_trades == 0:
            return -999.0  # Nessun trade = pessima strategia

        # Weighted scoring — i pesi riflettono la filosofia di investing (v3 §5.3)
        weights = {
            "pnl": 0.30,
            "sharpe": 0.25,
            "profit_factor": 0.20,
            "win_rate": 0.10,
            "trade_count": 0.10,  # Più trade = più affidabile (statisticamente)
            "drawdown_penalty": 0.05,
        }

        total_pnl_pct = getattr(result, "total_pnl_percent", None)
        if total_pnl_pct is None:
            total_pnl_pct = getattr(result, "total_pnl_pct", 0.0)
        sharpe_ratio = getattr(result, "sharpe_ratio", 0.0) or 0.0
        profit_factor = getattr(result, "profit_factor", 0.0) or 0.0
        win_rate = getattr(result, "win_rate", 0.0) or 0.0
        max_drawdown = getattr(result, "max_drawdown", 0.0) or 0.0

        score = (
            weights["pnl"] * min(total_pnl_pct, 100) / 100 +  # Cap a 100%
            weights["sharpe"] * min(sharpe_ratio, 10) / 10 +  # Cap a 10
            weights["profit_factor"] * min(profit_factor, 5) / 5 +
            weights["win_rate"] * win_rate / 100 +
            weights["trade_count"] * min(np.log(total_trades), 5) / 5 -
            weights["drawdown_penalty"] * max_drawdown / 100
        )

        return float(score)

    def gpu_param_arrays(self, param_grid: List[Dict]) -> Dict[str, np.ndarray]:
        """Restituisce i parametri come array tipizzati (uno per parametro)."""
        return {}

    def gpu_metric_names(self) -> List[str]:
        """Nomi delle metriche aggregate restituite dal kernel (lunghezza fissa 8)."""
        return list(GPU_METRIC_NAMES)
