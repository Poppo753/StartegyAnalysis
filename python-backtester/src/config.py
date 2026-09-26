"""
config.py - Caricamento e validazione della configurazione da .env.

Pattern errori (enterprise):
- Solleva sempre ConfigError (sottoclasse di ValueError), MAI sys.exit().
- Il print + exit è consentito solo al boundary CLI (main.py / __main__),
  che cattura ConfigError e stampa una sola volta.
"""

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv


class ConfigError(ValueError):
    """Eccezione personalizzata per errori di configurazione."""
    pass


@dataclass
class Config:
    """Configurazione completa del backtester caricata da .env"""

    # Directory
    data_dir: str = ""
    output_dir: str = ""

    # Simboli e date
    symbols: List[str] = field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    timeframe: str = "1s"

    # Parametri griglia
    x_values: List[float] = field(default_factory=list)
    y_values: List[int] = field(default_factory=list)
    z_values: List[float] = field(default_factory=list)
    ma_periods: List[int] = field(default_factory=lambda: [10, 20])
    z_thresholds: List[float] = field(default_factory=lambda: [1.0, 2.0])

    # Parametri trading
    max_hold_seconds: int = 300
    initial_capital: float = 1000.0
    position_size: float = 100.0
    fee_rate: float = 0.001
    slippage_rate: float = 0.0005
    direction: str = "signal-only"

    # Engine selection
    backtest_engine: str = "standard"  # "standard", "fast", o "gpu"
    fast_top_n: int = 20

    # Strategie da eseguire (Fase 1, F1-S04): nomi del registry
    # src/strategies (es. "momentum_drop", "mean_reversion").
    strategies: List[str] = field(default_factory=lambda: ["momentum_drop"])

    # GPU/Screening (Fase 3)
    gpu_batch_size: int = 2048
    train_ratio: float = 0.7
    validation_ratio: float = 0.3

    # Y dinamico (discovery mode)
    y_dynamic: bool = False
    y_max_window: int = 600

    # Filtri intelligenti
    min_trades: int = 20
    min_win_rate: float = 40.0
    min_profit_factor: float = 1.2
    max_drawdown_filter: float = 30.0
    skip_filters: bool = False


def _parse_range(range_str: str, cast_type: str = "float", param_name: str = "RANGE") -> list:
    """
    Parsa una stringa range nel formato start:end:step.

    Args:
        range_str: stringa nel formato "start:end:step"
        cast_type: "float" o "int"
        param_name: nome del parametro per messaggi di errore

    Returns:
        Lista di valori generati dal range

    Raises:
        ConfigError: se il formato è invalido o i vincoli non sono rispettati
    """
    parts = range_str.split(":")
    if len(parts) != 3:
        raise ConfigError(f"{param_name} deve essere nel formato start:end:step, ricevuto: {range_str}")

    try:
        start = float(parts[0])
        end = float(parts[1])
        step = float(parts[2])
    except ValueError as e:
        raise ConfigError(f"{param_name} contiene valori non numerici: {range_str}") from e

    if step <= 0:
        raise ConfigError(f"{param_name} step deve essere > 0, ricevuto: {step}")

    if start > end:
        raise ConfigError(f"{param_name} start ({start}) deve essere <= end ({end})")

    values: list = []
    current = start
    while current <= end + 1e-9:  # tolleranza floating point
        if cast_type == "int":
            values.append(int(round(current)))
        else:
            values.append(round(current, 6))
        current += step

    if cast_type == "int":
        values = [v for v in values if v <= int(round(end))]
    else:
        values = [v for v in values if v <= round(end, 6) + 1e-9]
        values = [round(v, 6) for v in values]

    if not values:
        raise ConfigError(f"{param_name} ha generato 0 valori con range: {range_str}")

    return values


