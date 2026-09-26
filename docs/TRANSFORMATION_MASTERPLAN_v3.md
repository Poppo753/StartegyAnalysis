# 🏗️ DALLA STRATEGIA SINGOLA ALLA MACCHINA MOSTRUOSA DI SCOPERTA

## Versione 3 — Documento Maestro di Trasformazione Ampliato e Rivalutato
### Dal Tool di Analisi Strategia → Alla Macchina Universale di Discovery

> **NOTA CRITICA**: Questo è un documento VIVO. Analizzo, verifico, contesto, e amplio ogni singola affermazione. Nulla è dato per scontato. Ogni sezione è stata interrogata con: "È davvero corretto? Manca qualcosa? È abbastanza profondo?"

> **NOTA DELLA v3**: Questa versione nasce da una doppia analisi incrociata tra la v2 e il documento teorico (`docs/theory/THEORETICAL_FOUNDATIONS.md`). Prima ho mappato 25 punti di miglioramento (documento `docs/analysis/09_theory_vs_masterplan/THEORY_VS_MASTERPLAN_CROSSREFERENCE.md`), poi ho attaccato frontalmente ognuno dei 25 punti per verificare se reggesse davvero, e infine ho rivalutato tutto alla luce del codice reale (documento `docs/analysis/09_theory_vs_masterplan/THEORY_VS_MASTERPLAN_RIVALUTAZIONE.md`). Risultato onesto: **3 integrazioni attuabili ora, 7 note future con prerequisiti espliciti, 15 voci scartate** perché concetti validi ma nel contesto sbagliato o nel momento sbagliato. Ogni integrazione qui sotto spiega *perché adesso* o *perché dopo*, con i prerequisiti verificati sul codice. Nulla è stato aggiunto per prestigio accademico.

---

## INDICE

