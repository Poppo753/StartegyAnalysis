# Caso #25 — Profiler cProfile + tracemalloc (profiling.py)

## 🔍 Analisi del Problema

### Codice originale (solo wall-time)

Prima dell'intervento, la strumentazione si limitava a `Timer` (`src/utils/__init__.py`, linee 15-30: wall-time via `time.time()`) e a stampe sparse di elapsed nei runner: si sapeva *quanto* durava uno screening, mai *dove* andava il tempo né quanta memoria allocava. (Nota di precisione: il contenuto precedente di questo documento descriveva solo `Timer` — era incompleto e viene qui sostituito.) Il modulo reale è `python-backtester/src/profiling.py`, stdlib-only:

```python
# profiling.py, linee 42-81 e 134-166
class Profiler:
    def __init__(self, label="", top_n=15, track_memory=False,
                 enabled=None, min_print_seconds=0.0): ...
    def __enter__(self):                       # perf_counter + tracemalloc + cProfile.enable()
    def __exit__(self, ...): ...               # report top-N per cumtime e per tottime
    def report_dict(self) -> dict[str, Any]: ...   # label/elapsed/peak_mem/cprofile_enabled

def profile(_func=None, *, label=None, top_n=15,   # decoratore, uso bare o parametrico
            track_memory=False, enabled=None): ...
```

Uso: `with Profiler("screening", top_n=15, track_memory=True)`, `@profile` / `@profile(label="fast", top_n=10, track_memory=True)`, attivazione globale via `PROFILING=1` (`_profiling_enabled_by_default`, linee 38-39).

### Bug Identificati

1. **Diagnosi cieca oltre il wall-time** — `Timer` dice che `run_gpu_pipeline` impiega 120s ma non distingue screening CUDA vs filtri pandas vs I/O CSV; ogni ottimizzazione era un'ipotesi non verificata (es. ottimizzare i filtri quando il 95% è trasferimento H2D).
2. **Memoria non osservata** — picchi di allocazione (batch GPU/CPU da 2048 combinazioni, DataFrame trades top-N) causavano OOM killer senza alcuna misura pre-mortem; `track_memory` con `tracemalloc` registra il picco Python-allocator del blocco profilato (linee 93-97).
3. **Overhead del profiler nel path misurato** — `cProfile` sempre attivo distorce proprio ciò che misura e rallenta il path hot. `enabled=None → env PROFILING` (linea 65) più `min_print_seconds` danno tre modalità: spento (solo wall-time, overhead zero), report compatto, dettaglio funzioni — mai un costo occulto.

### Analisi Approfondita delle Alternative

#### Soluzione A — `Profiler` (cProfile + pstats + tracemalloc) + decoratore `@profile`, stdlib-only (scelta)
- **Pro**: nessuna dipendenza (niente in `pyproject.toml` da aggiungere); top-N per `cumtime` (dove va il tempo incluse le chiamate) e `tottime` (self, esclude le chiamate) distinguono colli veri da funzioni che delegano; `report_dict()` per uso machine-readable; `functools.wraps` preserva nome/docstring delle funzioni decorate.
- **Contro**: `cProfile` non vede dentro i kernel CUDA/Numba (tempo attribuito alla chiamata host — corretto ma grossolano); `tracemalloc` traccia solo l'allocatore Python, non la memoria device.

#### Soluzione B — Solo `Timer` wall-time
- **Pro**: overhead nullo, già esistente.
- **Contro**: nessuna attribuzione per-funzione né memoria — il problema che ha motivato il caso resta irrisolto. Resta comunque come strumento per misure stabili nel tempo (benchmark), complementare al Profiler.

#### Soluzione C — Profiler esterno (`py-spy`, `line_profiler`, `memray`)
- **Pro**: sampling senza overhead, line-level, memoria nativa.
- **Contro**: dipendenze binarie per un bisogno occasionale di sviluppo; `py-spy` richiede permessi di sistema; overkill finché i colli sono a grana di funzione.

### Soluzione Scelta

**Soluzione A** — `Timer` resta per il wall-time permanente nei runner; `Profiler`/`@profile` servono alle sessioni di ottimizzazione mirata (`PROFILING=1 python main.py`). Dettaglio di correttezza: se `tracemalloc` era già attivo fuori dal blocco, il Profiler non lo ferma in uscita (`_tracemalloc_started_here`, linee 71/96-97) — non ruba lo stato al chiamante.

### Impatto

- **Previene**: ottimizzazioni alla cieca, OOM senza misure, benchmark distorti dall'overhead di profilazione sempre attiva.
- **Rischio del cambiamento**: nullo a default — con `PROFILING` non impostato il Profiler misura solo wall-time; il path hot dei motori non è toccato.
- **Test richiesti**: blocco con `enabled=True` → report con sezioni cumtime/tottime; `enabled=False` → solo riga wall-time; `track_memory=True` → `peak_memory_mb > 0` su blocco che alloca e `report_dict()` coerente; decoratore bare e parametrico preservano `__name__` e valore di ritorno.
