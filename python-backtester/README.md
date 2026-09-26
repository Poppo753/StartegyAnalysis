# 🐍 Python Backtester

Simulatore di strategie storiche su dati OHLC 1s generati dalla pipeline TypeScript di questa repository.

## 📋 Strategia

**"Momentum + Drop"**: Se il prezzo sale di X% in Y secondi, apri un segnale/trade. Poi monitora se dal massimo successivo il prezzo scende di Z%.

### Logica dettagliata:

1. Per ogni candela, calcola il movimento rispetto a Y secondi fa
2. Se il movimento >= X%, genera un segnale di ingresso
3. Dopo l'ingresso, monitora il prezzo:
   - Se il prezzo scende di Z% dal massimo raggiunto → chiudi con "drop-z"
   - Se passano MAX_HOLD_SECONDS → chiudi con "max-hold"
   - Se finisce il dataset → chiudi con "end-of-data"
4. Non si aprono trade sovrapposti (un trade alla volta)

## 🚀 Setup

### Prerequisiti

- Python 3.11+
- Dati OHLC generati dalla pipeline TypeScript in `../data/`

### Installazione (Windows)

```powershell
# 1. Entra nella directory del backtester
cd python-backtester

# 2. Crea un virtual environment
python -m venv .venv

# 3. Attiva il virtual environment
.venv\Scripts\activate

# 4. Installa le dipendenze
pip install -r requirements.txt

# 5. Copia il file di configurazione
copy env.example .env

# 6. Configura i parametri nel file .env
# Modifica SYMBOLS, START_DATE, END_DATE secondo i tuoi dati disponibili

# 7. Esegui il backtester
python main.py
```

### Installazione (Linux/Mac)

```bash
cd python-backtester
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# Modifica .env
python main.py
```

## ⚙️ Configurazione (.env)

| Variabile | Descrizione | Esempio |
|-----------|-------------|---------|
| `DATA_DIR` | Directory dati OHLC | `../data` |
| `OUTPUT_DIR` | Directory output risultati | `./backtest-results` |
| `SYMBOLS` | Simboli da testare | `DCRUSDT` |
| `START_DATE` | Data inizio | `2026-01-01` |
| `END_DATE` | Data fine | `2026-01-02` |
| `TIMEFRAME` | Timeframe candele | `1s` |
| `X_VALUES` | Percentuali salita (griglia) | `0.2,0.5,1` |
| `Y_VALUES` | Finestre temporali in secondi | `10,30,60` |
| `Z_VALUES` | Percentuali discesa (griglia) | `0.1,0.2,0.5` |
| `X_RANGE` | Range automatico X (start:end:step) | _(vuoto)_ |
| `Y_RANGE` | Range automatico Y (start:end:step) | _(vuoto)_ |
| `Z_RANGE` | Range automatico Z (start:end:step) | _(vuoto)_ |
| `MAX_HOLD_SECONDS` | Timeout massimo posizione | `300` |
| `INITIAL_CAPITAL` | Capitale iniziale USDT | `1000` |
| `POSITION_SIZE` | Size per trade USDT | `100` |
| `FEE_RATE` | Commissione (0.001 = 0.1%) | `0.001` |
| `SLIPPAGE_RATE` | Slippage (0.0005 = 0.05%) | `0.0005` |
| `DIRECTION` | Modalità trading | `signal-only` |

### Range automatici per la griglia

Invece di elencare ogni valore manualmente, puoi specificare un range con il formato `start:end:step`:

```ini
# Nel .env
X_RANGE=0.05:2.0:0.05
Y_RANGE=5:600:5
Z_RANGE=0.03:1.5:0.03
```

Regole:
- Se `*_RANGE` è valorizzato, viene usato al posto di `*_VALUES`
- Se `*_RANGE` è vuoto o non presente, si usa `*_VALUES` come prima
- X e Z generano valori **float** (arrotondati a 6 decimali)
- Y genera valori **int**
- `start` deve essere ≤ `end`, `step` deve essere > 0
- All'avvio viene stampato il numero di valori generati per asse e le combinazioni totali
- Se le combinazioni superano **10.000**, viene mostrato un warning (senza bloccare)

Esempio output console:
```
  [GRID] X values: 40 | Y values: 119 | Z values: 49
  [GRID] Combinazioni totali: 233240
  ⚠️  [WARNING] Numero di combinazioni elevato (233240 > 10000). L'esecuzione potrebbe richiedere molto tempo.
```

