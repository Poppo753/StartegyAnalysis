"""
data_splitter.py - Split temporale dei dati per anti-overfitting

Divide il dataset in:
- TRAIN: periodo di ottimizzazione (70% default)
- VALIDATION: periodo di verifica out-of-sample (30% default)

Lo split è TEMPORALE (non random) e basato su DATE REALI, non su indici,
per rispettare la natura sequenziale dei dati finanziari e prevenire data leakage.
"""

import pandas as pd
from typing import Tuple, List


def split_train_validation(
    df: pd.DataFrame,
    train_ratio: float = 0.7,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Divide il DataFrame in train e validation basandosi su date reali.

    Il split è basato sulla data temporale (non sull'indice), garantendo che:
    1. Tutte le candele con data <= split_date sono in TRAIN
    2. Tutte le candele con data > split_date sono in VALIDATION
    3. Nessuna candela è in entrambi i set (nessuna ambiguità al confine)
    4. Se ci sono candele con lo stesso timestamp al confine, tutte vanno in VALIDATION

    Args:
        df: DataFrame con i dati OHLC (deve avere colonna "datetime")
        train_ratio: proporzione per il training (0.0-1.0)

    Returns:
        Tuple (df_train, df_validation)
    """
    if len(df) == 0:
        raise ValueError("Cannot split empty DataFrame")

    if not pd.api.types.is_datetime64_any_dtype(df["datetime"]):
        raise ValueError("DataFrame must have a 'datetime' column with datetime dtype")

    # Assicura che i dati siano ordinati cronologicamente
    df_sorted = df.sort_values("datetime").reset_index(drop=True)

    n = len(df_sorted)
    if n < 2:
        return df_sorted.iloc[:1], df_sorted.iloc[0:0].copy()

    # Trova la data di split basata sulla posizione percentuale
    split_idx = int(n * train_ratio)
    split_idx = max(0, min(split_idx, n))  # range: [0, n]

    if split_idx == 0:
        # Tutto in VALIDATION
        return df_sorted.iloc[0:0].copy(), df_sorted.copy()
    elif split_idx >= n:
        # Tutto in TRAIN
        return df_sorted.copy(), df_sorted.iloc[0:0].copy()

    # Usa la data reale come confine, non l'indice
    # Tutte le candele con datetime < split_datetime vanno in TRAIN
    # Tutte le candele con datetime >= split_datetime vanno in VALIDATION
    split_datetime = df_sorted["datetime"].iloc[split_idx]

    # Trova la prima posizione con datetime >= split_datetime
    # Questo garantisce che nessuna candela al confine sia ambigua
    val_start_idx = split_idx
    while val_start_idx > 0 and df_sorted["datetime"].iloc[val_start_idx - 1] == split_datetime:
        val_start_idx -= 1

    df_train = df_sorted.iloc[:val_start_idx].reset_index(drop=True)
    df_validation = df_sorted.iloc[val_start_idx:].reset_index(drop=True)

    # Validazione: nessuna sovrapposizione
    if len(df_train) > 0 and len(df_validation) > 0:
        assert df_train["datetime"].max() < df_validation["datetime"].min(), \
            "Data leakage detected: TRAIN and VALIDATION have overlapping timestamps"

    return df_train, df_validation


def _boundary_to_run_start(datetimes: pd.Series, idx: int) -> int:
    """
    Sposta un indice di split all'inizio del run di timestamp uguali.

    Garantisce che timestamp identici non vengano mai divisi tra TRAIN e VAL
    (nessun leakage al confine). I duplicati vanno sempre in VAL,
    coerente con split_train_validation().
    """
    n = len(datetimes)
    if idx <= 0 or idx >= n:
        return max(0, min(idx, n))
    boundary_ts = datetimes.iloc[idx]
    while idx > 0 and datetimes.iloc[idx - 1] == boundary_ts:
        idx -= 1
    return idx


def k_fold_split(
    df: pd.DataFrame,
    k: int,
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Split in K fold temporali con finestra espandente (stile TimeSeriesSplit).

    I dati vengono divisi in k+1 chunk contigui; per lo split i (1..k):
    - TRAIN = chunk [0 .. i)
    - VAL   = chunk [i .. i+1) (ultimo VAL arriva a n)

    Proprietà garantite:
    1. TRAIN è sempre strettamente prima di VAL (nessun leakage futuro).
    2. Timestamp identici non vengono mai divisi tra TRAIN e VAL.
    3. Ogni TRAIN è non-vuoto (il primo contiene almeno 1 chunk).
    4. Deterministico: nessun shuffle, ordine cronologico preservato.

    Args:
        df: DataFrame con colonna "datetime" (datetime64).
        k: numero di split (deve essere >= 2).

    Returns:
        Lista di k tuple (df_train, df_val).

    Raises:
        ValueError: se k < 2, df vuoto, colonna datetime mancante,
            o dati insufficienti per k split non-vuoti.
    """
    if k < 2:
        raise ValueError(f"k must be >= 2, got {k}")
    if len(df) == 0:
        raise ValueError("Cannot split empty DataFrame")
    if "datetime" not in df.columns or not pd.api.types.is_datetime64_any_dtype(df["datetime"]):
        raise ValueError("DataFrame must have a 'datetime' column with datetime dtype")

    df_sorted = df.sort_values("datetime").reset_index(drop=True)
    n = len(df_sorted)
    datetimes = df_sorted["datetime"]

    n_chunks = k + 1
    fold_size = n // n_chunks
    if fold_size < 1:
        raise ValueError(f"Not enough rows ({n}) for k={k} non-empty folds")

    folds: List[Tuple[pd.DataFrame, pd.DataFrame]] = []

    for i in range(1, k + 1):
        train_end = _boundary_to_run_start(datetimes, i * fold_size)
        if i < k:
            val_end = _boundary_to_run_start(datetimes, (i + 1) * fold_size)
        else:
            val_end = n

        # Se l'aggiustamento ha svuotato TRAIN o VAL, i dati hanno un unico
        # timestamp dominante: impossibile fare K-fold significativo.
        if train_end <= 0 or val_end <= train_end:
            raise ValueError(
                f"k_fold_split: fold {i}/{k} vuoto dopo anti-leakage adjustment "
                f"(train_end={train_end}, val_end={val_end}, n={n}). "
                f"Riduci k o verifica duplicati timestamp."
            )

        df_train = df_sorted.iloc[:train_end].reset_index(drop=True)
        df_val = df_sorted.iloc[train_end:val_end].reset_index(drop=True)

        # Validazione anti-leakage: nessuna sovrapposizione temporale
        assert df_train["datetime"].max() < df_val["datetime"].min(), \
            "Data leakage detected in K-fold split"

        folds.append((df_train, df_val))

    return folds


def print_split_info(df: pd.DataFrame, df_train: pd.DataFrame, df_validation: pd.DataFrame):
    """Stampa informazioni sullo split temporale."""
    total = len(df)
    n_train = len(df_train)
    n_val = len(df_validation)

    train_start = df_train["datetime"].iloc[0] if n_train > 0 else pd.NaT
    train_end = df_train["datetime"].iloc[-1] if n_train > 0 else pd.NaT
    val_start = df_validation["datetime"].iloc[0] if n_val > 0 else pd.NaT
    val_end = df_validation["datetime"].iloc[-1] if n_val > 0 else pd.NaT

    print(f"\n  📐 Split temporale anti-overfitting:")
    print(f"     TRAIN:      {n_train:>10,} candele ({n_train/total*100:.1f}%)")
    if not pd.isna(train_start):
        print(f"                 {train_start} → {train_end}")
    print(f"     VALIDATION: {n_val:>10,} candele ({n_val/total*100:.1f}%)")
    if not pd.isna(val_start):
        print(f"                 {val_start} → {val_end}")
    print(f"     Totale:     {total:>10,} candele")


def print_kfold_info(
    df: pd.DataFrame,
    k: int,
    folds: List[Tuple[pd.DataFrame, pd.DataFrame]],
) -> None:
    """Stampa informazioni sui K fold temporali."""
    total = len(df)
    print(f"\n  📐 K-Fold Temporal Cross-Validation (k={k}):")
    print(f"     Totale: {total:,} candele")
    for i, (df_train, df_val) in enumerate(folds):
        n_train = len(df_train)
        n_val = len(df_val)
        train_start = df_train["datetime"].iloc[0] if n_train > 0 else pd.NaT
        train_end = df_train["datetime"].iloc[-1] if n_train > 0 else pd.NaT
        val_start = df_val["datetime"].iloc[0] if n_val > 0 else pd.NaT
        val_end = df_val["datetime"].iloc[-1] if n_val > 0 else pd.NaT
        print(f"     Fold {i+1}/{k}:")
        print(f"       TRAIN:      {n_train:>8,} ({n_train/total*100:.1f}%)")
        if not pd.isna(train_start):
            print(f"                 {train_start} → {train_end}")
        print(f"       VALIDATION: {n_val:>8,} ({n_val/total*100:.1f}%)")
        if not pd.isna(val_start):
            print(f"                 {val_start} → {val_end}")
