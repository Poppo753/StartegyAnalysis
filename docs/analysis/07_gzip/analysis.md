# Caso #7 — Aggiungere Compressione Gzip

## 🔍 Analisi del Problema

### Contesto

I file JSONL generati dalla pipeline possono essere molto grandi:
- BTCUSDT: ~500MB-2GB per un mese di dati
- ETHUSDT: ~300MB-1GB per un mese di dati

Questi file occupano molto spazio su disco e richiedono molto tempo per essere scaricati/scaricati via rete.

### Analisi Costi/Benefici

| Aspetto | Senza gzip | Con gzip |
|---------|-----------|----------|
| Dimensione file | 500MB-2GB | 50-200MB (80% riduzione) |
| Tempo download | ~10 minuti | ~2-3 minuti |
| Spazio su disco | Alto | Basso |
| Tempo decompressione | 0 | ~1-3 secondi |
| Tempo lettura streaming | Lento | Leggermente più lento |

### Codice da Modificare

1. **`src/storage/jsonlWriter.ts`** — Scrivere in .jsonl.gz
2. **`src/pipeline/downloadAggTrades.ts`** — Leggere .jsonl.gz
3. **`src/pipeline/aggregateStreaming.ts`** — Leggere .jsonl.gz
4. **`src/extractRange.ts`** — Leggere .jsonl.gz
5. **`src/storage/csvWriter.ts`** — Opzionale: comprimere CSV

### Analisi Approfondita delle Alternative

#### Alternativa A — Gzip per file JSONL (consigliata)
- Compressione con level 6 (buon compromesso velocità/compressione)
- Estensione `.jsonl.gz`
- **Pro**: Standard, ampiamente supportato, 80% risparmio
- **Contro**: Leggero overhead CPU

#### Alternativa B — Zstandard (zstd)
- Migliore compressione di gzip, decompressione più veloce
- **Pro**: ~20% migliore compressione di gzip
- **Contro**: Non disponibile nativamente in Node.js (richiede `zstandard` package)

#### Alternativa C — Brotli
- Compressione migliore di gzip
- **Pro**: Usato da HTTP/2, buona compressione
- **Contro**: Non nativo in Node.js per file generici

#### Alternativa D — Nessuna compressione (stato attuale)
- **Pro**: Zero overhead
- **Contro**: Spazio e tempo di download elevati

### Soluzione Scelta

**Alternativa A (gzip)** — Migliore compromesso. Nativo in Node.js (`zlib`), nessuna dipendenza aggiuntiva, buon rapporto compressione/velocità.

### Impatto

- **Previene**: Spreco di spazio su disco, tempi di download lunghi
- **Rischio**: Basso — gzip è standard, supportato nativamente
- **Test**: Verificare che la pipeline funzioni con file .jsonl.gz
