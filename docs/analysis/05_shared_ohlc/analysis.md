# Caso #5 — Estrarre Logica OHLC Condivisa

## 🔍 Analisi del Problema

### Duplicazione Identificata

La logica di aggregazione OHLC è copiata/incollata in **4 file**:

1. **`src/pipeline/aggregateStreaming.ts`** — `aggregateFileToOhlc1s()`
2. **`src/extractRange.ts`** — `main()` (blocchi `currentSecond`, `bucketOpen`, etc.)
3. **`src/pipeline/aggregateToOhlc.ts`** — `aggregateToOhlc1s()`
4. **`src/storage/csvWriter.ts`** — `formatNumber()` / `writeOhlcCsv()`

### Codice Duplicato (esempio dalla aggregateStreaming.ts e extractRange.ts)

Entrambi i file hanno:
```typescript
let currentSecond: number | null = null;
let bucketOpen = 0;
let bucketHigh = -Infinity;
let bucketLow = Infinity;
let bucketClose = 0;
let bucketVolume = 0;
let bucketTradeCount = 0;
// ... identica logica di bucketing ...
function fmt(value: number): string {
  return value.toFixed(10).replace(/\.?0+$/, '');
}
```

### Problemi

#### Problema 1: Manutenibilità
- Ogni fix o miglioramento all'aggregazione deve essere applicato a 4 file diversi
- Alto rischio di introdurre bug (dimenticare di aggiornare un file)

#### Problema 2: Inconsistenza
- `aggregateStreaming.ts` usa `trade.T > 9_999_999_999_999` per timestamp normalization
- `extractRange.ts` usa la stessa logica ma in modo diverso
- `aggregateToOhlc.ts` non ha la normalizzazione timestamp (si aspetta dati già normalizzati)
- **Rischio**: diverso comportamento se una modifica in un file non è riflessa negli altri

#### Problema 3: `aggregateToOhlc.ts` è codice morto
- `aggregateToOhlc1s()` accetta un array in memoria (`BinanceAggTrade[]`)
- Non viene mai chiamato dalla pipeline (che usa `aggregateFileToOhlc1s()`)
- Dovrebbe essere rimosso o reintegrato

### Analisi Approfondita delle Alternative

#### Soluzione A — Modulo condiviso `ohlcAggregator.ts` (consigliata)
```typescript
// src/pipeline/ohlcAggregator.ts
export interface OHLCBucket { ... }
export class OHLCAggregator { ... }
```
- **Pro**: Singola fonte di verità, type-safe, facilmente testabile
- **Contro**: Richiede rifattorizzazione di tutti i caller

#### Soluzione B — Classe OHLCAggregator con streaming e non-streaming
```typescript
export class OHLCAggregator {
  // Streaming: per file grandi
  static async fromStream(inputPath, outputPath): Promise<number>
  // Non-streaming: per array in memoria
  static fromArray(trades: BinanceAggTrade[]): OhlcCandle[]
}
```
- **Pro**: Copre tutti i casi d'uso, API pulita
- **Contro**: Richiede un po' di lavoro di rifattorizzazione

#### Soluzione C — Solo estrazione fmt/toFixed condiviso
- Mole minima, solo il formatting
- **Pro**: Cambio minimo
- **Contro**: Non risolve la duplicazione della logica di bucketing

### Soluzione Scelta

**Soluzione B** — Classe `OHLCAggregator` che copre entrambi i casi (streaming e array):
1. Nuovo file `src/pipeline/ohlcAggregator.ts` con la classe condivisa
2. `aggregateStreaming.ts` usa `OHLCAggregator.fromStream()`
3. `extractRange.ts` usa `OHLCAggregator.fromStream()`
4. `aggregateToOhlc.ts` usa `OHLCAggregator.fromArray()`
5. Rimozione della duplicazione

### Impatto

- **Previene**: Bug di inconsistenza, difficoltà di manutenzione
- **Rischio**: Medio — rifattorizzazione di 3 file
- **Test**: Verificare che l'output sia identico ai risultati precedenti
