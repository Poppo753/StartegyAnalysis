"""
metrics.py - Calcolo delle metriche di performance del backtest

Calcola:
- Win rate
- Total PnL
- Max drawdown (su equity curve)
- Profit factor
- Best/worst trade
- Media PnL
"""

import numpy as np
from typing import List
from src.strategy import BacktestParams, Trade, BacktestResult


def sortino_ratio(values: np.ndarray, target: float = 0.0) -> float:
    """
    Sortino Ratio: penalizza solo la volatilità negativa (v3 §5.3, CHG-001).

    Sortino = (mean(values) - target) / downside_std * sqrt(252)
    con downside_std = std dei soli rendimenti < target (solo numpy).

    Se non ci sono valori sotto il target, downside_std = 1e-9 (come da
    sketch v3: strategia senza downside → Sortino molto grande, non nullo).
    Se downside_std == 0 (downside costante) → 0.0 per convenzione.
    """
    arr = np.asarray(values, dtype=float).ravel()
    if arr.size == 0:
        return 0.0
    downside = arr[arr < target]
    if downside.size == 0:
        downside_std = 1e-9
    else:
        downside_std = float(np.std(downside))
    if downside_std == 0.0 or not np.isfinite(downside_std):
        return 0.0
    mean_value = float(np.mean(arr))
    if not np.isfinite(mean_value):
        return 0.0
    return float((mean_value - target) / downside_std * np.sqrt(252.0))


def calmar_ratio(annual_return: float, max_drawdown: float) -> float:
    """
    Calmar Ratio: rendimento annuo per unità di max drawdown (v3 §5.3, CHG-001).

    Calmar = annual_return / max_drawdown (entrambi in %).
    Se max_drawdown <= 0 → 0.0 (nessun drawdown da prezzare).
    """
    annual_return = float(annual_return)
    max_drawdown = float(max_drawdown)
    if not np.isfinite(annual_return) or not np.isfinite(max_drawdown):
        return 0.0
    if max_drawdown <= 0:
        return 0.0
    return float(annual_return / max_drawdown)


def sharpe_ratio(values: np.ndarray, risk_free: float = 0.0) -> float:
    """
    Sharpe Ratio annualizzato (F3-V01, CHG-006, prerequisito DSR).

    Sharpe = mean(values - risk_free) / std(values - risk_free) * sqrt(252)
    con std = deviazione standard popolazione (np.std, ddof=0), coerente
    con sortino_ratio sopra.

    Convenzione signal-only (stessa di F1-M01 / sortino): il chiamante
    (calculate_metrics) passa pnl_percent se direction == "signal-only",
    altrimenti pnl in USDT. Questa funzione non conosce la direction.

    Edge cases (stesse convenzioni di sortino):
    - serie vuota → 0.0
    - std == 0 (serie costante) o non-finita → 0.0
    - media non-finita → 0.0
    """
    arr = np.asarray(values, dtype=float).ravel()
    if arr.size == 0:
        return 0.0
    rf = float(risk_free)
    if not np.isfinite(rf):
        return 0.0
    excess = arr - rf
    std = float(np.std(excess))
    if std == 0.0 or not np.isfinite(std):
        return 0.0
    mean_excess = float(np.mean(excess))
    if not np.isfinite(mean_excess):
        return 0.0
    return float(mean_excess / std * np.sqrt(252.0))


