# ➕ COME AGGIUNGERE UNA STRATEGIA

## Procedura completa, verificata sul codice reale

> Verificato il 2026-09-26 contro `python-backtester/src/strategy_base.py`, `src/strategies/__init__.py`, `src/strategies/mean_reversion.py`, `src/searcher/bayesian_optimizer.py` e `main.py`.
> Risposta breve: **2 file + 1 test. `main.py` NON si tocca** — con un'unica eccezione documentata in §7.

---

## 1. Il principio

L'architettura è già stata costruita perché le strategie fossero **plug-in**:

```
STRATEGY_REGISTRY = { "nome": Classe }     ← unico punto di registrazione
```

Ogni altro componente è già generico:
- la **UI** (`/api/config`) **legge il listing dei file** in `src/strategies/*.py` → la strategia compare da sola nel form
- il **validatore** della UI rivalida contro quel listing
- **Optuna** (`--search optuna`) risolve la classe dal registry e chiama `run_backtest` in modo duck-typed → **zero codice dedicato**

Quindi il lavoro è: **scrivere la classe + registrarla**.

## 2. I 4 metodi obbligatori

La classe deve estendere `TradingStrategy` (da `src.strategy_base.py`) e implementare 3 metodi astratti. Il 4º (`run_backtest`) serve solo per Optuna/grid.

```python
from src.strategy_base import TradingStrategy, Signal
```

| Metodo | Obbligatorio | A cosa serve |
|---|---|---|
| `parameter_space() -> Dict[str, Tuple]` | ✅ | Spazio di ricerca: `{"nome": (lo, hi, kind)}` |
| `generate_signals(df, params) -> List[Signal]` | ✅ | Il cuore: quando entrare/uscire |
| `validate(params) -> bool` | ✅ | Scarta parametri invalidi **prima** di pagare un backtest |
| `run_backtest(df, params, symbol) -> List[Trade]` | per Optuna/grid | Da segnali a trade con PnL |

**`kind` ammessi** (costante `ALLOWED_PARAM_KINDS` in `strategy_base.py`): `"float"`, `"int"`, `"float_log"`, `"int_log"`. I `*_log` servono quando il parametro varia su più ordini di grandezza (es. soglie da 0.01 a 10).

## 3. Il template minimo (copia e adatta)

Copia `src/strategies/mean_reversion.py`: è l'esempio più compatto e completo.

```python
# python-backtester/src/strategies/mia.py
"""
mia.py - Strategia Mia.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

from src.strategy import BacktestParams, Trade
from src.strategy_base import Signal, TradingStrategy


class MiaStrategy(TradingStrategy):
    """Una riga di descrizione: cosa compra e cosa vende."""

    def parameter_space(self) -> Dict[str, Tuple]:
        return {
            "lookback": (10, 200, "int"),
            "soglia": (0.5, 3.0, "float"),
            "max_hold_seconds": (60, 1800, "int"),
            "position_size": (10.0, 1000.0, "float"),
        }

    def generate_signals(self, df: pd.DataFrame, params: Dict) -> List[Signal]:
        lookback = int(params["lookback"])
        soglia = float(params["soglia"])

        work = df.copy()
        work["ma"] = work["close"].rolling(lookback).mean()
        work["std"] = work["close"].rolling(lookback).std()
        work["z"] = (work["close"] - work["ma"]) / work["std"]

        use_datetime = "datetime" in work.columns
        signals: List[Signal] = []
        in_position = False

        for idx, row in work.iterrows():
            z = row["z"]
            # salta il warmup: MA/std NaN o std == 0
            if pd.isna(z) or row["std"] == 0:
                continue
            timestamp = pd.Timestamp(row["datetime"]) if use_datetime else pd.Timestamp(idx)
            price = float(row["close"])

            if not in_position and z < -soglia:
                signals.append(Signal(
                    timestamp=timestamp, type="ENTRY", side="LONG",
                    price=price, reason=f"z={z:.2f}",
                ))
                in_position = True
            elif in_position and z > -0.1:
                signals.append(Signal(
                    timestamp=timestamp, type="EXIT", side="LONG",
                    price=price, reason="uscita",
                ))
                in_position = False

        return signals

    def validate(self, params: Dict) -> bool:
        try:
            return int(params["lookback"]) >= 5 and float(params["soglia"]) > 0
        except (KeyError, TypeError, ValueError):
            return False

    def gpu_param_arrays(self, param_grid: List[Dict]) -> Dict[str, np.ndarray]:
        """Opzionale ma raccomandato: parametri come array per il path GPU."""
        return {
            "lookback": np.array([int(d["lookback"]) for d in param_grid], dtype=np.int64),
            "soglia": np.array([float(d["soglia"]) for d in param_grid], dtype=np.float64),
        }
```

### Sul `run_backtest`

Se non lo scrivi tu, non lo riutilizzi: è ~120 righe (`mean_reversion.py:96-217`) che accoppiano ENTRY→EXIT, applicano slippage, fee, `max_hold_seconds`, MAE/MFE e chiudono a fine dati. **Copia quel metodo da `mean_reversion.py` e cambia solo la mappatura dei parametri su `BacktestParams`.**

La mappatura serve perché `Trade` ha campi fissi (`x_percent`, `y_seconds`, `z_percent`): ci metti i parametri più significativi della tua strategia, così le metriche e i CSV restano comparabili.

## 4. Registrazione (1 file, 2 righe)

```python
# python-backtester/src/strategies/__init__.py
from src.strategies.mia import MiaStrategy

STRATEGY_REGISTRY = {
    "momentum_drop": MomentumDropStrategy,
    "mean_reversion": MeanReversionZScore,
    "mean_reversion_zscore": MeanReversionZScore,
    "mia": MiaStrategy,          # ← nome = chiave usata da CLI e UI
}

__all__ = [..., "MiaStrategy", "STRATEGY_REGISTRY"]
```

