# Caso #12 — Fix Sliding Window GPU (binary search + forward scan)

## 🔍 Analisi del Problema

### Codice originale (ricerca lineare del lookback)

La ricerca della candela di riferimento (segnale momentum: confronto close attuale vs close di `y` secondi fa) e, nella variante a Y dinamico, del minimo nella finestra di lookback, era implementata con scansione lineare all'indietro per ogni candela: O(finestra) per candela, O(n·finestra) totale. Il codice attuale usa binary search sul confine finestra + scansione forward limitata alla finestra. Kernel CUDA a Y dinamico (`python-backtester/src/gpu/gpu_simulator.py`, linee 282-305):

```cuda
// DOPO: binary search sul confine + forward scan nella sola finestra
int lo_bs = 0;
int hi_bs = i;
while (lo_bs < hi_bs) {                       // O(log n)
    int mid_bs = (lo_bs + hi_bs) / 2;
    if (epoch_ms[mid_bs] < window_start_time) {
        lo_bs = mid_bs + 1;
    } else {
        hi_bs = mid_bs;
    }
}
int window_start_idx = lo_bs;

// Forward scan da window_start_idx a i-1 — O(finestra), non O(n)
for (int k = window_start_idx; k < i; k++) {
    if (close[k] < min_close_in_window) {
        min_close_in_window = close[k];
        min_close_idx = k;
    }
}
```

Lo stesso pattern è replicato nel fallback CPU Numba (`python-backtester/src/gpu/gpu_fallback.py`, linee 236-251). Il kernel statico usa binary search analoga per il lookback a Y fisso (`gpu_simulator.py` linee 88-99, `gpu_fallback.py` linee 67-76).

### Bug Identificati

1. **Complessità quadratica nel caso denso** — con scansione lineare all'indietro per ogni candela, il costo totale è O(n·finestra); su dati 1s densi con `y_max_window` grande (default 600s, ma configurabile a valori alti) lo screening di migliaia di combinazioni diventa impraticabile su GPU e CPU.
2. **Divergenza GPU/CPU** — il kernel CUDA e il fallback Numba devono produrre metriche identiche (array `(n_comb, 8)` / `(n_comb, 9)`); due implementazioni della ricerca con semantiche di confine diverse (`<=` vs `<`, inclusione dell'indice `i`) generano screening non riproducibili tra engine.
3. **Semantica di confine ambigua** — la ricerca lineare nascondeva la policy su timestamp duplicati al confine finestra; la binary search la rende esplicita (`< window_start_time` → il confine appartiene alla finestra, coerente con `_boundary_to_run_start` del caso #24).

### Analisi Approfondita delle Alternative

#### Soluzione A — Binary search sul confine + forward scan nella finestra (scelta)
- **Pro**: confine in O(log n); la scansione è limitata alla finestra (`y_max_window` limitato per costruzione, default 600 candele su dati 1s); identica semantica CUDA/Numba; nessuna struttura dati aggiuntiva sul device.
- **Contro**: il forward scan resta O(finestra) per candela — totale O(n·(log n + W)); con finestre molto grandi il termine W domina.

#### Soluzione B — Deque monotonica (minimo sliding in O(1) ammortizzato)
- **Pro**: totale O(n) anche con finestre enormi.
- **Contro**: stato mutabile per-thread su GPU (registri/shared memory), codice CUDA significativamente più complesso, difficile da mantenere identico tra CUDA e Numba; overkill per W ≤ qualche migliaio.

#### Soluzione C — Pre-calcolo host del minimo per candela (array ausiliario)
- **Pro**: kernel ridotto a O(1) per candela.
- **Contro**: trasferimenti H2D aggiuntivi, memoria device extra O(n), e va ricalcolato per ogni `y_max_window` — sposta il costo invece di ridurlo.

### Soluzione Scelta

**Soluzione A** — con finestre limitate (`Y_MAX_WINDOW`, validato `> 0` in `config.py` linea 274-275) il termine dominante resta piccolo e il codice resta speculare tra `_get_kernel_dynamic_y` (CUDA) e `_cpu_screen_batch_dynamic_y` (Numba `prange`), garantendo parità numerica GPU/CPU. Complessità risultante per candela: O(log n + W) con W limitato, contro O(n) della scansione ingenua.

### Impatto

- **Previene**: timeout di screening su dataset grandi, divergenza metriche tra engine GPU e fallback CPU, ambiguità sui timestamp duplicati al confine.
- **Rischio del cambiamento**: basso — a parità di semantica di confine il risultato è identico, cambia solo il costo; il rischio è concentrato sugli operatori di confronto (`<` vs `<=`), coperti da test di equivalenza.
- **Test richiesti**: equivalenza numerica binary-search vs scansione lineare su fixture con timestamp duplicati, gap temporali e `y_max_window` > n; parità bit-a-bit (a tolleranza float) tra `gpu_screen_combinations_dynamic_y` e `cpu_screen_combinations_dynamic_y`.