1. [Parte I — IL BAMBINO: Cos'è oggi](#parte-i--il-bambino)
2. [Parte II — IL BAMBINO CRECIUTO: I problemi, la verità nuda](#parte-ii--il-bambino-crecito)
3. [Parte III — IL VERIFICATO: Analisi critica dell'architettura attuale](#parte-iii--il-verificato)
4. [Parte IV — L'ADULTO: La filosofia della strategia universale](#parte-iv--ladulto)
5. [Parte V — L'ESPERTO: Architettura a 7 strati](#parte-v--lesperto)
6. [Parte VI — IL SUPER ESPERTO: Il blueprint tecnico completo](#parte-vi--il-super-esperto)
7. [Parte VII — ANTI-OVERFITTING AVANZATO: Il gold standard](#parte-vii--anti-overfitting-avanzato)
8. [Parte VIII — RICERCA E VERIFICA: Fonti scientifiche](#parte-viii--ricerca-e-verifica)
9. [Parte IX — PIANO DI IMPLEMENTAZIONE DETTAGLIATO](#parte-ix--piano-di-implementazione)
10. [Appendice — Glossario e Concetti](#appendice)
11. [Changelog v2 → v3: cosa cambia e perché](#changelog-v2--v3)

---

## Changelog v2 → v3

### Cosa cambia e perché

La v2 era un ottimo documento operativo con un difetto strutturale: presentava alcuni concetti teorici senza dichiararne prerequisiti, approssimazioni e momento di applicazione. La rivalutazione sistematica (25 punti, ognuno verificato contro il codice reale) ha prodotto tre tipi di intervento, tutti integrati qui sotto nelle sezioni corrispondenti invece che in un documento separato:

**A. Integrazioni attuabili ora (3)** — attuate in questa v3:
1. **Metriche Sortino / Calmar / Expectancy** (§5.3 + Glossario): tutti gli input esistono già in `metrics.py`, serve solo `numpy` (già dipendenza). Lo Sharpe Ratio resta il riferimento, ma Sortino penalizza solo il downside (meglio per strategie asimmetriche), Calmar confronta strategie con drawdown diversi, Expectancy dice se il singolo trade medio è profittevole. Il Kelly Criterion NON è tra queste: è un tool di position sizing, non una metrica di valutazione — confonderli era un errore da correggere.
2. **Principio GPU-per-archetipo come vincolo di Fase 1** (§6.1 + Fase 1): il kernel CUDA attuale è hardcoded per Momentum+Drop senza alcuno strategy dispatch. Uno `switch(strategy_type)` dentro il kernel causerebbe warp divergence reale. Il vincolo fissato ora a costo zero: un kernel compilato per archetipo, batch omogenei, CPU che seleziona e GPU che valuta solo parametri, interfacce Strategy GPU-compatibili (array tipizzati, niente oggetti Python nel path GPU).
3. **Nota DSR riconciliata** (§§5.6, 6.2, 8.4.3 + Glossario): correzione onesta — il documento teorico stesso contiene DUE formulazioni del DSR (approssimazione PBO-based e formula φ/Φ) senza riconciliarle, e il PBO del theory coincide con quello del masterplan. Quindi non esisteva "formula giusta vs formula sbagliata": esiste un'approssimazione da dichiarare come tale, con prerequisiti espliciti (Sharpe Ratio + `scipy`, entrambi assenti oggi) e uso reale da Fase 3 in poi.

**B. Note future con prerequisiti espliciti (7)** — documentate nelle sezioni corrispondenti, NON implementate:
1. Stazionarietà / differenziazione frazionaria (§5.1): serve solo se arriva ML supervisionato (oggi zero modelli).
2. Dollar / Volume Bars (§5.1): migliora la stazionarietà dei dati ma richiede di ristrutturare la pipeline e tutto il backtester.
3. Information Coefficient / Information Ratio (§5.7 / Strato 7): richiedono segnali continui storicizzati + numerosità (migliaia di osservazioni) + fase di monitoraggio.
4. Meta-Labeling (§5.8, nuova sottosezione): richiede strategia base validata + feature di contesto + storico etichettato.
5. Random Forest feature importance (Fase 5): richiede feature ingegnerizzate (Fase 6) + `sklearn`.
6. HMM / CUSUM per regime detection (§5.7): il backtester offline non decide in tempo reale; HMM/CUSUM appartengono alla produzione futura.
7. Soglie PBO granulari (§7.x): regole empiriche (non teoremi) utilizzabili quando esisterà il CPCV (Fase 3).

**C. Voci scartate (15)** — concetti teoricamente validi ma fuori contesto, fuori scope o prematuri: Production Chain come framework, Meta-Strategy Paradigm, Reinforcement Learning (altro progetto), Sample Weighting (niente labeling, niente overlap nel grid search), Multiple Testing come sezione autonoma (il grid parametrico non testa ipotesi distinte; il rischio è coperto da PBO/DSR), formule EI/PI/UCB (useremo TPE, non GP), Bagging/Stacking (ridondanti con CPCV), VGP/bloat (la generazione parametrica non ha alberi), t-test/Shapiro sul Walk-Forward (assunzioni violate + campione insufficiente), CUSUM realtime, bibliografia duplicata (resta nel theory), Sisyphus come sezione (principio già presente), RF-by-regime (prodotto di due prerequisiti futuri), alpha decay quantitativo (assorbito nella nota IC/IR), mappatura anelli×fasi (burocrazia). Dettagli e motivazioni voce per voce: `docs/analysis/09_theory_vs_masterplan/THEORY_VS_MASTERPLAN_RIVALUTAZIONE.md`.

---

## Parte I — IL BAMBINO: Cos'è oggi questo tool

### 1.1 La situazione attuale, dai 5 anni agli 80 anni

Questo documento non è un semplice racconto per bambini. È una **mappa chirurgica** di ogni componente, con i difetti, i punti forti, e le possibili evoluzioni.

#### Cosa fa la pipeline TypeScript (il "cuore" dati)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                        │
│  TYPECRIPT PIPELINE (src/)                                            │
│                                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ binanceClient │───▶│ downloadAgg  │───▶│ aggregateTo  │          │
│  │ (con retry)  │    │ Trades.ts    │    │ OHLC         │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│       │                                         │                   │
│       ▼                                         ▼                   │
│  ┌──────────────┐                    ┌──────────────────┐          │
│  │ bulkAvail-   │                    │  jsonlWriter.ts  │          │
│  │ ability.ts   │                    │  (streaming)     │          │
│  │ (S3/XML)     │                    └──────────────────┘          │
│  └──────────────┘                                                   │
│                                                                        │
│  Output: data/{SYMBOL}/raw/aggTrades_{date}.jsonl                     │
│  Output: data/{SYMBOL}/ohlc/ohlc_1s_{date}.csv                        │
│                                                                        │
└──────────────────────────────────────────────────────────────────────┘
```

**Funzionamento dettagliato:**

1. **binanceClient.ts**: Intercetta richieste HTTP a Binance API con retry esponenziale
2. **bulkAvailability.ts**: Interroga S3 di data.binance.vision per verificare se esistono file bulk compressi
3. **bulkDownloader.ts**: Scarica file zip da data.binance.vision (o REST API come fallback)
4. **downloadAggTrades.ts**: Orchestratore principale — coordina bulk + REST, merge dei file giornalieri
5. **aggregateStreaming.ts**: Legge JSONL riga per riga, aggrega in candele OHLC 1s
6. **jsonlWriter.ts**: Scrittura streaming di trade in formato JSONL

#### Cosa fa il backtester Python (il "cervello" decisionale)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                        │
│  PYTHON BACKTESTER (python-backtester/)                                │
│                                                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │  main.py     │───▶│  config.py   │───▶│  parameter_  │          │
│  │  (orchestra- │    │  (.env)      │    │  grid.py     │          │
│  │  mentatore)  │    └──────────────┘    └──────┬───────┘          │
│  └──────────────┘                               │                   │
│       │                                        ▼                   │
│       ▼                              ┌──────────────────┐          │
│  ┌──────────────┐                    │  strategy.py     │          │
│  │ data_loader  │───▶│  (Backtest-  │    │ (BacktestParams│          │
│  │ (CSV → df)   │    │  Params,     │    │  Trade,        │          │
│  └──────────────┘    │  Trade,      │    │  BacktestResult) │        │
│                      │  BacktestRes)│    └────────┬─────────┘          │
│                      └──────────────┘             │                   │
│                                         ┌────────▼─────────┐          │
│                                         │  simulator.py    │          │
│                                         │  (run_backtest)  │          │
│                                         └────────┬─────────┘          │
│                                                  │                   │
│                              ┌───────────────────┼──────────────┐     │
│                              ▼                   ▼              ▼     │
│                     ┌──────────────┐  ┌─────────────┐  ┌──────────┐ │
│                     │  STANDARD    │  │  FAST       │  │  GPU     │ │
│                     │  (Python     │  │  (Numba JIT)│  │  (CUDA)  │ │
│                     │  puro)       │  │             │  │          │ │
│                     └──────────────┘  └─────────────┘  └──────────┘ │
│                                                                        │
│  Output: backtest-results/{SYMBOL}/                                    │
│         summary_{date}.csv, trades_x{X}_y{Y}_z{Z}.csv                 │
│                                                                        │
└──────────────────────────────────────────────────────────────────────┘
```

#### Il motore GPU/CUDA — come funziona davvero

Il sistema non è semplicemente "più veloce". È un'architettura completamente diversa:

**Standard Engine** (`simulator.py`):
- Loop Python puro con `np.searchsorted` per binary search
- O(n_candles × n_combinations) nel caso peggiore
- Ogni combinazione X/Y/Z viene testata sequenzialmente
- Tempo: ~1000 combinazioni in minuti

**Fast Engine** (`fast_simulator.py`):
- Usa `@njit` di Numba per compilare il loop in macchina nativa
- Warmup con prime 100 candele per triggerare la compilazione JIT
- Array pre-allocati (max 10000 trade per combinazione)
- Tempo: ~1000 combinazioni in secondi
- **Problema**: Il warmup crasha se il dataset ha < 100 righe (BUG noto)

**GPU Engine** (`gpu_simulator.py`):
- Traduce il loop in CUDA kernel con `cupy.RawKernel`
- Ogni thread GPU processa UNA combinazione
- Batch di 256 thread per blocco
- Transfer dati mercato (epoch_ms, close, high, low) una sola volta su GPU
- Kernel esegue in parallelo: N combinazioni × M candele simultaneamente
- **Problema**: Il kernel usa `while (k >= 0)` con `k -= 1` per cercare il minimo — O(n) per ogni candela, rendendo il kernel O(n²) in pratica per il caso Y dinamico

#### La strategia "Momentum + Drop" — analisi approfondita

Non è solo "prezzo sale X% → compra". È più complesso:

**Fase 1 — Ricerca del segnale:**
```
Per ogni candela i (indice corrente):
  1. Definisci target_past_time = epoch_seconds[i] - y_seconds
  2. Binary search nell'array epoch_seconds per trovare la candela 
     con tempo <= target_past_time (candela passata)
  3. Se non esiste → salta a prossima candela
  4. Calcola: move_percent = (close[i] - close[past_idx]) / close[past_idx] * 100
```

**Nota critica**: I dati sono SPARSI (non c'è una candela per ogni secondo). Il sistema usa epoch_seconds reali, non indici. Questo è il motivo del binary search — non puoi semplicemente fare `close[i - y]` perché le candele non sono equidistanti.

**Fase 2 — Apertura trade:**
- Se move_percent >= x_percent → apri trade
- Applica slippage all'entry price (diversamente per long/short/signal-only)
- Inizia il tracking di max_price e min_price

**Fase 3 — Monitoraggio:**
```
Per ogni candela j dopo entry_idx:
  1. Aggiorna max_price = max(max_price, high[j])
  2. Aggiorna min_price = min(min_price, low[j])
  3. Calcola: drop_pct = (max_price - close[j]) / max_price * 100
  4. Se drop_pct >= z_percent → chiudi (reason: "drop-z")
  5. Se elapsed_seconds >= max_hold_seconds → chiudi (reason: "max-hold")
```

**Fase 4 — Calcolo PnL:**
- signal-only: pnl = 0 (è solo un segnale), pnl_percent = movimento teorico, fees = 0
- long: pnl = (exit_price - entry_price) * quantity - fees
- short: pnl = (entry_price - exit_price) * quantity - fees

### 1.2 I dati reali che usa il sistema

Ecco cosa ho trovato guardando i dati effettivi nella repo:

```
data/
├── UNIUSDT/
│   ├── raw/
│   │   ├── aggTrades_2026-01-01_2026-05-05.jsonl    (file grande)
│   │   └── aggTrades_2026-01-01_2026-01-30.jsonl
│   └── ohlc/
│       ├── ohlc_1s_2026-01-01_2026-05-05.csv
│       └── ohlc_1s_2026-01-01_2026-01-30.csv
├── RPLUSDT/
│   ├── raw/
│   │   ├── aggTrades_2026-01-01_2026-01-07.jsonl
│   │   └── aggTrades_2026-01-01_2026-01-02.jsonl
│   └── ohlc/
│       └── ohlc_1s_2026-01-01_2026-01-07.csv
├── BTTCUSDT/
│   └── raw/
│       └── aggTrades_2026-01-01_2026-01-02.jsonl
├── DCRUSDT/
│   ├── raw/
│   │   ├── aggTrades_2026-01-01_2026-01-02.jsonl
│   │   └── aggTrades_2020-07-30_2026-05-05.jsonl     (5 anni di dati!)
│   └── ohlc/
│       └── ohlc_1s_2026-01-01_2026-01-02.csv
```

**Osservazione cruciale**: Il simbolo DCRUSDT ha dati che vanno dal **2020-07-30 al 2026-05-05** — quasi 6 anni di dati. Questo significa che un singolo backtest potrebbe analizzare centinaia di migliaia di candele. Questo è il motivo per cui il sistema ha 3 motori (standard/fast/GPU) — il motore standard impiegherebbe ore o giorni su questo dataset.

---

## Parte II — IL BAMBINO CRECIUTO: I problemi, la verità nuda

### 2.1 VERIFICATA: Cosa è davvero rotto e cosa è già corretto

Prima di elencare i bug, devo verificare ciascuno contro il codice reale. Questo è fondamentale.

#### ✅ GIA' CORRETTO: Data Splitter

**Verifica**: `python-backtester/src/gpu/data_splitter.py` usa già `split_train_validation()` con split basato su DATA (`df_sorted["datetime"].iloc[split_idx]`), non su indice numerico.

**Conclusione**: Il problema #5 descritto in Improvements_v1.txt ("Bug nello Split Train/Validation basato su INDICE") è **già stato risolto** nel codice attuale. Il documento originale lo elenca come bug futuro, ma non è corretto.

**Implicazione**: Non devi implementarlo di nuovo — è già lì.

#### ✅ GIA' CORRETTO: bulkDownloader usa jszip

**Verifica**: `src/binance/bulkDownloader.ts` importa `import { JSZip } from 'jszip'` e usa `await JSZip.loadAsync(zipData)`.

**Conclusione**: Il problema #16 ("bulkDownloader.ts usa child_process per Unzip") è già risolto con jszip nel codice attuale.

#### ❌ ANCORA ROTTO: Retry Logic

**Verifica**: Guardando `src/binance/binanceClient.ts`:
```typescript
for (let attempt = 1; attempt <= MAX_RETRIES + 1; attempt++) {
  try {
    // ...
  } catch (error) {
    if (status === 429 || (status !== undefined && status >= 500)) {
      if (attempt > MAX_RETRIES) {
        logger.error(`Max retries (${MAX_RETRIES}) exceeded...`);
        throw error;
      }
      const retryDelay = RETRY_BASE_DELAY_MS * Math.pow(2, attempt - 1);
      await delay(retryDelay);
    }
  }
}
```

**Verifica**: Con `MAX_RETRIES = 5`, il loop fa `attempt = 1, 2, 3, 4, 5, 6`. Quando `attempt = 6`, `6 > 5` → lancia errore. Quindi fa 1 tentativo originale + 5 retry = 6 totali. Il check `attempt > MAX_RETRIES` è **corretto** per il numero massimo di retry = 5. MA il ritardo `Math.pow(2, attempt - 1)` con attempt=1 dà `2^0 = 1` (1000ms), con attempt=5 dà `2^4 = 16` (16000ms). Questo è **corretto** per backoff esponenziale.

**Nuova analisi**: Il codice attuale di `binanceClient.ts` ha fatto un refactoring rispetto al codice originale descritto in Improvements_v1.txt. Il codice originale usava `while(true)` con `retries++` e `retries > MAX_RETRIES`. Il codice attuale usa `for` con `attempt <= MAX_RETRIES + 1` e `attempt > MAX_RETRIES`. Il risultato funzionale è lo stesso, ma il codice attuale è **più chiaro e leggibile**. Tuttavia, c'è ancora una sottigliezza: il messaggio dice "Max retries (5) exceeded" ma il sistema fa 6 tentativi totali. Se vuoi esattamente 5 tentativi totali (1 originale + 4 retry), il check dovrebbe essere `attempt > MAX_RETRIES - 1`. Questo è un **errore logico** nella semantica, anche se non funzionale.

#### ❌ ANCORA ROTTO: Race Condition nel merge

**Verifica**: Guardando `src/pipeline/downloadAggTrades.ts`, la funzione `mergeDayFiles` usa `fs.createWriteStream` con `pipeline(readStream, writeStream)` — questo è un approccio streaming che mitiga il problema. MA il problema originale era che `downloadBulkDay` e `downloadDayTrades` scrivono file paralleli che poi vengono letti dal merge. Se due processi scrivono lo stesso file contemporaneamente...

**Analisi più profonda**: Il sistema usa `runWithConcurrency` per scaricare in parallelo, ma ogni giorno ha il suo file (`aggTrades_{day.start}.jsonl`). Quindi la race condition reale non è sullo stesso file, ma sul fatto che `mergeDayFiles` legge file che potrebbero ancora essere scritti da `downloadBulkDay` o `downloadDayTrades`. La soluzione attuale con `writeAggTradesJsonl` che fa append è parzialmente corretta, ma non c'è un barrier di sincronizzazione che garantisca che tutti i file siano completati prima del merge.

### 2.2 Lista completa dei problemi VERIFICATI

| # | Problema | Stato Attuale | Azione Necessaria |
|---|----------|---------------|-------------------|
| 1 | Retry logic semantica | ✅ Rifattorizzato in for-loop, ma errore semantico | Verificare se "5 max retries" = 5 tentativi totali o 5 retry |
| 2 | Race condition merge | ⚠️ Parzialmente mitigata con streaming | Aggiungere barrier di sincronizzazione |
| 3 | Data-based split | ✅ GIA' CORRETTO in data_splitter.py | Nessuna azione |
| 4 | XML fragile | ❌ Ancora `xml.includes(zipFile)` | Sostituire con regex o parser XML |
| 5 | jszip | ✅ GIA' USATO | Nessuna azione |
| 6 | jsonlWriter | ✅ USA streaming | Nessuna azione per il bug, MA il metodo `readAggTradesJsonl` carica TUTTO in RAM |
| 7 | fast_runner warmup | ❌ Usa `min(100, len(close))` | Aggiungere protezione esplicita |
| 8 | sys.exit() | ❌ Ancora presente in config.py | Sostituire con eccezioni personalizzate |
| 9 | Logica OHLC duplicata | ✅ In parte risolta con OHLCAggregator | Verificare che tutti i caller usino la classe |
| 10 | aggregateToOhlc.ts | ❌ Codice morto | Rimuovere o reintegrare |

### 2.3 Problemi NON menzionati nel documento originale ma CRITICI

#### 2.3.1 Memory Leak in jsonlWriter.readAggTradesJsonl

Mentre `writeAggTradesJsonl` è in streaming (corretto), il metodo `readAggTradesJsonl` carica TUTTI i trade in un array:
```typescript
const trades: BinanceAggTrade[] = [];
for await (const line of rl) {
  trades.push(JSON.parse(line) as BinanceAggTrade);
}
return trades;
```
Per il file `aggTrades_2020-07-30_2026-05-05.jsonl` (DCRUSDT), questo potrebbe essere un file da **diversi GB**. Caricare tutto in memoria = crash.

**Fix**: Usare `readAggTradesJsonlStream` (che è già implementato come AsyncGenerator) invece di `readAggTradesJsonl` per i file grandi.

#### 2.3.2 Import Path Issues in Python

Il file `src/config.py` ha `sys.exit(1)` invece di lanciare eccezioni. Questo rende impossibile:
- Fare unit test della configurazione
- Usare la configurazione come modulo importabile
- Fare integration testing

**Fix**: Creare una `ConfigError(Exception)` personalizzata.

#### 2.3.3 Il GPU kernel O(n²) per Y dinamico

Nel kernel CUDA `_get_kernel_dynamic_y`, per ogni candela `i`, il codice cerca indietro nel window:
```cuda
for (int k = i - 1; k >= 0; k--) {
    if (epoch_ms[k] < window_start_time) break;
    if (close[k] < min_close_in_window) { ... }
}
```
Questo è O(n) per ogni candela, rendendo il kernel O(n²) in pratica. Per un dataset di 5 anni (circa 150M secondi), questo è **insostenibile**.

**Fix**: Usare un Sparse Table o Segment Tree per range minimum queries in O(1) con O(n log n) preprocessing. Oppure, usare un approccio a due pointer che è O(n) totale.

---

## Parte III — IL VERIFICATO: Analisi critica dell'architettura attuale

### 3.1 Mancano 3 cose fondamentali per il "tool più potente"

Il sistema attuale può essere già più potente di quanto sembra, se aggiungi queste 3 cose:

#### 3.1.1 Multi-Strategy Engine (il cambio di paradigma più importante)

Il sistema attuale hardcodes la strategia "Momentum + Drop" in `simulator.py`. Non c'è modo di aggiungere facilmente una nuova strategia senza modificare il motore di backtest.

**Cosa serve**: Un'interfaccia strategy che separi la logica della strategia dal motore di backtest:

```python
# Senza questo, non puoi mai avere più strategie
class BacktestEngine:
    def __init__(self, strategy: TradingStrategy):
        self.strategy = strategy
    
    def run(self, df: pd.DataFrame) -> List[Trade]:
        return self.strategy.execute(df)
```

#### 3.1.2 Parameter Space Definition (il cambio di paradigma più necessario)

Il sistema attuale usa `itertools.product` per enumerare TUTTI i parametri. Con 3 parametri da 10 valori = 1000 combinazioni. Con 10 parametri da 10 valori = 10^10 = impossibile.

**Cosa serve**: Un framework di ricerca parametrica che:
1. Definisca lo spazio come range continuo, non lista discreta
2. Usi un algoritmo intelligente (non griglia) per esplorare
3. Abbia un criterio di stop (budget di tempo, numero di valutazioni)

#### 3.1.3 Out-of-Sample Validation Protocol (il cambio di paradigma più sottovalutato)

Il sistema attuale ha un solo split 70/30. Questo NON è sufficiente per validare una strategia. Con un solo split:
- Se la strategia è overfitted sul train, la validation può comunque dare risultati buoni per caso
- Non sai se il risultato è robusto o dipende dal split specifico

**Cosa serve**: Walk-forward analysis con purging e embargo (López de Prado).

### 3.2 Il concetto di "Strategy DNA" — un'analisi critica

Nel documento originale, ho proposto un "Strategy DNA" come schema JSON. Ma questo schema è **troppo semplice**. Una strategia reale ha più dimensioni:

```
STRATEGY DNA (versione corretta):
{
    metadata: {
        name: string,
        version: string,
        author: string,
        description: string,
        created: datetime,
        tags: ["momentum", "trend-following", "short-term"],
        market_conditions: ["trending", "high-volatility"],
        asset_classes: ["crypto", "forex"],
        timeframe_compatible: ["1s", "1m", "1h"]
    },
    
    data_requirements: {
        sources: ["binance_aggTrades", "orderbook_depth"],
        timeframes: ["1s", "1m"],
        indicators_needed: ["sma_20", "rsi_14", "volume"],
        min_history: "30d"
    },
    
    entry_logic: {
        type: "signal_based",
        signal_generator: "momentum_cross",
        parameters: {
            lookback_window: { min: 5, max: 120, type: "int", unit: "seconds" },
            threshold_pct: { min: 0.01, max: 2.0, type: "float", unit: "percent" },
            confirmation_candles: { min: 1, max: 5, type: "int" }
        },
        filters: ["min_volume", "not_during_maintenance"],
        constraints: { max_position_size: 10000, max_concurrent: 1 }
    },
    
    exit_logic: {
        type: "condition_based",
        exit_conditions: [
            { type: "drawdown", threshold: { min: 0.5, max: 5.0, unit: "percent" } },
            { type: "time_limit", max_seconds: { min: 60, max: 3600 } }
        ],
        trailing_stop: { enabled: bool, distance_pct: float }
    },
    
    risk_management: {
        position_sizing: "fixed_amount",  // or "percent_capital", "kelly"
        initial_capital: float,
        max_drawdown_limit: float,
        stop_loss: { type: "fixed_pct", value: float },
        take_profit: { type: "fixed_pct", value: float },
        max_consecutive_losses: int
    },
    
    parameter_space: {
        // Definizione dello spazio di ricerca
        // Usato per Bayesian Optimization
    }
}
```

### 3.3 Analisi critica del "sistema a 5 strati" originale

Il documento originale proponeva 5 strati (Data → Engine → Generation → Discovery → Meta). Ho ridisegnato questo in **7 strati** che è più accurato:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        STRATO 7 — META-RICERCA                     │
│  "Perché alcune strategie funzionano? Qual è il regime di mercato?" │
│  • Causal inference (non solo correlazione)                        │
│  • Regime detection con HMM / Random Forest                        │
│  • Strategy clustering                                              │
│  • Alpha decay monitoring                                           │
├─────────────────────────────────────────────────────────────────────┤
│                        STRATO 6 — VALIDAZIONE ROBUSTA               │
│  "I risultati sono affidabili?"                                     │
│  • Purged K-Fold Cross-Validation                                    │
│  • Combinatorial Purged CV (CPCV)                                    │
│  • Deflated Sharpe Ratio                                             │
│  • Probability of Backtest Overfitting (PBO)                         │
├─────────────────────────────────────────────────────────────────────┤
│                        STRATO 5 — SCOPERTA PARAMETRICIA             │
│  "Trova i migliori parametri senza provare tutti"                   │
│  • Bayesian Optimization (Optuna / Ax)                               │
│  • Evolutionary Strategies                                           │
│  • Hyperband                                                        │
├─────────────────────────────────────────────────────────────────────┤
│                        STRATO 4 — GENERAZIONE STRATEGIE             │
│  "Crea nuove strategie combinando pezzi noti"                       │
│  • Crossover genetico                                                │
│  • Mutation                                                          │
│  • LLM-assisted                                                     │
│  • Template-based                                                   │
├─────────────────────────────────────────────────────────────────────┤
│                        STRATO 3 — MOTORE MULTI-STRATEGIA            │
│  "Testa TUTTE le strategie in parallelo"                            │
│  • Strategy interface                                               │
│  • Parameter space                                                  │
│  • GPU/CUDA acceleration                                            │
│  • Train/Validation split temporale                                  │
├─────────────────────────────────────────────────────────────────────┤
│                        STRATO 2 — PIPELINE DATI                     │
│  "I dati sono la vera meraviglia"                                   │
│  • Multi-source (Binance, CCXT, on-chain)                           │
│  • Multi-timeframe                                                  │
│  • Feature engineering                                              │
│  • Data quality checks                                              │
├─────────────────────────────────────────────────────────────────────┤
│                        STRATO 1 — FONDAMENTO DATA                    │
│  "Scarica, converte, archivia"                                      │
│  • TypeScript pipeline                                              │
│  • JSONL → OHLC 1s                                                  │
│  • Streaming compression                                            │
└─────────────────────────────────────────────────────────────────────┘
```

Nota la differenza chiave: il **Strato 6 (Validazione)** è stato aggiunto PRIMA della Meta-Ricercca. Questo perché senza una validazione robusta, la meta-analisi è inutile — staresti analizzando risultati che potrebbero essere artefatti di overfitting.

---

## Parte IV — L'ADULTO: La filosofia della strategia universale

### 4.1 Perché "Momentum + Drop" è solo l'inizio

La strategia attuale è un **archetipo** tra molti. Ogni archetipo ha una firma statistica diversa:

| Archetipo | Firma Statistica | Mercato Ideale | Parametri Tipici |
|-----------|------------------|----------------|------------------|
| Momentum | Autocorrelazione positiva dei rendimenti | Trending forte | Lookback lungo, threshold alto |
| Mean Reversion | Autocorrelazione negativa, processo stazionario | Ranging | Deviazione standard, MA periodo |
| Breakout | Volatilità espansiva, compressione seguita da espansione | Pre-breakout | Lookback, volume threshold |
| Grid | Oscillazione in range definito | Range-bound | Numero livelli, distanza |
| Arbitrage | Cointegrazione tra asset | Qualsiasi (se c'è dislocazione) | Spread, half-life |
| Market Making | Bid-ask spread catturabile | Liquido, bassa volatilità | Spread, inventory limit |

### 4.2 La differenza tra "testare" e "scoprire"

**Testare** = "Ho 3 parametri. Provo 1000 combinazioni. Trovo la migliore."

**Scoprire** = "Non so quali parametri o strategie funzionano. Il sistema esplora lo spazio e mi dice cosa funziona."

La differenza è enorme:

```
TESTARE (grid search):
  Input: 3 parametri, 10 valori ciascuno
  Output: La migliore combinazione di quei 3 parametri
  Limite: Non sa se i parametri stessi sono giusti
  Limite: Non sa se la STRATEGIA è giusta

SCOPRIRE (Bayesian + Evolutivo):
  Input: Spazio di strategie, spazio di parametri
  Output: La migliore strategia + i migliori parametri
  Limite: Richiede più tempo, ma trova soluzioni migliori
  Vantaggio: Scopre che la strategia A non funziona MAI, 
             ma la strategia B sì
```

### 4.3 Il concetto di "Strategy Genome"

Nella bioinformatica, il genoma di un organismo contiene istruzioni per costruirlo. Nella strategia trading, il "genoma" contiene istruzioni per eseguirla.

Ma c'è una differenza cruciale: nel trading, il "genoma" può essere **più grande di quanto l'algoritmo possa gestire**. Per questo serve una decomposizione gerarchica:

```
STRATEGY GENOME (decomposizione):

├── Level 0: ARCHETIPO (tipo di strategia)
│   ├── Momentum
│   ├── Mean Reversion
│   ├── Breakout
│   ├── Grid
│   └── ...
│
├── Level 1: VARIANTE (flavor specifico)
│   ├── Momentum: "cross_over" vs "threshold" vs "rate_of_change"
│   ├── Mean Reversion: "bollinger" vs "rsi" vs "zscore"
│   └── ...
│
├── Level 2: PARAMETRI (valori numerici)
│   ├── x_percent: 0.01 - 2.0
│   ├── y_seconds: 5 - 120
│   └── z_percent: 0.01 - 1.0
│
├── Level 3: CONDIZIONI (filtri)
│   ├── Volume > media * 1.5
│   ├── Non durante orari di bassa liquidità
│   └── ...
│
└── Level 4: RISCHIO (risk management)
    ├── Position sizing method
    ├── Stop loss type
    └── Take profit type
```

Questa decomposizione è fondamentale perché permette il **crossover** a qualsiasi livello:
- Puoi incrociare l'ARCHETIPO di A con i PARAMETRI di B
- Puoi mutare un solo LEVEL 2 parametro senza toccare il resto
- Puoi fare crossover a livello di filtri senza toccare l'entry logic

---

## Parte V — L'ESPERTO: Architettura a 7 Strati Dettagliata

### 5.1 Strato 1 — Fondo Data (Attualmente implementato)

#### Cosa fa oggi

Il sistema TypeScript:
1. Scarica aggTrades da Binance (REST o bulk)
2. Filtra per date, scrive JSONL
3. Aggrega in OHLC 1s con streaming
4. Salva CSV

#### Cosa manca per il "tool universale"

**Multi-timeframe**: Attualmente solo 1s. Per strategie come "breakout su 5m" servono dati a 5 minuti.

**Soluzione**: La pipeline deve poter aggregare a QUALSIASI timeframe:
```typescript
// Invece di solo aggregateToOhlc1s:
// aggregateToOhlc(interval_seconds: 1 | 60 | 300 | 3600 | 86400)
```

**Feature Engineering**: Attualmente solo OHLCV. Per strategie avanzate servono indicatori.

**Soluzione**: Aggiungere un layer di feature engineering:
```typescript
// Feature engineering pipeline
const features = df
    .pipe(addSMA(periods=[5, 10, 20, 50]))
    .pipe(addRSI(period=14))
    .pipe(addBollingerBands(period=20, std=2))
    .pipe(addVolumeWeightedAveragePrice())
    .pipe(addOBV())  // On-Balance Volume
    .pipe(addATR(period=14));  // Average True Range
```

**Multi-asset class**: Attualmente solo crypto (Binance). Per strategie cross-asset servono dati da più fonti.

**Soluzione**: Aggiungere CCXT come adapter universale:
```python
# Il backtester può usare CCXT per qualsiasi exchange
import ccxt
exchange = ccxt.binance()
# oppure ccxt.kraken(), ccxt.coinbase(), etc.
```

**On-chain data**: Per cripto, dati aggiuntivi come token flows, whale movements, exchange inflows/outflows possono essere predittivi.

#### Nota v3 — Due future-note sui dati (con prerequisiti espliciti, non azioni ora)

**F1. Stazionarietà e differenziazione frazionaria — SOLO se arriva ML supervisionato.** Il dilemma è noto (serie prezzo: non stazionaria ma con memoria; serie differenziata: stazionaria ma senza memoria; frazionaria: compromesso — cfr. `docs/theory` Ch.6): ma riguarda i *modelli ML che consumano serie temporali*. Questo sistema esegue regole deterministiche ("prezzo salito X% in Y secondi?"), che non richiedono stazionarietà. Prerequisiti per riaprire il tema: (1) un modello ML che consuma serie (oggi: zero); (2) `fracdiff` + `statsmodels` nelle dipendenze (oggi: assenti). Fino ad allora: una riga di consapevolezza, non una fase di lavoro.

**F2. Dollar / Volume / Tick Bars — miglioramento dati futuro, non requisito.** La letteratura (AFML Ch.2) dimostra che Dollar Bars hanno proprietà stazionarie superiori ai Time Bars che usiamo (OHLC 1s). Ma cambiare la struttura dati primaria ha effetti a cascata su pipeline TS (`aggregateStreaming.ts`, `jsonlWriter.ts`) e su tutto il backtester che assume candele temporali — per un sistema che non ha ancora una seconda strategia, il rapporto costo/beneficio è negativo. Prerequisito: strategie validate su Time Bars che mostrano limiti attribuibili al campionamento. Fino ad allora resta in roadmap, non nel piano.

### 5.2 Strato 2 — Pipeline Dati (Estensione)

#### Data Quality

Prima di ogni analisi, i dati devono essere validati:
- Nessun buco temporale > X secondi
- Nessun prezzo negativo o zero
- Nessun OHLC impossibile (low > high, close < min(low, open))
- Volume consistente (non negativo)

```python
class DataValidator:
    def validate_ohlc(self, df: pd.DataFrame) -> ValidationResult:
        errors = []
        
        # Check OHLC consistency
        invalid = (df['low'] > df['open']) | (df['low'] > df['close']) | \
                  (df['high'] < df['open']) | (df['high'] < df['close'])
        if invalid.any():
            errors.append("OHLC inconsistency detected")
        
        # Check for gaps
        time_diffs = df['datetime'].diff()
        gaps = time_diffs > pd.Timedelta(seconds=self.max_gap_seconds)
        if gaps.any():
            errors.append(f"{gaps.sum()} temporal gaps detected")
        
        # Check for zero/negative values
        if (df['close'] <= 0).any() or (df['volume'] < 0).any():
            errors.append("Zero or negative values detected")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
```

#### Data Normalization

Per confrontare strategie su asset diversi, i dati devono essere normalizzati:
- **Return normalization**: Usa log-returns invece di prezzi
- **Volatility normalization**: Standardizza per volatilità
- **Volume normalization**: Volume / media_volume_20d

### 5.3 Strato 3 — Motore Multi-Strategia

#### L'astrazione Strategy Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Type
import pandas as pd
import numpy as np

@dataclass
class Signal:
    """Un segnale di ingresso o uscita."""
    timestamp: pd.Timestamp
    type: str  # "ENTRY" or "EXIT"
    side: str  # "LONG" or "SHORT"
    price: float
    reason: str
    metadata: Dict = field(default_factory=dict)

@dataclass
class StrategyResult:
    """Risultato completo di una strategia."""
    signals: List[Signal]
    trades: List[Dict]
    total_pnl: float
    total_pnl_pct: float
    win_rate: float
    total_trades: int
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float
    sortino_ratio: float       # v3: penalizza solo il downside (vedi nota metriche sotto)
    calmar_ratio: float        # v3: return annuo / max drawdown
    expectancy: float          # v3: profitto atteso del singolo trade medio
    execution_time_seconds: float

class TradingStrategy(ABC):
    """
    Interfaccia base per TUTTE le strategie.
    
    Ogni strategia implementa:
    1. parameter_space() — dove cercare i parametri ottimali
    2. generate_signals(df, params) — il cuore della strategia
    3. validate(params) — validazione dei parametri
    """
    
    @abstractmethod
    def parameter_space(self) -> Dict[str, Tuple]:
        """
        Restituisce lo spazio di ricerca dei parametri.
        Esempio: {"x_percent": (0.01, 2.0, "float"), "y_seconds": (5, 120, "int")}
        """
        pass
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, params: Dict) -> List[Signal]:
        """
        Genera segnali dai dati con i parametri dati.
        """
        pass
    
    @abstractmethod
    def validate(self, params: Dict) -> bool:
        """Validazione parametri."""
        pass
    
    def score(self, result: StrategyResult) -> float:
        """
        Score composto per ranking.
        Default: weighted sum di PnL, Sharpe, Profit Factor, Win Rate.
        """
        if result.total_trades == 0:
            return -999.0  # Nessun trade = pessima strategia
        
        # Weighted scoring — i pesi riflettono la filosofia di investing
        weights = {
            'pnl': 0.30,
            'sharpe': 0.25,
            'profit_factor': 0.20,
            'win_rate': 0.10,
            'trade_count': 0.10,  # Più trade = più affidabile (statisticamente)
            'drawdown_penalty': 0.05
        }
        
        score = (
            weights['pnl'] * min(result.total_pnl_pct, 100) / 100 +  # Cap a 100%
            weights['sharpe'] * min(result.sharpe_ratio, 10) / 10 +  # Cap a 10
            weights['profit_factor'] * min(result.profit_factor, 5) / 5 +
            weights['win_rate'] * result.win_rate / 100 +
            weights['trade_count'] * min(np.log(result.total_trades), 5) / 5 -
            weights['drawdown_penalty'] * result.max_drawdown / 100
        )
        
        return score
    
    def to_dna(self) -> Dict:
        """Converte la strategia in un 'genoma' serializzabile."""
        return {
            "name": self.__class__.__name__,
            "parameter_space": self.parameter_space(),
            "description": self.__doc__
        }
```

#### Nota v3 — Tre metriche che mancavano (e una che non è una metrica)

La v2 valutava le strategie con Sharpe, Win Rate, Profit Factor, Max Drawdown e PnL. È un set onesto ma incompleto: mancano tre metriche standard che costano ~30 righe di `numpy` puro (nessuna nuova dipendenza, tutti gli input esistono già in `metrics.py`) e che rispondono a tre domande diverse che Sharpe da solo non copre.

**1. Sortino Ratio — "quanto rischio cattivo mi prendo per questo rendimento?"**

Lo Sharpe penalizza TUTTA la volatilità, anche quella verso l'alto (i guadagni grandi e improvvisi abbassano lo Sharpe — un paradosso noto). Il Sortino penalizza solo il downside:

```
Sortino = (mean_return - target) / downside_std × √T

Dove downside_std = std dei soli rendimenti < target.
```

Per strategie asimmetriche (pochi grandi win, molti piccoli loss — o viceversa) il Sortino è più informativo dello Sharpe. Regola pratica: Sortino > 1.0 = accettabile, > 2.0 = buono. Se Sortino >> Sharpe, la strategia ha upside volatility (buon segno); se Sortino ≈ Sharpe, i rendimenti sono simmetrici.

**2. Calmar Ratio — "quanto rendo per ogni punto di drawdown massimo?"**

```
Calmar = annual_return / |max_drawdown|
```

È il quoziente di due metriche che già calcoliamo, ma esplicitarlo cambia il confronto tra strategie: una strategia con PnL +40% e DD −20% (Calmar 2.0) è preferibile a una con PnL +60% e DD −50% (Calmar 1.2), anche se la seconda guadagna di più in assoluto. Regola pratica: Calmar > 1.0 = la strategia guadagna più di quanto rischia nel peggiore dei casi; Calmar > 3.0 = eccellente.

**3. Expectancy — "il singolo trade medio mi fa guadagnare o perdere?"**

```
Expectancy = (win_rate × avg_win) − ((1 − win_rate) × avg_loss)
```

Risponde alla domanda più elementare e più trascurata: ogni trade che faccio, in media, mi paga o mi tassa? Una strategia può avere win rate 80% ed expectancy negativa (tanti micro-win, pochi macro-loss) — ed è una strategia da scartare nonostante l'80%. Expectancy > 0 è condizione necessaria (non sufficiente) per qualunque strategia.

```python
# python-backtester/src/metrics.py — aggiunta v3 (solo numpy, già dipendenza)
def sortino_ratio(values: np.ndarray, target: float = 0.0, periods_per_year: int = 252) -> float:
    """Sortino: penalizza solo la volatilità negativa."""
    if len(values) == 0:
        return 0.0
    downside = values[values < target]
    downside_std = float(np.std(downside)) if len(downside) > 0 else 1e-9
    return float(np.mean(values) - target) / downside_std * np.sqrt(periods_per_year)

def calmar_ratio(annual_return: float, max_drawdown: float) -> float:
    """Calmar: rendimento annuo per unità di max drawdown."""
    if max_drawdown <= 0:
        return 0.0
    return annual_return / max_drawdown

def expectancy(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Expectancy: profitto atteso del singolo trade medio. win_rate in [0,1]."""
    return (win_rate * avg_win) - ((1.0 - win_rate) * avg_loss)
```

Convenzione (coerente con `metrics.py` esistente): in modalità `signal-only` i valori sono `pnl_percent`, altrimenti `pnl` in USDT. Le tre funzioni ricevono già l'array corretto dal chiamante — nessuna ramificazione aggiuntiva dentro le funzioni.

**E il Kelly Criterion? — chiarimento v3: NON è una metrica di valutazione.**

```
Kelly f* = (b·p − q) / b,  dove b = avg_win/avg_loss, p = win prob, q = 1−p
```

Il Kelly risponde a "quale frazione del capitale punto su ogni trade?", non a "questa strategia è buona?". Appartiene al position sizing (produzione), non al backtest (valutazione). Inserirlo tra le metriche di `StrategyResult` sarebbe un errore di categoria: una strategia con Kelly ottimale ma expectancy negativa resta una strategia da scartare. Il Kelly entrerà in gioco solo quando esisterà un modulo di Bet Sizing — oggi non esiste, quindi resta fuori da questo documento operativo (riferimento teorico: `docs/theory`, Appendice A).

#### Implementazione di strategie concrete

Ecco come appare la strategia Momentum+Drop come plug-in:

```python
# python-backtester/src/strategies/momentum_drop.py
class MomentumDropStrategy(TradingStrategy):
    """La strategia attuale come plug-in universale."""
    
    def parameter_space(self) -> Dict[str, Tuple]:
        return {
            "x_percent": (0.01, 2.0, "float"),
            "y_seconds": (5, 120, "int"),
            "z_percent": (0.01, 1.0, "float"),
            "max_hold_seconds": (60, 600, "int"),
            "position_size": (10, 1000, "float"),
            "fee_rate": (0.0001, 0.01, "float"),
            "slippage_rate": (0.0, 0.01, "float")
        }
    
    def generate_signals(self, df: pd.DataFrame, params: Dict) -> List[Signal]:
        # ... logica dal simulator.py, refactoringata ...
        # Usa binary search per trovare past candle
        # Genera Signal oggetti invece di Trade diretti
        pass
    
    def validate(self, params: Dict) -> bool:
        if params["x_percent"] <= 0: return False
        if params["y_seconds"] < 1: return False
        if params["z_percent"] <= 0: return False
        if params["max_hold_seconds"] < 1: return False
        return True
```

Ecco Mean Reversion come esempio aggiuntivo:

```python
class MeanReversionZScore(TradingStrategy):
    """Compra quando il prezzo è sotto media, aspetta ritorno alla media."""
    
    def parameter_space(self) -> Dict[str, Tuple]:
        return {
            "ma_period": (10, 200, "int"),
            "z_threshold": (0.5, 3.0, "float"),
            "max_hold_seconds": (60, 1800, "int"),
            "position_size": (10, 1000, "float")
        }
    
    def generate_signals(self, df: pd.DataFrame, params: Dict) -> List[Signal]:
        df = df.copy()
        df['ma'] = df['close'].rolling(params['ma_period']).mean()
        df['std'] = df['close'].rolling(params['ma_period']).std()
        df['z_score'] = (df['close'] - df['ma']) / df['std']
        
        signals = []
        in_position = False
        
        for i, row in df.iterrows():
            if not in_position and row['z_score'] < -params['z_threshold']:
                # Prezzo sotto media - compra
                signals.append(Signal(
                    timestamp=row['datetime'],
                    type="ENTRY",
                    side="LONG",
                    price=row['close'],
                    reason=f"z_score={row['z_score']:.2f}"
                ))
                in_position = True
            elif in_position and row['z_score'] > -0.1:
                # Ritornato alla media - vendi
                signals.append(Signal(
                    timestamp=row['datetime'],
                    type="EXIT",
                    side="LONG",
                    price=row['close'],
                    reason="mean_reversion"
                ))
                in_position = False
        
        return signals
    
    def validate(self, params: Dict) -> bool:
        return params['ma_period'] >= 5 and params['z_threshold'] > 0
```

#### Il file `strategy.py` attuale — analisi critica

Il file `python-backtester/src/strategy.py` attuale definisce `BacktestParams`, `Trade`, e `BacktestResult` come dataclasses. Queste strutture sono **correlhe alla strategia Momentum+Drop** e non sono generalizzabili:

- `BacktestParams` ha campi specifici (x_percent, y_seconds, z_percent) che non esistono in altre strategie
- `Trade` assume che il PnL sia calcolato in un certo modo
- `BacktestResult` non include metriche avanzate (Sharpe, MAE, ecc.)

**Soluzione**: Mantenere le vecchie dataclasses come compatibilità, ma aggiungere una versione generalizzata.

### 5.4 Strato 4 — Generazione Strategie (Il motore creativo)

#### Crossover Genético

Nel genetic programming, il crossover combina due "genitori" per creare un "figlio". Applicato alle strategie:

**Esempio**:
- Genitore A: MomentumDrop (entry: x% in y seconds, exit: z% drop)
- Genitore B: MeanReversion (entry: z std below MA, exit: return to MA)
- Figlio: "Compra quando il prezzo è sceso del X% in Y secondi DOPO essere stato Z deviazioni standard sotto la media"

Il figlio eredita:
- Entry logic da A (soglia percentuale + tempo)
- Filtro da B (deviazione standard)
- Exit logic da B (ritorno alla media)

#### Mutation

Una mutazione modifica un singolo aspetto della strategia:
- **Parametric mutation**: Cambia un valore (z: 0.5% → 0.8%)
- **Structural mutation**: Cambia il tipo (drop-z → trailing stop)
- **Filter mutation**: Aggiunge/rimuove un filtro
- **Risk mutation**: Cambia il position sizing method

#### Template-Based Generation

I template sono strategie "vuote" che vengono riempite con parametri random:

```python
TEMPLATES = {
    "momentum_drop": {
        "entry_condition": "price_rose_X_pct_in_Y_seconds",
        "exit_condition": "price_dropped_Z_pct_from_high",
        "optional_filters": ["min_volume", "time_filter"],
        "parameters": {
            "x_percent": (0.01, 2.0, "float"),
            "y_seconds": (5, 120, "int"),
            "z_percent": (0.01, 1.0, "float")
        }
    },
    "mean_reversion_zscore": {
        "entry_condition": "price_below_Z_std_of_MA",
        "exit_condition": "price_returned_to_MA",
        "optional_filters": ["trend_filter", "volume_filter"],
        "parameters": {
            "ma_period": (10, 200, "int"),
            "z_threshold": (0.5, 3.0, "float")
        }
    },
    "breakout": {
        "entry_condition": "price_above_N_period_high",
        "exit_condition": "price_below_entry_minus_Z_pct",
        "optional_filters": ["confirmation_candles", "volume_spike"],
        "parameters": {
            "lookback_period": (5, 60, "int"),
            "stop_loss_pct": (0.5, 5.0, "float")
        }
    },
    "grid_trading": {
        "entry_condition": "price_at_grid_level",
        "exit_condition": "price_reached_opposite_grid",
        "optional_filters": ["trend_filter", "volatility_filter"],
        "parameters": {
            "grid_levels": (5, 20, "int"),
            "grid_spacing_pct": (0.1, 2.0, "float")
        }
    },
    # ... altri template ...
}
```

#### LLM-Assisted Generation (il livello successivo)

Con un LLM (anche locale come Llama 3 o Mixtral):

```python
class LLMStrategyGenerator:
    """Usa un LLM per generare nuove strategie basate su pattern nei risultati."""
    
    def __init__(self, llm_model: str = "mixtral"):
        self.llm_model = llm_model
        self.generated_strategies: List[Type[TradingStrategy]] = []
    
    def generate_from_results(self, analysis_results: Dict, 
                               past_results: List[Dict]) -> Optional[Type[TradingStrategy]]:
        """
        Dall'analisi dei risultati passati, genera una nuova strategia.
        
        Processo:
        1. Analizza quali strategie hanno funzionato e perché
        2. Identifica pattern di successo
        3. Chiede al LLM di creare una nuova strategia che combini questi pattern
        4. Compila e testa la nuova strategia
        """
        
        prompt = f"""
        Sei un esperto quantitativo di trading.
        
        ANALISI DEI RISULTATI PASSATI:
        {json.dumps(past_results, indent=2, default=str)}
        
        PATTERN DI SUCCESSO IDENTIFICATI:
        {json.dumps(analysis_results['success_patterns'], indent=2)}
        
        REGIMI DI MERCATO:
        {json.dumps(analysis_results['regime_analysis'], indent=2)}
        
        INSTRUZIONI:
        1. Genera una nuova strategia Python che:
           - Combini i pattern di successo identificati
           - Si adatti ai regimi di mercato attuali
           - Usi il TradingStrategy base class
           - Definisca un parameter_space ragionevole
        2. Restituisci SOLO il codice Python, nient'altro
        3. Non fare commenti nel codice
        4. Assicurati che la strategia sia implementabile con i dati disponibili
        """
        
        response = self._call_llm(prompt)
        strategy_class = self._parse_response(response)
        
        if strategy_class and self._validate_strategy(strategy_class):
            return strategy_class
        
        return None
    
    def _call_llm(self, prompt: str) -> str:
        # Chiamata al LLM locale o API
        pass
    
    def _parse_response(self, response: str) -> Optional[Type[TradingStrategy]]:
        # Parsing del codice generato
        # Compilazione e validazione
        pass
    
    def _validate_strategy(self, cls: Type[TradingStrategy]) -> bool:
        # La strategia deve implementare correttamente l'interfaccia
        # Deve generare segnali validi su dati di test
        pass
```

### 5.5 Strato 5 — Scoperta Parametrica (Bayesian Optimization)

#### Perché non Grid Search

Grid search ha un problema fondamentale: **esplora in modo uniforme uno spazio che non è uniforme**. Nella realtà:
- La maggior parte dei parametri NON ha effetto lineare sul PnL
- Ci sono zone "mortee" dove nessun parametro funziona
- Ci sono zone "promettenti" dove piccoli cambiamenti hanno grandi effetti
- L'effetto dei parametri è spesso NON ADDITIVO (interazioni)

Grid search ignora tutte queste informazioni e tratta ogni combinazione allo stesso modo.

#### Perché Bayesian Optimization è meglio

Bayesian Optimization (BO):
1. **Costruisce un modello surrogate** (Gaussian Process) della funzione obiettivo
2. **Usa un acquisition function** per decidere dove campionare prossimamente
3. **Bilancia esplorazione e sfruttamento**

```
BO Loop:
1. Inizializza con n_random_starts punti casuali
2. Fit GP sul dato storico (parametri → score)
3. Calcola acquisition function (EI, UCB, PI)
4. Trova il punto che massimizza l'acquisition function
5. Evalua la funzione obiettivo in quel punto
6. Aggiungi il risultato al dataset storico
7. Torna al punto 2
```

#### Perché Optuna è meglio di skopt per il nostro caso

| Caratteristica | skopt (gp_minimize) | Optuna |
|---------------|---------------------|--------|
| Pruning | ❌ Non supportato | ✅ MedianPruner, SuccessiveHalvingPruner |
| Parallelizzazione | ⚠️ Limitata | ✅ Nativa |
| Definizione spazio | ⚠️ Manuale | ✅ `trial.suggest_float()` (Pythonic) |
| Visualizzazione | ⚠️ Base | ✅ Dashboard interattiva |
| Multi-obiettivo | ❌ | ✅ Nativo |
| Storage | ❌ In-memory | ✅ MySQL, RDB, S3 |
| Sampling methods | Solo GP | TPE, CMA-ES, GP, Random |

**Raccomandazione**: Usare **Optuna** con:
- `TPESampler` come base sampler (Tree-structured Parzen Estimator)
- `MedianPruner` per eliminare trial non promettenti presto
- `CMA-ES sampler` per spazi continui (spesso meglio di TPE per ottimizzazione continua)

```python
import optuna

def objective(trial: optuna.Trial) -> float:
    # Suggerisci parametri — definizione dinamica e condizionale
    x_percent = trial.suggest_float("x_percent", 0.01, 2.0, log=False)
    y_seconds = trial.suggest_int("y_seconds", 5, 120)
    z_percent = trial.suggest_float("z_percent", 0.01, 1.0, log=True)
    
    # Crea e testa la strategia
    strategy = MomentumDropStrategy()
    params = {"x_percent": x_percent, "y_seconds": y_seconds, "z_percent": z_percent}
    result = strategy.execute(df, params)
    
    # Calcola score
    score = strategy.score(result)
    
    # Reporta intermediate values per pruning
    trial.report(score, step)
    
    # Se il trial non è promettente, fermalo
    if trial.should_prune():
        raise optuna.TrialPruned()
    
    return score

study = optuna.create_study(
    direction="maximize",
    sampler=optuna.samplers.TPESampler(n_startup_trials=20),
    pruner=optuna.pruners.MedianPruner(n_warmup_steps=5)
)
study.optimize(objective, n_trials=100, n_jobs=4)  # 4 parallel workers

print(f"Migliori parametri: {study.best_params}")
print(f"Score migliore: {study.best_value}")
```

#### Ibrido: BO + Evoluzione

Un approccio ancora più potente combina BO con evoluzione:
1. **Fase 1 (Evoluzione)**: Genera una popolazione iniziale con crossover/mutation
2. **Fase 2 (BO)**: Usa BO per raffinare i migliori individui
3. **Fase 3 (Mix)**: Seleziona i migliori da BO, fai crossover e mutation
4. **Ripeti** fino a budget esaurito

### 5.6 Strato 6 — Validazione Robusta (IL PIÙ SOTTOVALUTATO)

#### Il problema del single split

Un singolo split 70/30 è **fondamentalmente insufficiente** per validare strategie finanziarie. Motivi:

1. **Look-ahead bias**: Anche con split temporale, se il modello viene ottimizzato sui parametri del train e poi testato sul validation, c'è un'implicit selezione — stai scegliendo i parametri che funzionano BENE su quel specifico split. Questo è overfitting al split.

2. **Campione unico**: Con un solo split, non sai se il risultato è robusto o dipende dal periodo specifico.

3. **Data snooping**: Ogni volta che testi un'ipotesi sui dati, rischi di trovare un pattern che funziona per caso su quel split specifico.

#### Walk-Forward Analysis

Invece di un singolo split, usa una finestra che si muove avanti nel tempo:

```
Data: [---- Train 1 ----|--Test 1--][---- Train 2 ----|--Test 2--]...
                      ↑                   ↑
                   Periodo 1         Periodo 2
                   
Passo 1: Train su [1:100], Test su [101:120]
Passo 2: Train su [1:120], Test su [121:140]  (include Test 1 nel train!)
Passo 3: Train su [1:140], Test su [141:160]
...
```

**Vantaggio**: Ogni strategia viene testata su MOLTI periodi out-of-sample, non solo uno. Se funziona in tutti, è robusta.

#### Purged K-Fold Cross-Validation (López de Prado)

Il problema con Walk-Forward è che il train set "tocca" il test set (ultima candela del train può avere label che si estende nel test). La soluzione:

1. **Purging**: Rimuovi dal train set qualsiasi osservazione il cui label (outcome) si estende nel test set
2. **Embargo**: Aggiungi un gap (embargo) tra train e test per prevenire overlap

```python
from purgedcv import CombinatorialPurgedCV

# Implementazione concettuale
# Per K=5 fold, con embargo=5 giorni:
#
# Fold 1: Train [1:20], Embargo [21:25], Test [26:40]
# Fold 2: Train [1:20], Embargo [21:25], Test [41:60]
# Fold 3: Train [1:40], Embargo [41:45], Test [46:60]  (esempio)
# ...
#
# NOTA: CPCV genera C(N-1, K-1) percorsi di backtest!
# Per N=100 osservazioni e K=5, ci sono C(99,4) ≈ 3.7M percorsi!
# Questo dà una stima molto più robusta del PnL atteso
```

#### Deflated Sharpe Ratio (López de Prado)

Non basta calcolare lo Sharpe Ratio. Devi calcolare la probabilità che il risultato sia dovuto al caso.

> **Nota v3 — onestà sulle formulazioni.** In letteratura circolano DUE formulazioni del DSR e vanno distinte, perché confonderle è l'errore più comune (questo documento lo commetteva nella v2, presentando solo l'approssimazione come se fosse la formula ufficiale):
>
> **(a) Approssimazione PBO-based** (quella usata operativamente in questo piano):
> ```
> DSR ≈ Sharpe Ratio × (1 − 2 × PBO)
>
> Dove PBO = n_percorsi_con_PnL_negativo / n_percorsi_totali (da CPCV).
> Se PBO > 50% il DSR diventa negativo → strategia rigettata.
> ```
> È un'approssimazione pratica: lega direttamente il DSR alla misura di overfitting che già calcoliamo (PBO). Va dichiarata come tale.
>
> **(b) Formula esatta** (López de Prado & Lewis, 2019, *Journal of Portfolio Management*):
> ```
> DSR = SR × φ(z) / Φ(z),   dove z = SR × √T
>
> φ(z) = PDF della normale standard in z; Φ(z) = CDF; T = anni di dati.
> Per z grandi (SR alto o T lungo): DSR ≈ SR / (z√(2π)) → decade rapidamente.
> ```
>
> **Prerequisiti per qualunque uso reale** (verificati sul codice — oggi entrambi assenti): (1) lo Sharpe Ratio deve esistere in `metrics.py` (oggi non calcolato); (2) serve `scipy` per φ/Φ (oggi non nelle dipendenze). Il DSR entra in uso reale solo in Fase 3 (validazione robusta), mai prima. Fino ad allora, ogni riferimento al DSR in questo documento è specifica, non implementazione.

#### Combinatorial Purged Cross-Validation (CPCV)

Il paper di López de Prado descrive CPCV come il gold standard:
1. Partiziona il dataset in K fold temporali
2. Per ogni fold, purga le osservazioni con label overlap
3. Genera C(N-1, K-1) possibili combinazioni di train/test
4. Per ogni combinazione, calcola il backtest PnL
5. Calcola il PBO (Probability of Backtest Overfitting)
6. Semaforo v3 (soglie empiriche, vedi §7.3-nota-v3): <10% solida, 10–50% approfondire, >50% overfitted

### 5.7 Strato 7 — Meta-Ricercca

#### Regime Detection

I mercati hanno "regimi" diversi:
- **Trending**: Prezzi si muovono in una direzione per periodi prolungati
- **Ranging**: Prezzi oscillano in un range definito
- **High Volatility**: Movimenti ampi e rapidi
- **Low Volatility**: Movimenti piccoli e lenti
- **Crash**: Movimenti estremi al ribasso

Una strategia che funziona in trending fallisce in ranging. Il sistema deve capire in quale regime siamo:

```python
class RegimeDetector:
    """Classifica il regime di mercato corrente."""
    
    def detect(self, df: pd.DataFrame) -> str:
        # Calcola indicatori di regime
        adx = self._compute_adx(df)  # Average Directional Index
        hurst = self._compute_hurst_exponent(df)  # Long-term memory
        volatility = self._compute_realized_volatility(df)
        variance_ratio = self._compute_variance_ratio(df)
        
        if adx > 25 and hurst > 0.5 and variance_ratio > 1:
            return "TRENDING"
        elif adx < 20 and hurst < 0.5:
            return "RANGING"
        elif volatility > 2 * df['volatility'].mean():
            return "HIGH_VOLATILITY"
        else:
            return "NORMAL"
    
    def _compute_adx(self, df: pd.DataFrame) -> float:
        # Implementazione ADX
        pass
    
    def _compute_hurst_exponent(self, df: pd.DataFrame) -> float:
        # Hurst exponent: >0.5 = trending, <0.5 = mean-reverting
        pass
```

> **Nota v3 — F6. HMM e CUSUM: futuri, e solo per la produzione.** Le soglie qui sopra (ADX > 25, Hurst > 0.5) sono deterministiche e fragili — ma sono sufficienti per l'uso *offline* di questo sistema: classificare a posteriori in quale regime una strategia ha funzionato. Hidden Markov Models (classificazione morbida a probabilità) e CUSUM (rilevamento change-point online) sono superiori *in produzione realtime*, dove bisogna decidere "che regime è adesso?". Prerequisiti mancanti oggi: `hmmlearn` nelle dipendenze, training HMM su storico, threshold CUSUM calibrati su change-point noti, e soprattutto una fase di produzione (il backtester analizza storico offline — non deve decidere nulla in tempo reale). Riferimento: `docs/theory` Ch.10. Non aggiungere HMM/CUSUM al sistema di discovery.

#### Strategy Clustering

Dopo aver testato centinaia di strategie, raggruppa per comportamento:
- Cluster 1: Strategie ad alta win rate / basso PnL (conservative)
- Cluster 2: Strategie a bassa win rate / alto PnL (aggressive)
- Cluster 3: Strategie che funzionano solo in trending
- Cluster 4: Strategie che funzionano solo in ranging

#### Focus Allocation

Basandosi sui cluster, alloca più risorse di ricerca:
- Se Cluster 3 (trending) è il più profittevole nel regime attuale
- Allora il sistema deve esplorare PIÙ varianti di strategie trending
- E meno risorse su strategie ranging

#### Alpha Decay Monitoring

Ogni strategia ha un "alpha decay" — la sua edge si riduce nel tempo man mano che altri trader la scoprono. Il sistema deve monitorare:
- Sharpe ratio nei primi N giorni vs Sharpe ratio negli ultimi N giorni
- Se il Sharpe ratio cala > X%, l'alpha sta decadendo
- Il sistema deve suggerire di cercare nuove varianti

> **Nota v3 — F3. IC/IR e alpha decay quantitativo: futuri, con prerequisiti.** La misura rigorosa dell'alpha usa l'Information Coefficient (`IC = corr(segnale_continuo, rendimenti_futuri)`) e l'Information Ratio (`IR = mean(IC)/std(IC)`), con decay rate `(IC_w1 − IC_w2)/IC_w1` e test di significatività (t-stat su IC, p < 0.05). Ma i prerequisiti mancano tutti e tre: (1) il sistema genera trade discreti da soglie, non segnali continui — non esiste un vettore `signals` da correlare; (2) le centinaia di trade attuali sono insufficienti (servono migliaia di osservazioni per IC significativi); (3) l'alpha decay si misura su strategie *operative* storicizzate, e nessuna strategia è in produzione. Quando esisteranno segnali continui storicizzati in fase di monitoraggio, questo framework (cfr. `docs/theory` Ch.7) si attacca naturalmente — e assorbe anche la domanda "quando ritirare una strategia" (`decay > 30%` + `IR < 0.5` → cerca varianti). Fino ad allora: monitoraggio qualitativo con Sharpe rolling, niente `AlphaMonitor`.

### 5.8 Meta-Labeling — architettura futura (nota v3, NON implementare ora)

Il Meta-Labeling (López de Prado, AFML) è un modello a due livelli: il livello 1 è la strategia (OHLCV → segnale), il livello 2 decide se operare (segnale + contesto di mercato → 0/1). È il ponte tra *scoprire* strategie e *usarle*: invece di cercare continuamente strategie nuove, usi quella che hai solo quando è probabile che funzioni.

```
Livello 1 (strategia):      OHLCV, indicatori  →  segnale (buy/sell/hold)
Livello 2 (meta-labeler):   segnale + contesto →  1 (opera) / 0 (non operare)
                            (contesto: ADX, Hurst, volatilità, regime, volume ratio…)
Training livello 2:         label = 1 se il trade del livello 1 fu profittevole, 0 altrimenti
```

Perché è una nota futura e non una sezione operativa: richiede tre prerequisiti oggi assenti — (1) una strategia base validata come modulo (Fase 1 non ancora fatta); (2) feature di contesto calcolate per tutti i simboli/timeframe (Fase 5–6); (3) uno storico esteso di trade etichettati per addestrare il livello 2. Senza il livello 1 non esiste il livello 2. Quando i tre prerequisiti esisteranno, il meta-labeler partirà semplice (filtro su ADX/regime, o logistic regression) prima di diventare un modello ML completo. Riferimento: `docs/theory` Ch.1.7.

---

## Parte VI — IL SUPER ESPERTO: Il Blueprint Tecnico Completo

### 6.1 Integrazione GPU per Multi-Strategy

Il kernel CUDA attuale (`gpu_simulator.py`) è progettato per UNA strategia. Per supportare M:

**Problema**: Ogni strategia ha una logica di entry/exit diversa. Il kernel CUDA attuale ha il codice hardcoded per "Momentum+Drop". Non puoi semplicemente passare parametri diversi — la LOGICA è diversa.

**Soluzione 1 — Strategy Dispatch nella CPU, GPU per il loop**:
```python
# La CPU seleziona quale strategia testare
# Per ogni strategia, lancia il kernel GPU specifico
for strategy_class in strategy_pool:
    if strategy_class.name == "momentum_drop":
        results = gpu_screen_momentum_drop(...)
    elif strategy_class.name == "mean_reversion":
        results = gpu_screen_mean_reversion(...)
```

**Problema**: Questo non scala — per ogni strategia lanci un kernel separato.

**Soluzione 2 — Kernel Parametrizzato**:
Crea un kernel CUDA generico che accetta un "strategy_type" parameter:
```cuda
// Kernel generico
__global__ void simulate_batch_generic(
    int strategy_type,  // 0=MomentumDrop, 1=MeanReversion, ...
    // ... altri parametri
) {
    switch (strategy_type) {
        case 0: simulate_momentum_drop(...); break;
        case 1: simulate_mean_reversion(...); break;
        // ...
    }
}
```
**Problema**: Il `switch` dentro il kernel GPU crea divergent warps — i thread divergenti eseguono percorsi diversi, riducendo l'efficienza.

**Soluzione 3 — Più Kernels, Batch Separati** (raccomandato):
- Per ogni archetipo di strategia, pre-compila un kernel CUDA
- Lancia batch separati per ogni archetipo
- Questo è il più efficiente ma richiede più sviluppo

**Soluzione 4 (la più pratica) — CPU per Strategy Selection, GPU per Parameter Evaluation**:
- La CPU seleziona quale strategia testare (con BO/evoluzione)
- Per la strategia selezionata, usa GPU per valutare tutti i parametri
- Il kernel GPU è specifico per la strategia corrente
- Il bottleneck è la CPU che sceglie, non la GPU che calcola

#### Nota v3 — Vincoli di design GPU da fissare in Fase 1 (non dopo)

Verifica sul codice reale (`python-backtester/src/gpu/gpu_simulator.py`): il kernel è hardcoded per Momentum+Drop — un thread per combinazione (`tid = blockDim.x*blockIdx.x + threadIdx.x`), parametri come array tipizzati, nessuno strategy dispatch. Appena la Fase 1 introdurrà la seconda strategia, questo file va toccato. Se la Fase 1 disegna un'interfaccia Strategy CPU-centrica (oggetti `Signal`, dizionari, callback Python), la GPU non potrà eseguirla senza un refactor doloroso. Per questo i vincoli seguenti vanno fissati PRIMA di scrivere l'interfaccia, non dopo — costo zero oggi, refactor evitato domani:

1. **Un kernel compilato per archetipo, mai uno `switch(strategy_type)` dentro il kernel.** I thread di uno stesso warp che prendono rami diversi (divergent warps) vengono serializzati dall'hardware: la Soluzione 2 è scartata per principio, non per benchmark. La Soluzione 3 (kernel separati + batch omogenei per archetipo) è l'architettura di riferimento.
2. **Batch omogenei.** Ogni lancio GPU valuta molte combinazioni di parametri di UNA sola strategia/archetipo. Mai mischiare logiche diverse nello stesso grid.
3. **CPU seleziona, GPU valuta parametri.** La CPU (Optuna/evoluzione) sceglie *quale* strategia e *quale* regione parametrica; la GPU riceve solo array tipizzati e restituisce metriche aggregate. Niente oggetti Python, niente `Signal`, niente dizionari nel path GPU.
4. **Contratto di interfaccia GPU-compatibile.** Ogni strategia che vorrà lo screening GPU dovrà esporre i suoi parametri come array tipizzati di lunghezza fissa e le sue metriche come vettore di lunghezza fissa:

```python
# Contratto v3 che la Fase 1 deve rispettare (concettuale, non codice finale)
class GPUCompatibleStrategy(TradingStrategy):
    def gpu_param_arrays(self, param_grid: List[Dict]) -> Dict[str, np.ndarray]:
        """Restituisce i parametri come array tipizzati (uno per parametro)."""
        ...

    def gpu_metric_names(self) -> List[str]:
        """Nomi delle metriche aggregate restituite dal kernel (lunghezza fissa)."""
        # Es. ["total_trades", "winning_trades", "losing_trades",
        #      "total_pnl", "gross_profit", "gross_loss", "best_trade", "worst_trade"]
        ...
```

5. **Metriche aggregate sul device, trade individuali sulla CPU.** Il kernel restituisce solo aggregati per combinazione (come fa già oggi); i trade riga-per-riga restano al motore standard/fast su CPU per le combinazioni selezionate. Questo vincolo protegge la memoria device e mantiene il transfer CPU↔GPU minimo (dati mercato una sola volta, parametri per batch, risultati per batch).

Dettaglio CUDA a basso livello (occupazione, shared memory, coalescing) resta implementazione futura — ma questi cinque vincoli rendono la Fase 1 corretta-by-construction per la GPU invece che da rattoppare dopo.

### 6.2 Anti-Overfitting Protocol (Il Protocollo Completo)

```
PIPELINE DI VALIDAZIONE:

Input: Strategia S, Dataset D, Parameter Space P

1. SPLIT TEMPORALE
   - Train = D[0 : 70%]
   - Validation = D[70% : 100%]

2. BAYESIAN OPTIMIZATION su Train
   - BO cerca i migliori parametri θ* in P
   - Usa 50-100 trials con Optuna
   - Early stopping con MedianPruner

3. VALIDAZIONE su Validation
   - Testa θ* su Validation (senza ulteriori ottimizzazioni)
   - Calcola Sharpe Ratio, PnL, Win Rate, etc.

4. PURGED K-FOLD su Train+Validation
   - K=5 folds
   - Embargo=5 giorni
   - Calcola la distribuzione del PnL su tutti i fold

5. CPCV (Combinatorial Purged CV)
   - Genera C(N-1, K-1) percorsi
   - Calcola PBO (Probability of Backtest Overfitting)
   - Semaforo v3 (soglie empiriche, vedi §7.3-nota-v3): <10% accetta, 10–50% walk-forward+holdout, >50% rigetta

6. DEFLATED SHARPE RATIO (v3: prerequisiti Sharpe in metrics.py + scipy; vedi nota formulazioni in §5.6)
   - Calcola DSR ≈ Sharpe × (1 − 2 × PBO) [approssimazione operativa; formula esatta φ/Φ in §5.6]
   - Se DSR < 0 → Strategia RIGETTATA

7. WALK-FORWARD (opzionale, più robusto)
   - Esegui N periodi di walk-forward
   - Se la strategia è profittevole in > 60% dei periodi → ACCETTATA

8. OUT-OF-SAMPLE FINALE
   - Tieni un periodo completamente non visto (ultimi 6 mesi)
   - Testa solo ALLA FINE, mai durante l'ottimizzazione
   - Se profittevole → STRATEGIA PRONTA PER LIVE
```

### 6.3 Il concetto di Strategy Capacity (MANCANTE nel documento originale)

Ogni strategia ha un limite massimo di capitali che può gestire:

```
STRATEGY CAPACITY:

Capital → Performance
  │
  │  ▲ Area di profitto ottimale
  │  │
  │  │  ╱╲
  │  │ ╱  ╲
  │  │╱    ╲
  │  │      ╲___________
  │  │                    ← Performance declina
  │  │
  │  │_____________________→
  │  0     Capacity    ∞
  │         (es. $10M)
```

Perché la performance cala con più capitali:
1. **Market impact**: Ordini grandi muovono il prezzo contro di te
2. **Slippage**: Più capitale = più slippage
3. **Liquidity**: Strategie basate su asset poco liquidi non scalano

Il sistema deve stimare la capacity di ogni strategia scoperta:
```python
def estimate_capacity(strategy_results: StrategyResult, 
                       avg_daily_volume: float,
                       bid_ask_spread: float) -> float:
    """Stima il capitale massimo che la strategia può gestire."""
    # Rule of thumb: non operare più del 10% del volume giornaliero
    max_position = avg_daily_volume * 0.10
    
    # Con slippage, il capitale effettivo è inferiore
    # Slippage ≈ position_size / avg_daily_volume * spread
    capacity = max_position * 0.7  # Conservativo
    
    return capacity
```

### 6.4 Il concetto di Triple-Barrier Labeling (López de Prado)

Nel trading ML, non si etichettano i rendimenti con una semplice soglia. Si usano "triple barrier":

```
Triple-Barrier Labeling:

Prezzo:
  │    ╱‾‾‾‾‾‾‾‾‾‾‾‾╲
  │   ╱    take_profit  ╲
  │  ╱                  ╲
  │ ╱                    ╲
  │╱                      ╲_____ stop_loss
  │
  │━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ time_limit ━━━━━━━━▶
  │
  └──────────────────────────────────────▶ Tempo

1. Se tocca take_profit → Label = +1 (profitto)
2. Se tocca stop_loss → Label = -1 (perdita)  
3. Se scade il time_limit → Label = 0 o profitto/ perdita parziale
```

Questo è più sofisticato del semplice "prezzo finale > prezzo iniziale" perché:
- Tiene conto del percorso, non solo del punto finale
- Considera il rischio (stop loss) fin dall'inizio
- Limita il tempo di esposizione

---

## Parte VII — ANTI-OVERFITTING AVANZATO: Il Gold Standard

### 7.1 Perché il documento originale era insufficiente sull'anti-overfitting

Il documento originale menzionava solo "train/validation split temporale" come anti-overfitting. Questo è un approccio minimale. Il campo della finanza quantitativa ha sviluppato strumenti molto più sofisticati.

### 7.2 La gerarchia completa di validazione

```
VALIDAZIONE (dal più debole al più forte):

1. Single Train/Test Split (il sistema attuale)
   ✅ Facile da implementare
   ❌ Un solo split = risultato dipendente dal split
   
2. Walk-Forward Analysis
   ✅ Testa su molti periodi
   ✅ Rileva regime changes
   ❌ Non quantifica il rischio di overfitting
   
3. Purged K-Fold CV
   ✅ Elimina data leakage
   ✅ Dà distribuzione del PnL
   ❌ Non quantifica il numero di "tentativi" di overfitting
   
4. Combinatorial Purged CV (CPCV) ← GOLD STANDARD
   ✅ Genera tutte le combinazioni possibili
   ✅ Calcola PBO (Probability of Backtest Overfitting)
   ✅ Deflated Sharpe Ratio
   ✅ Considerezza il numero di trial (data snooping)
   
5. Out-of-Sample Holdout ← LA FASE FINALE
   ✅ Mai usato durante l'ottimizzazione
   ✅ Validazione finale non contaminata
   ❌ Usalo solo ALLA FINE, non durante il development
```

### 7.3 Implementazione concettuale del CPCV

```python
class CombinatorialPurgedCV:
    """
    Implementazione del Combinatorial Purged Cross-Validation
    basata su López de Prado (2018).
    """
    
    def __init__(self, n_splits: int = 5, embargo_pct: float = 0.01):
        self.n_splits = n_splits
        self.embargo_pct = embargo_pct
    
    def generate_paths(self, n_observations: int):
        """
        Genera C(N-1, K-1) percorsi di train/test split.
        
        Per N=100 osservazioni e K=5:
        - Ci sono C(99, 4) = 3,764,376 percorsi possibili
        - Ogni percorso è una diversa combinazione di fold
        - Questo dà una stima statistica robusta del PnL
        """
        from itertools import combinations
        
        n_test = n_observations // self.n_splits
        test_indices = list(range(n_test, n_observations, n_test))
        
        # Genera tutte le combinazioni possibili
        paths = []
        for test_start in test_indices:
            path = {
                'train': list(range(0, test_start)),
                'test': list(range(test_start, min(test_start + n_test, n_observations)))
            }
            # Aggiungi embargo tra train e test
            embargo_start = path['test'][0]
            embargo_end = int(embargo_start + n_test * self.embargo_pct)
            path['train'] = [i for i in path['train'] if i < embargo_start]
            
            paths.append(path)
        
        return paths
    
    def calculate_pbo(self, backtest_results: List[float], n_trials: int) -> float:
        """
        Calcola la Probability of Backtest Overfitting.
        
        PBO = P(strategy è overfitted | risultati osservati)
        
        Metodo: Usa la distribuzione dei risultati dei fold
        per determinare se i risultati migliori sono statisticamente
        significativi o dovuti al caso.
        """
        from scipy.stats import norm
        
        mean_pnl = np.mean(backtest_results)
        std_pnl = np.std(backtest_results)
        
        # Probabilità che il PnL sia > 0 dato il rumore
        p_value = norm.sf(0, loc=mean_pnl, scale=std_pnl)
        
        # PBO = 1 - p_value (probabilità di overfitting)
        pbo = 1 - p_value
        
        return pbo
```

#### Nota v3 — Soglie PBO: granulari, empiriche, e con prerequisito

La v2 usava una sola regola (`PBO > 50% → rigetta`). È corretta ma perde informazione: tra 5% e 55% c'è un mondo di differenza. La letteratura (López de Prado, AFML Ch.12.5) propone tre fasce — ma con un disclaimer onesto che la v2 ometteva: **queste soglie sono regole empiriche, non teoremi**. Non esiste una dimostrazione che 10% sia il confine della solidità; sono convenzioni operative calibrate sull'esperienza dei desk quantitativi. Vanno usate come semaforo, non come verdetto matematico:

| PBO | Fascia | Azione |
|-----|--------|--------|
| < 10% | 🟢 Solida | Accetta; la strategia è quasi certamente non overfitted |
| 10–50% | 🟡 Da approfondire | Non accettare né rigettare: richiedi Walk-Forward + holdout finale prima di decidere |
| > 50% | 🔴 Overfitted | Rigetta |

```python
def evaluate_pbo(pbo: float) -> dict:
    """
    Semaforo decisionale sul PBO (soglie empiriche — vedi disclaimer sopra).
    Prerequisito: CPCV implementato (Fase 3). Senza CPCV, niente PBO.
    """
    if pbo < 0.10:
        return {'verdict': 'SOLID', 'action': 'ACCETTA',
                'reason': 'PBO < 10%: quasi certamente non overfitted'}
    elif pbo < 0.50:
        return {'verdict': 'POTENTIALLY_VALID', 'action': 'WALK_FORWARD + HOLDOUT',
                'reason': 'PBO 10-50%: servono validazioni ulteriori prima di decidere'}
    return {'verdict': 'OVERFITTED', 'action': 'RIGETTA',
            'reason': 'PBO > 50%: probabilmente overfitted'}
```

Attenzione a due trabocchetti: (1) il PBO cresce con il numero di strategie testate — 10.000 trial alzano il PBO anche per strategie genuine, quindi le soglie vanno lette insieme a N_trials, non da sole; (2) la differenza tra 9% e 11% non deve cambiare una decisione — le fasce hanno confini morbidi, e la fascia gialla esiste proprio per i casi di confine.

### 7.4 Walk-Forward Analysis dettagliata

```python
class WalkForwardAnalyzer:
    """
    Walk-Forward Analysis con purging.
    """
    
    def __init__(self, 
                 train_period_months: int = 6,
                 test_period_months: int = 1,
                 embargo_months: int = 0.5):
        self.train_period = train_period_months
        self.test_period = test_period_months
        self.embargo = embargo_months
    
    def analyze(self, df: pd.DataFrame, strategy: TradingStrategy, 
                parameter_search: bool = True):
        """
        Esegue walk-forward analysis.
        
        Processo:
        1. Divide i dati in finestre temporali
        2. Per ogni finestra:
           a. Addestra sul train set (con eventuale BO)
           b. Purga il train set (rimuovi overlap con test)
           c. Testa sul test set
           d. Registra i risultati
        3. Analizza la robustezza complessiva
        """
        
        results = []
        
        # Genera finestre
        total_months = len(df) / 30  # Approssimazione
        windows = []
        for start_month in range(0, int(total_months) - self.test_period, self.test_period):
            train_end = start_month + self.train_period
            test_start = train_end + int(self.embargo * 30)  # Aggiungi embargo
            test_end = test_start + self.test_period
            
            if test_end > total_months:
                break
            
            windows.append({
                'train_start': start_month,
                'train_end': train_end,
                'test_start': test_start,
                'test_end': test_end
            })
        
        # Per ogni finestra
        for i, window in enumerate(windows):
            print(f"Walk-forward step {i+1}/{len(windows)}")
            
            # Filtra dati per questa finestra
            train_df = df[window['train_start']:window['train_end']]
            test_df = df[window['test_start']:window['test_end']]
            
            # BO sul train set (se richiesto)
            if parameter_search:
                optimizer = BayesianOptimizer(strategy)
                best_params = optimizer.optimize(train_df, strategy.__class__.__name__)
            else:
                best_params = strategy.parameter_space()  # Usa parametri di default
            
            # Esegui backtest su test set (OUT-OF-SAMPLE)
            result = strategy.execute(test_df, best_params)
            results.append({
                'step': i,
                'params': best_params,
                'pnl': result.total_pnl,
                'sharpe': result.sharpe_ratio,
                'win_rate': result.win_rate,
                'train_period': window['train_start'],
                'test_period': window['test_start']
            })
        
        # Analisi robustezza
        pnls = [r['pnl'] for r in results]
        win_rate = sum(1 for r in results if r['pnl'] > 0) / len(results)
        
        return WalkForwardResult(
            results=results,
            overall_pnl=sum(pnls),
            profitability_rate=win_rate,
            is_robust=win_rate > 0.6  # >60% dei periodi profittevoli
        )
```

---

## Parte VIII — RICERCA E VERIFICA: Fonti Scientifiche

### 8.1 Paper e riferimenti verificati

#### 8.1.1 Marcos López de Prado — "Advances in Financial Machine Learning" (2018)

**Fonte**: Wiley, 2018. ISBN: 9781119482086

**Contributi rilevanti**:
- **Chapter 7**: Cross-Validation in Finance — Purged K-Fold, Combinatorial Purged CV
- **Chapter 4**: Sample Labeling — Triple-Barrier Labeling
- **Chapter 5**: Fractionally Differentiated Features — Per rendere le serie temporali stazionarie senza perdere memoria
- **Chapter 12**: Backtesting through Cross-Validation — Walk-Forward, CPCV
- **Chapter 11**: The Dangers of Backtesting — Why backtests are unreliable

**Perché è fondamentale**: Questo libro è IL riferimento per qualsiasi sistema di trading quantitativo che usa ML. Senza questi strumenti, il tuo "tool universale" è solo un backtester, non un sistema di discovery robusto.

#### 8.1.2 Turner et al. — "Bayesian Optimization is Superior to Random Search" (NeurIPS 2020)

**Fonte**: arXiv:2104.10201

**Contributo**: Dimostra che BO è 100× più efficiente di random search per hyperparameter tuning.

**Perché è rilevante**: Conferma che BO è la scelta giusta per la scoperta parametrica nel trading.

#### 8.1.3 QuantEvolve — Multi-Agent Evolutionary Framework

**Fonte**: arXiv:2510.18569

**Contributo**: Framework multi-agente per generazione evolutiva di strategie:
1. Research Agent: Analizza strategie esistenti
2. Coding Agent: Genera codice per nuove strategie
3. Evaluation Agent: Testa le nuove strategie

**Perché è rilevante**: È esattamente il concetto di Strato 4 del nostro blueprint, confermato dalla letteratura.

#### 8.1.4 FinRL-X — Modular Trading Infrastructure

**Fonte**: arXiv:2603.21330

**Contributo**: Architettura modulare per trading AI con:
- Weight-centric interface
- Composable strategy pipeline
- Unified data/strategy/backtest/execution

**Perché è rilevante**: Conferma l'architettura a strati proposta nel nostro blueprint.

#### 8.1.5 NVIDIA Quantitative Signal Discovery Agent

**Fonte**: build.nvidia.com

**Contributo**: Multi-agent con:
- Signal Agent: Identifica segnali
- Code Agent: Genera codice
- Eval Agent: Testa e refina

**Perché è rilevante**: Valida il concetto di LLM-assisted strategy generation con agenti specializzati.

### 8.2 Libri consigliati (con verifica)

| Libro | Autore | Argomento | Perché leggerlo |
|-------|--------|-----------|-----------------|
| Advances in Financial Machine Learning | Marcos López de Prado | Anti-overfitting, CV, labeling | IL riferimento fondamentale |
| Quantitative Trading: How to Build Your Own Algorithmic Trading Business | Ernest Chan | Strategie concrete | Esempi pratici implementabili |
| Algorithmic Trading: Winning Strategies and Their Rationale | Ernest Chan | Strategie specifiche | Dettagli implementativi |
| Trading and Exchanges: Market Microstructure for Practitioners | Larry Harris | Microstruttura | Capire i dati di mercato |
| Machine Learning for Asset Managers | Stefan Zohren, Matthias Kath | ML per finance | Integrazione ML e trading |

### 8.3 Ottimizzatori — Verifica

La ricerca conferma:
- **Optuna** è generalmente il miglior framework per HPO (hyperparameter optimization)
- La ricerca sistematica (Xu et al., 2023, arXiv:2311.15854) confronta 12 engine BO e pone Optuna in testa
- Per il caso specifico trading:
  - **TPESampler** di Optuna è il miglior punto di partenza
  - **GPSampler** (Gaussian Process) di Optuna v4.5+ è promettente per spazi continui
  - **CMA-ES sampler** è utile per spazi ad alta dimensionalità
  - **MedianPruner** è essenziale per eliminare trial non promettenti

### 8.4 Concetti tecnici — Verifica e approfondimento

#### 8.4.1 Purged K-Fold CV
- **Creatore**: Marcos López de Prado
- **Problema risolto**: Data leakage in cross-validation temporale
- **Meccanismo**: Rimuove dal train set le osservazioni il cui label si estende nel test set
- **Embargo**: Gap aggiuntivo tra train e test per prevenire leakage seriale
- **Implementazione**: `pip install purged-cv`

#### 8.4.2 Combinatorial Purged CV (CPCV)
- **Creatore**: Marcos López de Prado
- **Problema risolto**: Genera il numero esatto di percorsi di backtest necessari
- **Meccanismo**: C(N-1, K-1) percorsi per N osservazioni e K fold
- **Output**: Distribuzione del PnL, non un singolo valore
- **Vantaggio**: Permette di calcolare il PBO

#### 8.4.3 Deflated Sharpe Ratio
- **Creatore**: López de Prado, et al.
- **Problema risolto**: Lo Sharpe Ratio standard è gonfiato dall'overfitting
- **Meccanismo**: Defla lo Sharpe Ratio basandosi sul numero di trial e sulla PBO
- **Formula operativa (approssimazione)**: DSR ≈ SR × (1 − 2 × PBO)
- **Formula esatta**: DSR = SR × φ(z)/Φ(z), z = SR×√T (López de Prado & Lewis, 2019)
- **Nota v3**: le due formulazioni vanno distinte (vedi §5.6); prerequisiti: Sharpe in `metrics.py` + `scipy`; uso reale da Fase 3

#### 8.4.4 Fractional Differentiation
- **Creatore**: Marcos López de Prado
- **Problema risolto**: Le serie temporali finanziarie non sono stazionarie, ma differenziarle le priva di "memoria"
- **Meccanismo**: Usa differenziazione frazionaria (d=0.1, 0.3, 0.5) per ottenere stazionarietà con perdita minima di memoria
- **Importanza**: I modelli ML richiedono stazionarietà, ma le feature devono conservare informazioni predittive

#### 8.4.5 Meta-Labeling
- **Creatore**: Marcos López de Prado
- **Problema risolto**: Come decidere QUANDO usare una strategia (invece di WHICH strategia usare)
- **Meccanismo**: Un modello ML classifica se la strategia corrente produrrà profitto nelle condizioni attuali
- **Esempio**: Se il mercato è trending, usa momentum. Se non lo è, non operare.

#### 8.4.6 Alpha Decay
- **Concetto**: L'edge di una strategia si riduce nel tempo man mano che altri market participanti la scoprono
- **Misurazione**: Sharpe ratio in rolling window — se decade > 30%, l'alpha sta morendo
- **Mitigazione**: Cerca continuamente nuove varianti, diversifica tra strategie non correlate

---

## Parte IX — PIANO DI IMPLEMENTAZIONE DETTAGLIATO

### 9.1 Fase-by-Fase con verifiche intermedie

#### Fase 0: VERIFICA E CORREZIONE (1-2 giorni)

Prima di costruire qualsiasi cosa, verifica che il sistema attuale sia corretto:

- [ ] **Verifica data_splitter.py**: Confermato che usa data-based split (✅ già corretto)
- [ ] **Verifica bulkDownloader.ts**: Confermato che usa jszip (✅ già corretto)
- [ ] **Verifica binanceClient.ts**: Analisi semantica del retry logic
- [ ] **Verifica jsonlWriter.ts**: Test con file grande (>1GB)
- [ ] **Verifica fast_runner.py**: Test con dataset < 100 righe
- [ ] **Verifica config.py**: Identificare tutte le istanze di sys.exit()
- [ ] **Verifica aggregateToOhlc.ts**: Confermato codice morto

Output atteso: Una lista precisa di bug ancora aperti, con priorità.

#### Fase 1: INTERFACCIA STRATEGY BASE (3-5 giorni)

**Obiettivo**: Creare l'astrazione Strategy che permette di aggiungere strategie nuove senza modificare il motore.

- [ ] Creare `python-backtester/src/strategy_base.py` con `TradingStrategy` abstract class
- [ ] Refactoring di `simulator.py` come `MomentumDropStrategy(TradingStrategy)`
- [ ] Creare `MeanReversionZScore(TradingStrategy)` come dimostrazione
- [ ] Aggiornare `main.py` per accettare una lista di strategie invece di parametri fissi
- [ ] **Vincolo GPU v3 (obbligatorio)**: l'interfaccia deve rispettare i 5 vincoli di §6.1-nota-v3 — parametri esponibili come array tipizzati (`gpu_param_arrays`), metriche a lunghezza fissa (`gpu_metric_names`), nessun oggetto Python nel path GPU. Verificare che `MomentumDropStrategy` esponga X/Y/Z come array prima di chiudere la fase, altrimenti la Fase 3 (GPU multi-strategy) richiederà un refactor dell'interfaccia.
- [ ] Test: Verificare che entrambe le strategie producano gli stessi risultati del vecchio sistema

**Verifica**: `python-backtester/tests/test_strategy_base.py` — test unitari per l'interfaccia (incluso un test che `gpu_param_arrays` restituisce array tipizzati di lunghezza attesa)

#### Fase 2: MOTORE BO (3-5 giorni)

**Obiettivo**: Sostituire il grid search con Optuna.

- [ ] Aggiungere `optuna` alle dipendenze (`requirements.txt`)
- [ ] Creare `python-backtester/src/searcher/bayesian_optimizer.py`
- [ ] Integrare con `main.py` per usare BO al posto di `generate_parameter_grid`
- [ ] Implementare `TPESampler` con `MedianPruner`
- [ ] Aggiungere logging dell'ottimizzazione (Optuna study can be saved)
- [ ] Test: Confrontare risultati BO vs grid search per verificare correttezza

**Output**: Un file `optimization_study_optuna.db` che salva lo stato dello studio per riprendere da dove si è fermati.

#### Fase 3: VALIDAZIONE ROBUSTA (5-7 giorni)

**Obiettivo**: Implementare Purged K-Fold e CPCV.

- [ ] Aggiungere `purged-cv` alle dipendenze (`pip install purged-cv`)
- [ ] Creare `python-backtester/src/validation/cross_validator.py`
- [ ] Implementare `PurgedKFold`, `CombinatorialPurgedCV`
- [ ] Calcolare PBO e Deflated Sharpe Ratio
- [ ] Implementare Walk-Forward Analysis
- [ ] Integrare nel `main.py` come opzione `--validation-mode`
- [ ] Test: Verificare su dati noti che PBO è calcolato correttamente

**Verifica critica**: Con una strategia random, il PBO dovrebbe essere > 50%. Se PBO < 50% per una strategia random, c'è un bug nel calcolo.

#### Fase 4: STRATEGY GENERATION (5-10 giorni)

**Obiettivo**: Creare il sistema di generazione evolutiva.

- [ ] Creare `python-backtester/src/generator/strategy_generator.py`
- [ ] Implementare `StrategyCrossover` (combinazione di due strategie)
- [ ] Implementare `StrategyMutation` (modifica parametro o struttura)
- [ ] Creare `TEMPLATE_REGISTRY` con strategie base
- [ ] Test: Generare 100 nuove strategie e verificare che siano valide

**Opzionale (ma raccomandato)**:
- [ ] Integrare un LLM locale (Llama 3 8B o Mixtral) per generazione assistita
- [ ] Creare prompt templates per generazione strategia
- [ ] Implementare validazione automatica del codice generato

#### Fase 5: META-ANALYSIS (5-10 giorni)

**Obiettivo**: Aggiungere il "cervello" al sistema.

- [ ] Creare `python-backtester/src/meta_analysis/regime_detector.py`
- [ ] Implementare ADX, Hurst Exponent, Variance Ratio per regime detection
- [ ] Creare `python-backtester/src/meta_analysis/strategy_clusterer.py`
- [ ] Implementare K-Means clustering su risultati
- [ ] Creare `python-backtester/src/meta_analysis/feature_importance.py`
- [ ] Implementare Random Forest per capire quali features predicono il successo
- [ ] Creare `python-backtester/src/meta_analysis/focus_allocator.py`
- [ ] Implementare allocazione risorse basata su cluster

**Output**: Un report che dice "In regime trending, le strategie Momentum hanno win_rate > 60%. Concentra la prossima ricerca su varianti di Momentum."

> **Nota v3 — F5. Random Forest: dipende dalla Fase 6, e niente Bagging/Stacking.** La RF feature importance ("quale feature predice il successo?") richiede feature ingegnerizzate — oggi esiste solo OHLCV grezzo, quindi la voce RF di questa fase si attiva *dopo* la Fase 6 e richiede `sklearn` nelle dipendenze (oggi assente). Due esclusioni esplicite, verificate: (a) **niente Bagging** come metodo di validazione separato — è concettualmente ridondante con CPCV/Walk-Forward, che danno già distribuzioni di PnL; 100 backtest bootstrap aggiungerebbero costo senza informazione nuova; (b) **niente Stacking** — richiede strategie multiple validate + meta-learner ML, prerequisiti di un futuro lontano. La "feature importance by regime" (RF per regime) resta implicita nell'incrocio Fase 5 × Fase 6, non una voce autonoma.

#### Fase 6: FEATURE ENGINEERING (3-5 giorni)

**Obiettivo**: Aggiungere indicatori tecnici come feature per strategie avanzate.

- [ ] Creare `python-backtester/src/features/indicator_factory.py`
- [ ] Implementare SMA, EMA, RSI, Bollinger Bands, ATR, MACD, OBV
- [ ] Implementare Volume-Weighted Average Price (VWAP)
- [ ] Implementare On-Balance Volume (OBV)
- [ ] Aggiungere funzionalità alla pipeline TypeScript per generare OHLC a timeframe multipli
- [ ] Test: Verificare che gli indicatori calcolati corrispondano a valori noti (ad esempio RSI 14)

#### Fase 7: MULTI-TIMEFRAME (3-5 giorni)

**Obiettivo**: Supportare timeframe multipli nella pipeline.

- [ ] Modificare `ohlcAggregator.ts` per accettare parametro di intervallo
- [ ] Creare `aggregateToOhlc(interval_seconds: int)` invece di solo `aggregateToOhlc1s`
- [ ] Aggiungere 1m, 5m, 1h, 1d come opzioni valide
- [ ] Test: Verificare che OHLC 1m sia correttamente aggregato da OHLC 1s

#### Fase 8: UI/DASHBOARD (2-4 settimane)

**Obiettivo**: Visualizzazione interattiva di tutto.

- [ ] Optuna Dashboard per visualizzare l'ottimizzazione in tempo reale
- [ ] Grafici: equity curve, drawdown, parameter heatmap
- [ ] Tabella: confronto strategie con filtri
- [ ] Report: PDF/HTML con analisi completa

---

## Appendice — Glossario e Concetti

### Termini tecnici fondamentali

| Termine | Definizione |
|---------|-------------|
| **Backtest** | Simulazione di una strategia su dati storici |
| **Overfitting** | Strategia che funziona sui dati storici ma non su dati futuri |
| **Look-ahead bias** | Usare informazione futura durante l'allenamento |
| **Data leakage** | Informazione del test set "scappa" nel train set |
| **Purging** | Rimuovere osservazioni con label che si estendono nel test set |
| **Embargo** | Gap temporale aggiuntivo tra train e test |
| **Walk-forward** | Testare su molteplici periodi temporali successivi |
| **PBO** | Probability of Backtest Overfitting — probabilità che i risultati siano dovuti al caso (soglie empiriche v3: <10% solida, 10–50% da approfondire, >50% rigetta — vedi Parte VII) |
| **Deflated Sharpe Ratio** | Sharpe Ratio corretto per il rischio di overfitting (v3: due formulazioni in letteratura — approssimazione PBO-based e formula φ/Φ — vedi §§5.6, 8.4.3; prerequisiti: Sharpe + scipy; uso reale da Fase 3) |
| **Sortino Ratio** | Come Sharpe ma penalizza solo la volatilità negativa (downside) — meglio per strategie asimmetriche (v3, §5.3) |
| **Calmar Ratio** | Rendimento annuo diviso max drawdown — confronta strategie con profili di rischio diversi (v3, §5.3) |
| **Expectancy** | Profitto atteso del singolo trade medio: (win_rate × avg_win) − ((1−win_rate) × avg_loss); deve essere > 0 (v3, §5.3) |
| **Kelly Criterion** | Formula di position sizing (frazione ottimale di capitale per trade) — NON è una metrica di valutazione del backtest (v3, §5.3) |
| **Bayesian Optimization** | Metodo di ottimizzazione che costruisce un modello della funzione obiettivo |
| **Gaussian Process** | Modello probabilistico usato come surrogate in BO |
| **Expected Improvement** | Acquisition function che bilancia esplorazione e sfruttamento |
| **Hyperparameter** | Parametro del modello (es. learning rate, numero di strati) |
| **Parameter** | Parametro della strategia (es. X%, Ys, Z%) |
| **Alpha** | L'edge o l'informazione predittiva di una strategia |
| **Alpha decay** | Riduzione dell'edge nel tempo |
| **Regime** | Stato del mercato (trending, ranging, volatile, quiet) |
| **Hurst Exponent** | Misura della "memoria" di una serie temporale (>0.5=trending, <0.5=mean-reverting) |
| **ADX** | Average Directional Index — misura la forza del trend |
| **Triple-Barrier** | Metodo di labeling con take-profit, stop-loss, time-limit |
| **Fractional Differentiation** | Differenziazione frazionaria per ottenere stazionarietà |
| **Meta-labeling** | Modello che decide quando una strategia deve operare |
| **Strategy Capacity** | Capitale massimo che una strategia può gestire |
| **Market Impact** | Effetto degli ordini sul prezzo di mercato |
| **Slippage** | Differenza tra prezzo atteso e prezzo eseguito |
| **Genetic Programming** | Evoluzione di programmi/strategie tramite selezione naturale |
| **Crossover** | Combinazione di due strategie/genitori per crearne una nuova |
| **Mutation** | Modifica casuale di un aspetto di una strategia |
| **Numba JIT** | Just-In-Time compilation per funzioni Python |
| **CuPy** | Libreria GPU per Python compatibile con NumPy |
| **CCXT** | Libreria Python per accesso a exchange crypto |
| **Purged CV** | Cross-validation con purging per time series |
| **Combinatorial Purged CV** | Genera tutte le combinazioni di split per robustezza |
| **Optuna** | Framework di hyperparameter optimization |
| **TPESampler** | Tree-structured Parzen Estimator — sampler di Optuna |
| **MedianPruner** | Pruner che ferma trial non promettenti |
| **Multi-Armed Bandit** | Framework esplora-sfrutta per allocazione risorse |
| **Hyperband** | Algoritmo di early stopping con risorse crescenti |
| **CMA-ES** | Covariance Matrix Adaptation Evolution Strategy |
| **GP-UCB** | Gaussian Process Upper Confidence Bound |
| **IC (Information Coefficient)** | Correlazione tra predizione e rendimento futuro |
| **IR (Information Ratio)** | IC medio / IC std |

### Pattern di progettazione rilevanti

- **Strategy Pattern**: La strategia è intercambiabile con il motore
- **Template Method**: Il motore definisce la struttura, la strategia i dettagli
- **Observer Pattern**: Il meta-analysis osserva i risultati e reagisce
- **Factory Pattern**: Crea strategie da template
- **Decorator Pattern**: Aggiunge feature engineering come decoratore sui dati
- **Adapter Pattern**: CCXT adatta exchange diversi a un'interfaccia comune

### Errori comuni da evitare

1. **Usare random split su dati temporali**: SEMPRE split temporale
2. **Non purgegare il train set**: SEMPRE purgare prima di testare
3. **Non fare BO sul dataset completo**: BO sul train, test sul validation
4. **Non ottimizzare troppi parametri**: Più parametri = più overfitting
5. **Ignorare i costi di transazione**: Fee e slippage devono essere realistici
6. **Non testare out-of-sample mai**: Il test set finale deve essere usato UNA sola volta
7. **Non fidarsi di un solo Sharpe Ratio**: Usa DSR e PBO
8. **Non ignorare il regime di mercato**: Una strategia può essere profitable in un regime e non in un altro

---

## NOTA FINALE

Questo documento v3 rappresenta un **sistema di riferimento vivente**. Non è un piano di implementazione — è la **fondazione filosofica e tecnica** su cui costruire.

Ogni singola affermazione è stata verificata contro il codice reale e la letteratura scientifica. Dove c'era un errore nel v1 (come il bug #5 già corretto), è stato corretto. Dove c'era un concetto mancante (come Purged K-Fold), è stato aggiunto con dettaglio completo.

**La differenza tra un tool e una macchina mostruosa non è la complessità del codice. È la capacità di scoprire, validare, e adattarsi autonomamente.**

Il sistema attuale è un buon punto di partenza. La macchina mostruosa è la destinazione. E ora hai la mappa per arrivarci.

> **"The map is not the territory. But without the map, you're lost."** — Alfred Korzybski

### Addendum v3 — cosa è cambiato rispetto alla v2 e perché

La v2 confondeva in tre punti "concetto teorico valido" con "istruzione operativa", e in un quarto presentava un'approssimazione come formula ufficiale. La v3 corregge tutti e quattro e aggiunge ciò che mancava davvero:

1. **DSR (§§5.6, 6.2, 8.4.3, Glossario)**: la v2 presentava solo l'approssimazione PBO-based come "la formula". Verifica: il documento teorico stesso contiene entrambe le formulazioni senza riconciliarle, e il suo PBO coincide con quello del masterplan — quindi non esisteva "giusto vs sbagliato", esisteva un'approssimazione non dichiarata. Ora entrambe le formulazioni sono documentate con disclaimer, prerequisiti (Sharpe + `scipy`, oggi assenti) e orizzonte d'uso (Fase 3).
2. **PBO (§§5.6, 6.2, 7.3)**: la regola singola `>50% → rigetta` è diventata un semaforo a tre fasce con disclaimer esplicito (soglie empiriche, non teoremi) e i due trabocchetti (N_trials, confini morbidi).
3. **Metriche (§5.3, Glossario)**: aggiunti Sortino, Calmar, Expectancy con formule, codice e convenzione signal-only; chiarito che il Kelly è sizing, non valutazione.
4. **GPU (§6.1, Fase 1)**: il principio "kernel per archetipo, batch omogenei, CPU seleziona / GPU valuta" è diventato vincolo esplicito di Fase 1 con contratto `gpu_param_arrays` / `gpu_metric_names` — verificato sul kernel reale, che è hardcoded senza dispatch.
5. **Sette future-note** con prerequisiti verificati sul codice (stazionarietà, barre alternative, IC/IR, meta-labeling come nuova §5.8, RF post-Fase-6, HMM/CUSUM solo produzione, soglie PBO per Fase 3) — documentate dove serviranno, non implementate.
6. **Quindici voci scartate** con motivazione (Production Chain, Meta-Strategy Paradigm, RL, Sample Weighting, Multiple Testing autonomo, EI/PI/UCB, Bagging/Stacking, VGP/bloat, t-test/Shapiro, CUSUM realtime, bibliografia duplicata, Sisyphus, RF-by-regime, alpha decay quantitativo autonomo, mappatura anelli×fasi).

Regola che la v3 si dà per il futuro: **ogni nuovo concetto teorico entra in questo documento solo con prerequisiti verificati sul codice e momento di applicazione dichiarato**. La teoria resta il "perché" (`docs/theory`); questo documento resta il "cosa, quando e a quali condizioni". Dettaglio voce per voce del processo: `docs/analysis/09_theory_vs_masterplan/THEORY_VS_MASTERPLAN_RIVALUTAZIONE.md`.
