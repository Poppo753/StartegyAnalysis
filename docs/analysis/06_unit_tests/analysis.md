# Caso #6 — Aggiungere Test Unitari

## 🔍 Analisi del Problema

### Stato Attuale
- **ZERO test unitari** in tutto il progetto
- Nessun file `.test.ts` o `.spec.ts`
- Nessun framework di test configurato
- Nessuna copertura di codice (0%)

### File da Testare (Priorità)

#### Priority 1 — Core Pipeline (altissimo impatto)
1. **`src/utils/rateLimiter.ts`** — `GlobalRateLimiter`, `delay`, `runWithConcurrency`
2. **`src/utils/dateUtils.ts`** — `dateToTimestampMs`, `floorToSecond`, `splitIntoDays`
3. **`src/config/config.ts`** — `loadConfig()`, validazione input
4. **`src/binance/types.ts`** — Type definitions

#### Priority 2 — Pipeline (alto impatto)
5. **`src/pipeline/ohlcAggregator.ts`** — `OHLCAggregator.fromArray()`, `fromStream()`
6. **`src/pipeline/aggregateStreaming.ts`** — Aggregazione streaming
7. **`src/pipeline/downloadAggTrades.ts`** — Download e merge
8. **`src/binance/binanceClient.ts`** — Retry logic

#### Priority 3 — Storage (medio impatto)
9. **`src/storage/jsonlWriter.ts`** — Write/read JSONL
10. **`src/storage/csvWriter.ts`** — Write CSV

#### Priority 4 — Python (medio impatto)
11. **`python-backtester/src/config.py`** — Validazione config
12. **`python-backtester/src/strategy.py`** — BacktestParams, Trade, BacktestResult
13. **`python-backtester/src/simulator.py`** — Logica di backtest
14. **`python-backtester/src/metrics.py`** — Metriche
15. **`python-backtester/src/parameter_grid.py`** — Griglia parametri
16. **`python-backtester/src/data_splitter.py`** — Split train/val

### Analisi Approfondita delle Alternative

#### Alternativa A — Jest (consigliata)
- Framework di test più popolare per TypeScript
- Supporto nativo per TypeScript, mocking, snapshot testing
- Ecosistema vastissimo (jest, @types/jest, ts-jest)
- **Pro**: Standard industriale, documentazione eccellente, facile da usare
- **Contro**: Configurazione iniziale più complessa

#### Alternativa B — Vitest
- Alternativa moderna a Jest, creato dal team di Vite
- Supporto nativo per TypeScript, ESM
- **Pro**: Più veloce di Jest, configurazione minima
- **Contro**: Meno maturo, meno plugin di terze parti

#### Alternativa C — Mocha + Chai
- Stack classico Node.js
- **Pro**: Molto flessibile
- **Contro**: Meno funzionalità out-of-the-box

#### Alternativa D — Solo test Python con pytest
- Per Python, pytest è lo standard
- **Pro**: Nessuna configurazione aggiuntiva
- **Contro**: Non copre il lato TypeScript

### Soluzione Scelta

**Jest** per TypeScript + **pytest** per Python — entrambi sono gli standard di settore.

### Impatto

- **Previene**: Regressioni, bug introdotti da modifiche future
- **Rischio**: Medio — richiede setup e scrittura di test
- **Tempo stimato**: 4-8 ore per setup + scrittura test essenziali
- **ROI**: Molto alto — ogni bug futuro trovato prima in produzione costa 10x di più da risolvere
