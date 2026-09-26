# Caso #17 — Type Hints su tutti i file Python

## 🔍 Analisi del Problema

### Codice originale (firme senza annotazioni)

Prima dell'intervento le funzioni del backtester non dichiaravano tipi di parametri e ritorni, lasciando il contratto implicito (es. `epoch_seconds` in secondi o millisecondi? `direction` stringa o intero?). Esempio dello stato attuale, con annotazioni verificate via grep su `src/`:

```python
# src/simulator.py, linea 17
def run_backtest(df: pd.DataFrame, params: BacktestParams, symbol: str) -> List[Trade]:

# src/fast/fast_metrics.py, linee 25-30
def calculate_fast_metrics(
    trades_array: np.ndarray,
    n_trades: int,
    direction: int,
    initial_capital: float,
) -> dict[str, object]:

# src/gpu/data_splitter.py, linea 82
def _boundary_to_run_start(datetimes: pd.Series, idx: int) -> int:
```

### Bug Identificati

1. **Contratti impliciti tra engine** — i tre motori si scambiano array e codici (`direction: 0/1/2` in Numba/CUDA vs `"signal-only"/"long"/"short"` in Python, reason `1/2/3`): senza annotazioni, passare una stringa dove serve un intero fallisce solo a runtime dentro il kernel JIT, con errori oscuri.
2. **Refactoring non sicuri** — rinominare un campo di `Trade`/`BacktestResult` o cambiare il layout delle colonne dell'array trade (`[0..9]`) senza type-check statico lascia call-site rotti scoperti solo dall'esecuzione completa dello screening.
3. **Onboarding e review lenti** — senza firme tipizzate, ogni lettore deve inferire i tipi dal corpo (es. `train_ratio: float` vs stringa da `.env` già convertita), aumentando il rischio di misuse.

### Analisi Approfondita delle Alternative

#### Soluzione A — Annotazioni `typing` + `numpy`/`pandas` su tutto `src/` (scelta)
- **Pro**: zero costo runtime (le annotazioni sono ignorate dall'interprete, incluse le funzioni `@njit`); abilita `mypy`/IDE; documenta i confini tra engine (DataFrame → `epoch_ms: int64` / `close: float64`).
- **Contro**: `mypy` non verifica l'interno delle funzioni Numba/CUDA (stringhe kernel); i tipi degli array (`float64[:, 10]`) restano convenzioni documentate nei docstring, non vincoli.

#### Soluzione B — Solo docstring senza annotazioni
- **Pro**: nessun import `typing`.
- **Contro**: non verificabile meccanicamente; i docstring divergono dal codice senza che nulla lo segnali.

#### Soluzione C — `pydantic` / dataclass con validazione runtime
- **Pro**: validazione effettiva dei valori, non solo dei tipi.
- **Contro**: overhead runtime sul path hot (milioni di trade) e dipendenza aggiuntiva; eccessivo per invarianti già garantite da `ConfigError`/`DataLoadError` ai boundary.

### Soluzione Scelta

**Soluzione A** — file verificati con annotazioni complete: `config.py` (`_parse_range(...) -> list`, `load_config() -> Config`, `_validate_config(config: Config) -> None`), `strategy.py` (dataclass `BacktestParams`/`Trade`/`BacktestResult`), `simulator.py`, `metrics.py`, `results_writer.py`, `parameter_grid.py`, `data_splitter.py` (+ `k_fold_split`, `print_*`), `screening_metrics.py`, `filters.py`, `gpu_detector.py`, `trade_utils.py`, `gpu_simulator.py`, `gpu_fallback.py`, `fast_simulator.py` (`_simulate_single(...) -> Tuple[np.ndarray, int]`, con stub non-tipizzati solo nel ramo `not NUMBA_AVAILABLE`), `fast_metrics.py`, `fast_runner.py`, `gpu_runner.py`, `profiling.py` (`from __future__ import annotations`), `main.py` (`main() -> None`). Lacune residue note: `Timer.__enter__/__exit__` e `print_config_summary(symbols: list, ...)` in `utils/__init__.py` sono parzialmente non annotati — candidati per un follow-up, nessun impatto funzionale.

### Impatto

- **Previene**: misuse stringa/intero tra engine, rotture silenziose da refactoring, ambiguità sui layout degli array trade.
- **Rischio del cambiamento**: nullo a runtime — le annotazioni non alterano il comportamento; l'unico rischio è formale (firma errata che mente al lettore), mitigato da `mypy` in CI.
- **Test richiesti**: `mypy src/` (o almeno `mypy` sui moduli core) senza nuovi errori; `pytest tests/` invariato; grep di controllo che ogni `def` pubblico in `src/` abbia `->`.
