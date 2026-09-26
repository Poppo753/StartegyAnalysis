# Caso #20 — Creazione pyproject.toml

## 🔍 Analisi del Problema

### Codice originale (nessun manifest di progetto)

Prima dell'intervento, `python-backtester/` non aveva alcun manifest standard: dipendenze sparse in `requirements.txt`, nessuna dichiarazione di nome/versione/`requires-python`, nessuna configurazione del test runner versionata. Il file reale è `python-backtester/pyproject.toml`:

```toml
[project]
name = "python-backtester"
version = "0.1.0"
description = "A Python backtesting framework with GPU acceleration and temporal cross-validation"
requires-python = ">=3.10"
dependencies = [
    "pandas",
    "numpy",
    "python-dotenv",
    "numba",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["src.gpu"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = ["-v", "--tb=short"]
```

### Bug Identificati

1. **Dipendenze non dichiarate in formato standard** — senza `[project].dependencies`, l'installazione riproducibile (`pip install -e .`) è impossibile: ogni macchina ricostruisce l'ambiente a mano da `requirements.txt`, con rischio di versioni divergenti di `numba`/`cupy` che cambiano i risultati numerici dello screening.
2. **Interprete minimo non vincolato** — senza `requires-python = ">=3.10"`, l'esecuzione su Python 3.9 fallisce con errori di sintassi oscuri (`dict[str, object]`, `X | None`, `tomllib`-style) invece di un rifiuto dichiarativo all'installazione. Nota: `fast_metrics.py` usa `dict[str, object]` (builtin generics, 3.9+ a runtime con `from __future__` assente — di fatto richiede 3.10 come dichiarato).
3. **Configurazione pytest dispersa** — senza `[tool.pytest.ini_options]`, `testpaths`/`addopts` dipendono da flag CLI o `pytest.ini` separato; un `pytest` lanciato dalla root sbagliata raccoglie test di `.venv` (migliaia di file) invece di `tests/`.

### Analisi Approfondita delle Alternative

#### Soluzione A — `pyproject.toml` unico (PEP 517/518) (scelta)
- **Pro**: un solo file per metadati + dipendenze + build + tool-config; supportato da pip/setuptools/poetry; `pip install -e .` + `pytest` funzionano out-of-the-box.
- **Contro**: la voce `packages = ["src.gpu"]` riflette un layout non standard (manca `src.fast`, `src.utils` nel packaging) — da allineare se il progetto verrà distribuito come wheel; oggi l'uso è via `sys.path`, quindi nessun effetto operativo.

#### Soluzione B — Solo `requirements.txt` + `setup.py`
- **Pro**: formato noto, nessuna migrazione.
- **Contro**: `setup.py` è legacy (esecuzione arbitraria all'installazione), nessuna sezione standard per i tool, due file da tenere sincronizzati.

#### Soluzione C — Poetry (`poetry.lock` + `pyproject` Poetry)
- **Pro**: lockfile deterministico delle transitive.
- **Contro**: toolchain aggiuntiva per un progetto interno single-env; il lock di `cupy` (variante CUDA-specifica) crea più problemi di quanti ne risolva.

### Soluzione Scelta

**Soluzione A** — `pyproject.toml` con backend `setuptools.build_meta` minimizza il delta (nessuna migrazione di codice), fissa `requires-python >= 3.10` coerente con la sintassi usata, e àncora pytest a `tests/` con output `-v --tb=short`. (Nota di precisione: documentazioni precedenti riportavano `setuptools.backends._legacy:_Backend` — il file reale usa `setuptools.build_meta`.)

### Impatto

- **Previene**: ambienti non riproducibili, esecuzioni su interpreti incompatibili, collection pytest sulla `.venv`.
- **Rischio del cambiamento**: basso — nessun effetto sul codice; unico punto di attenzione è `packages = ["src.gpu"]`, incompleto per un futuro packaging ma ininfluente sull'uso corrente via `sys.path`.
- **Test richiesti**: `pip install -e .` in venv pulita Python 3.10 → import `src.*` ok; `pytest` senza argomenti raccoglie solo `tests/`; `pip install` su Python 3.9 rifiutato dal marker `requires-python`.