def load_config() -> Config:
    """
    Carica la configurazione dal file .env nella directory corrente.

    Returns:
        Config: oggetto con tutti i parametri validati

    Raises:
        ConfigError: se la configurazione è invalida
    """
    load_dotenv()

    config = Config()

    # --- Directory ---
    config.data_dir = os.getenv("DATA_DIR", "../data")
    config.output_dir = os.getenv("OUTPUT_DIR", "./backtest-results")

    # --- Simboli ---
    symbols_str = os.getenv("SYMBOLS", "")
    if not symbols_str.strip():
        raise ConfigError("SYMBOLS non configurato nel .env")
    config.symbols = [s.strip().upper() for s in symbols_str.split(",") if s.strip()]
    if not config.symbols:
        raise ConfigError("SYMBOLS deve contenere almeno un simbolo valido")

    # --- Date ---
    config.start_date = os.getenv("START_DATE", "")
    config.end_date = os.getenv("END_DATE", "")
    if not config.start_date or not config.end_date:
        raise ConfigError("START_DATE e END_DATE devono essere configurati nel .env")

    for date_str, name in [(config.start_date, "START_DATE"), (config.end_date, "END_DATE")]:
        parts = date_str.split("-")
        if len(parts) != 3 or len(parts[0]) != 4:
            raise ConfigError(f"{name} deve essere nel formato YYYY-MM-DD, ricevuto: {date_str}")

    # --- Timeframe ---
    config.timeframe = os.getenv("TIMEFRAME", "1s")

    # --- Parametri griglia ---
    x_range_str = os.getenv("X_RANGE", "").strip()
    y_range_str = os.getenv("Y_RANGE", "").strip()
    z_range_str = os.getenv("Z_RANGE", "").strip()

    x_str = os.getenv("X_VALUES", "0.2,0.5,1")
    y_str = os.getenv("Y_VALUES", "10,30,60")
    z_str = os.getenv("Z_VALUES", "0.1,0.2,0.5")

    if x_range_str:
        config.x_values = _parse_range(x_range_str, cast_type="float", param_name="X_RANGE")
    else:
        try:
            config.x_values = [float(v.strip()) for v in x_str.split(",") if v.strip()]
        except ValueError as e:
            raise ConfigError(f"X_VALUES contiene valori non numerici: {x_str}") from e

    if y_range_str:
        config.y_values = _parse_range(y_range_str, cast_type="int", param_name="Y_RANGE")
    else:
        try:
            config.y_values = [int(v.strip()) for v in y_str.split(",") if v.strip()]
        except ValueError as e:
            raise ConfigError(f"Y_VALUES contiene valori non interi: {y_str}") from e

    if z_range_str:
        config.z_values = _parse_range(z_range_str, cast_type="float", param_name="Z_RANGE")
    else:
        try:
            config.z_values = [float(v.strip()) for v in z_str.split(",") if v.strip()]
        except ValueError as e:
            raise ConfigError(f"Z_VALUES contiene valori non numerici: {z_str}") from e

    try:
        config.ma_periods = [int(v.strip()) for v in os.getenv("MA_PERIODS", "10,20").split(",") if v.strip()]
        config.z_thresholds = [float(v.strip()) for v in os.getenv("Z_THRESHOLDS", "1,2").split(",") if v.strip()]
    except ValueError as e:
        raise ConfigError("MA_PERIODS e Z_THRESHOLDS devono essere elenchi numerici") from e

    # --- Parametri trading ---
    try:
        config.max_hold_seconds = int(os.getenv("MAX_HOLD_SECONDS", "300"))
    except ValueError as e:
        raise ConfigError("MAX_HOLD_SECONDS deve essere un intero") from e

    try:
        config.initial_capital = float(os.getenv("INITIAL_CAPITAL", "1000"))
    except ValueError as e:
        raise ConfigError("INITIAL_CAPITAL deve essere un numero") from e

    try:
        config.position_size = float(os.getenv("POSITION_SIZE", "100"))
    except ValueError as e:
        raise ConfigError("POSITION_SIZE deve essere un numero") from e

    try:
        config.fee_rate = float(os.getenv("FEE_RATE", "0.001"))
    except ValueError as e:
        raise ConfigError("FEE_RATE deve essere un numero") from e

    try:
        config.slippage_rate = float(os.getenv("SLIPPAGE_RATE", "0.0005"))
    except ValueError as e:
        raise ConfigError("SLIPPAGE_RATE deve essere un numero") from e

    config.direction = os.getenv("DIRECTION", "signal-only").strip().lower()
    valid_directions = ["signal-only", "long", "short"]
    if config.direction not in valid_directions:
        raise ConfigError(f"DIRECTION deve essere uno tra {valid_directions}, ricevuto: {config.direction}")

    # --- Engine ---
    config.backtest_engine = os.getenv("BACKTEST_ENGINE", "standard").strip().lower()
    valid_engines = ["standard", "fast", "gpu"]
    if config.backtest_engine not in valid_engines:
        raise ConfigError(
            f"BACKTEST_ENGINE deve essere uno tra {valid_engines}, ricevuto: {config.backtest_engine}"
        )

    try:
        config.fast_top_n = int(os.getenv("FAST_TOP_N", "20"))
    except ValueError as e:
        raise ConfigError("FAST_TOP_N deve essere un intero") from e

    if config.fast_top_n <= 0:
        raise ConfigError("FAST_TOP_N deve essere > 0")

    # --- GPU / Fase 3 ---
    try:
        config.gpu_batch_size = int(os.getenv("GPU_BATCH_SIZE", "2048"))
    except ValueError as e:
        raise ConfigError("GPU_BATCH_SIZE deve essere un intero") from e

    try:
        config.train_ratio = float(os.getenv("TRAIN_RATIO", "0.7"))
        config.validation_ratio = float(os.getenv("VALIDATION_RATIO", "0.3"))
    except ValueError as e:
        raise ConfigError("TRAIN_RATIO e VALIDATION_RATIO devono essere numeri") from e

    if config.train_ratio + config.validation_ratio > 1.01:
        raise ConfigError("TRAIN_RATIO + VALIDATION_RATIO non può superare 1.0")

    try:
        config.min_trades = int(os.getenv("MIN_TRADES", "20"))
        config.min_win_rate = float(os.getenv("MIN_WIN_RATE", "40.0"))
        config.min_profit_factor = float(os.getenv("MIN_PROFIT_FACTOR", "1.2"))
        config.max_drawdown_filter = float(os.getenv("MAX_DRAWDOWN_FILTER", "30.0"))
    except ValueError as e:
        raise ConfigError("Parametri filtri devono essere numerici") from e

    config.skip_filters = os.getenv("SKIP_FILTERS", "false").strip().lower() in ("true", "1", "yes")

    # --- Strategie (F1-S04) ---
    strategies_str = os.getenv("STRATEGIES", "momentum_drop")
    strategies = [s.strip().lower() for s in strategies_str.split(",") if s.strip()]
    config.strategies = strategies if strategies else ["momentum_drop"]

    # --- Y Dinamico ---
    config.y_dynamic = os.getenv("Y_DYNAMIC", "false").strip().lower() in ("true", "1", "yes")
    try:
        config.y_max_window = int(os.getenv("Y_MAX_WINDOW", "600"))
    except ValueError as e:
        raise ConfigError("Y_MAX_WINDOW deve essere un intero") from e
    if config.y_max_window <= 0:
        raise ConfigError("Y_MAX_WINDOW deve essere > 0")

    _validate_config(config)

    return config


