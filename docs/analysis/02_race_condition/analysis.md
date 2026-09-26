# Caso #2 — Fix Race Condition nel Merge (downloadAggTrades.ts)

## 🔍 Analisi del Problema

### Contesto

La funzione `downloadAggTrades()` in `src/pipeline/downloadAggTrades.ts` esegue il download di più giorni di dati in parallelo, scrive ogni giorno in un file JSONL separato (`aggTrades_YYYY-MM-DD.jsonl`), e poi li unisce in un unico file finale (`aggTrades_START_END.jsonl`).

### Codice originale (mergeDayFiles, linee 191-227)

```typescript
async function mergeDayFiles(
  dayResults: Array<{ dayFilePath: string; start: string; trades: number }>,
  finalFilePath: string
): Promise<number> {
  const dir = path.dirname(finalFilePath);
  fs.mkdirSync(dir, { recursive: true });

  const sorted = [...dayResults].sort((a, b) => a.start.localeCompare(b.start));
  let totalTrades = 0;
  let isFirst = true;

  for (const day of sorted) {
    if (day.trades === 0) continue;
    if (!fs.existsSync(day.dayFilePath)) continue;

    const content = fs.readFileSync(day.dayFilePath, 'utf-8');

    if (isFirst) {
      fs.writeFileSync(finalFilePath, content, 'utf-8');
      isFirst = false;
    } else {
      fs.appendFileSync(finalFilePath, content, 'utf-8');
    }

    totalTrades += day.trades;
    if (day.dayFilePath !== finalFilePath) {
      fs.unlinkSync(day.dayFilePath);
    }
  }
  return totalTrades;
}
```

### Bug Identificati

#### Bug 1: Lettura sincrona di file potenzialmente grandi
- `fs.readFileSync()` carica l'intero contenuto del file in memoria
- Per giorni con milioni di trade (es. BTCUSDT), ogni file JSONL può essere **500MB+**
- Se `mergeDayFiles()` viene chiamato mentre i download sono ancora in corso (race condition), il file potrebbe essere corrotto

#### Bug 2: `appendFileSync` non atomico
- `fs.appendFileSync` non è garantito atomic su tutti i filesystem
- In Windows, `appendFileSync` può corrompere i dati se il file è ancora in scrittura
- Più worker paralleli potrebbero tentare di scrivere sullo stesso file giornaliero

#### Bug 3: Race condition nel fallback bulk→REST
- Se il bulk download fallisce e si usa il fallback REST API, `downloadDayTrades()` scrive direttamente nel `rawDir`
- Questo può creare conflitti se un altro worker sta scrivendo lo stesso file

#### Bug 4: `writeAggTradesJsonl()` usa `fs.writeFileSync` con tutta la memoria
```typescript
// jsonlWriter.ts
export function writeAggTradesJsonl(trades: BinanceAggTrade[], filePath: string, append: boolean = false): void {
  const lines = trades.map((t) => JSON.stringify(t)).join('\n') + '\n';
  if (append) {
    fs.appendFileSync(filePath, lines, 'utf-8');
  } else {
    fs.writeFileSync(filePath, lines, 'utf-8');
  }
}
```
- `trades.map().join()` carica **tutti** i trade in memoria prima di scrivere
- Per 100,000+ trade per giorno, questo può essere **200MB+** di stringa in memoria
- Il buffer viene poi scritto interamente — rischio OOM

### Analisi Approfondita delle Alternative

#### Soluzione A — Stream-based merge (consigliata)
- Usare `fs.createReadStream` + `fs.createWriteStream` per mergeare senza caricare tutto in memoria
- Ogni file viene letto linea per linea e scritto nel file finale
- **Pro**: Memory-safe, nessun OOM, true streaming
- **Contro**: Più complesso, richiede gestione multi-stream

#### Soluzione B — File temporale + rename atomico
- Scrivere in file temporaneo, poi `fs.rename()` (atomico su Linux)
- **Pro**: Scrive in sicurezza
- **Contro**: Non risolve il problema del merge stesso

#### Soluzione C — Lock-based approach
- Usare un mutex/semaforo per coordinare l'accesso ai file
- **Pro**: Semplice concettualmente
- **Contro**: Aggiunge latenza, non portabile in Node.js nativo

### Soluzione Scelta

**Soluzione A (stream-based merge)** con i seguenti cambiamenti:
1. `mergeDayFiles()` usa `fs.createReadStream` per ogni giorno e `fs.createWriteStream` per il finale
2. `writeAggTradesJsonl()` usa `fs.appendFileSync` solo per piccoli batch, altrimenti stream
3. Aggiungere un meccanismo di "file completion" per garantire che il merge avvenga solo quando tutti i download sono completati

### Impatto

- **Previene**: Corruzione dati, OOM crash, race condition
- **Rischio**: Medio — richiede refactoring della funzione merge e della writer
- **Test**: Verificare con dataset di test di dimensioni variabili

## 🔧 Addendum audit — due bug nel merge gzip (stessa funzione)

La ri-analisi ha trovato due difetti nella versione streaming di `mergeDayFiles`:

1. **`pipeline()` in loop chiude il sink**: `stream.pipeline(src, dst)` chiude il
   destination al completamento, quindi dal secondo giorno in poi il merge
   falliva con write-after-end. Il caso multi-giorno (= quello normale) era rotto.
   Fix: pump manuale `pumpDecodedFile()` che scrive chunk con backpressure
   (`write` + `once 'drain'`) senza mai chiudere il sink; chiusura unica alla fine.
2. **Output `.gz` non compresso**: i byte decompressi dei giorni venivano scritti
   tali e quali in un file chiamato `.jsonl.gz`, illeggibile dal gunzip a valle.
   Fix: unico `createGzip` sul sink finale (un solo membro gzip), più
   `writeEmptyGzip()` per il caso vuoto (zero byte non sono un gzip valido).

Regression test: `downloadAggTrades.test.ts` → `mergeDayFiles` (3 file `.gz`
→ `.gz` ordinato e leggibile; 2 file piani; caso vuoto leggibile come `[]`).
