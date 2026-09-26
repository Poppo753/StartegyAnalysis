# Caso #24 — K-Fold Temporal Cross-Validation (data_splitter.py)

## 🔍 Analisi del Problema

### Codice originale (split singolo fragile / K-fold con fold-0 vuoto)

Il codice precedente presentava due difetti: (a) un parametro `train_ratio` dichiarato ma inutilizzato nel K-fold, (b) fold-0 con `TRAIN` vuoto (`df_sorted.iloc[0:0]`), che sprecava uno split su una validazione senza training e indeboliva la stima out-of-sample. L'implementazione reale (`python-backtester/src/gpu/data_splitter.py`, `k_fold_split(df, k)`, linee 99-170) usa expanding window su `k+1` chunk, senza `train_ratio`:

```python
def k_fold_split(df: pd.DataFrame, k: int) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    n_chunks = k + 1
    fold_size = n // n_chunks
    ...
    for i in range(1, k + 1):                       # TRAIN sempre non-vuoto
        train_end = _boundary_to_run_start(datetimes, i * fold_size)
        val_end = _boundary_to_run_start(datetimes, (i + 1) * fold_size) if i < k else n
        if train_end <= 0 or val_end <= train_end:
            raise ValueError(                        # fold svuotato dai duplicati
                f"k_fold_split: fold {i}/{k} vuoto dopo anti-leakage adjustment ...")
        df_train = df_sorted.iloc[:train_end]...
        df_val = df_sorted.iloc[train_end:val_end]...
        assert df_train["datetime"].max() < df_val["datetime"].min()
```

L'anti-leakage sui duplicati è centralizzato in `_boundary_to_run_start` (linee 82-96): sposta il confine all'inizio del run di timestamp uguali, così i duplicati finiscono sempre in VAL, coerente con `split_train_validation` (linee 65-72).

### Bug Identificati

1. **`train_ratio` inutilizzato** — parametro accettato ma ignorato nel calcolo dei fold: firma bugiarda che suggeriva un controllo mai applicato. Rimosso dalla firma reale `(df, k)`; la geometria è interamente determinata da `k` (`k+1` chunk).
2. **Fold-0 con TRAIN vuoto** — il vecchio ciclo `for i in range(k)` con `df_train = iloc[0:0]` al primo giro produceva uno split che "valida" senza aver addestrato: rumore nella stima, non segnale. Il ciclo reale `range(1, k+1)` garantisce TRAIN ⊇ 1 chunk in ogni fold (proprietà documentata, linea 113).
3. **Divisione di timestamp duplicati tra TRAIN e VAL** — senza aggiustamento al confine, candele con identico timestamp finivano in entrambi i set (leakage puntuale). Ora entrambi i confini passano per `_boundary_to_run_start` e l'invariante è enforced da `assert max(TRAIN) < min(VAL)` (linee 165-166); se l'aggiustamento svuota un fold, `ValueError` esplicito invece di split degeneri silenziosi.

### Analisi Approfondita delle Alternative

#### Soluzione A — Expanding window temporale con `k+1` chunk + anti-leakage (scelta)
- **Pro**: nessun leakage futuro (TRAIN strettamente prima di VAL), deterministico senza shuffle, ogni fold ha TRAIN non-vuoto, fallisce esplicitamente su dati degeneri (timestamp unico dominante).
- **Contro**: i fold non hanno VAL di uguale dimensione statistica sull'ultimo split (`val_end = n`); costo computazionale ×k sullo screening.

#### Soluzione B — KFold random di sklearn
- **Pro**: una riga di codice, fold bilanciati.
- **Contro**: mescola passato e futuro → look-ahead bias sistematico; stime ottimistiche che crollano live. Inaccettabile per serie finanziarie; scartata per vincolo metodologico.

#### Soluzione C — Walk-forward con finestra scorrevole fissa (sliding, non expanding)
- **Pro**: TRAIN a dimensione costante, più reattivo ai regime shift.
- **Contro**: butta i dati vecchi (meno storia per fold); più parametri (train_size, step); non necessario finché lo screening usa tutto il passato disponibile.

### Soluzione Scelta

**Soluzione A** — per `k=5` su 1000 candele: fold 1 = TRAIN[0:167]/VAL[167:334], …, fold 5 = TRAIN[0:834]/VAL[834:1000] (a meno di aggiustamenti anti-leakage). Complementa `split_train_validation` (singolo split 70/30 su date reali, linee 16-79) per lo screening rapido, mentre il K-fold serve alla validazione robusta anti-overfitting. `print_kfold_info` (linee 194-216) rende ogni fold ispezionabile.

### Impatto

- **Previene**: overfitting da validazione singola, look-ahead bias, leakage da timestamp duplicati al confine, fold degeneri silenziosi.
- **Rischio del cambiamento**: basso — funzione additiva che non modifica `split_train_validation`; unico costo è computazionale (k screening).
- **Test richiesti**: `tests/test_data_splitter.py` — `max(TRAIN) < min(VAL)` per ogni fold, TRAIN non-vuoti e crescenti, copertura senza buchi né overlap, `ValueError` per `k < 2`/df vuoto/duplicati che svuotano un fold; equivalenza con `train_ratio` rimosso (la firma non lo accetta più).
