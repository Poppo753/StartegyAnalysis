"""
strategy.py - Definizione delle dataclass e strutture dati per il backtester

Contiene:
- BacktestParams: parametri di un singolo backtest
- Trade: dettagli di un singolo trade
- BacktestResult: risultato completo di un backtest
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class BacktestParams:
    """Parametri per una singola esecuzione del backtest."""

    x_percent: float          # Percentuale minima di salita per segnale
    y_seconds: int            # Finestra temporale in secondi per calcolo salita
    z_percent: float          # Percentuale di discesa dal massimo per chiusura
    max_hold_seconds: int     # Tempo massimo di mantenimento posizione
    initial_capital: float    # Capitale iniziale in USDT
    position_size: float      # Dimensione posizione per trade in USDT
    fee_rate: float           # Commissione per operazione (es. 0.001 = 0.1%)
    slippage_rate: float      # Slippage stimato (es. 0.0005 = 0.05%)
    direction: str            # "signal-only", "long", "short"


@dataclass
class Trade:
    """Dettagli di un singolo trade/segnale eseguito."""

    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    max_price_during_trade: float
    min_price_during_trade: float
    pnl: float                # Profitto/perdita in USDT
    pnl_percent: float        # Profitto/perdita in percentuale
    fees: float               # Commissioni totali pagate
    reason: str               # "drop-z", "max-hold", "end-of-data"
    x_percent: float          # Parametro X usato
    y_seconds: int            # Parametro Y usato
    z_percent: float          # Parametro Z usato
    mae_pct: float = 0.0      # Maximum Adverse Excursion (%)
    mfe_pct: float = 0.0      # Maximum Favorable Excursion (%)


@dataclass
class BacktestResult:
    """Risultato completo di un backtest per una combinazione di parametri."""

    symbol: str
    params: BacktestParams
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    max_drawdown: float = 0.0
    average_pnl: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    profit_factor: float = 0.0
    avg_mae: float = 0.0
    avg_mfe: float = 0.0
    trades: List[Trade] = field(default_factory=list)