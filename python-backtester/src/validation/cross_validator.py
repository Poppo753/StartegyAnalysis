"""cross_validator.py - Purged K-Fold temporale (Fase 3, F3-V02).

Riusa la logica di confine datetime di src/gpu/data_splitter
(`_boundary_to_run_start`) invece di duplicarla: timestamp identici non
vengono mai divisi tra train e test (i duplicati vanno nel test).

Protocollo:
- K split temporali contigui (default K=5), nessun shuffle.
- Purging: si rimuove dal train ogni osservazione i la cui label
  [i, i+horizon) tocca il test [test_start, test_end), cioe`
  i < test_end and i + horizon > test_start.
- Embargo: si rimuove dal train anche la finestra
  [test_end, test_end + int(n * embargo_pct)).

API: split(X, y=None, horizon=1) -> generator di (train_idx, test_idx)
come array numpy ordinati. X puo` essere un DataFrame (con o senza
colonna 'datetime'), una Series, un ndarray o una lista; conta solo
len(X) e l'ordine temporale (riga 0 = piu` vecchia).
"""

from typing import Generator, List, Optional, Tuple

import itertools
import logging
import math

import numpy as np
import pandas as pd

try:
    from src.gpu.data_splitter import _boundary_to_run_start
except Exception:  # pragma: no cover - fallback se il modulo gpu manca
    def _boundary_to_run_start(datetimes, idx: int) -> int:  # type: ignore[misc]
        n = len(datetimes)
        if idx <= 0 or idx >= n:
            return max(0, min(int(idx), int(n)))
        boundary_ts = datetimes.iloc[idx]
        while idx > 0 and datetimes.iloc[idx - 1] == boundary_ts:
            idx -= 1
        return int(idx)


