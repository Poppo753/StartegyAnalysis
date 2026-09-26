# Caso #11 — Modulo Condiviso trade_utils.py

## 🔍 Analisi del Problema

### Codice originale (logica duplicata pre-refactoring)

Prima del refactoring, le utility di analisi post-hoc erano copiate in più script (`stoploss_analysis.py`, `trade_profile.py`, `data_loader.py`): caricamento CSV trades con validazione colonne, metriche aggregate da array PnL, reporting testuale, caricamento OHLC. Il modulo unico è ora `python-backtester/src/utils/trade_utils.py`, con re-export di compatibilità in `python-backtester/src/data_loader.py` (linee 7-10):

```python
# src/data_loader.py — re-export, nessuna logica propria
from src.utils.trade_utils import load_ohlc_data, DataLoadError
from src.utils.trade_utils import _expected_candles, expected_candles

__all__ = ["load_ohlc_data", "DataLoadError", "_expected_candles", "expected_candles"]
```

API reale del modulo condiviso (`trade_utils.py`):

```python
class DataLoadError(ValueError): ...                                   # linea 24
def load_trades(filepath: str, required_columns: List[str]) -> pd.DataFrame  # linea 29
def calc_metrics(pnls: np.ndarray, capital: float) -> Dict[str, Any]    # linea 71
def format_metrics(m: Dict[str, Any]) -> str                           # linea 112
def diagnose(m: Dict[str, Any], position_size: float) -> str           # linea 129
def load_ohlc_data(config: Config, symbol: str) -> pd.DataFrame        # linea 152
def expected_candles(df: pd.DataFrame) -> int                          # linea 215
```

### Bug Identificati

1. **Violazione DRY** — la stessa formula (win-rate, profit factor con cap `999.0`, drawdown su equity `capital + cumsum`, break-even `ratio/(1+ratio)`) esisteva in N copie: una correzione (es. divisione per zero su `gl == 0`, linea 96) applicata a una sola copia lasciava le altre errate.
2. **Inconsistenza dei risultati** — piccole divergenze tra copie (arrotondamenti, gestione `entry_time`/`exit_time` → `hold_seconds`, linee 63-66; normalizzazione legacy `max_price` → `max_price_during_trade`, linee 54-57) producevano report diversi a parità di input.
3. **Error handling frammentato** — ogni copia validava a modo suo file mancanti/colonne assenti; ora `DataLoadError` (sottoclasse di `ValueError`) è l'unico contratto e, per policy del modulo (docstring linee 11-12), non chiama mai `sys.exit()`: l'exit resta confinato al boundary CLI.

### Analisi Approfondita delle Alternative

#### Soluzione A — Modulo condiviso con alias legacy (scelta)
- **Pro**: single source of truth; `_fmt_metrics`/`_diagnose`/`_expected_candles` (linee 124, 147, 223) mantengono compatibilità con gli import esistenti; `data_loader.py` resta come shim senza rompere i consumer.
- **Contro**: gli alias duplicano (volutamente) i nomi pubblici — vanno documentati come deprecati per evitare nuovo codice che li usi.

#### Soluzione B — Mantenere le copie con test di equivalenza
- **Pro**: nessun change agli import.
- **Contro**: costo di manutenzione moltiplicato; i test fotografano la divergenza invece di eliminarla.

#### Soluzione C — Package esterno installabile
- **Pro**: versionamento indipendente, riuso cross-repo.
- **Contro**: overhead di packaging/release ingiustificato per utility interne a un solo backtester.

### Soluzione Scelta

**Soluzione A** — `trade_utils.py` è single source of truth per `load_trades` (con validazione colonne e `DataLoadError` su file mancante/illeggibile/colonne mancanti), `calc_metrics` (dict con `n/nw/nl/wr/avg_w/avg_l/gp/gl/pf/total/best/worst/dd_u/dd_p/expect`, `{}` su array vuoto), `format_metrics`/`diagnose` (restituiscono stringhe, non stampano — componibili e testabili), `load_ohlc_data` (path `{data_dir}/{symbol}/ohlc/ohlc_{timeframe}_{start}_{end}.csv`, parsing timestamp ms/ISO, `epoch_seconds`, ordinamento cronologico). Gli alias legacy garantiscono migrazione graduale.

### Impatto

- **Previene**: fix applicati a metà, report divergenti tra script, `sys.exit()` dentro codice libreria (non testabile).
- **Rischio del cambiamento**: medio — tutti gli import dei consumer vanno aggiornati; mitigato dagli alias e dallo shim `data_loader.py`.
- **Test richiesti**: equivalenza numerica `calc_metrics` vs implementazioni precedenti su fixture con 0/1/N trade e solo-vincenti/solo-perdenti; `pytest.raises(DataLoadError)` su file mancante, vuoto, con colonne assenti e timestamp non convertibili.
