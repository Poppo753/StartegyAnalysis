# Caso #22 — JSON Structured Logging (jsonLogger.ts)

## 🔍 Analisi del Problema

### Codice originale (solo console human-readable)

Prima dell'intervento, `src/utils/logger.ts` emetteva esclusivamente stringhe su console (`[timestamp] [LEVEL] message`), non parsabili meccanicamente e senza metadati strutturati. Il sistema attuale separa i due canali (`src/utils/jsonLogger.ts` + `logger.ts`):

```typescript
// src/utils/jsonLogger.ts, linee 49-69
export function jsonLog(level: JsonLogLevel, message: string, meta?: unknown): void {
  if (!shouldEmit(level)) return;
  const entry = {
    timestamp: new Date().toISOString(),
    level,
    service: SERVICE,          // da LOG_SERVICE, default 'ohlc-pipeline' (linea 21)
    message,
    meta: safeMeta(meta),
  };
  let line: string;
  try {
    line = JSON.stringify(entry);
  } catch {
    // Circular reference fallback — never crash the pipeline for logging.
    line = JSON.stringify({ ...entry, meta: { stringifyError: 'non-serializable meta' } });
  }
  process.stderr.write(line + '\n');   // stderr: mai su stdout
}
```

Integrazione in `logger.ts`: con `JSON_LOGGING=true`, `info/warn/error` delegano a `jsonLogger` (linee 9-30); `logger.json.*` emette sempre JSON strutturato (linee 38-48) indipendentemente dal flag. (Nota di precisione: il contenuto precedente di questo documento descriveva `jsonlWriter` — modulo di scrittura dati, non di logging — ed è stato sostituito perché errato.)

### Bug Identificati

1. **Log non machine-readable** — le righe `[INFO] messaggio` richiedono regex fragili per estrarre livello/timestamp; qualsiasi cambio di formato rompe ELK/Splunk/CloudWatch/`jq`. Il formato JSON `{timestamp, level, service, message, meta}` è parsabile con `JSON.parse` per riga.
2. **Inquinamento di stdout** — i dati della pipeline (CSV/JSONL) viaggiano su stdout; log sullo stesso stream corrompono i pipe. `jsonLog` scrive esclusivamente su `stderr` (linea 68), per design (docstring linee 12-13).
3. **Nessun level filtering / crash su meta circolari** — senza `LOG_LEVEL` ogni `debug` finiva in produzione; senza safe-stringify un `meta` con riferimenti circolari faceva crashare `JSON.stringify` nel path di logging. Risolti da `shouldEmit` (`LOG_LEVEL`, default `info`, con legacy `DEBUG=true` → `debug`, linee 30-41) e dal fallback `stringifyError` (linee 61-67).

### Analisi Approfondita delle Alternative

#### Soluzione A — Doppio canale: `logger` human + `jsonLogger`/`logger.json.*` su stderr con filtro (scelta)
- **Pro**: sviluppo locale invariato (console leggibile); produzione machine-readable senza toccare i call-site esistenti (`JSON_LOGGING=true` commuta il canale); `service` correla i log di multi-istanza; filtro `LOG_LEVEL` senza ricompilare.
- **Contro**: due formati da conoscere; `meta` deve essere JSON-serializzabile (mitigato dal fallback che non crasha mai).

#### Soluzione B — Solo console human-readable
- **Pro**: zero codice.
- **Contro**: nessuna aggregazione/filtro field-based, parsing regex, stdout a rischio inquinamento.

#### Soluzione C — JSON su stdout
- **Pro**: un solo stream da raccogliere.
- **Contro**: rompe i pipe dati su stdout — inaccettabile per una pipeline che emette CSV/JSONL; scartata per vincolo architetturale, non per gusto.

### Soluzione Scelta

**Soluzione A** — `LOG_SERVICE`/`LOG_LEVEL`/`DEBUG`/`JSON_LOGGING` danno quattro manopole senza ricompilare; `safeMeta` normalizza `meta` (`undefined/null → {}`, primitivi → `{value}`); il fallback circolare garantisce che il logging non faccia mai fallire la pipeline. `logger.json.*` resta disponibile per eventi che devono essere strutturati anche in sviluppo.

### Impatto

- **Previene**: pipe di dati corrotti da log su stdout, crash per `meta` non serializzabili, log di debug in produzione, parsing regex dei log negli aggregatori.
- **Rischio del cambiamento**: basso — default invariato (console human-readable); il JSON si attiva solo con env esplicito; riga singola per evento, compatibile `jq`/ELK/Splunk/CloudWatch.
- **Test richiesti**: con `JSON_LOGGING=true`, ogni riga su stderr deve superare `JSON.parse` e contenere `timestamp/level/service/message/meta`; stdout deve restare byte-identico con e senza logging; `LOG_LEVEL=error` silenzia `info/warn`; `meta` circolare produce `stringifyError` senza throw.
