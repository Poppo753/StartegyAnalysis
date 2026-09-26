# Caso #9 — Fix XML Parsing con Regex Escaping (bulkAvailability.ts)

## 🔍 Analisi del Problema

### Codice originale (src/binance/bulkAvailability.ts, linee 36-44)

Il controllo di disponibilità bulk su `data.binance.vision` parsava la risposta S3 `ListBucketResult` con un semplice string matching:

```typescript
const xml = response.data as string;

// PRIMA: string matching fragile
for (const day of monthDays) {
  const zipFile = `${symbol}-aggTrades-${day}.zip`;
  if (xml.includes(zipFile)) {
    available.add(day);
  }
}
```

Il codice attuale (`bulkAvailability.ts`, linee 6-8 e 40-41) usa invece una regex ancorata ai tag `<Key>` con escaping:

```typescript
function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// DOPO: match esatto sul tag <Key>
const keyPattern = new RegExp('<Key>' + escapeRegex(zipFile) + '</Key>');
if (keyPattern.test(xml)) {
  available.add(day);
}
```

### Bug Identificati

1. **Falsi positivi per sottostringa** — `xml.includes(zipFile)` restituisce `true` anche se il nome è sottostringa di un'altra chiave (es. `...-2024-01-01.zip` dentro `...-2024-01-010.zip`). Il giorno verrebbe marcato come disponibile in bulk senza che il file esista, causando 404 a valle nel download.
2. **Nessun ancoraggio alla struttura XML** — `includes()` matcha ovunque nel documento: tag `<Prefix>`, `<Marker>`, messaggi di errore S3 (`<Message>`) o chiavi di altri simboli con prefisso comune. Il pattern `<Key>...</Key>` restringe il match all'unico elemento che certifica l'esistenza dell'oggetto.
3. **Caratteri speciali non escapati** — i nomi file contengono `.` e `-` (metacaratteri regex). Una futura evoluzione a `new RegExp(zipFile)` senza `escapeRegex()` trasformerebbe ogni `.` in "qualsiasi carattere", reintroducendo falsi positivi. `escapeRegex()` (linea 6-8) neutralizza l'intera classe `[.*+?^${}()|[\]\\]`.

### Analisi Approfondita delle Alternative

#### Soluzione A — Regex con escaping su tag `<Key>` (scelta)
- **Pro**: zero dipendenze, match esatto O(n) per giorno, robusta a caratteri speciali; il formato `ListBucketResult` di S3 è stabile.
- **Contro**: accoppiata al formato XML S3; se AWS cambiasse schema servirebbe aggiornamento.

#### Soluzione B — Parser XML dedicato (`fast-xml-parser`, `xml2js`)
- **Pro**: parsing strutturalmente corretto, validazione del documento, gestione errori esplicita su XML malformato/403.
- **Contro**: nuova dipendenza per un check di presenza; overhead di parsing DOM completo per risposte con `max-keys=100`; sovradimensionato rispetto al bisogno.

#### Soluzione C — Head-request per singolo file (`axios.head(getBulkDownloadUrl(...))`)
- **Pro**: nessuna interpretazione XML, segnale di esistenza diretto (200 vs 404).
- **Contro**: N richieste HTTP invece di 1 per mese (rate-limit, latenza); trasforma un controllo batch in O(giorni) round-trip.

### Soluzione Scelta

**Soluzione A** — miglior compromesso robustezza/costo: il raggruppamento per `monthPrefix` (linee 21-27) mantiene 1 sola richiesta S3 per mese, e la regex escapata elimina le tre classi di falsi positivi senza dipendenze né traffico aggiuntivo. La soluzione B resta l'evoluzione naturale solo se il controllo dovrà estrarre metadati (size, last-modified).

### Impatto

- **Previene**: download bulk tentati su file inesistenti (404), fallback REST non necessari, date marcate disponibili per errore.
- **Rischio del cambiamento**: basso — la semantica resta "presenza/assenza per giorno"; il pattern `<Key>` è parte stabile dell'API S3 `ListObjects`.
- **Test richiesti**: XML fixture con (a) chiave prefisso-sottostringa, (b) nome file dentro `<Message>` di errore, (c) filename con metacaratteri regex; verificare `available` atteso in tutti e tre i casi.
