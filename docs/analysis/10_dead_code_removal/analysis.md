# Caso #10 — Rimozione Dead Code (aggregateToOhlc.ts)

## 🔍 Analisi del Problema

### Codice originale (`src/pipeline/aggregateToOhlc.ts` — file rimosso)

Il file implementava l'aggregazione da array di trade a candele OHLC a 1 secondo con una propria logica di bucketing per secondo, formattazione numerica e normalizzazione timestamp. Verificato in data 2026-09-25: `Test-Path src/pipeline/aggregateToOhlc.ts` restituisce `False` — il file non esiste più nella codebase. La pipeline contiene un'unica implementazione in `src/pipeline/ohlcAggregator.ts`, il cui metodo statico copre il caso d'uso del file rimosso:

```typescript
// src/pipeline/ohlcAggregator.ts, linee 88-100
static fromArray(trades: BinanceAggTrade[]): OhlcCandle[] {
  const sorted = [...trades].sort((a, b) => a.T - b.T || a.a - b.a);
  const buckets = new Map<number, BinanceAggTrade[]>();

  for (const trade of sorted) {
    const secondKey = floorToSecond(OHLCAggregator.normalizeTimestamp(trade.T));
    const bucket = buckets.get(secondKey);
    if (bucket) {
      bucket.push(trade);
    } else {
      buckets.set(secondKey, [trade]);
    }
  }
  // ... open = primo prezzo, high/low = max/min, close = ultimo prezzo,
  //     volume = somma quantità, tradeCount = dimensione bucket (linee 102-119)
}
```

### Bug Identificati

1. **Duplicazione della responsabilità** — due implementazioni del medesimo bucketing (secondo → open/high/low/close/volume/tradeCount) coesistevano in `aggregateToOhlc.ts` e `OHLCAggregator.fromArray`. Ogni fix (es. gestione timestamp in microsecondi via `normalizeTimestamp`, linee 31-36) andava applicato due volte.
2. **Rischio di divergenza silenziosa** — i due path potevano produrre candele diverse (ordinamento, arrotondamento via `fmt`, linee 27-29) a parità di input, rendendo i backtest non riproducibili a seconda del chiamante.
3. **Ambiguità di ownership** — i nuovi consumer (`runPipeline.ts`, `csvWriter.ts`, `extractRange.ts`) usano `OHLCAggregator`; mantenere il vecchio modulo invitava a usarne la variante obsoleta.

### Analisi Approfondita delle Alternative

#### Soluzione A — Rimozione del file, `OHLCAggregator.fromArray` come unica implementazione (scelta)
- **Pro**: single source of truth; un solo punto di fix/test; `fromArray` è pura e statica, quindi banale da testare (`ohlcAggregator.test.ts`).
- **Contro**: richiede aggiornamento di tutti gli import esistenti in un unico change.

#### Soluzione B — Adapter: tenere il file come thin-wrapper sopra `fromArray`
- **Pro**: zero rotture per chiamanti esterni.
- **Contro**: conserva un modulo senza logica propria; il wrapper diventa dead code di fatto e va comunque manutenuto/migrato.

#### Soluzione C — Tenere entrambe le implementazioni con test di equivalenza
- **Pro**: nessun rischio di regressione immediata.
- **Contro**: costo doppio permanente (fix, test, review) per zero valore funzionale; i test di equivalenza stessi vanno manutenuti.

### Soluzione Scelta

**Soluzione A** — `OHLCAggregator` copre entrambi i casi d'uso (`fromStream` per file JSONL anche `.gz`, `fromArray` per array in memoria), quindi il vecchio modulo non aggiungeva capacità. La rimozione netta, accompagnata dalla migrazione degli import, è l'unica opzione che riduce stabilmente il costo di manutenzione.

### Impatto

- **Previene**: divergenza tra due motori di aggregazione, bug fix applicati a metà, uso accidentale del path obsoleto.
- **Rischio del cambiamento**: basso — `fromArray` preserva la semantica (ordinamento per `T` poi `a`, bucket per secondo floor, open=primo/close=ultimo prezzo); nessun consumer punta più al file rimosso.
- **Test richiesti**: test di equivalenza input/output su fixture con trade multipli nello stesso secondo, secondi sparsi e timestamp in microsecondi; `npm test` deve passare senza riferimenti residui (`grep aggregateToOhlc` vuoto).