def expectancy(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Expectancy: profitto atteso del singolo trade medio (v3 §5.3, CHG-001).

    Expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    con win_rate in [0, 1] e avg_win/avg_loss come magnitudini positive.
    Solo numpy-free (aritmetica pura); nessun Kelly qui (cfr. checklist §13).
    """
    win_rate = float(win_rate)
    avg_win = float(avg_win)
    avg_loss = float(avg_loss)
    return float((win_rate * avg_win) - ((1.0 - win_rate) * avg_loss))


def calculate_metrics(trades: List[Trade], params: BacktestParams, symbol: str) -> BacktestResult:
    """
    Calcola tutte le metriche di performance da una lista di trade.

    Args:
        trades: lista dei trade eseguiti
        params: parametri del backtest
        symbol: simbolo testato

    Returns:
        BacktestResult con tutte le metriche calcolate
    """
    result = BacktestResult(
        symbol=symbol,
        params=params,
        trades=trades,
    )

    total_trades = len(trades)
    result.total_trades = total_trades

    # Se non ci sono trade, restituisci risultato vuoto
    if total_trades == 0:
        return result

    # Estrai PnL di ogni trade
    pnls = np.array([t.pnl for t in trades])
    pnl_percents = np.array([t.pnl_percent for t in trades])

    # --- Winning/Losing trades ---
    if params.direction == "signal-only":
        # In signal-only, usa pnl_percent per determinare win/loss
        result.winning_trades = int(np.sum(pnl_percents > 0))
        result.losing_trades = int(np.sum(pnl_percents <= 0))
    else:
        result.winning_trades = int(np.sum(pnls > 0))
        result.losing_trades = int(np.sum(pnls <= 0))

    # --- Win rate ---
    result.win_rate = result.winning_trades / total_trades * 100.0 if total_trades > 0 else 0.0

    # --- Total PnL ---
    result.total_pnl = float(np.sum(pnls))
    result.total_pnl_percent = float(np.sum(pnl_percents))

    # --- Average PnL ---
    if params.direction == "signal-only":
        result.average_pnl = float(np.mean(pnl_percents))
    else:
        result.average_pnl = float(np.mean(pnls))

    # --- Best/Worst trade ---
    if params.direction == "signal-only":
        result.best_trade = float(np.max(pnl_percents))
        result.worst_trade = float(np.min(pnl_percents))
    else:
        result.best_trade = float(np.max(pnls))
        result.worst_trade = float(np.min(pnls))

    # --- Max Drawdown ---
    result.max_drawdown = _calculate_max_drawdown(pnls, params)

    # --- Profit Factor ---
    result.profit_factor = _calculate_profit_factor(pnls, pnl_percents, params)

    result.avg_mae = float(np.mean([t.mae_pct for t in trades])) if trades else 0.0
    result.avg_mfe = float(np.mean([t.mfe_pct for t in trades])) if trades else 0.0

    # --- Metriche v3 (CHG-001): convenzione esistente ---
    # signal-only → serie pnl_percent, altrimenti serie pnl (USDT).
    if params.direction == "signal-only":
        values = pnl_percents
    else:
        values = pnls

    result.sortino_ratio = sortino_ratio(values, 0.0)
    result.sharpe_ratio = sharpe_ratio(values, 0.0)

    positives = values[values > 0]
    negatives = values[values < 0]
    avg_win = float(np.mean(positives)) if positives.size > 0 else 0.0
    avg_loss = float(np.mean(np.abs(negatives))) if negatives.size > 0 else 0.0
    win_rate_dec = result.winning_trades / total_trades if total_trades > 0 else 0.0
    result.expectancy = expectancy(win_rate_dec, avg_win, avg_loss)

    if params.direction == "signal-only":
        total_return_pct = float(np.sum(pnl_percents))
    elif params.initial_capital > 0:
        total_return_pct = float(np.sum(pnls)) / params.initial_capital * 100.0
    else:
        total_return_pct = 0.0
    # Annualizza solo su span >= 1 giorno, altrimenti usa il total-period
    # (proxy documentata: i trade intraday non hanno base annua misurabile).
    period_years = _period_years(trades)
    if period_years is not None and period_years >= 1.0 / 365.0:
        annual_return = total_return_pct / period_years
    else:
        annual_return = total_return_pct
    result.calmar_ratio = calmar_ratio(annual_return, result.max_drawdown)

    return result


def _period_years(trades: List[Trade]):
    """
    Span temporale dei trade in anni (per annualizzare il Calmar).

    Returns:
        float anni se determinabile, altrimenti None.
    """
    try:
        entries = [t.entry_time for t in trades]
        exits = [t.exit_time for t in trades]
        start = min(entries)
        end = max(exits)
        seconds = (end - start).total_seconds()
    except (ValueError, TypeError, AttributeError):
        return None
    if seconds is None or seconds <= 0:
        return None
    return float(seconds) / (365.0 * 24.0 * 3600.0)


def _calculate_max_drawdown(pnls: np.ndarray, params: BacktestParams) -> float:
    """
    Calcola il max drawdown sull'equity curve.

    Per direction != signal-only: equity curve basata su PnL cumulativo.
    Per signal-only: basata su pnl_percent cumulativo (come proxy).

    Args:
        pnls: array di PnL per trade
        params: parametri del backtest

    Returns:
        Max drawdown come valore positivo (percentuale o USDT)
    """
    if len(pnls) == 0:
        return 0.0

    # Costruisci equity curve
    if params.direction == "signal-only":
        # Per signal-only usiamo i pnl_percent come proxy
        equity = params.initial_capital + np.cumsum(pnls)
    else:
        equity = params.initial_capital + np.cumsum(pnls)

    # Calcola running maximum
    running_max = np.maximum.accumulate(equity)

    # Drawdown ad ogni punto
    drawdowns = running_max - equity

    # Max drawdown
    max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

    # Converti in percentuale rispetto al capitale iniziale
    if params.initial_capital > 0:
        max_dd_percent = max_dd / params.initial_capital * 100.0
    else:
        max_dd_percent = 0.0

    return max_dd_percent


def _calculate_profit_factor(
    pnls: np.ndarray,
    pnl_percents: np.ndarray,
    params: BacktestParams,
) -> float:
    """
    Calcola il profit factor = somma profitti / |somma perdite|.

    Args:
        pnls: array di PnL per trade
        pnl_percents: array di PnL percentuali
        params: parametri del backtest

    Returns:
        Profit factor (0 se non ci sono perdite)
    """
    if params.direction == "signal-only":
        values = pnl_percents
    else:
        values = pnls

    gross_profit = float(np.sum(values[values > 0]))
    gross_loss = float(np.abs(np.sum(values[values < 0])))

    if gross_loss == 0:
        # Nessuna perdita: profit factor infinito (usiamo 999.99 come cap)
        return 999.99 if gross_profit > 0 else 0.0

    return gross_profit / gross_loss