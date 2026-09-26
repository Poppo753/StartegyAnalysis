# Caso #3 — Fix Data-based Split (data_splitter.py)

## 🔍 Analisi del Problema

### Codice originale (data_splitter.py, linee 33-42)

```python
def split_train_validation(
    df: pd.DataFrame,
    train_ratio: float = 0.7,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    n = len(df)
    split_idx = int(n * train_ratio)
    split_idx = max(1, min(split_idx, n - 1))

    df_train = df.iloc[:split_idx].reset_index(drop=True)
    df_validation = df.iloc[split_idx:].reset_index(drop=True)

    return df_train, df_validation
```

### Bug Identificati

#### Bug 1: Split basato su INDICE, non su DATA
- Se i dati hanno distribuzione non uniforme (es. weekend con poche candele), lo split a indice 70% non corrisponde a 70% del periodo temporale
- **Esempio**: 1000 righe totali (700 da lun-ven, 300 da sab-dom). Lo split a indice 700 mette tutto il weekend in VALIDATION, rendendo la validazione non rappresentativa
- **Conseguenza**: Il modello viene validato su un periodo che potrebbe avere pattern diversi (weekend vs weekday)

#### Bug 2: Nessun controllo di integrità temporale
- Non verifica che i dati siano ordinati cronologicamente
- Se il DataFrame non è ordinato, lo split è privo di significato

#### Bug 3: `split_idx = max(1, min(split_idx, n - 1))` è ridondante
- Se `train_ratio=0.7` e `n=10`, `split_idx = 7`, `min(7, 9) = 7`, `max(1, 7) = 7` — OK
- Se `train_ratio=0.0`, `split_idx = 0`, `max(1, 0) = 1` — forzato a 1, non a 0
- Se `train_ratio=1.0`, `split_idx = 10`, `min(10, 9) = 9` — forzato a 9, non a 10
- Questo comportamento forzato può portare a split inaspettati

### Analisi Approfondita delle Alternative

#### Soluzione A — Split basato su data/timestamp (consigliata)
```python
split_date = df["datetime"].iloc[int(n * train_ratio)]
df_train = df[df["datetime"] <= split_date]
df_validation = df[df["datetime"] > split_date]
```
- **Pro**: Garantisce che il split sia temporale, non per indice
- **Contro**: Se ci sono candele con lo stesso timestamp, potrebbero finire entrambe in TRAIN o entrambe in VALIDATION

#### Soluzione B — Split basato su data con tolleranza
```python
split_date = df["datetime"].iloc[int(n * train_ratio)]
# Sposta indietro le candele esattamente allo split date
df_train = df[df["datetime"] < split_date]
df_validation = df[df["datetime"] >= split_date]
```
- **Pro**: Garantisce che nessuna candela al confine sia ambigua
- **Contro**: Potrebbe lasciare candele "vuote" al confine

#### Soluzione C — Validazione della data di confine
```python
split_date = df["datetime"].iloc[int(n * train_ratio)]
# Trova la prima candela con data >= split_date
# e includi tutte le candele con la stessa data in VALIDATION
val_start = df[df["datetime"] >= split_date]["datetime"].min()
df_train = df[df["datetime"] < val_start]
df_validation = df[df["datetime"] >= val_start]
```
- **Pro**: Perfetta integrità temporale, nessuna ambiguità
- **Contro**: Leggermente più complesso

### Soluzione Scelta

**Soluzione C** — La più robusta. Garantisce:
1. Split temporale basato su date reali, non indici
2. Integrità temporale: nessuna candela è in entrambi i set
3. Nessuna perdita di dati al confine

### Impatto

- **Previene**: Overfitting per data leakage, validazione non rappresentativa
- **Rischio**: Basso — solo cambio della logica di split
- **Test**: Verificare che il confine sia pulito, nessuna sovrapposizione tra TRAIN e VALIDATION
