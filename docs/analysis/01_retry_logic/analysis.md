# Caso #1 — Fix Bug Retry Logic (binanceClient.ts)

## 🔍 Analisi del Problema

### Codice originale (binanceClient.ts, linee 36-68)

```typescript
let retries = 0;

while (true) {
  try {
    await this.rateLimiter.acquire();
    await delay(this.requestDelayMs);
    const response = await this.client.get<BinanceAggTrade[]>('/api/v3/aggTrades', { params: queryParams });
    return response.data;
  } catch (error) {
    const status = axiosError.response?.status;
    if (status === 429 || (status !== undefined && status >= 500)) {
      retries++;                    // <-- BUG 1
      if (retries > MAX_RETRIES) {  // <-- BUG 2
        logger.error(`Max retries (${MAX_RETRIES}) exceeded`);
        throw error;
      }
      const retryDelay = RETRY_BASE_DELAY_MS * Math.pow(2, retries - 1); // <-- BUG 3
      await delay(retryDelay);
    } else {
      throw error;
    }
  }
}
```

### Bug Identificati

#### Bug 1: `retries++` prima del check — Logica off-by-one
- `retries` viene incrementato **prima** del check
- Con `MAX_RETRIES = 5`, il loop fa:
  - Tentativo 1 (fallito) → retries=1 → 1 > 5? No → retry
  - Tentativo 2 (fallito) → retries=2 → 2 > 5? No → retry
  - Tentativo 3 (fallito) → retries=3 → 3 > 5? No → retry
  - Tentativo 4 (fallito) → retries=4 → 4 > 5? No → retry
  - Tentativo 5 (fallito) → retries=5 → 5 > 5? No → retry
  - Tentativo 6 (fallito) → retries=6 → 6 > 5? **Sì** → Lancia errore
- **Risultato**: 6 tentativi totali (1 originale + 5 retry), ma il messaggio dice "Max retries (5)"

#### Bug 2: `retries > MAX_RETRIES` dovrebbe essere `retries >= MAX_RETRIES`
- Con la condizione attuale, si fanno **MAX_RETRIES + 1** tentativi totali
- Il check corretto dovrebbe essere `retries >= MAX_RETRIES` per fare esattamente MAX_RETRIES retry

#### Bug 3: Calcolo del delay esponenziale errato
- `Math.pow(2, retries - 1)` con retries=1 dà `2^0 = 1` → delay = 1000ms (primo retry)
- `Math.pow(2, retries - 1)` con retries=2 dà `2^1 = 2` → delay = 2000ms (secondo retry)
- Questo è **corretto** per il backoff esponenziale classico
- MA il problema è che con il fix del Bug 1/2, se `retries >= MAX_RETRIES` lancia l'errore PRIMA di calcolare il delay, l'ultimo retry mai viene tentato
- **Soluzione**: Il check deve essere dopo il tentativo, prima del delay

### Analisi Approfondita delle Alternative

#### Soluzione A — Fix minimo (consigliata)
```typescript
retries++;
if (retries > MAX_RETRIES) { throw error; }
const retryDelay = RETRY_BASE_DELAY_MS * Math.pow(2, retries - 1);
```
- **Pro**: Minimo cambiamento, comportamento chiaro
- **Contro**: Il contatore è leggermente confuso (retries=1 significa primo retry)

#### Soluzione B — Refactoring completo con tentativi massimi
```typescript
for (let attempt = 1; attempt <= MAX_RETRIES + 1; attempt++) {
  try {
    return await this.client.get(...);
  } catch (error) {
    if (isRetryable(error) && attempt <= MAX_RETRIES) {
      const delay = RETRY_BASE_DELAY_MS * Math.pow(2, attempt - 1);
      await delay(delay);
    } else {
      throw error;
    }
  }
}
```
- **Pro**: Più leggibile, no infinite loop, tentativi espliciti
- **Contro**: Richiede più modifiche al codice

#### Soluzione C — Usa Axios retry interceptor
- Usare `axios-retry` come libreria esterna
- **Pro**: Zero codice custom, gestione standard
- **Contro**: Aggiunge dipendenza esterna, meno controllo

### Soluzione Scelta

**Soluzione B (refactoring completo)** — è la più robusta, leggibile e mantenibile. Elimina il `while(true)` rischioso, rende esplicito il numero massimo di tentativi, e il calcolo del delay è immediatamente chiaro.

### Impatto

- **Previene**: Timeout infiniti, consumo eccessivo di risorse, log ingannevoli
- **Rischio del cambiamento**: Basso — la logica è identica, solo più esplicita
- **Test richiesti**: Simulare errori 429/5xx e verificare il numero esatto di tentativi
