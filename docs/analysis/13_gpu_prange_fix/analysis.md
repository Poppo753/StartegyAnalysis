# Caso #13 — Fix Thread-Safety prange + Warmup Numba

## 🔍 Analisi del Problema

### Codice originale (parallelismo Numba e compilazione JIT alla prima chiamata)

Il fallback CPU (`python-backtester/src/gpu/gpu_fallback.py`, linea 21) parallelizza lo screening con `@njit(cache=True, parallel=True)` e `prange`; ogni thread scrive esclusivamente la propria riga di output (linee 172-180, replicate in 343-351 per la variante a Y dinamico):

```python
# gpu_fallback.py, linee 47 e 172-180
for tid in prange(n_combinations):   # un thread per combinazione
    ...
    total_trades += 1                # accumulatori = scalari locali al thread
    ...
    # DOPO il loop: scrittura disgiunta, unica garanzia di thread-safety
    results[tid, 0] = float(total_trades)
    results[tid, 1] = float(winning_trades)
    ...
    results[tid, 6] = best_trade if total_trades > 0 else 0.0
    results[tid, 7] = worst_trade if total_trades > 0 else 0.0
```

Il warmup JIT è in `python-backtester/src/fast/fast_runner.py` (`_warmup_numba`, linee 173-202) con guardia sui dataset piccoli:

```python
# fast_runner.py, linee 185-188
if len(close) < 100:
    return
n_warmup = min(100, len(close))
_simulate_single(epoch_ms[:n_warmup], close[:n_warmup], ...)
```

### Bug Identificati

1. **Race condition potenziale su `results`** — con `parallel=True`, qualsiasi scrittura su righe diverse da `results[tid]` (o su accumulatori condivisi) introdurrebbe data race non deterministici: screening diversi a parità di input. Il design attuale lo previene per costruzione: accumulatori sempre scalari locali, unica scrittura su `results[tid, ...]` a thread concluso.
2. **First-run penalty JIT nei benchmark** — la prima chiamata a `_simulate_single`/`_cpu_screen_batch` include la compilazione Numba (secondi/minuti), falsando le misurazioni di `run_fast_backtest` se il tempo di compilazione finisce dentro il batch misurato. Il warmup esplicito (linee 72-77, con stampa del tempo) separa compilazione da esecuzione.
3. **Warmup non guardato su dataset piccoli** — senza `if len(close) < 100: return`, il warmup su < 100 candele affetterebbe array degeneri e userebbe `config.x_values[0]`/`y_values[0]` senza verificarne la presenza, rischiando `IndexError` prima ancora del backtest reale. La guardia rende il warmup un no-op sicuro.

### Analisi Approfondita delle Alternative

#### Soluzione A — Scritture disgiunte `results[tid]` + warmup con guardia (scelta)
- **Pro**: thread-safety per costruzione (nessun lock, nessun overhead); warmup trasparente (tempo stampato) e sicuro su dataset piccoli; `cache=True` riusa la compilazione tra run.
- **Contro**: la disciplina "solo `results[tid]`" è convenzionale, non enforcement del compilatore — va preservata in review.

#### Soluzione B — Lock / sezione critica per le scritture
- **Pro**: tollera scritture condivise.
- **Contro**: serializza i thread proprio sul collo di bottiglia, annullando il beneficio di `prange`; inutile dato che le righe sono per costruzione disgiunte.

#### Soluzione C — Warmup incondizionato senza guardia
- **Pro**: codice più corto.
- **Contro**: crash/`IndexError` su dataset di test piccoli; warmup che fallisce lascia il primo batch reale con la penalty JIT — il problema che si voleva risolvere.

### Soluzione Scelta

**Soluzione A** — la combinazione di (a) accumulatori thread-local + scrittura finale su sola riga `tid` e (b) warmup su slice di 100 candele con early-return sotto soglia risolve entrambi i problemi senza lock né dipendenze: il primo batch misurato è già compilato e i risultati sono deterministici tra run.

### Impatto

- **Previene**: risultati non deterministici da data race, benchmark falsati dalla compilazione JIT, crash del warmup su dataset < 100 candele.
- **Rischio del cambiamento**: basso — il warmup non altera i risultati numerici (usa solo i primi valori della griglia su dati reali ma scartati); la disciplina di scrittura è già applicata in entrambe le varianti (`_cpu_screen_batch`, `_cpu_screen_batch_dynamic_y`).
- **Test richiesti**: doppio run sullo stesso input con `parallel=True` → output bit-identici; dataset di 50 candele → nessun errore dal warmup; log del warmup presente e separato dal tempo di batch.

## 🔧 Addendum audit — `fast_simulator.py` (stessa famiglia di bug)

Durante la ri-analisi sono emersi tre difetti gemelli nel motore fast,
non coperti dal fix originario di `gpu_fallback.py`:

1. **`_simulate_single` allocava 12 colonne ma ne scriveva 10** (`np.empty((max_trades, 12))`, scritture solo `0-9`): le colonne 10-11 restavano spazzatura non inizializzata. Poiché `gpu_runner.py` rileva la modalità dynamic-Y con `shape[1] > 10`, un risultato classic a 12 colonne veniva scambiato per dynamic — `avg_y_actual` calcolato su garbage e scritto nei CSV. Fix: allocazione a 10 colonne; il dynamic-Y resta a 11 (0-10 con `y_actual_s` reale).
2. **`_simulate_single_dynamic_y` aveva ancora il loop O(n²)** (`k = i-1; while k >= 0: ... k -= 1`): sostituito con la stessa binary-search + forward scan di `gpu_fallback` (O(log n + W) per candela).
3. **Docstring falsa su colonne MAE/MFE** (`[10] mae_pct / [11] mfe_pct` mai scritte): rimossa; MAE/MFE sono derivati in `fast_metrics.py` da entry/max/min (direction-aware, clipped ≥ 0).
4. **`check_numba_available()` faceva `sys.exit(1)`** in codice libreria: ora solleva `NumbaMissingError(RuntimeError)`; il catch + exit vive solo al boundary CLI (`main.run_fast_engine` / `run_gpu_engine`).

Regression test: `tests/test_fast_simulator_shapes.py` (width 10/11, `y_actual ≥ 0`, `NumbaMissingError ⊂ RuntimeError) — 3 passed.
