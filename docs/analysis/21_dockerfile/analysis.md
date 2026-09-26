# Caso #21 — Dockerfile per ambiente riproducibile

## 🔍 Analisi del Problema

### Codice originale (assenza)
Nessun `Dockerfile` presente: build dipendenti da Node/Python locali,
versioni non pinnate a runtime, `data/` e `.env` mescolati con il codice.

### Bug Identificati
1. **Non-riproducibilità**: `npm ci` vs `npm install`, versioni Node/Python diverse tra macchine.
2. **Dev-dipendenze nel runtime**: immagine gonfia e superficie d'attacco maggiore.
3. **Dati nel layer**: rischio di includere GB di `data/` nell'immagine.
4. **GPU ambigua**: CuPy/CUDA richiedono base image diversa dalla CPU.

### Analisi Approfondita delle Alternative
#### Soluzione A — Un solo Dockerfile con tutto (node+python)
- **Pro**: una sola immagine.
- **Contro**: immagine enorme, versioni accoppiate, anti-pattern un-processo-per-container.

#### Soluzione B — Due Dockerfile minimali + .dockerignore (scelta)
- **Pro**: stage separati, immagini slim, `data/` come volume, `.env` montato a runtime.
- **Contro**: due build invece di una (accettabile).

#### Soluzione C — docker-compose orchestrator
- **Pro**: una riga per pipeline+backtest.
- **Contro**: overkill ora; aggiungibile dopo senza cambiare i Dockerfile.

### Soluzione Scelta
**Soluzione B**:
- `Dockerfile` (root): multi-stage `node:20-slim` build → runtime `--omit=dev`, `VOLUME /app/data`, `CMD node dist/index.js`.
- `python-backtester/Dockerfile`: `python:3.10-slim`, `requirements.txt` fissi, nota CUDA/CuPy come commento operativo.
- `.dockerignore`: esclude `node_modules`, `dist`, `data/`, `.venv`, `.env`.

### Impatto
- **Previene**: "funziona sulla mia macchina", immagini gonfie, leak di dati/secret nei layer.
- **Rischio del cambiamento**: Basso — nessun codice toccato; verificare `docker build` su CI.
- **Test richiesti**: `docker build` di entrambe le immagini; `docker run --env-file` con volume `data/`.