### Direzioni disponibili:

- **`signal-only`**: Solo segnali, PnL = 0, registra il movimento teorico
- **`long`**: Simula posizioni long con fee e slippage
- **`short`**: Simula posizioni short con fee e slippage

## 📂 Struttura Input

I dati devono essere nella struttura generata dalla pipeline TypeScript:

```
../data/
  {SYMBOL}/
    ohlc/
      ohlc_1s_{START_DATE}_{END_DATE}.csv
```

Formato CSV:
```
timestamp,open,high,low,close,volume,tradeCount
```

## 📂 Struttura Output

```
backtest-results/
  {SYMBOL}/
    summary_{START_DATE}_{END_DATE}.csv
    trades_x{X}_y{Y}_z{Z}.csv
    trades_x{X}_y{Y}_z{Z}.csv
    ...
```

### Summary CSV

Una riga per ogni combinazione X/Y/Z con metriche aggregate.

### Trades CSV

Dettaglio di ogni trade per una specifica combinazione.

## 📊 Metriche calcolate

- **Total trades**: Numero totale di trade
- **Win rate**: Percentuale trade vincenti
- **Total PnL**: Profitto/perdita totale
- **Max drawdown**: Massimo calo dall'equity peak
- **Average PnL**: Media profitto per trade
- **Best/Worst trade**: Miglior/peggior trade
- **Profit factor**: Somma profitti / |Somma perdite|

## 🏗️ Architettura

```
python-backtester/
├── main.py              # Entry point e orchestrazione
├── requirements.txt     # Dipendenze Python
├── env.example          # Template configurazione
├── README.md            # Questa documentazione
└── src/
    ├── __init__.py      # Package init
    ├── config.py        # Caricamento e validazione config
    ├── data_loader.py   # Lettura file OHLC CSV
    ├── strategy.py      # Dataclass (Trade, BacktestParams, BacktestResult)
    ├── simulator.py     # Motore di simulazione standard
    ├── metrics.py       # Calcolo metriche performance
    ├── parameter_grid.py # Generazione combinazioni X/Y/Z
    ├── results_writer.py # Scrittura CSV output
    ├── utils.py         # Utility e formattazione console
    └── fast/            # Fase 2 - Motore accelerato Numba
        ├── __init__.py
        ├── fast_simulator.py  # Core numba @njit
        ├── fast_metrics.py    # Metriche su numpy arrays
        └── fast_runner.py     # Orchestrazione fast engine
```

## 🔮 Roadmap futura

- [x] ~~GPU CUDA (cupy) per parallelizzare sulla RTX 5070~~ ✅ Fase 3
- [x] ~~Anti-overfitting con split TRAIN/VALIDATION~~ ✅ Fase 3
- [ ] Strategie multiple pluggabili
- [ ] Visualizzazione equity curve
- [ ] Supporto multi-timeframe
- [ ] Walk-forward optimization

## ⚠️ Note

- Questa sezione Python è **indipendente** dalla pipeline TypeScript
- Non modifica né interferisce con il download/generazione dati
- Richiede che i dati OHLC siano già stati generati dalla pipeline TS
- `standard` engine: Python puro + pandas, leggibile e debuggabile
- `fast` engine: Numba JIT su CPU, ottimizzato per griglie grandi
- `gpu` engine: screening massivo GPU/CPU + validazione anti-overfitting (Fase 3)

## ⚡ Fase 2 - Fast Engine (Numba JIT)