class PurgedKFold:
    """K-Fold temporale con purging ed embargo (F3-V02).

    Args:
        n_splits: numero di split temporali (default 5 da checklist).
        embargo_pct: frazione del dataset esclusa dopo ogni test come
            embargo (default 0.01 = 1%, dentro il range 1-5% da checklist).
    """

    def __init__(self, n_splits: int = 5, embargo_pct: float = 0.01) -> None:
        if int(n_splits) < 2:
            raise ValueError(f"n_splits must be >= 2, got {n_splits}")
        embargo_pct = float(embargo_pct)
        if not 0.0 <= embargo_pct < 1.0:
            raise ValueError(f"embargo_pct must be in [0, 1), got {embargo_pct}")
        self.n_splits = int(n_splits)
        self.embargo_pct = embargo_pct

    def get_n_splits(self) -> int:
        """Numero di split (K)."""
        return self.n_splits

    def _datetimes_of(self, X) -> Optional[pd.Series]:
        if isinstance(X, pd.DataFrame) and "datetime" in X.columns:
            col = X["datetime"]
            try:
                if pd.api.types.is_datetime64_any_dtype(col):
                    return col.reset_index(drop=True)
            except Exception:
                return None
        return None

    def split(
        self,
        X,
        y=None,
        horizon: int = 1,
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """Genera (train_idx, test_idx) per K split temporali.

        Args:
            X: dati in ordine temporale (len = n). Se DataFrame con colonna
                'datetime' datetime64, i confini vengono aggiustati con
                `_boundary_to_run_start` (riuso data_splitter).
            y: ignorato (compatibilita` API sklearn), puo` essere None.
            horizon: ampiezza label in barre. La label di i copre
                [i, i+horizon). horizon=0 disattiva il purging.

        Yields:
            tuple (train_idx, test_idx) come np.ndarray ordinati.
        """
        horizon = int(horizon)
        if horizon < 0:
            raise ValueError(f"horizon must be >= 0, got {horizon}")
        n = len(X)
        if n < self.n_splits:
            raise ValueError(f"Not enough samples ({n}) for n_splits={self.n_splits}")
        datetimes = self._datetimes_of(X)

        # Confini dei blocchi contigui (gestisce il resto di n // K).
        bounds = [(i * n) // self.n_splits for i in range(self.n_splits + 1)]

        embargo_len = int(n * self.embargo_pct)

        for k in range(self.n_splits):
            test_start, test_end = int(bounds[k]), int(bounds[k + 1])
            if datetimes is not None:
                test_start = int(_boundary_to_run_start(datetimes, test_start))
                if test_end < n:
                    test_end = int(_boundary_to_run_start(datetimes, test_end))
                else:
                    test_end = int(n)
            if test_end <= test_start:
                raise ValueError(
                    f"PurgedKFold: split {k + 1}/{self.n_splits} vuoto dopo "
                    f"anti-leakage adjustment (start={test_start}, end={test_end}, n={n})."
                )
            test_idx = np.arange(test_start, test_end, dtype=int)

            embargo_end = min(n, test_end + embargo_len)
            train_mask = np.ones(n, dtype=bool)
            train_mask[test_start:test_end] = False
            if embargo_end > test_end:
                train_mask[test_end:embargo_end] = False
            if horizon > 0:
                # Purge: label [i, i+horizon) che tocca [test_start, test_end).
                lo = max(0, test_start - horizon)
                # Solo i < test_start possono essere nel train qui (il test
                # e` gia` escluso), ma il controllo esaustivo sotto copre tutto.
                purge_idx = np.arange(lo, test_start, dtype=int)
                train_mask[purge_idx] = False

            train_idx = np.flatnonzero(train_mask)
            yield train_idx, test_idx


logger = logging.getLogger(__name__)

# Default conservativi (F3-V03, punto D-1 differito per design):
# enumerazione completa solo sotto soglia, altrimenti campionamento
# stratificato con seed fisso. Mai bloccare in attesa di decisioni.
DEFAULT_CPCV_MAX_PATHS = 5000
DEFAULT_CPCV_SEED = 42


def calculate_pbo(path_performances) -> float:
    """PBO operativo v3: frazione di percorsi con performance negativa.

    PBO = n_negativi / n_totali, con negativo = performance OOS < 0
    (cfr. masterplan v3 §5.6-nota-v3: PBO = n_percorsi_con_PnL_negativo /
    n_percorsi_totali da CPCV).

    Args:
        path_performances: 1-D array-like di PnL/Sharpe OOS per percorso.

    Returns:
        float in [0, 1] (frazione, NON percentuale).
    """
    arr = np.asarray(list(path_performances), dtype=float).ravel()
    if arr.size == 0:
        raise ValueError("calculate_pbo: path_performances vuoto")
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        raise ValueError("calculate_pbo: nessuna performance finita")
    return float(np.sum(finite < 0.0) / finite.size)


def evaluate_pbo(pbo: float, n_trials=None) -> dict:
    """Semaforo decisionale v3 sul PBO (CHG-005, F3-V03/V04).

    DISCLAIMER (checklist §6, masterplan v3 §7.3-nota-v3): le soglie
    <10 / 10-50 / >50 sono regole empiriche calibrate sull'esperienza
    dei desk quantitativi, NON teoremi. Non esiste una dimostrazione che
    10% sia il confine della solidita`: vanno usate come semaforo
    operativo, non come verdetto matematico. I confini sono morbidi per
    l'operatore (nota entro ±2pp), deterministici per il codice.

    Unita` accettate (documentato, per riconciliare masterplan e DoD):
    frazione 0-1 (masterplan §7.3: 0.10/0.50) oppure percentuale 0-100
    (DoD F3-V04: 9.9/10.1/49.9/50.1). Se pbo > 1 si intende percentuale,
    altrimenti frazione. Il PBO cresce con N_trials (trabocchetto v3):
    N_trials e` sempre loggato accanto al PBO, mai da solo.

    Mapping (deterministico): <10 SOLID→ACCEPT; 10-50
    POTENTIALLY_VALID→WALK_FORWARD_HOLDOUT; >50 OVERFITTED→REJECT.
    """
    pbo = float(pbo)
    if pbo < 0:
        raise ValueError(f"evaluate_pbo: pbo negativo ({pbo})")
    pbo_percent = pbo * 100.0 if pbo <= 1.0 else float(pbo)
    if pbo_percent > 100.0:
        raise ValueError(f"evaluate_pbo: pbo fuori scala ({pbo})")
    if pbo_percent < 10.0:
        verdict, action = "SOLID", "ACCEPT"
        reason = "PBO < 10%: quasi certamente non overfitted"
    elif pbo_percent <= 50.0:
        verdict, action = "POTENTIALLY_VALID", "WALK_FORWARD_HOLDOUT"
        reason = "PBO 10-50%: walk-forward + holdout obbligatori prima di decidere"
    else:
        verdict, action = "OVERFITTED", "REJECT"
        reason = "PBO > 50%: probabilmente overfitted"
    near = min(abs(pbo_percent - 10.0), abs(pbo_percent - 50.0)) <= 2.0
    boundary_note = (
        "Valore entro ±2pp dai confini (10/50): trattare come fascia gialla "
        "a prescindere dal verdetto deterministico (confini morbidi per l'operatore)."
        if near else ""
    )
    log_line = (
        f"PBO={pbo_percent:.2f}% | N_trials={n_trials if n_trials is not None else 'unknown'} "
        f"| verdict={verdict} action={action}"
        + (f" | NOTE: {boundary_note}" if boundary_note else "")
    )
    logger.info(log_line)
    return {
        "pbo_percent": float(pbo_percent),
        "pbo_fraction": float(pbo_percent / 100.0),
        "verdict": verdict,
        "action": action,
        "reason": reason,
        "n_trials": n_trials,
        "boundary_note": boundary_note,
        "log_line": log_line,
    }


class CombinatorialPurgedCV:
    """CPCV con purging/embargo + cap pratico (F3-V03).

    Partiziona in N gruppi contigui; ogni split usa n_test_groups gruppi
    come test (tutte le C(N, n_test) combinazioni), train = resto con
    purging (label che toccano un qualsiasi intervallo di test) ed embargo
    dopo ogni intervallo di test. I percorsi (paths) sono insiemi di split
    i cui test partizionano tutti gli N gruppi esattamente una volta
    (copertura OOS completa); il conteggio di riferimento C(N-1,K-1) e`
    citato dal masterplan v3 §5.6 per la costruzione sequenziale — il
    conteggio effettivo enumerato e` riportato da `n_paths_theoretical`.

    Default conservativi (D-1 differito): max_paths=5000, seed=42.
    Sotto soglia: enumerazione completa. Sopra soglia: campionamento
    stratificato (per primo split del percorso) con seed fisso.
    """

    def __init__(
        self,
        n_partitions: int = 6,
        n_test_groups: int = 2,
        max_paths: int = DEFAULT_CPCV_MAX_PATHS,
        seed: int = DEFAULT_CPCV_SEED,
        embargo_pct: float = 0.01,
    ) -> None:
        if int(n_partitions) < 3:
            raise ValueError(f"n_partitions must be >= 3, got {n_partitions}")
        if not 1 <= int(n_test_groups) < int(n_partitions):
            raise ValueError(
                f"n_test_groups must be in [1, n_partitions), got {n_test_groups}"
            )
        if int(max_paths) <= 0:
            raise ValueError(f"max_paths must be > 0, got {max_paths}")
        embargo_pct = float(embargo_pct)
        if not 0.0 <= embargo_pct < 1.0:
            raise ValueError(f"embargo_pct must be in [0, 1), got {embargo_pct}")
        self.n_partitions = int(n_partitions)
        self.n_test_groups = int(n_test_groups)
        self.max_paths = int(max_paths)
        self.seed = int(seed)
        self.embargo_pct = embargo_pct

    def _bounds(self, n: int) -> List[int]:
        N = self.n_partitions
        return [(i * n) // N for i in range(N + 1)]

    def test_group_combos(self) -> List[Tuple[int, ...]]:
        """Tutte le C(N, n_test) combinazioni di gruppi di test."""
        return list(
            itertools.combinations(range(self.n_partitions), self.n_test_groups)
        )

    def splits(self, n: int, horizon: int = 1) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Tutti gli split (train_idx, test_idx) con purging + embargo."""
        horizon = int(horizon)
        if horizon < 0:
            raise ValueError(f"horizon must be >= 0, got {horizon}")
        if n < self.n_partitions:
            raise ValueError(f"Not enough samples ({n}) for {self.n_partitions} partitions")
        bounds = self._bounds(n)
        embargo_len = int(n * self.embargo_pct)
        out: List[Tuple[np.ndarray, np.ndarray]] = []
        for combo in self.test_group_combos():
            intervals = [(bounds[g], bounds[g + 1]) for g in combo]
            test_idx = np.concatenate(
                [np.arange(s, e, dtype=int) for s, e in intervals]
            )
            mask = np.ones(n, dtype=bool)
            mask[test_idx] = False
            for s, e in intervals:
                embargo_end = min(n, e + embargo_len)
                if embargo_end > e:
                    mask[e:embargo_end] = False
                if horizon > 0:
                    lo = max(0, s - horizon)
                    mask[lo:s] = False
            out.append((np.flatnonzero(mask), np.sort(test_idx)))
        return out

    def n_paths_theoretical(self) -> int:
        """Conteggio dei percorsi full-coverage (partizioni in chunk uguali).

        Richiede N % n_test == 0; altrimenti i percorsi full-coverage non
        esistono e vale 0 (usare gli split singoli come percorsi).
        """
        N, k = self.n_partitions, self.n_test_groups
        if N % k != 0:
            return 0
        # N! / ((k!)^(N/k) * (N/k)!)
        return math.factorial(N) // (
            (math.factorial(k) ** (N // k)) * math.factorial(N // k)
        )

    def _enumerate_partitions(self, groups: List[int]) -> Generator[List[Tuple[int, ...]], None, None]:
        k = self.n_test_groups
        if not groups:
            yield []
            return
        first, rest = groups[0], groups[1:]
        for combo in itertools.combinations(rest, k - 1):
            chunk = (first,) + tuple(combo)
            remaining = [g for g in rest if g not in combo]
            for tail in self._enumerate_partitions(remaining):
                yield [chunk] + tail

    def get_paths(self, n: int, horizon: int = 1) -> List[List[int]]:
        """Percorsi come liste di indici di split (copertura OOS completa).

        Ogni percorso copre tutti gli N gruppi esattamente una volta nel
        test. Se N % n_test != 0 oppure l'enumerazione supera la soglia
        pratica, si usa il fallback documentato (split singoli o
        campionamento); il campionamento e` stratificato per primo split
        con seed fisso e quindi deterministico.
        """
        combos = self.test_group_combos()
        split_index = {frozenset(c): i for i, c in enumerate(combos)}
        theory = self.n_paths_theoretical()
        rng = np.random.default_rng(self.seed)

        if theory == 0:
            # N non divisibile: percorsi ≡ split singoli (documentato).
            return [[i] for i in range(len(combos))]

        if theory <= max(self.max_paths, 100000):
            paths: List[List[int]] = []
            for part in self._enumerate_partitions(list(range(self.n_partitions))):
                paths.append([split_index[frozenset(chunk)] for chunk in part])
            if len(paths) <= self.max_paths:
                return paths
            return self._stratified_sample(paths, self.max_paths, rng)

        # Enumerazione impraticabile: costruzione randomizzata con seed.
        seen, out, attempts = set(), [], 0
        while len(out) < self.max_paths and attempts < self.max_paths * 20:
            attempts += 1
            perm = list(rng.permutation(self.n_partitions))
            part = [
                frozenset(perm[i:i + self.n_test_groups])
                for i in range(0, self.n_partitions, self.n_test_groups)
            ]
            key = tuple(sorted(tuple(sorted(p)) for p in part))
            if key in seen:
                continue
            seen.add(key)
            out.append([split_index[p] for p in part])
        return out

    @staticmethod
    def _stratified_sample(paths: List[List[int]], m: int, rng) -> List[List[int]]:
        strata: dict = {}
        for p in paths:
            strata.setdefault(p[0], []).append(p)
        for v in strata.values():
            rng.shuffle(v)
        out: List[List[int]] = []
        keys = sorted(strata)
        i = 0
        while len(out) < m:
            added = False
            for k in keys:
                if i < len(strata[k]) and len(out) < m:
                    out.append(strata[k][i])
                    added = True
            if not added:
                break
            i += 1
        return out

    def split_oos_pnl(
        self,
        returns,
        signals,
        cost: float = 0.0,
        horizon: int = 1,
    ) -> np.ndarray:
        """PnL OOS per split (test-only): sum(signals*returns - cost).

        Args:
            returns: array-like dei rendimenti per barra.
            signals: array-like delle posizioni (-1/0/+1) allineate.
            cost: costo per barra con posizione aperta (|signal| > 0).
            horizon: passato agli split (purging/embargo del train; il PnL
                OOS usa solo il test, quindi horizon non lo altera).

        Returns:
            np.ndarray con un PnL OOS per split.
        """
        r = np.asarray(returns, dtype=float).ravel()
        s = np.asarray(signals, dtype=float).ravel()
        if r.shape != s.shape:
            raise ValueError("returns e signals devono avere stessa lunghezza")
        n = r.size
        per_bar = s * r - float(cost) * (np.abs(s) > 0).astype(float)
        return np.array(
            [float(np.sum(per_bar[test])) for _, test in self.splits(n, horizon)],
            dtype=float,
        )