**Il nome della chiave è il nome che userai** nel terminale e che vedrai nel form della UI.

Alias gratis: se la strategia è raggiungibile con due nomi, registra due chiavi che puntano alla stessa classe (vedi `mean_reversion` / `mean_reversion_zscore`).

## 5. I test (1 file)

```python
# python-backtester/tests/test_mia.py
import numpy as np
import pandas as pd

from src.strategies.mia import MiaStrategy


def _df(prices):
    n = len(prices)
    return pd.DataFrame({
        "datetime": pd.date_range("2026-01-01", periods=n, freq="s"),
        "open": prices, "high": prices, "low": prices,
        "close": prices, "volume": np.ones(n),
    })


def test_validate():
    s = MiaStrategy()
    assert s.validate({"lookback": 50, "soglia": 1.5}) is True
    assert s.validate({"lookback": 2, "soglia": 1.5}) is False   # troppo corto
    assert s.validate({"lookback": 50}) is False                # mancante


def test_trend_monotono_non_genera_segnali():
    # In trend senza mean-reversion non deve entrare mai
    s = MiaStrategy()
    segnali = s.generate_signals(_df(np.linspace(100, 200, 400)), {"lookback": 50, "soglia": 2.0})
    assert [g for g in segnali if g.type == "ENTRY"] == []


def test_segnali_alternano_entry_exit():
    # Su una serie oscillante: mai due ENTRY consecutivi
    n = 600
    prices = 100 + 10 * np.sin(np.arange(n) / 12)
    s = MiaStrategy()
    segnali = s.generate_signals(_df(prices), {"lookback": 20, "soglia": 0.5})
    for a, b in zip(segnali, segnali[1:]):
        assert a.type != b.type


def test_gpu_param_arrays():
    s = MiaStrategy()
    out = s.gpu_param_arrays([{"lookback": 10, "soglia": 1.0}, {"lookback": 20, "soglia": 2.0}])
    assert set(out) == {"lookback", "soglia"}
    assert all(isinstance(v, np.ndarray) and v.dtype != object for v in out.values())
    assert len(out["lookback"]) == 2
```

## 6. Verifica

```powershell
cd python-backtester
.\.venv\Scripts\python -m pytest tests/ -q                      # tutto verde
.\.venv\Scripts\python main.py --symbol UNIUSDT --strategy mia --engine standard --search grid
```

Nella **UI** (`npm run dashboard`): riavvia il server (le strategie sono lette a ogni richiesta di `/api/config`) → "mia" è nel dropdown senza toccare nulla.

## 7. L'unica eccezione: `--search grid` è una whitelist

Questo è l'unico punto dove il generico non è ancora arrivato, ed è **un limite dell'architettura, non qualcosa che devi fare per ogni strategia**.

In `main.py` il routing grid è una catena di `elif`:

```python
elif strategy == "momentum_drop":        ...
elif strategy in ("mean_reversion", ...): ...
else:
    print("❌ strategia registrata ma senza runner grid standard dedicato.")
    sys.exit(1)                          # ← la tua strategia si ferma qui
```

Quindi:
- **`--search optuna`** → funziona subito, zero `main.py` (percorso generico via registry)
- **`--search grid`** → la strategia nuova non parte finché non le dedichi un branch

**Scelta pragmatica**: usa Optuna per le strategie nuove. Se ti serve per forza la grid esaustiva, il branch è 5 righe — ma allora la procedura diventa 3 file + `main.py`, ed è la **peggiore scelta** perché:

1. ogni nuova strategia ricomincia a toccare l'orchestratore
2. il branch alla fine esegue una griglia dimostrativa piccola e fissa, non il tuo `parameter_space` vero (vedi `run_standard_engine_mean_reversion`, che è 2×2)
3. percorri esattamente la strada che ha prodotto 120 righe duplicate di `run_backtest`

**La correzione strutturale** (una volta sola, per tutte le strategie future) è far usare al percorso grid il `run_backtest` generico che già esiste, cadendo su `parameter_space()` per la griglia. Se la facciamo, `main.py` diventa generico anche per grid e questa sezione sparisce. Non l'ho fatta perché è una modifica al routing del backtester, non all'aggiunta di una strategia: merita una sua decisione esplicita.

## 8. Checklist in 6 righe

1. `src/strategies/mia.py` — classe con 3 metodi astratti (+ `run_backtest` copiato da `mean_reversion.py`)
2. `src/strategies/__init__.py` — import + 1 riga nel `STRATEGY_REGISTRY`
3. `tests/test_mia.py` — validate, alternanza segnali, caso limite, `gpu_param_arrays`
4. `pytest tests/ -q` verde
5. `main.py --symbol X --strategy mia --search optuna` gira
6. la strategia **appare da sola** nella UI

## 9. Errori da non fare

| Errore | Conseguenza |
|---|---|
| `kind` fuori da `ALLOWED_PARAM_KINDS` | Optuna lo rifiuta a runtime |
| `generate_signals` che emette 2 ENTRY di fila | `run_backtest` accoppiaENTRY→EXIT e perde il trade |
| `validate` che non intercetta i parametri buchi | Optuna paga backtest inutili su spazi invalidi |
| `gpu_param_arrays` che restituisce liste Python | viola il contratto GPU (§6.1 masterplan v3) |
| chiave del registry diversa dal nome del file | la UI la mostra comunque (listing file), ma CLI e UI divergono |
| dimenticare `run_backtest` | Optuna fallisce con errore esplicito, grid non parte |

---

> Una strategia è un file. Il resto lo fa il framework.