Il motore **fast** usa [Numba](https://numba.pydata.org/) per compilare la logica di simulazione
in codice macchina nativo, eliminando l'overhead di Python.

### Quando usare fast:

| Scenario | Engine consigliato |
|---|---|
| Debugging strategia | `standard` |
| Poche combinazioni (<50) | `standard` |
| Molte combinazioni (>100) | `fast` |
| Grid search massiva | `fast` |
| Sviluppo/test nuove feature | `standard` |

### Come attivare:

```ini
# Nel .env
BACKTEST_ENGINE=fast
FAST_TOP_N=20
```

### Installazione numba:

```powershell
pip install numba
# oppure reinstalla tutto:
pip install -r requirements.txt
```

### Differenze rispetto a standard:

- **Velocita**: 10-50x piu veloce grazie a JIT compilation
- **Output**: salva trades dettagliati solo per le top N combinazioni
- **Struttura output**: risultati in `backtest-results/{SYMBOL}/fast/`
- **Warmup**: la prima esecuzione ha overhead di compilazione (~2-5s)
- **Logica identica**: stessa strategia, stessi parametri, stessi risultati

### Output fast engine:

```
backtest-results/
  {SYMBOL}/
    fast/
      summary_{START_DATE}_{END_DATE}.csv
      trades_best_001_x{X}_y{Y}_z{Z}.csv
      trades_best_002_x{X}_y{Y}_z{Z}.csv
      ...
```

## 🧠 Fase 3 — Ricerca Strategie Robusta (GPU + Anti-Overfitting)

Il motore **gpu** implementa una pipeline completa per trovare strategie
che funzionano nel mondo reale, non solo sui dati storici.

### Il problema dell'overfitting

Quando testi migliaia di combinazioni su un dataset, troverai SEMPRE qualcosa
che funziona — per puro caso. Questo è **overfitting**: la strategia ha
"memorizzato" il passato ma non ha capacità predittiva.

### La soluzione: Split temporale

```
|← ——————— TRAIN (70%) ——————— →|← — VALIDATION (30%) — →|
|   GPU cerca qui                |   CPU verifica qui      |
|   (in-sample)                  |   (out-of-sample)       |
```

- **TRAIN**: il GPU screening cerca le migliori combinazioni solo su questo periodo
- **VALIDATION**: le strategie vincenti vengono ritestate su dati MAI visti

Se una strategia funziona su TRAIN ma fallisce su VALIDATION → è **overfittata**.
Se funziona su entrambi → è **robusta** e probabilmente ha valore reale.

### Pipeline completa

```
1. GPU SCREENING (TRAIN)
   → testa tutte le combinazioni X/Y/Z
   → output: metriche aggregate (NO trades dettagliati)

2. FILTRI INTELLIGENTI
   → scarta strategie con: pochi trade, win rate basso,
     profit factor insufficiente, drawdown eccessivo

3. SCORING & RANKING
   → score composito (non solo PnL)
   → classifica per robustezza

4. VALIDAZIONE CPU (TRAIN + VALIDATION)
   → ricalcola top N strategie con dettaglio completo
   → confronta risultati TRAIN vs VALIDATION
   → identifica overfitting
```

### Come attivare:

```ini
# Nel .env
BACKTEST_ENGINE=gpu

# Split temporale
TRAIN_RATIO=0.7
VALIDATION_RATIO=0.3

# Filtri
MIN_TRADES=20
MIN_WIN_RATE=40.0
MIN_PROFIT_FACTOR=1.2
MAX_DRAWDOWN_FILTER=30.0

# GPU
GPU_BATCH_SIZE=2048
```

### GPU opzionale:

La GPU (CuPy + CUDA) è **opzionale**. Se non disponibile, il sistema
usa automaticamente Numba parallelo su CPU come fallback.

Per installare il supporto GPU (richiede CUDA toolkit):
```powershell
pip install cupy-cuda12x
```

### Output gpu engine:

```
backtest-results/
  {SYMBOL}/
    gpu/
      summary_train.csv             # Tutte le strategie screened
      filtered_strategies.csv       # Solo quelle che passano i filtri
      best_strategies.csv           # Confronto TRAIN vs VALIDATION
      trades_train_001_x..csv       # Dettaglio trades su TRAIN
      trades_validation_001_x..csv  # Dettaglio trades su VALIDATION
```

### Interpretazione risultati:

| Status | Significato | Azione |
|--------|-------------|--------|
| ✅ ROBUST | Profitto su TRAIN e VALIDATION | Candidata per trading reale |
| ⚠️ OVERFIT | Profitto solo su TRAIN | Scartare — non affidabile |
| ❌ WEAK | Non profittevole neanche su TRAIN | Scartare |

### Metriche avanzate (Fase 3):

| Metrica | Descrizione |
|---------|-------------|
| `sharpe_ratio` | Rendimento medio / volatilità |
| `expectancy` | Valore atteso per trade |
| `avg_win` | Media profitto trade vincenti |
| `avg_loss` | Media perdita trade perdenti |
| `max_consecutive_losses` | Serie negativa più lunga |
| `score` | Ranking composito multi-fattore |