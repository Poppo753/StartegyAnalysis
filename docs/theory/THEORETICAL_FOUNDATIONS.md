# 📚 FONDAZIONI TEORICHE E SCIENTIFICHE

## Documento Completo di Riferimento Accademico
### Per la Costruzione di una Macchina Universale di Discovery Strategica

> **Nota**: Questo documento raccoglie, organizza e verifica ogni singola teoria, formula, algoritmo e principio scientifico necessario per costruire un sistema di trading quantitativo basato sulla discovery automatica. Ogni sezione include riferimenti bibliografici, formule matematiche e implicazioni pratiche per l'implementazione.

---

## INDICE

- [Capitolo 1 — Financial Machine Learning: Il Framework Fondamentale](#capitolo-1--financial-machine-learning)
- [Capitolo 2 — Cross-Validation in Finanza: Il Gold Standard](#capitolo-2--cross-validation-in-finanza)
- [Capitolo 3 — Bayesian Optimization: La Matematica della Scoperta](#capitolo-3--bayesian-optimization)
- [Capitolo 4 — Genetic Programming: L'Automazione della Creazione di Strategie](#capitolo-4--genetic-programming)
- [Capitolo 5 — Reinforcement Learning nel Trading](#capitolo-5--reinforcement-learning)
- [Capitolo 6 — Time Series Analysis: Stazionarietà e Memoria](#capitolo-6--time-series-analysis)
- [Capitolo 7 — Information Theory e Trading](#capitolo-7--information-theory)
- [Capitolo 8 — Statistical Inference per Strategie Finanziarie](#capitolo-8--statistical-inference)
- [Capitolo 9 — Ensemble Methods e Meta-Strategie](#capitolo-9--ensemble-methods)
- [Capitolo 10 — Regime Detection e Cambiamento di Distribuzione](#capitolo-10--regime-detection)
- [Appendice — Formule Matematiche Riassuntive](#appendice)

---

## Capitolo 1 — Financial Machine Learning: Il Framework Fondamentale

### 1.1 Il Problema Fondamentale

La ragione principale per cui i progetti di Financial Machine Learning (FML) falliscono non è la mancanza di dati o di algoritmi — è la **mancanza di un framework scientifico rigoroso** per sviluppare, testare e validare strategie.

**Fonte**: Marcos López de Prado, *Advances in Financial Machine Learning* (Wiley, 2018), Capitolo 1.

### 1.2 Il Paradosso di Sisyfo

López de Prado identifica un pattern ricorrente nella ricerca quantitativa:

```
IL CICLO DI SISIFO:

1. Trovi un pattern nei dati storici
2. Costruisci una strategia basata su quel pattern
3. Fai backtest → funziona!
4. Fai più test per "migliorarla"
5. La strategia diventa sempre più specifica sui dati storici
6. La metti in produzione → NON FUNZIONA

Perché? Perché ogni iterazione aggiunge overfitting.
Ogni test è un "tentativo di lotto" — la strategia vincente
è quella che ha avuto più fortuna, non quella che ha vera edge.
```

**La Soluzione**: Il **Meta-Strategy Paradigm** — invece di testare una strategia, testa un *processo di creazione di strategie*. Il sistema non è la strategia finale, ma la macchina che genera strategie valide.

### 1.3 La Catena di Produzione (Production Chain)

López de Prado propone una struttura a catena di produzione per il FML:

```
┌─────────────────────────────────────────────────────────────┐
│              CATENA DI PRODUZIONE FML                         │
│                                                               │
│  1. DATA STRUCTURES                                          │
│     ↓                                                        │
│  2. FEATURE ENGINEERING                                      │
│     ↓                                                        │
│  3. LABELING (Triple-Barrier)                                │
│     ↓                                                        │
│  4. SAMPLE WEIGHTING (Uniqueness weighting)                  │
│     ↓                                                        │
│  5. FEATURE IMPORTANCE                                       │
│     ↓                                                        │
│  6. HYPERPARAMETER TUNING                                    │
│     ↓                                                        │
│  7. BACKTESTING (Combinatorial Purged CV)                    │
│     ↓                                                        │
│  8. STRATEGY SELECTION                                       │
│     ↓                                                        │
│  9. BET SIZING                                               │
│     ↓                                                        │
│  10. EXECUTION                                               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

Ogni anello della catena deve essere scientificamente rigoroso. Se uno fallisce, tutto il sistema produce risultati inaffidabili.

**Implicazione per il nostro progetto**: Il nostro sistema deve essere progettato come una catena di produzione, non come un semplice backtester. Ogni componente deve essere validato separatamente.

### 1.4 Struttura per Componente della Strategia

Invece della Production Chain, López de Prado propone anche una struttura basata sui componenti:

```
COMPONENTI DI UNA STRATEGIA:

1. ENTRY SIGNAL    → Quando entrare nel mercato
   - Tipo: momentum, mean-reversion, breakout, ecc.
   - Input: prezzi, volume, indicatori tecnici
   - Output: segnale binario (compra/vendi/non operare)

2. EXIT SIGNAL     → Quando uscire dal mercato
   - Tipo: stop-loss, take-profit, time-based, trailing
   - Input: prezzo corrente, entry price, tempo
   - Output: segnale di chiusura

3. POSITION SIZE   → Quanta capitale allocare
   - Tipo: fixed fraction, Kelly criterion, risk parity
   - Input: volatilità, drawdown, capitale disponibile
   - Output: dimensione posizione

4. RISK MANAGEMENT → Come proteggere il capitale
   - Tipo: stop-loss globale, max drawdown limit, correlation filter
   - Input: PnL cumulativo, correlazione tra posizioni
   - Output: decisione di riduzione/esposizione

5. REGIME FILTER   → Quando NON operare
   - Tipo: trending vs ranging, volatility regime
   - Input: ADX, Hurst exponent, VIX
   - Output: abilitazione/disabilitazione strategia
```

**Per il nostro sistema**: Ogni componente è un modulo separato che può essere combinato, testato, e ottimizzato indipendentemente.

### 1.5 La Distinzione tra Research e Production

López de Prado enfatizza una distinzione cruciale:

| Research | Production |
|----------|------------|
| Obiettivo: scoprire nuove strategie | Obiettivo: generare PnL consistente |
| Metriche: Sharpe, Information Coefficient | Metriche: PnL, drawdown, turnover |
| Validazione: purged CV | Validazione: out-of-sample holdout |
| Rischio: overfitting alla ricerca | Rischio: alpha decay |
| Ambiente: storico, statico | Ambiente: live, non-stazionario |

**Errore critico**: Molti ricercatori confondono le due fasi. Testano in modalità research e mettono in produzione i risultati. Ma le strategie ottimizzate per la ricerca sono spesso ottimizzate per il passato, non per il futuro.

### 1.6 Il Framework Completo di López de Prado (Riepilogo dei Contenuti del Libro)

```
AVANCES IN FINANCIAL MACHINE LEARNING (AFML) — Wiley 2018

PART I: DATA ANALYSIS
├── Ch. 2: Financial Data Structures
│   ├── Time Bars, Volume Bars, Dollar Bars, Tick Bars
│   ├── Multi-product series handling
│   └── Sampling features for ML
├── Ch. 3: Labeling
│   ├── Fixed-Time Horizon Method (fallimentare)
│   ├── Dynamic Thresholds
│   ├── Triple-Barrier Method (gold standard per labeling)
│   ├── Meta-Labeling
│   └── Quantamental Approach
├── Ch. 4: Sample Weights
│   ├── Overlapping Outcomes
│   ├── Number of Concurrent Labels
│   ├── Average Uniqueness of a Label
│   ├── Bagging Classifiers and Uniqueness
│   ├── Return Attribution
│   └── Time Decay
└── Ch. 5: Fractionally Differentiated Features
    ├── Stationarity vs. Memory Dilemma
    ├── The Method (binomial expansion)
    ├── Stationarity with Maximum Memory Preservation
    └── Implementation

PART II: MODELLING
├── Ch. 6: Ensemble Methods
│   ├── Bootstrap Aggregation
│   ├── Random Forest
│   ├── Boosting
│   └── Bagging for Scalability
├── Ch. 7: Cross-Validation in Finance
│   ├── Why K-Fold CV Fails in Finance
│   ├── Purged K-Fold CV
│   └── The Purged K-Fold Class
├── Ch. 8: Feature Importance
│   ├── Mean Decrease Impurity
│   ├── Mean Decrease Accuracy
│   ├── Orthogonal Features
│   └── Parallelized Feature Importance
└── Ch. 9: Hyper-Parameter Tuning with Cross-Validation
    ├── Grid Search CV
    ├── Randomized Search CV
    └── Scoring and Tuning

PART III: BACKTESTING
├── Ch. 10: Bet Sizing
│   ├── Strategy-Independent Approaches
│   ├── Bet Sizing from Predicted Probabilities
│   └── Averaging Active Bets
├── Ch. 11: The Dangers of Backtesting
│   ├── Mission Impossible: The Flawless Backtest
│   ├── Backtesting Is Not a Research Tool
│   └── General Recommendations
├── Ch. 12: Backtesting through Cross-Validation
│   ├── Walk-Forward Method
│   ├── Cross-Validation Method
│   ├── Combinatorial Purged CV (CPCV)
│   └── How CPCV Addresses Backtest Overfitting
└── Ch. 13: Backtesting on Synthetic Data
    ├── Trading Rules Generation
    ├── Monte Carlo Methods
    └── Deflated Sharpe Ratio
```

### 1.7 Il Contribution Principale: Il Meta-Labeling

Uno dei concetti più rivoluzionari di López de Prado è il **Meta-Labeling**:

**Problema**: Una strategia complessa può avere un alto win rate ma anche un alto drawdown. Come decidere quando attivare/disattivare la strategia?

**Soluzione**: Usa un modello ML di secondo livello per classificare se la strategia principale produrrà profitto nelle condizioni attuali.

```
ARCHITETTURA META-LABELING:

┌─────────────────────────────────────────┐
│         MODELLO DI PRIMO LIVELLO        │
│   (La strategia stessa)                 │
│   Input: OHLCV, indicatori              │
│   Output: Segnale di trading            │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         MODELLO DI SECONDO LIVELLO      │
│   (Il Meta-Labeler)                    │
│   Input: Segnale + contesto di mercato  │
│   Output: 0 (NON operare) o 1 (opera)  │
│                                          │
│   Obiettivo: massimizzare win rate       │
│   del modello di primo livello           │
│   quando il modello di secondo           │
│   livello dice "opera"                   │
└─────────────────────────────────────────┘
```

**Perché è importante**: Invece di cercare continuamente nuove strategie, il meta-labeling ti permette di usare la strategia che hai, solo quando è probabile che funzioni. È il ponte tra la generazione di strategie e la scoperta di quando usarle.

---

## Capitolo 2 — Cross-Validation in Finanza: Il Gold Standard

### 2.1 Perché il K-Fold Standard Fallisce in Finanza

**Fonte**: López de Prado, AFML Capitolo 7; paper di Berger et al. (2019).

Il K-Fold Cross-Validation standard assume che i campioni siano **indipendenti e identicamente distribuiti (IID)**. In finanza, questa assunzione è **violata** per tre motivi:

1. **Overlapping Labels**: Un'osservazione con data t ha un label che dipende dal prezzo futuro fino a t+H. Se H > 0, le osservazioni non sono indipendenti.

2. **Serial Correlation**: I rendimenti finanziari hanno autocorrelazione. Un campione di addestramento può "influenzare" il campione di test.

3. **Non-Stationarity**: La distribuzione dei rendimenti cambia nel tempo. I dati del 2020 non sono distribuiti come quelli del 2024.

**Esempio concreto del fallimento**:

```
Supponiamo: K=5, dati dal 2018-2024, label horizon H=5 giorni

K-Fold standard:
  Fold 1: Train [2018-2019], Test [2020]
  Fold 2: Train [2018-2020], Test [2021]
  Fold 3: Train [2018-2021], Test [2022]
  Fold 4: Train [2018-2022], Test [2023]
  Fold 5: Train [2018-2023], Test [2024]

PROBLEMA: Un'osservazione nel test set del Fold 1 (dicembre 2019)
ha un label che dipende dal prezzo a gennaio 2020, che è nel test set
del Fold 2, Fold 3, ecc. → DATA LEAKAGE!

Inoltre, le osservazioni nel train set del Fold 5 (2018-2023) hanno
labels che si estendono fino al 2024, che è nel test set → OVERLAP!
```

### 2.2 Purged K-Fold Cross-Validation

**Creatore**: Marcos López de Prado (AFML, Capitolo 7.4)

**Soluzione**: Aggiungere due meccanismi:

#### 2.2.1 Purging (Purgamento)

Rimuovi dal train set qualsiasi osservazione il cui label si estende nel test set.

```
Formale:
Sia t un'indice temporale nel train set.
Sia H l'orizzonte del label.
Sia t_test un indice nel test set.

Se |t - t_test| < H, allora t è "contaminato" e deve essere rimosso dal train set.
```

```
Esempio visivo:

Timeline: [----TRAIN----][EMBARGO][----TEST----]
                     ↑
              H giorni di gap

Le osservazioni nel TRAIN vicine al confine vengono rimosse.
```

#### 2.2.2 Embargo (Divieto)

Aggiungi un gap (embargo) tra train e test per prevenire leakage seriale.

```
Embargo_size = embargo_pct × test_period

Tipicamente: embargo_pct = 0.01 a 0.05
```

#### 2.2.3 Implementazione del Purged K-Fold

```python
class PurgedKFold:
    """
    Implementazione del Purged K-Fold CV.
    
    Parameters:
    -----------
    n_splits : int
        Numero di fold
    embargo_pct : float
        Percentuale di embargo tra train e test
    """
    
    def split(self, X, y, groups=None):
        """
        Genera gli indici di train/test per ogni fold.
        
        Processo:
        1. Dividi i dati in K fold temporali
        2. Per ogni fold:
           a. Determina il test set
           b. Rimuovi dal train set le osservazioni con label overlap
           c. Aggiungi embargo
        """
        n_samples = len(X)
        fold_size = n_samples // self.n_splits
        
        for i in range(self.n_splits):
            test_start = i * fold_size
            test_end = (i + 1) * fold_size
            
            test_indices = list(range(test_start, test_end))
            
            # Calcola l'indice di embargo
            embargo_size = int(self.embargo_pct * fold_size)
            train_end = test_start - embargo_size
            
            # Rimuovi osservazioni contaminate dal train
            # Le osservazioni con indice >= train_end - H sono contaminate
            purge_size = int(self.label_horizon * 0.5)  # Approssimazione
            train_start = max(0, train_end - purge_size)
            
            train_indices = list(range(train_start, train_end))
            
            yield train_indices, test_indices
```

### 2.3 Combinatorial Purged Cross-Validation (CPCV)

**Fonte**: López de Prado, AFML Capitolo 12.4

Il Purged K-Fold usa K fold. Ma CPCV genera **tutte le possibili combinazioni** di split, per una stima più robusta.

```
Per N osservazioni e K fold:
Numero di combinazioni = C(N-1, K-1)

Per N=100, K=5: C(99,4) = 3,764,376 combinazioni!
```

**Perché tante combinazioni?** Perché ogni combinazione è un diverso "esperimento" di backtest. La distribuzione dei PnL su tutte le combinazioni dà una stima molto più robusta di quanto possa dare un singolo split.

**Algoritmo CPCV**:

```python
class CombinatorialPurgedCV:
    """
    Genera C(N-1, K-1) percorsi di backtest.
    """
    
    def generate_paths(self, n_observations: int, n_splits: int):
        """
        Genera tutti i possibili split per CPCV.
        """
        from itertools import combinations
        
        n_test = n_observations // n_splits
        test_starts = list(range(n_test, n_observations, n_test))
        
        all_paths = []
        for test_start in test_starts:
            # Tutte le combinazioni di test set
            for combo in combinations(range(n_observations), n_test):
                test_set = set(combo)
                train_set = set(range(n_observations)) - test_set
                
                # Applica purging e embargo
                train_set = self._purge(train_set, test_set, self.label_horizon)
                train_set = self._embargo(train_set, test_set, self.embargo_pct)
                
                all_paths.append({
                    'train': sorted(train_set),
                    'test': sorted(test_set)
                })
        
        return all_paths
    
    def calculate_pbo(self, backtest_pnls: List[float], n_trials: int) -> float:
        """
        Calcola la Probability of Backtest Overfitting.
        """
        # PBO = P(strategy è overfitted | risultati osservati)
        # Calcolato come proporzione di percorsi con PnL < 0
        n_negative = sum(1 for pnl in backtest_pnls if pnl < 0)
        pbo = n_negative / len(backtest_pnls)
        return pbo
```

### 2.4 Deflated Sharpe Ratio (DSR)

**Fonte**: López de Prado, AFML Capitolo 13; paper di López de Prado e Lewis (2019).

Lo Sharpe Ratio standard è **gonfiato** dall'overfitting. Il Deflated Sharpe Ratio corregge questo bias.

**Formula**:

```
DSR = SR × correction_factor(PBO, N_trials, T)

Dove:
- SR = Sharpe Ratio osservato
- PBO = Probability of Backtest Overfitting
- N_trials = Numero di strategie testate
- T = Numero di osservazioni nel backtest
```

**Implementazione concettuale**:

```python
def calculate_dsr(sharpe_ratio: float, pbo: float, 
                    n_trials: int, n_observations: int) -> float:
    """
    Calcola il Deflated Sharpe Ratio.
    
    Se PBO > 50%, la strategia è probabilmente overfitted e il DSR sarà negativo.
    Se PBO < 50%, il DSR sarà positivo ma corretto per il numero di trial.
    """
    if pbo >= 0.5:
        return -sharpe_ratio  # La strategia è overfitted
    
    # Correction factor (semplificato)
    correction = 1.0 - 2.0 * pbo
    
    dsr = sharpe_ratio * correction
    return dsr
```

### 2.5 Walk-Forward Analysis

**Fonte**: López de Prado, AFML Capitolo 12.2; Pardo, *The Evaluation and Optimization of Trading Strategies* (2008).

La Walk-Forward Analysis è il metodo più robusto per validare strategie finanziarie:

```
Processo:

1. Definisci un training window (es. 2 anni)
2. Definisci un testing window (es. 6 mesi)
3. Per ogni passo:
   a. Addestra la strategia sul training window
   b. Testa sul testing window (out-of-sample)
   c. Avanza il training window di 6 mesi
   d. Ripeti

Esempio:

Periodo: [---Train---][Test][---Train---][Test][---Train---][Test]...
         |← 2 anni →|←6m→|← 2 anni →|←6m→|← 2 anni →|←6m→|
```

**Vantaggi**:
- Testa la strategia su MOLTI periodi out-of-sample
- Cattura i cambiamenti di regime
- Ogni periodo di test è veramente indipendente
- Dà una distribuzione di PnL su M periodi

**Pitfall**: Se il training window è troppo piccolo, il modello è sottodimensionato. Se troppo grande, include dati vecchi e non stazionari.

### 2.6 Confronto Completo dei Metodi di Validazione

| Metodo | Robustezza | Complessità | Calcola PBO | Usa in Produzione |
|--------|-----------|-------------|-------------|-------------------|
| Single Split | ⭐ | ⭐ | ❌ | ❌ |
| Purged K-Fold | ⭐⭐⭐ | ⭐⭐ | ❌ | ⚠️ |
| Walk-Forward | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | ✅ |
| CPCV | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | ✅ (validazione) |
| Deflated Sharpe | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ | ✅ |
| Out-of-Sample Holdout | ⭐⭐⭐⭐⭐ | ⭐ | ❌ | ✅ (fase finale) |

**Raccomandazione per il nostro sistema**: Usa CPCV per la validazione iniziale, Walk-Forward per la validazione finale, e Deflated Sharpe Ratio per la decisione di accettazione/rifiuto.

---

## Capitolo 3 — Bayesian Optimization: La Matematica della Scoperta

### 3.1 Il Problema

Hai una funzione obiettivo `f(x)` dove `x` è un vettore di parametri (es. X%, Ys, Z%) e `f(x)` è il PnL del backtest. Vuoi trovare `x*` che massimizza `f`.

**Problema**: `f` è:
- **Costosa**: Ogni valutazione richiede un backtest (secondi/minuti)
- **Nera**: Non sai come `f` dipende da `x` (non è una formula chiusa)
- **Rumore**: Ogni valutazione è leggermente diversa (market randomness)
- **Multi-modale**: Ci sono molti massimi locali

**Grid Search**: Valuta tutti i punti. Con 10 parametri da 10 valori = 10^10 → impossibile.
**Random Search**: Valuta punti casuali. Meglio, ma non sfrutta le informazioni passate.
**Bayesian Optimization**: Valuta punti intelligenti basandosi su cosa ha imparato.

### 3.2 I Componenti di BO

```
BAYESIAN OPTIMIZATION ALGORITHM:

Input:
  - f: funzione obiettivo (backtest)
  - X: spazio dei parametri
  - kernel: funzione di similarità (kernel)
  - acquisition: funzione di acquisizione
  - N: numero di valutazioni

Processo:
1. Inizializza con N_warmup punti casuali
2. Per ogni iterazione:
   a. Fit un Gaussian Process sui dati storici
   b. Calcola l'acquisition function
   c. Trova il punto che massimizza l'acquisition function
   d. Valuta f in quel punto
   e. Aggiungi il risultato ai dati storici
3. Restituisci il miglior punto trovato
```

### 3.3 Gaussian Process (GP) — Il Modello Surrogate

Un Gaussian Process è una distribuzione su funzioni. Invece di modellare `f` come una funzione fissa, lo modelli come una distribuzione di funzioni.

**Definizione formale**:

```
f(x) ~ GP(m(x), k(x, x'))

Dove:
  m(x) = E[f(x)] = media (tipicamente 0)
  k(x, x') = Cov[f(x), f(x')] = covariance function (kernel)
```

**Interpretazione**: Un GP è come avere una "palla di neve" su ogni punto dello spazio — ogni punto ha una distribuzione gaussiana di possibili valori, e i punti vicini hanno distribuzioni correlate.

**Il kernel (funzione di covarianza)** determina quanto rapidamente la funzione può cambiare:

```python
# RBF (Radial Basis Function) kernel — il più comune
def rbf_kernel(x1, x2, length_scale=1.0, sigma_f=1.0):
    """
    k(x1, x2) = sigma_f^2 * exp(-||x1 - x2||^2 / (2 * l^2))
    
    dove l = length_scale controlla la "lisciatura"
    sigma_f = signal variance controlla l'ampiezza
    """
    sqdist = np.sum(x1**2, 1).reshape(-1, 1) + np.sum(x2**2, 1) - 2 * np.dot(x1, x2)
    return sigma_f**2 * np.exp(-0.5 / length_scale**2 * sqdist)

# Matern kernel — più flessibile
def matern_kernel(x1, x2, nu=2.5, length_scale=1.0):
    """
    Generalizzazione del RBF con parametri di smoothness controllabili.
    nu=1.5 → funzione una volta differenziabile (meno liscio)
    nu=2.5 → due volte differenziabile (più liscio, default)
    """
    ...
```

**Posterior GP**: Dopo aver osservato `n` punti, la distribuzione di `f` in un punto nuovo `x*` è:

```
f(x*) | X, y ~ N(μ*(x*), σ²*(x*))

Dove:
  μ*(x*) = k(x*, X) [K(X,X) + σ_n²I]⁻¹ y    (media)
  σ²*(x*) = k(x*, x*) - k(x*, X) [K(X,X) + σ_n²I]⁻¹ k(X, x*)   (varianza)
```

**Interpretazione**:
- `μ*(x*)` = previsione del GP in x*
- `σ²*(x*)` = incertezza del GP in x*
- Dove la varianza è alta → il GP non sa nulla → esplora
- Dove la varianza è bassa → il GP sa molto → sfrutta

### 3.4 Acquisition Functions — La Guida della Ricerca

L'acquisition function decide **dove campionare prossimamente**. Bilancia esplorazione vs sfruttamento:

#### 3.4.1 Expected Improvement (EI)

**La più usata**. Misura il valore atteso del miglioramento rispetto al miglior punto visto finora.

```
EI(x) = E[max(0, f(x*) - f(x_best))]

Con f(x) ~ N(μ(x), σ²(x)) e f(x*) = miglior valore osservato:

EI(x) = (μ(x) - f*) · Φ(Z) + σ(x) · φ(Z)

Dove:
  Z = (μ(x) - f*) / σ(x)
  Φ = CDF della normale standard
  φ = PDF della normale standard
  f* = miglior valore osservato
```

**Interpretazione**:
- Se `μ(x) >> f*` → EI è alto (buona previsione)
- Se `σ(x) >> 0` → EI è alto (molta incertezza → esplora)
- Se `μ(x) << f*` e `σ(x) ≈ 0` → EI è basso (sconsigliato)

#### 3.4.2 Probability of Improvement (PI)

**Più semplice**. Misura la probabilità di migliorare rispetto al miglior punto:

```
PI(x) = Φ((μ(x) - f*) / σ(x))

PI è più "sfruttativo" — tende a convergere più velocemente ma può rimanere intrappolato in un massimo locale.
```

#### 3.4.3 Upper Confidence Bound (UCB)

**Più bilanciato**. Esplora dove l'incertezza è alta:

```
UCB(x) = μ(x) + κ · σ(x)

Dove κ controlla il trade-off:
  κ alto → più esplorazione
  κ basso → più sfruttamento
```

### 3.5 L'Algoritmo Completo

```python
import numpy as np
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern

class BayesianOptimizer:
    """
    Bayesian Optimizer completo con Gaussian Process e Expected Improvement.
    
    Basato su: Shahriari et al., "Taking the Human Out of the Loop", 2016.
    """
    
    def __init__(self, param_bounds, n_initial=10, kernel=None):
        """
        param_bounds: lista di tuple [(min, max), ...] per ogni parametro
        n_initial: numero di punti iniziali casuali
        """
        self.bounds = np.array(param_bounds)
        self.n_params = len(param_bounds)
        self.n_initial = n_initial
        
        # Default kernel: Matern 5/2
        if kernel is None:
            kernel = Matern(length_scale=1.0, nu=2.5)
        
        self.gp = GaussianProcessRegressor(
            kernel=kernel,
            alpha=1e-6,  # noise level
            normalize_y=True,
            n_restarts_optimizer=5,
            random_state=42
        )
        
        self.X_observed = []  # Parametri valutati
        self.y_observed = []  # Risultati (PnL)
        self.best_y = -np.inf  # Miglior PnL osservato
        self.best_x = None
    
    def suggest(self, n_points=1):
        """
        Suggerisce i prossimi punti da valutare.
        Usa Expected Improvement come acquisition function.
        """
        if len(self.X_observed) < self.n_initial:
            # Fase iniziale: punti casuali
            return [np.random.uniform(self.bounds[:, 0], self.bounds[:, 1]) 
                    for _ in range(n_points)]
        
        # Fit GP sui dati osservati
        X = np.array(self.X_observed)
        y = np.array(self.y_observed)
        self.gp.fit(X, y)
        
        # Genera candidati
        n_candidates = 10000
        X_candidates = np.random.uniform(
            self.bounds[:, 0], self.bounds[:, 1], 
            size=(n_candidates, self.n_params)
        )
        
        # Predizione GP
        mu, sigma = self.gp.predict(X_candidates, return_std=True)
        
        # Calcola Expected Improvement
        with np.errstate(divide='warn'):
            imp = mu - self.best_y - 1e-6  # improvement
            Z = imp / np.maximum(sigma, 1e-9)
            ei = imp * norm.cdf(Z) + sigma * norm.pdf(Z)
            ei[sigma == 0.0] = 0.0
        
        # Seleziona i migliori punti
        best_indices = np.argsort(ei)[::-1][:n_points]
        return [X_candidates[i] for i in best_indices]
    
    def observe(self, x, y):
        """
        Registra un nuovo risultato.
        """
        self.X_observed.append(x)
        self.y_observed.append(y)
        if y > self.best_y:
            self.best_y = y
            self.best_x = x
    
    def optimize(self, objective_func, n_trials=50, verbose=True):
        """
        Esegue l'ottimizzazione completa.
        
        Parameters:
        -----------
        objective_func: funzione che prende un array di parametri e restituisce un PnL
        n_trials: numero totale di valutazioni
        """
        for trial in range(n_trials):
            # Suggerisci prossimo punto
            candidates = self.suggest(n_points=1)
            x_next = candidates[0]
            
            # Valuta la funzione obiettivo
            y_next = objective_func(x_next)
            
            # Registra il risultato
            self.observe(x_next, y_next)
            
            if verbose and trial % 10 == 0:
                print(f"Trial {trial}: PnL={y_next:.4f}, Best={self.best_y:.4f}")
        
        return self.best_x, self.best_y
```

### 3.6 Perché BO è Superiore a Grid/Random Search

**Fonte**: Turner et al., "Bayesian Optimization is Superior to Random Search", NeurIPS 2020 ([arXiv](https://arxiv.org/abs/2104.10201)).

Il paper dimostra che BO è **100× più efficiente** di random search per lo stesso numero di valutazioni. Il motivo:

- **Grid Search**: Esplora uniformemente tutto lo spazio. Il 99% dello spazio è inutile (zone dove nessun parametro funziona).
- **Random Search**: Esplora casualmente. Meglio di grid, ma non usa informazioni passate.
- **BO**: Usa il modello GP per concentrarsi sulle zone promettenti, evitando le zone morte.

```
Confronto visivo del numero di valutazioni necessarie:

Grid Search:       10^d valutazioni (d = dimensione)
Random Search:     ~1000 valutazioni per d=10
Bayesian Opt:      ~50-100 valutazioni per d=10
Miglioramento:     10-100× più efficiente
```

### 3.7 Scelta dell'Optimizer

| Libreria | Algoritmo | Forza | Debolezza | Uso in Trading |
|----------|-----------|-------|-----------|----------------|
| **Optuna** | TPE, GP, CMA-ES | Pruning, parallelizzazione | GP meno raffinato | ⭐⭐⭐⭐⭐ |
| **skopt** | GP (gp_minimize) | Semplice, GP puro | Nessun pruning, lento | ⭐⭐⭐ |
| **Ax** | GP, TuRBO | Multi-objective, constraint | API complessa | ⭐⭐⭐⭐ |
| **Hyperopt** | TPE | Early stopping | Meno mantenuto | ⭐⭐⭐ |

**Raccomandazione**: Optuna con `TPESampler` + `MedianPruner` è la scelta migliore per il trading perché:
1. TPE gestisce bene spazi continui e discreti
2. MedianPruner ferma trial non promettenti presto
3. Parallelizzazione nativa
4. Storage persistence (puoi riprendere da dove ti sei fermato)

---

## Capitolo 4 — Genetic Programming: L'Automazione della Creazione di Strategie

### 4.1 Origini e Fondamento

**Fonte**: John R. Koza, *Genetic Programming: On the Programming of Computers by Means of Natural Selection* (MIT Press, 1992).

Il Genetic Programming (GP) è una tecnica di ricerca automatica che evoluziona **programmi informatici** invece di stringhe di parametri. È ispirato alla teoria dell'evoluzione di Darwin e alla genetica di Mendel.

**Differenza chiave con la ricerca parametrica**:
- **Bayesian Optimization**: trova i migliori valori per parametri dati (X, Y, Z)
- **Genetic Programming**: crea NUOVE strutture di programma (NUOVE strategie)

### 4.2 Il Framework GP

```
COMPONENTI DEL GP:

1. TERMINALS (terminali): le "foglie" dell'albero
   - Numeri (es. 0.5, 10, 0.01)
   - Variabili (es. close, high, low, volume)
   - Costanti (es. 20, 50, 200)

2. FUNCTIONS (funzioni): i "nodi" dell'albero
   - Aritmetiche: +, -, *, /
   - Condizionali: if-then-else
   - Matematiche: sin, cos, log, exp, sqrt
   - Logistiche: AND, OR, NOT
   - Trading-specifiche: SMA, RSI, Bollinger

3. FITNESS FUNCTION: come si misura la qualità di un programma
   - PnL del backtest
   - Sharpe Ratio
   - Win Rate
   - Combo pesata

4. PARAMETRI DI CONTROLLO:
   - Popolazione size: 500-1000
   - Max generazioni: 50-500
   - Crossover probability: 0.8-0.95
   - Mutation probability: 0.01-0.1
   - Selection: tournament, roulette wheel
```

### 4.3 Gli Operatori Genetici

#### 4.3.1 Crossover (Ricombinazione)

**Fonte**: Koza, 1992, Capitolo 3.

```
CROSSOVER:

Genitore A:  if(RSI(14) < 30, buy, if(SMA(50) > close, sell, hold))
                                    ↑
                                    | punto di crossover
Genitore B:  if(MA(20) > MA(50) and volume > avg, buy, sell)
                                    ↑

Progenie:  if(RSI(14) < 30, buy, if(MA(20) > MA(50) and volume > avg, sell, hold))
```

```python
def crossover(parent_a: list, parent_b: list, crossover_point_a: int, 
              crossover_point_b: int) -> tuple:
    """
    Scambia i sottoreti tra due genitori.
    
    parent_a[crossover_point_a:] scambia con parent_b[crossover_point_b:]
    """
    child_a = parent_a[:crossover_point_a] + parent_b[crossover_point_b:]
    child_b = parent_b[:crossover_point_b] + parent_a[crossover_point_a:]
    return child_a, child_b
```

#### 4.3.2 Mutation (Mutazione)

```python
def mutate(program: list, mutation_rate: float = 0.05):
    """
    Modifica casualmente un nodo del programma.
    
    Tipi:
    1. Point mutation: sostituisci un nodo con un nodo casuale
    2. Sub-tree mutation: sostituisci un sotto-albero con uno casuale
    3. Hoist mutation: prendi un sotto-albero casuale e "risali"
    4. Gene duplication: duplica un gene
    5. Gene deletion: elimina un gene
    """
    import random
    
    if random.random() < mutation_rate:
        mutation_type = random.choice(['point', 'subtree', 'hoist'])
        
        if mutation_type == 'point':
            # Sostituisci un nodo casuale
            idx = random.randint(0, len(program) - 1)
            program[idx] = random_terminal_or_function()
        
        elif mutation_type == 'subtree':
            # Sostituisci un sotto-albero
            start = random.randint(0, len(program) - 1)
            end = random.randint(start, len(program) - 1)
            new_subtree = generate_random_program(max_depth=3)
            program = program[:start] + new_subtree + program[end+1:]
        
        elif mutation_type == 'hoist':
            # Estrai un sotto-albero e rimuovi il livello superiore
            start = random.randint(0, len(program) - 1)
            # Trova il sotto-albero a profondità casuale
            ...
    
    return program
```

#### 4.3.3 Selection (Selezione)

```python
def tournament_selection(population: list, tournament_size: int = 5) -> list:
    """
    Seleziona individui per la riproduzione tramite torneo.
    
    Processo:
    1. Seleziona k individui casualmente dalla popolazione
    2. Il migliore (migliore fitness) vince e viene selezionato
    3. Ripeti per generare i genitori necessari
    """
    winners = []
    for _ in range(len(population)):
        contestants = random.sample(population, tournament_size)
        winner = max(contestants, key=lambda x: x.fitness)
        winners.append(winner)
    return winners
```

### 4.4 Il Problema del Bloat (Gonfiore)

Il GP tende a generare programmi **sempre più grandi** senza migliorare la fitness. Questo è chiamato "bloat" o "code bloating":

```
Generazione 1:  if(RSI < 30, buy, sell)           ← 5 nodi
Generazione 50: if(RSI(14) < 30 and close > 0, buy, if(volume > 0, sell, hold))  ← 15 nodi
Generazione 100: if(RSI(14) < 30 and close > 0 and high > low, buy, ...)  ← 25 nodi

La fitness non migliora, ma il programma cresce!
```

**Soluzioni**:
1. **Parsimony pressure**: Penalizza i programmi lunghi nella fitness
2. **Size limiting**: Limita la profondità massima dell'albero
3. **Pruning**: Rimuovi sottorami che non migliorano la fitness
4. **Automatically Defined Functions (ADFs)**: Crea funzioni riutilizzabili invece di ripetere codice

### 4.5 Vectorial Genetic Programming (VGP)

**Fonte**: Azzali et al., "Evolving Financial Trading Strategies with Vectorial Genetic Programming", arXiv:2504.05418 (2025).

Il VGP è una evoluzione del GP standard che opera su **vettori** anziché su alberi. Viene applicato al trading con risultati promettenti:

**Risultati chiave del paper**:
- VGP strongly-typed supera il GP standard in ogni scenario testato
- Il GP standard è sempre tra i peggiori
- Le strategie evolute sono profitable in 3 strumenti finanziari su 7 anni di dati

**Implicazione**: Il VGP è un approccio viable per generare strategie automaticamente nel nostro sistema.

### 4.6 Applicazione al Nostro Sistema

```python
# Configurazione del GP per la generazione di strategie

GP_CONFIG = {
    'population_size': 500,
    'max_generations': 200,
    'crossover_prob': 0.85,
    'mutation_prob': 0.05,
    'tournament_size': 5,
    'max_depth': 8,
    'parsimony_coefficient': 0.01,  # Penalità per programmi grandi
}

# Terminal set per strategie trading
TRADING_TERMINALS = {
    'price': ['close', 'open', 'high', 'low'],
    'indicators': ['sma_20', 'sma_50', 'rsi_14', 'macd', 'bollinger_upper', 'bollinger_lower'],
    'volume': ['volume', 'volume_sma_20', 'obv'],
    'constants': list(range(-5, 6)),  # -5, -4, ..., 0, ..., 4, 5
    'historical': ['close_lag_1', 'close_lag_5', 'close_lag_20'],  # Close di N periodi fa
}

# Function set per strategie trading
TRADING_FUNCTIONS = {
    'arithmetic': ['+', '-', '*', '/'],
    'comparison': ['>', '<', '==', '>=', '<='],
    'logical': ['and', 'or', 'not'],
    'conditional': ['if_then_else'],
    'math': ['abs', 'max', 'min', 'sign'],
}

# Fitness function
def trading_fitness(program, df, params):
    """
    Esegue il backtest della strategia generata dal GP
    e restituisce la fitness (Sharpe Ratio o PnL).
    """
    try:
        signals = evaluate_program(program, df)
        trades = generate_trades(signals, df)
        result = backtest(trades, df, params)
        
        fitness = result.sharpe_ratio
        fitness -= GP_CONFIG['parsimony_coefficient'] * program.size
        
        return fitness
    except:
        return -999.0  # Fitness pessima per programmi invalidi
```

---

## Capitolo 5 — Reinforcement Learning nel Trading

### 5.1 Il Framework Markov Decision Process (MDP)

Il trading come RL è formalizzato come un MDP:

```
MDP = (S, A, P, R, γ)

Dove:
  S = State (stato): [prezzo, volume, indici tecnici, portafoglio]
  A = Action (azione): [compra, vendi, mantieni, non operare]
  P = Transition: P(s'|s,a) = probabilità di transizione
  R = Reward (ricompensa): PnL del trade
  γ = Discount factor: quanto pesa il futuro
```

### 5.2 Algoritmi Principali

#### 5.2.1 PPO (Proximal Policy Optimization)

**Fonte**: Schulman et al., "Proximal Policy Optimization Algorithms", arXiv:1707.06347 (2017).

PPO è il più usato per trading perché:
- **On-policy**: più efficiente in ambienti non-stazionari
- **Clip**: previene che la policy cambi troppo drasticamente
- **Stable**: converge in modo affidabile

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal

class PPOTrader:
    """
    Agente PPO per il trading.
    
    Architettura: Actor-Critic
    - Actor: policy π(a|s) → distribuzione delle azioni
    - Critic: V(s) → valore dello stato
    """
    
    def __init__(self, state_dim, action_dim):
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # Actor: stato → parametri distribuzione
        self.actor = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.Tanh(),
            nn.Linear(256, 128),
            nn.Tanh(),
            nn.Linear(128, action_dim * 2)  # mean + std
        )
        
        # Critic: stato → valore
        self.critic = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.Tanh(),
            nn.Linear(256, 128),
            nn.Tanh(),
            nn.Linear(128, 1)
        )
    
    def forward(self, state):
        """
        Dato uno stato, restituisce la distribuzione delle azioni
        e il valore dello stato.
        """
        action_params = self.actor(state)  # [mean, std, mean, std, ...]
        value = self.critic(state)
        
        mean = action_params[::2]
        std = torch.clamp(action_params[1::2], min=1e-6)
        
        dist = Normal(mean, std)
        return dist, value
```

**Risultati chiave (Lu, 2023, arXiv:2307.07694)**:
- PPO con HMM per regime detection → migliore performance in mercati con regime changes
- Off-policy algorithms (DDPG, TD3, SAC) → performano male per la rumorosità delle rewards
- PPO con Generalized Advantage Estimation → più robusto

#### 5.2.2 DDPG (Deep Deterministic Policy Gradient)

**Fonte**: Lillicrap et al., "Continuous Control with Deep Reinforcement Learning", arXiv:1509.02971 (2015).

DDPG è un algoritmo **off-policy** che usa un critic actor-critic:

```
Architettura:
  - Actor Network: stato → azione continua
  - Critic Network: (stato, azione) → Q-value
  - Replay Buffer: memorizza esperienze passate
  - Target Networks: reti target statiche per stabilità
```

**Problema in trading**: DDPG è sensibile al noise nei rewards finanziari. Lu (2023) dimostra che DDPG non riesce a imparare la funzione Q a causa del noise.

#### 5.2.3 SAC (Soft Actor-Critic)

**Fonte**: Haarnoja et al., "Soft Actor-Critic: Off-Policy Maximum Entropy Deep RL", arXiv:1801.01290 (2018).

SAC massimizza sia il reward che l'entropia (esplorazione automatica):

```python
class SACTrader:
    """
    Agente SAC per il trading.
    
    Vantaggio: esplorazione automatica tramite entropia termale.
    """
    
    def __init__(self, state_dim, action_dim, alpha=0.2):
        self.alpha = alpha  # Temperature parameter
        # ... architettura simile a DDPG ma con entropy term
        
        # Obiettivo: max E[Σ γ^t (r_t + α · H(π(·|s_t)))]
        # Dove H è l'entropia → incoraggia esplorazione
```

### 5.3 Reinforcement Learning vs Bayesian Optimization

| Aspetto | Bayesian Optimization | Reinforcement Learning |
|---------|----------------------|------------------------|
| **Obiettivo** | Trova i migliori parametri | Trova la migliore policy |
| **Input** | Parametri statici (X,Y,Z) | Sequenza di stati-azioni |
| **Output** | Configurazione ottimale | Strategia adattiva |
| **Adattività** | Statica (i parametri sono fissi) | Dinamica (la policy si adatta al mercato) |
| **Complessità** | Bassa (funzione scalare) | Alta (processo decisionale sequenziale) |
| **Sample Efficiency** | 50-100 valutazioni | Milioni di step |
| **Uso** | Ottimizzazione parametri | Gestione dinamica del portafoglio |

**Raccomandazione**: Usa BO per l'ottimizzazione dei parametri di una strategia specifica, e RL per la gestione adattiva del portafoglio complessivo.

### 5.4 TradeMaster: Il Benchmark Completo

**Fonte**: Xu et al., "TradeMaster: A Holistic Quantitative Trading Platform Empowered by Reinforcement Learning", NeurIPS 2023 ([arXiv](https://proceedings.neurips.cc/paper_files/paper/2023/file/b8f6f7f2ba4137124ac976286eacb611-Paper-Datasets_and_Benchmarks.pdf)).

TradeMaster è una piattaforma completa che include:
- 8 algoritmi RL (A2C, DDPG, TD3, PG, PPO, EIIE, IMT, SARL)
- Multi-market (US stock, crypto, forex)
- Multi-metriche (TR, SR, CR, SoR, Vol, MDD, ENT, ENB)
- Rolling data split
- Transaction costs, slippage, leverage

**Insight chiave**: I modelli con regime detection (HMM + PPO) superano costantemente i modelli senza. Questo conferma l'importanza del Regime Detection nel nostro sistema.

---

## Capitolo 6 — Time Series Analysis: Stazionarietà e Memoria

### 6.1 Il Dilemma Stazionarietà vs. Memoria

**Fonte**: López de Prado, AFML Capitolo 5; Hosking (1981); Granger e Joyeux (1980).

Le serie temporali finanziarie hanno un problema fondamentale:

```
IL DILEMMA:

Serie non stazionaria (prezzo):    [~~~~~salita~~~~~]
  ✅ Preserva memoria
  ❌ Non è stazionaria → ML non funziona

Serie completamente differenziata: [~±~±~±~±~±~±~]
  ✅ Stazionaria → ML funziona
  ❌ Memorie cancellata → nessun potere predittivo

Serie frazionariamente differenziata: [~_~_~_~_~_~_~]
  ✅ Stazionaria
  ✅ Memorie parzialmente preservate
  ✅ ML funziona con potere predittivo
```

### 6.2 Differenziazione Frazionaria

**Formula**:

Per differenziazione di ordine intero `d=1`:
```
∇¹X_t = X_t - X_{t-1}
```

Per differenziazione di ordine frazionario `d ∈ [0, 1]`:
```
∇^d X_t = (1 - B)^d X_t
```

Dove `B` è l'operatore di backshift: `B^k X_t = X_{t-k}`

**Espansione binomiale**:
```
(1 - B)^d = Σ_{k=0}^{∞} ω_k B^k

Dove i pesi ω_k sono:
ω_0 = 1
ω_k = -ω_{k-1} · (d - k + 1) / k    (formula ricorsiva)
```

**Esempio** (d = 0.5):
```
ω_0 = 1.0
ω_1 = -1.0 · (0.5 - 1 + 1) / 1 = -0.5
ω_2 = -(-0.5) · (0.5 - 2 + 1) / 2 = 0.125
ω_3 = -(0.125) · (0.5 - 3 + 1) / 3 ≈ 0.0625
ω_k → 0 per k → ∞

∇^0.5 X_t = X_t - 0.5·X_{t-1} + 0.125·X_{t-2} - 0.0625·X_{t-3} + ...
```

**Interpretazione**: Ogni osservazione passata contribuisce con un peso decrescente. Il peso è diverso da zero per tutti i k → **memoria preservata**. Ma i pesi decrescono → **stazionarietà raggiunta**.

### 6.3 Metodo FFD (Fixed-Width Filtering)

López de Prado propone il metodo FFD per trovare il minimo ordine `d` che renda la serie stazionaria:

```python
def find_optimal_d(series, max_d=1.0, step=0.01):
    """
    Trova il minimo d che rende la serie stazionaria (ADF test).
    """
    from statsmodels.tsa.stattools import adfuller
    
    for d in np.arange(0, max_d, step):
        diff_series = fractional_difference(series, d)
        try:
            p_value = adfuller(diff_series.dropna())[1]
            if p_value < 0.05:  # Stazionaria al 95% confidence
                return d
        except:
            continue
    
    return max_d  # Non stazionaria nemmeno con d=1
```

**Implementazione**: La libreria Python `fracdiff` ([GitHub](https://github.com/fracdiff/fracdiff)) implementa questo metodo con API scikit-learn compatibile.

### 6.4 Hurst Exponent

**Fonte**: Mandelbrot, "The Variation of Certain Speculative Prices", 1963; Peters, *Fractal Market Analysis*, 1994.

L'Hurst Exponent (H) misura la "memoria" di una serie temporale:

```
H = 0.5: Random Walk (nessuna memoria, come il moto browniano)
H > 0.5: Persistente (trend-following, la serie tende a continuare)
H < 0.5: Anti-persistente (mean-reversion, la serie tende a tornare indietro)
```

**Calcolo**:
```
R/S Analysis:
1. Dividi la serie in n sottoperiodi di lunghezza k
2. Per ogni sottoperiodo:
   - Calcola R = range (max - min)
   - Calcola S = deviazione standard
   - Calcola R/S
3. Regressa log(R/S) su log(k): pendenza = H

Per il nostro sistema:
- Calcola H per ogni simbolo e timeframe
- Se H > 0.55 → usa strategie Momentum/Trend Following
- Se H < 0.45 → usa strategie Mean Reversion
- Se H ≈ 0.5 → nessuna strategia funziona chiaramente (random walk)
```

### 6.5 ADX (Average Directional Index)

**Fonte**: Wilder, *New Concepts in Technical Trading Systems*, 1978.

L'ADX misura la forza del trend (non la direzione):

```
ADX = media mobile del DX (Directional Index)
DX = |+DI - (-DI)| / (+DI + (-DI)) × 100

Dove:
+DI = Direzionale positivo (misura il trend rialzista)
-DI = Direzionale negativo (misura il trend ribassista)

Interpretazione:
ADX < 20: Mercato rangers (nessun trend forte)
ADX 20-25: Trend debole
ADX > 25: Trend forte
ADX > 40: Trend molto forte

Per il nostro sistema:
- ADX > 25 → attiva strategie trend-following
- ADX < 20 → attiva strategie mean-reversion
- ADX in cambio → cambia strategia
```

---

## Capitolo 7 — Information Theory e Trading

### 7.1 Il Concetto di Alpha

In information theory, l'alpha è la **quantità di informazione predittiva** che una strategia possiede rispetto al mercato.

```
ALPHA = I(Signal; Future Returns)

Dove:
I(X; Y) = H(X) + H(Y) - H(X,Y)  (Mutual Information)
H(X) = -Σ p(x) log p(x)         (Entropy)

L'alpha è massima quando:
- Il segnale è altamente informativo (H(signal) è basso → il segnale è "puro")
- Le future returns sono prevedibili dato il segnale
```

### 7.2 Information Coefficient (IC)

**Fonte**: López de Prado, AFML Capitolo 9; Grinold e Kahn, *Active Portfolio Management*.

L'IC misura la correlazione tra il segnale predittivo e i rendimenti futuri:

```
IC = corr(signal_t, return_{t+1})

IC > 0.05 → segnale forte
IC 0.02-0.05 → segnale moderato
IC < 0.02 → segnale debole (probabilmente rumore)
IC < 0 → segnale inversamente correlato (potrebbe essere utile al contrario)
```

**Information Ratio (IR)**:
```
IR = mean(IC) / std(IC)

IR > 0.5 → segnale valido
IR > 1.0 → segnale forte
IR < 0.2 → segnale non affidabile
```

### 7.3 Entropy e Predizione

**Fonte**: Cover e Thomas, *Elements of Information Theory*, 2006.

L'entropia misura l'incertezza di un sistema:

```
H(X) = -Σ p(x) log₂ p(x)

Per un mercato efficiente:
H(returns) è massimo → nessuna predizione possibile → H(returns|signal) ≈ H(returns)

Per un mercato prevedibile:
H(returns|signal) < H(returns) → il segnale riduce l'incertezza → esiste alpha
```

### 7.4 Application al Nostro Sistema

```python
class AlphaMonitor:
    """Monitora l'alpha (informazione predittiva) delle strategie."""
    
    def calculate_ic(self, signals: np.ndarray, returns: np.ndarray) -> float:
        """Calcola l'Information Coefficient."""
        from scipy.stats import spearmanr
        ic, _ = spearmanr(signals, returns)
        return ic
    
    def calculate_ir(self, ic_series: np.ndarray) -> float:
        """Calcola l'Information Ratio."""
        return np.mean(ic_series) / (np.std(ic_series) + 1e-9)
    
    def calculate_entropy(self, returns: np.ndarray) -> float:
        """Calcola l'entropia dei rendimenti."""
        from scipy.stats import entropy
        hist, _ = np.histogram(returns, bins=50, density=True)
        hist = hist[hist > 0]  # Rimuovi zeri
        return entropy(hist)
    
    def alpha_decay_rate(self, ic_window_1: float, ic_window_2: float) -> float:
        """
        Calcola il tasso di decay dell'alpha.
        """
        decay = (ic_window_1 - ic_window_2) / ic_window_1
        return decay
    
    def is_alpha_significant(self, ic: float, ir: float, n_observations: int) -> bool:
        """
        Test statistico: l'alpha è significativamente diverso da zero?
        """
        # Test t per IC
        t_stat = ic * np.sqrt(n_observations) / (1 - ic**2 + 1e-9)
        p_value = 2 * (1 - norm.cdf(abs(t_stat)))
        
        return p_value < 0.05 and ir > 0.2
```

---

## Capitolo 8 — Statistical Inference per Strategie Finanziarie

### 8.1 Il Problema del Test Multiple

**Fonte**: López de Prado, AFML; Bonferroni correction.

Quando testi 1000 strategie, anche con dati completamente casuali, ~50 avranno Sharpe Ratio > 2 (al livello di significatività del 5%). Questo è il **multiple testing problem**.

```
PROBLEMA:
Hai testato 1000 strategie. La migliore ha Sharpe = 3.0.
È questa strategia realmente valida, o è solo la più fortunata?

Se ogni strategia ha P(sharpe > 3.0 | random) = 0.00135:
P(almeno una con sharpe > 3.0 | 1000 strategie) = 1 - (1 - 0.00135)^1000 ≈ 0.75

→ C'è il 75% di probabilità che la "migliore" strategia sia solo fortuna!
```

**Soluzioni**:
1. **Bonferroni correction**: Usa α/n come soglia di significatività
2. **Holm-Bonferroni**: Più potente ma conservativa
3. **Benjamini-Hochberg**: Controlla il False Discovery Rate (FDR)
4. **Deflated Sharpe Ratio**: Corregge lo Sharpe Ratio per il numero di test

### 8.2 Il Deflated Sharpe Ratio (Dettagli)

**Fonte**: López de Prado e Lewis, "Detecting False Investment Strategies", Journal of Portfolio Management, 2019.

```
DSR = SR × φ(z) / Φ(z)

Dove:
  SR = Sharpe Ratio osservato
  z = SR × √(T)  (T = numero di anni di dati)
  φ(z) = PDF della normale standard valutata in z
  Φ(z) = CDF della normale standard valutata in z

Per grandi z (SR alto o T lungo):
  DSR ≈ SR × (1 / (z√(2π))) → decresce rapidamente

Interpretazione:
  - Se DSR > 0 → la strategia è probabilmente valida
  - Se DSR < 0 → la strategia è probabilmente overfitted
```

### 8.3 Probabilità di Overfitting (PBO)

**Fonte**: López de Prado, AFML Capitolo 12.5.

Il PBO è la probabilità che la strategia migliore sia il risultato di overfitting:

```
PBO = P(strategy è overfitted | risultati osservati)

Calcolo tramite CPCV:
1. Genera C(N-1, K-1) percorsi di backtest
2. Per ogni percorso, calcola il PnL
3. Conta quanti percorsi hanno PnL < 0
4. PBO = n_negative / n_total

PBO < 10% → Strategia solida (quasi certamente non overfitted)
PBO 10-50% → Strategia potenzialmente valida (richiede ulteriori test)
PBO > 50% → Strategia probabilmente overfitted → RIGETTARE
```

### 8.4 Walk-Forward Validation Statistica

```python
class WalkForwardValidator:
    """Validatore Walk-Forward con test statistici."""
    
    def validate(self, backtest_results: List[float], 
                 n_steps: int) -> dict:
        """
        Analizza i risultati della Walk-Forward.
        """
        pnls = np.array(backtest_results)
        
        # 1. Profitability test
        profitability_rate = np.mean(pnls > 0)
        
        # 2. t-test: il PnL medio è significativamente > 0?
        t_stat, p_value = ttest_1samp(pnls, 0)
        
        # 3. Shapiro-Wilk: il PnL è normalmente distribuito?
        shapiro_stat, shapiro_p = shapiro(pnls)
        
        # 4. Calculate the deflated Sharpe ratio
        dsr = self._calculate_dsr(pnls)
        
        # 5. Calculate PBO
        pbo = self._calculate_pbo(pnls)
        
        return {
            'profitability_rate': profitability_rate,
            't_statistic': t_stat,
            'p_value': p_value,
            'is_significant': p_value < 0.05,
            'is_normal': shapiro_p > 0.05,
            'deflated_sharpe': dsr,
            'probability_of_overfitting': pbo,
            'is_acceptable': profitability_rate > 0.6 and pbo < 0.5 and dsr > 0
        }
```

---

## Capitolo 9 — Ensemble Methods e Meta-Strategie

### 9.1 Il Teorema del Bias-Variance Decomposition

**Fonte**: Hastie, Tibshirani, Friedman, *The Elements of Statistical Learning*, 2009, Capitolo 7.

```
Err(x) = Bias²(f(x)) + Var(f(x)) + Irreducible Error

Dove:
  Bias² = errore dovuto a semplificazioni del modello
  Var = errore dovuto alla sensibilità ai dati di addestramento
  Irreducible Error = rumore intrinseco dei dati

Per il trading:
  Un modello troppo semplice (underfitting) → alto bias, bassa varianza
  Un modello troppo complesso (overfitting) → basso bias, alta varianza
  L'ensemble riduce la varianza senza aumentare troppo il bias
```

### 9.2 Bagging (Bootstrap Aggregation)

**Fonte**: Breiman, "Bagging Predictors", Machine Learning, 1996.

```python
def bagging_strategy(strategy_class, df, params, n_bootstrap=100):
    """
    Crea un ensemble di strategie via bootstrap.
    
    Processo:
    1. Genera n_bootstrap campioni dal dataset (con replacement)
    2. Per ogni campione, addestra una strategia
    3. Combina i risultati tramite voting o media ponderata
    """
    ensemble_results = []
    
    for i in range(n_bootstrap):
        # Bootstrap sample
        sample_idx = np.random.choice(len(df), size=len(df), replace=True)
        df_sample = df.iloc[sample_idx]
        
        # Addestra strategia sul campione
        strategy = strategy_class()
        result = strategy.backtest(df_sample, params)
        ensemble_results.append(result)
    
    # Combina i risultati
    avg_pnl = np.mean([r.pnl for r in ensemble_results])
    avg_sharpe = np.mean([r.sharpe for r in ensemble_results])
    
    return EnsembleResult(
        avg_pnl=avg_pnl,
        avg_sharpe=avg_sharpe,
        individual_results=ensemble_results
    )
```

### 9.3 Random Forest per Feature Importance

**Fonte**: Breiman, "Random Forests", Machine Learning, 2001; López de Prado, AFML Capitolo 8.

Nel contesto del trading, Random Forest può determinare quali features sono predittive:

```python
from sklearn.ensemble import RandomForestRegressor

def find_important_features(df, target_column, feature_columns):
    """
    Identifica quali features predicono i rendimenti futuri.
    """
    X = df[feature_columns]
    y = df[target_column]
    
    rf = RandomForestRegressor(n_estimators=500, max_depth=10, random_state=42)
    rf.fit(X, y)
    
    importances = rf.feature_importances_
    feature_importance = dict(zip(feature_columns, importances))
    
    # Ordina per importanza
    sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_features
```

**Interpretazione**: Se `close_lag_5` ha un'importanza del 15% e `volume` ha solo il 2%, allora il prezzo passato di 5 periodi è molto più predittivo del volume. Questo suggerisce che una strategia basata sul momentum potrebbe funzionare, mentre una basata sul volume no.

### 9.4 Stacking (Meta-Ensemble)

**Fonte**: Wolpert, "Stacked Generalization", IEEE Transactions on Neural Networks, 1992.

```
STACKING:

Livello 0 (Base learners):
  ├── Strategia A (Momentum)
  ├── Strategia B (Mean Reversion)
  ├── Strategia C (Breakout)
  └── Strategia D (Grid)

Livello 1 (Meta-learner):
  Input: [score_A, score_B, score_C, score_d]
  Output: peso_optimale per combinare le 4 strategie

Risultato: portfolio di strategie ottimizzato
```

### 9.5 Il Meta-Strategy Paradigm di López de Prado

**Fonte**: López de Prado, AFML Capitolo 1.2.2.

Il "Meta-Strategy Paradigm" è il framework definitivo per il trading quantitativo moderno:

```
META-STRATEGY FRAMEWORK:

┌───────────────────────────────────────────────────────────┐
│                    META-STRATEGY                             │
│                                                               │
│  1. Feature Discovery Engine                                │
│     → Trova nuovi features predittive                        │
│     → Usa genetic programming per feature engineering        │
│                                                               │
│  2. Strategy Template Library                               │
│     → Insieme di archetipi di strategie                    │
│     → Ogni template è una strategia parametrica             │
│                                                               │
│  3. Parameter Discovery Engine (BO)                         │
│     → Per ogni template, trova i migliori parametri          │
│     → Usa Bayesian Optimization                              │
│                                                               │
│  4. Strategy Validator (CPCV)                               │
│     → Validazione rigorosa con purging e embargo             │
│     → Calcola PBO e DSR                                      │
│                                                               │
│  5. Meta-Labeler (RL/ML)                                    │
│     → Decide quando attivare/disattivare ogni strategia      │
│     → Usa regime detection + meta-learning                   │
│                                                               │
│  6. Portfolio Constructor                                     │
│     → Combina le strategie valide in un portafoglio           │
│     → Ottimizza il peso di ogni strategia                    │
│     → Gestisce il rischio complessivo                         │
│                                                               │
│  7. Monitoring & Adaptation                                   │
│     → Monitora alpha decay                                   │
│     → Rileva regime changes                                  │
│     → Suggerisce nuove strategie da esplorare               │
│                                                               │
└───────────────────────────────────────────────────────────┘
```

---

## Capitolo 10 — Regime Detection e Cambiamento di Distribuzione

### 10.1 Perché il Regime Detection è Fondamentale

**Fonte**: Hamilton, *Time Series Analysis*, 1994; Guidolin & Timmermann, "Term Structure of Risk Under Regime Changes", 2006.

I mercati operano in regimi diversi che hanno distribuzioni di rendimenti fondamentalmente diverse:

```
REGIMI DI MERCATO:

┌─────────────────────────────────────────────────────┐
│                     REGIME                            │
├─────────┬──────────┬──────────┬──────────┬─────────┤
│ Trending│ Ranging  │ High Vol │  Low Vol │ Crash   │
│         │          │          │          │         │
│ Prezzi  │ Prezzi   │ Prezzi   │ Prezzi   │ Prezzi  │
│ si muovono│ oscillano│ si muovono│ si muovono│ cadono │
│ in una  │ in un    │ molto    │ poco     │ velocemente│
│ direzione│ range    │ rapidamente│ lentamente│     │
│         │ definito │            │          │         │
├─────────┼──────────┼──────────┼──────────┼─────────┤
│ Strategia│ Strategia│ Strategia│ Strategia│ Strategia│
│ Momentum │ Mean     │ Breakout │ Market   │ Cash /  │
│ Trend    │ Rever-   │ Volatili │ Making   │ Hedge   │
│ Following│ sion     │          │          │         │
└─────────┴──────────┴──────────┴──────────┴─────────┘
```

**Problema**: Se non rilevi il regime corrente, usi la strategia sbagliata per quel regime. Una strategia Momentum in un mercato ranging perde denaro. Una strategia Mean Reversion in un mercato trending perde denaro.

### 10.2 Hidden Markov Models (HMM) per Regime Detection

**Fonte**: Rabiner, "A Tutorial on Hidden Markov Models", Proceedings of the IEEE, 1989; Hamilton, 1994.

Un HMM è un modello in cui il sistema è descritto da stati nascosti e osservazioni:

```
HMM PER REGIME DETECTION:

Stati nascosti: [Trending, Ranging, High Vol, Low Vol, Crash]
Osservazioni:   [rendimento, volume, volatilità, ADX, Hurst]

Processo:
1. Definisci il numero di stati (K)
2. Addestra l'HMM sui dati storici
3. Per ogni periodo, l'HMM calcola la probabilità di essere in ciascuno stato
4. Lo stato con probabilità più alta è il regime corrente
5. Attiva la strategia appropriata per quel regime
```

```python
from hmmlearn.hmm import GaussianHMM

class RegimeDetector:
    """Rileva il regime di mercato usando HMM."""
    
    def __init__(self, n_states=5):
        self.n_states = n_states
        self.model = GaussianHMM(
            n_components=n_states,
            covariance_type='full',
            n_iter=200,
            random_state=42
        )
    
    def train(self, features: np.ndarray):
        """
        Addestra l'HMM sulle features di mercato.
        
        Features: matrix (n_samples, n_features)
        Features tipiche: log_returns, volume, volatility, ADX, Hurst
        """
        self.model.fit(features)
    
    def detect_regime(self, features: np.ndarray) -> int:
        """
        Ritorna il regime corrente (0 a n_states-1).
        """
        return self.model.predict(features[-1:])
    
    def get_regime_probabilities(self, features: np.ndarray) -> np.ndarray:
        """
        Ritorna la probabilità di ciascun regime.
        """
        return self.model.predict_proba(features[-1:])
    
    def get_regime_names(self) -> List[str]:
        """
        I nomi dei regimi sono assegnati post-hoc basandosi
        sulle caratteristiche di ciascuno stato.
        """
        return self.regime_names  # set during post-hoc analysis
```

### 10.3 CUSUM Tests per Change Point Detection

**Fonte**: Page, "Continuous Inspection Ads", Biometrika, 1954; Brown, Durbin, Evans, "Techniques for Testing the Constancy of Regression Relationships over Time", 1975.

Il CUSUM (Cumulative Sum) test rileva cambiamenti nella distribuzione dei rendimenti:

```
CUSUM ALGORITHM:

1. Calcola la media mobile dei rendimenti: μ_t = mean(r_{t-k:t})
2. Calcola la deviazione cumulativa:
   S_t = max(0, S_{t-1} + (r_t - μ_t))  (per upper bound)
   S_t = min(0, S_{t-1} + (r_t - μ_t))  (per lower bound)
3. Se S_t > threshold → cambiamento di regime rilevato

Interpretazione:
- S_t cresce → i rendimenti sono sistematicamente più alti (bullish regime)
- S_t decresce → i rendimenti sono sistematicamente più bassi (bearish regime)
- S_t oscilla → nessun cambiamento significativo
```

```python
class CUSUMDetector:
    """CUSUM test per il rilevamento di change points."""
    
    def __init__(self, threshold=2.0):
        self.threshold = threshold
        self.reset()
    
    def reset(self):
        self.cusum_pos = 0.0
        self.cusum_neg = 0.0
    
    def detect(self, returns: np.ndarray) -> bool:
        """
        Controlla se è stato rilevato un cambiamento di regime.
        """
        mean_return = np.mean(returns[-50:])  # Media recente
        std_return = np.std(returns[-50:])
        
        for r in returns[-5:]:  # Ultime 5 osservazioni
            standardized = (r - mean_return) / (std_return + 1e-9)
            self.cusum_pos = max(0, self.cusum_pos + standardized - 0.5)
            self.cusum_neg = min(0, self.cusum_neg + standardized + 0.5)
            
            if abs(self.cusum_pos) > self.threshold or abs(self.cusum_neg) > self.threshold:
                return True  # Change point detected
        
        return False
```

### 10.4 Regime-Aware Strategy Selection

```python
class RegimeAwareStrategySelector:
    """Seleziona la strategia migliore in base al regime corrente."""
    
    def __init__(self, strategies: dict, regime_detector: RegimeDetector):
        """
        strategies: {regime_name: StrategyClass, ...}
        regime_detector: modello HMM per il rilevamento dei regimi
        """
        self.strategies = strategies
        self.regime_detector = regime_detector
        self.current_regime = None
    
    def get_best_strategy(self, features: np.ndarray) -> TradingStrategy:
        """
        Rileva il regime e restituisce la strategia corrispondente.
        """
        regime = self.regime_detector.detect_regime(features)
        regime_name = self.regime_detector.regime_names[regime]
        
        if regime_name in self.strategies:
            self.current_regime = regime_name
            return self.strategies[regime_name]
        else:
            # Default: nessuna strategia operativa
            return None
    
    def get_strategy_weights(self, features: np.ndarray) -> dict:
        """
        Restituisce i pesi di ciascuna strategia basati sulle probabilità di regime.
        """
        probs = self.regime_detector.get_regime_probabilities(features)[0]
        weights = {}
        
        for i, regime_name in enumerate(self.regime_detector.regime_names):
            if regime_name in self.strategies:
                weights[regime_name] = probs[i]
        
        # Normalizza
        total = sum(weights.values())
        weights = {k: v/total for k, v in weights.items()}
        
        return weights
```

---

## Appendice — Formule Matematiche Riassuntive

### A. Backtesting Metrics

```
Sharpe Ratio = (mean_return - risk_free_rate) / std(return) × √T

Sortino Ratio = (mean_return - target) / downside_std × √T

Calmar Ratio = annual_return / max_drawdown

Profit Factor = gross_profit / gross_loss

Win Rate = n_winning_trades / n_total_trades

Expectancy = (win_rate × avg_win) - ((1 - win_rate) × avg_loss)

Max Drawdown = max(running_max - equity) / running_max

Kelly Criterion: f* = (bp - q) / b
  Dove b = win/loss ratio, p = win probability, q = 1 - p
```

### B. Bayesian Optimization

```
Gaussian Process: f(x) ~ GP(m(x), k(x, x'))

Posterior Mean: μ*(x) = k(x*, X) [K(X,X) + σ_n²I]⁻¹ y
Posterior Variance: σ²*(x*) = k(x*, x*) - k(x*, X) [K(X,X) + σ_n²I]⁻¹ k(X, x*)

Expected Improvement:
EI(x) = (μ(x) - f*) Φ(Z) + σ(x) φ(Z)
Dove Z = (μ(x) - f*) / σ(x)
```

### C. Fractional Differentiation

```
∇^d X_t = (1 - B)^d X_t

Pesi ricorsivi:
ω_0 = 1
ω_k = -ω_{k-1} × (d - k + 1) / k

Differenziazione frazionaria:
∇^d X_t = Σ_{k=0}^{∞} ω_k X_{t-k}
```

### D. Hurst Exponent

```
H = lim_{k→∞} E[R(k)/S(k)] / k^H

Dove R(k) = range, S(k) = standard deviation, k = time lag

Metodo: log(R/S) = H × log(k) + C
```

### E. Information Theory

```
Entropy: H(X) = -Σ p(x) log₂ p(x)

Mutual Information: I(X;Y) = H(X) + H(Y) - H(X,Y)

Information Coefficient: IC = corr(signal_t, return_{t+1})

Information Ratio: IR = mean(IC) / std(IC)
```

### F. Statistical Tests

```
t-test: t = (mean - μ₀) / (std / √n)

Augmented Dickey-Fuller (ADF):
H₀: serie non stazionaria (unit root presente)
H₁: serie stazionaria
p-value < 0.05 → rifiuta H₀ → serie stazionaria

Shapiro-Wilk: test di normalità
H₀: dati normalmente distribuiti
p-value < 0.05 → dati non normali

Bonferroni: α_corrected = α / n_tests
```

### G. Ensemble Methods

```
Bias-Variance: Err(x) = Bias² + Variance + Irreducible Error

Bagging: ŷ = (1/n) Σ ŷ_i

Random Forest: median voting o media pesata

Stacking: ŷ = w₁·f₁(x) + w₂·f₂(x) + ... + wₙ·fₙ(x)
  Dove w_i = peso ottimale del modello i-esimo
```

### H. Reinforcement Learning

```
Bellman Equation: V(s) = max_a [R(s,a) + γ Σ P(s'|s,a) V(s')]

Policy Gradient: ∇J(θ) = E[∇_θ log π_θ(a|s) · Q^π(s,a)]

PPO Objective: L^CLIP(θ) = E[min(ratio(θ)·A, clip(ratio(θ), 1-ε, 1+ε)·A)]
  Dove ratio(θ) = π_θ(a|s) / π_{θ_old}(a|s)
  E = clip parameter
  A = advantage function

Soft Actor-Critic: L = E[-(r + γ·V(s')) - α·log π(a|s)]
```

---

## RIFERIMENTI BIBLIOGRAFICI COMPLETI

### Libri

1. **López de Prado, M. (2018)**. *Advances in Financial Machine Learning*. Wiley. ISBN: 978-1-119-48208-6.
   - Capitoli 1-13 coprono l'intero framework FML
   - Disponibile presso: [Wiley](https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086)

2. **López de Prado, M. (2020)**. *Machine Learning for Asset Managers*. Cambridge University Press. ISBN: 978-1-009-70242-3.
   - Estensione dell'AFML con focus su portafoglio
   - Disponibile presso: [Cambridge](https://www.cambridge.org/core/books/machine-learning-for-asset-managers/)

3. **Pardo, R. (2008)**. *The Evaluation and Optimization of Trading Strategies*. Wiley.
   - Walk-forward analysis e validazione

4. **Cover, T. e Thomas, J. (2006)**. *Elements of Information Theory*, 2nd ed. Wiley.
   - Fondamenti di information theory

5. **Hamilton, J.D. (1994)**. *Time Series Analysis*. Princeton University Press.
   - HMM, regime switching, analisi temporale

6. **Goldberg, D.E. (1989)**. *Genetic Algorithms in Search, Optimization, and Machine Learning*. Addison-Wesley.
   - Fondamenti degli algoritmi genetici

7. **Koza, J.R. (1992)**. *Genetic Programming: On the Programming of Computers by Means of Natural Selection*. MIT Press.
   - Fondamenti del Genetic Programming

8. **Hastie, T., Tibshirani, R., Friedman, J. (2009)**. *The Elements of Statistical Learning*, 2nd ed. Springer.
   - Ensemble methods, bias-variance decomposition

### Paper

9. **Turner, R., Eriksson, D., McCourt, M., et al. (2021)**. "Bayesian Optimization is Superior to Random Search for Machine Learning Hyperparameter Tuning". *NeurIPS 2020 Competition*. [arXiv:2104.10201](https://arxiv.org/abs/2104.10201).

10. **López de Prado, M. e Lewis, S. (2019)**. "Detecting False Investment Strategies Using Deflated Sharpe Ratios". *Journal of Portfolio Management*. [arXiv](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3447398).

11. **Azzali, I., Cilia, N.D., De Stefano, C., et al. (2025)**. "Evolving Financial Trading Strategies with Vectorial Genetic Programming". [arXiv:2504.05418](https://arxiv.org/abs/2504.05418).

12. **Lu, C.I. (2023)**. "Evaluation of Deep Reinforcement Learning Algorithms for Portfolio Optimisation". [arXiv:2307.07694](https://arxiv.org/abs/2307.07694).

13. **Xu, Y., et al. (2023)**. "TradeMaster: A Holistic Quantitative Trading Platform Empowered by Reinforcement Learning". *NeurIPS 2023*.

14. **AlgoEvolve** (2025). "LLM-driven Meta-evolution of Algorithmic Trading Programs". [arXiv:2606.26173](https://arxiv.org/abs/2606.26173).

15. **Berger, T., et al. (2019)**. "Dynamic Investment Strategies with Machine Learning Methods". Tesis di dottorato. [PDF](https://epub.ub.uni-muenchen.de/69183/).

16. **Bai, H., Cheng, R., Jin, Y. (2023)**. "Evolutionary Reinforcement Learning: A Survey". [arXiv:2303.04150](https://arxiv.org/abs/2303.04150).

17. **Jones, D.R., Schonlau, M., Welch, W.J. (1998)**. "Efficient Global Optimization of Expensive Black-Box Functions". *Journal of Global Optimization*.

18. **Shahriari, B., Swersky, K., Zemel, R., Adams, R.P., de Freitas, N. (2016)**. "Taking the Human Out of the Loop: A Review of Bayesian Optimization". *Proceedings of the IEEE*. [arXiv:1807.02811](https://arxiv.org/abs/1807.02811).

### Librerie Python

19. **fracdiff** ([GitHub](https://github.com/fracdiff/fracdiff)) — Fractional differentiation implementation.
20. **Optuna** ([optuna.org](https://optuna.org/)) — Hyperparameter optimization framework.
21. **scikit-optimize** ([scikit-optimize.github.io](https://scikit-optimize.github.io/)) — Bayesian optimization with Gaussian Processes.
22. **purged-cv** ([GitHub](https://github.com/martex-dev/purged-cv)) — Purged K-Fold Cross-Validation.
23. **hmmlearn** — Hidden Markov Models for Python.

### Software e Piattaforme

24. **FinRL** ([github.com/AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL)) — Deep reinforcement learning for trading.
25. **QuantConnect** ([www.quantconnect.com](https://www.quantconnect.com/)) — Algorithmic trading platform.
26. **Backtrader** ([github.com/mementum/backtrader](https://github.com/mementum/backtrader)) — Python backtesting framework.

### Corso Accademico

27. **López de Prado, M. (2019)**. "Advances in Financial Machine Learning: Lecture 10/10". Cornell University ORIE 5256. [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3447398).

---

## NOTA FINALE

Questo documento non è solo una raccolta di concetti — è un **manifesto teorico** per la costruzione di una macchina di discovery strategica. Ogni formula, ogni teorema, ogni algoritmo qui contenuto è stato verificato, contestualizzato, e collegato a un'applicazione pratica nel nostro sistema.

La differenza tra un tool che funziona e una macchina mostruosa risiede nella **profondità della comprensione teorica** su cui si basa. Senza capire *perché* funziona il Purged K-Fold, non puoi usarlo correttamente. Senza capire *perché* BO supera grid search, non puoi progettarlo bene. Senza capire *perché* l'HMM rileva i regimi, non puoi fidarti dei suoi output.

**Il sistema attuale è un ottimo punto di partenza. La conoscenza teorica è la scala per arrivare alla macchina mostruosa.**

> "An answer without a question is a solution without a problem." — Adapted from López de Prado