def _validate_config(config: Config) -> None:
    """
    Validazioni aggiuntive sulla configurazione.

    Raises:
        ConfigError: se un vincolo non è rispettato.
    """
    if config.position_size <= 0:
        raise ConfigError("POSITION_SIZE deve essere > 0")

    if config.initial_capital <= 0:
        raise ConfigError("INITIAL_CAPITAL deve essere > 0")

    if config.fee_rate < 0:
        raise ConfigError("FEE_RATE deve essere >= 0")

    if config.slippage_rate < 0:
        raise ConfigError("SLIPPAGE_RATE deve essere >= 0")

    if config.max_hold_seconds <= 0:
        raise ConfigError("MAX_HOLD_SECONDS deve essere > 0")

    if not config.x_values:
        raise ConfigError("X_VALUES non può essere vuoto")

    if not config.y_values and not config.y_dynamic:
        raise ConfigError("Y_VALUES non può essere vuoto (a meno di Y_DYNAMIC=true)")

    if not config.z_values:
        raise ConfigError("Z_VALUES non può essere vuoto")

    if not config.ma_periods or any(value < 2 for value in config.ma_periods):
        raise ConfigError("MA_PERIODS deve contenere interi >= 2")
    if not config.z_thresholds or any(value <= 0 for value in config.z_thresholds):
        raise ConfigError("Z_THRESHOLDS deve contenere valori > 0")

    for x in config.x_values:
        if x <= 0:
            raise ConfigError(f"Tutti i valori X devono essere > 0, trovato: {x}")

    for y in config.y_values:
        if y <= 0:
            raise ConfigError(f"Tutti i valori Y devono essere > 0, trovato: {y}")

    for z in config.z_values:
        if z <= 0:
            raise ConfigError(f"Tutti i valori Z devono essere > 0, trovato: {z}")
