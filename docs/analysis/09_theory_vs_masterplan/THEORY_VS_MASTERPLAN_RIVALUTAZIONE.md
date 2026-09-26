# ⚖️ RIVALUTAZIONE ESTENSIVA: TUTTI I 25 PUNTI UNO PER UNO

## Seconda Analisi Completa con Evidenze dal Codice Reale
### "Sicuro sicuro?" — Sì, ora sì. Ecco le prove.

> **Metodo**: Per ogni punto ho verificato (a) cosa dice il theory, (b) cosa dice il masterplan, (c) cosa dice il codice reale. Solo dopo ho dato il verdetto.
>
> **Fatti verificati dal codice**:
> - `requirements.txt`: solo `pandas, numpy, python-dotenv, numba`. Niente optuna, scipy, sklearn, hmmlearn, fracdiff.
> - `src/strategy.py`: NESSUNA interfaccia Strategy. Solo dataclass `BacktestParams/Trade/BacktestResult` con campi hardcoded `x_percent, y_seconds, z_percent`.
> - `src/metrics.py`: NESSUNO Sharpe/Sortino/Calmar/expectancy. Solo win_rate, pnl, drawdown, profit_factor, best/worst, MAE/MFE.
> - `src/parameter_grid.py`: `itertools.product` puro.
> - `src/gpu/gpu_simulator.py`: kernel CUDA hardcoded Momentum+Drop, nessuno strategy dispatch.
> - Theory doc riga 436 vs 1452: il theory contiene ENTRAMBE le versioni del DSR senza riconciliarle. Il PBO del theory (riga 1481) è identico a quello del masterplan.
>
> **Verdetti possibili**: 🟢 KEEP-NOW (attuabile oggi) · 🟡 FUTURE-NOTE (nota per dopo) · 🔴 DROP (fuori contesto/scope)

---

## PUNTO 1 — Production Chain (10 anelli di López de Prado)

**Cosa dice il theory**: Catena a 10 anelli (Data Structures → ... → Execution). Ogni anello rigoroso o tutto inaffidabile.

**Cosa dice il masterplan**: Architettura a 7 strati. Nessun riferimento alla Production Chain.

**Cosa dice il codice**: Il flusso è lineare: TS scarica → Python fa backtest → stampa risultati. Non esiste nessun "processo" multi-stadio da mappare.

**Analisi**: La Production Chain è un framework di *processo di ricerca* per desk quantitativi istituzionali. I 7 strati sono un'architettura *software*. Sono due viste diverse ma la Production Chain non aggiunge nessuna decisione operativa: gli anelli mancanti (Sample Weighting, Bet Sizing, Execution) sono o inapplicabili (vedi punti 14, 16) o fuori scope (il sistema non esegue trading reale). Mappare 10 anelli su 7 strati produce una tabella, non una funzionalità.

**Verdetto: 🔴 DROP.** Framework accademico-istituzionale, nessuna decisione operativa ne deriva.

---

## PUNTO 2 — Dilemma Stazionarietà vs. Memoria

**Cosa dice il theory**: Serie prezzo = non stazionaria (ML non funziona). Serie differenziata = stazionaria ma senza memoria. Frazionaria = compromesso.

**Cosa dice il masterplan**: Accenno in Feature Engineering + `find_optimal_d` + glossario.

**Cosa dice il codice**: Il sistema NON alimenta nessun modello ML con le serie. Esegue regole deterministiche ("prezzo salito X% in Y secondi?"). La stazionarietà è un requisito dei modelli statistici/ML, non delle regole if-then. Nessun file importa o usa differenziazione di alcun tipo.

**Analisi**: Il dilemma è reale *in generale* ma irrilevante *per questo sistema*. Diventerà rilevante solo se/quando si aggiungerà un modello ML che consuma serie temporali (oggi: zero). La libreria `fracdiff` non è nelle dipendenze.

**Verdetto: 🟡 FUTURE-NOTE.** Una riga nella sezione dati: "se in futuro si aggiungono modelli ML, affrontare stazionarietà (cfr. theory Ch.6)". Non una sezione, non una fase.

---

## PUNTO 3 — Formula DSR

**Cosa dice il theory**: Riga 436: `DSR = SR × correction_factor(PBO, N_trials, T)` con `correction = 1.0 - 2.0*pbo`. Riga 1452: `DSR = SR × φ(z)/Φ(z)`, `z = SR×√T`. Le due versioni NON sono mai riconciliate nel documento.

**Cosa dice il masterplan**: Riga 1124: `Sharpe × sqrt(T) × (1 - P(overfitting))`. Riga 1669: `SR × correction(PBO, N_trials, T)`. Sostanzialmente la stessa approssimazione del theory Ch.2.

**Cosa dice il codice**: `metrics.py` NON calcola nemmeno lo Sharpe Ratio. Senza Sharpe non esiste DSR. `scipy` (necessario per φ/Φ) NON è nelle dipendenze. Nessun file calcola DSR o PBO.

**Analisi**: La mia critica originale ("il masterplan sbaglia, il theory ha ragione") era sbagliata: il theory contiene la stessa approssimazione. Il vero stato dei fatti: (a) entrambi i documenti sono incoerenti al loro interno sul DSR; (b) il DSR non è calcolabile oggi perché manca lo Sharpe e manca scipy; (c) la formula φ/Φ richiede T in anni e SR — con dati di pochi mesi e 1000 combinazioni parametriche il risultato sarebbe statisticamente insignificante. Quindi: non è un bug urgente, è una nota di documentazione + un prerequisito mancante (Sharpe).

**Verdetto: 🟢 KEEP AS DOC-NOTE (non come urgenza).** Aggiungere nel masterplan: "Le due formulazioni del DSR nei documenti vanno riconciliate; prerequisito: implementare Sharpe Ratio + scipy; uso reale solo da Fase 3 in poi." Costo: 5 righe di testo. Niente codice oggi.

---

## PUNTO 4 — Multiple Testing Problem

**Cosa dice il theory**: Con 1000 test casuali, P(migliore con sharpe>3 per fortuna) ≈ 75%. Soluzioni: Bonferroni, Holm, Benjamini-Hochberg, DSR.

**Cosa dice il masterplan**: Copre PBO/DSR ma non nomina Bonferroni/BH/FDR né il calcolo del 75%.

**Cosa dice il codice**: `parameter_grid.py` fa `itertools.product` su parametri X/Y/Z della STESSA strategia. Non testa ipotesi alternative distinte — esplora una superficie parametrica. Bonferroni (α/n) su 5000 combinazioni darebbe α≈1e-5: soglia inutilizzabile per grid search, progettata per test di ipotesi indipendenti, non per ottimizzazione parametrica.

**Analisi**: Confusione tra due problemi diversi. (A) "Quale tra 1000 strategie DIVERSE è vera?" → multiple testing, serve correzione. (B) "Quali parametri massimizzano il PnL di UNA strategia?" → ottimizzazione, serve validazione out-of-sample (PBO/DSR/Walk-Forward). Il nostro sistema fa (B). La sezione dedicata al multiple testing servirebbe solo quando arriveranno strategie distinte (Fase 4). Il rischio attuale è già concettualmente coperto da PBO/DSR.

**Verdetto: 🔴 DROP come sezione autonoma.** Al massimo una riga: "quando si testeranno strategie distinte (Fase 4+), affrontare multiple testing (cfr. theory Ch.8.1)".

---

## PUNTO 5 — Formule Acquisition Functions (EI, PI, UCB)

**Cosa dice il theory**: Formule esplicite di EI, PI, UCB per Gaussian Process.

**Cosa dice il masterplan**: Raccomanda Optuna con `TPESampler` + `MedianPruner`. Descrive BO ma senza formule.

**Cosa dice il codice**: Optuna NON è nelle dipendenze. Niente BO implementato. E quando lo sarà, TPE (Tree-structured Parzen Estimator) NON usa EI/PI/UCB — quelli sono per GP. Le formule del theory non corrispondono al sampler raccomandato dal masterplan.

**Analisi**: Le formule EI/PI/UCB servono solo a chi implementa BO con Gaussian Process da zero. Noi useremo Optuna/TPE. Documentare formule inapplicabili allo stack scelto è rumore. Il riferimento al theory basta per i curiosi.

**Verdetto: 🔴 DROP.** Le formule restano nel theory per chi vuole capire; il masterplan non deve duplicarle.

---

## PUNTO 6 — Meta-Strategy Paradigm (7 componenti)

**Cosa dice il theory**: Framework a 7 componenti (Feature Discovery, Template Library, Parameter Discovery, Validator, Meta-Labeler, Portfolio Constructor, Monitoring).

**Cosa dice il masterplan**: 7 strati architetturali con copertura parziale; manca Portfolio Constructor.

**Cosa dice il codice**: Nessuna delle 7 componenti esiste come modulo. Il sistema non ha template library, non ha validator, non ha meta-labeler, non ha portfolio.

**Analisi**: È un framework organizzativo per desk istituzionali, non un requisito software. Il principio chiave ("testa il processo di generazione, non la singola strategia") è già espresso nel masterplan §4.2 ("testare vs scoprire"). Il Portfolio Constructor presuppone un sistema che gestisce portafogli — il nostro fa backtest singoli. Integrare formalmente il paradigma non cambia nessuna riga di codice pianificata.

**Verdetto: 🔴 DROP come integrazione formale.** Il principio resta (già presente); il framework no.

---

## PUNTO 7 — Volume/Dollar/Tick Bars

**Cosa dice il theory**: Time Bars < Volume Bars < Dollar Bars per stazionarietà (AFML Ch.2).

**Cosa dice il masterplan**: Solo OHLC 1s (Time Bars). Nessuna alternativa discussa.

**Cosa dice il codice**: La pipeline TS aggrega aggTrades in OHLC 1s. Supportare Dollar Bars richiederebbe: volume×prezzo per ogni trade, soglie di aggregazione in dollari, modifiche a `aggregateStreaming.ts`, `jsonlWriter.ts`, e a tutto il backtester che assume candele temporali. Nessuna di queste esiste.

**Analisi**: La teoria ha ragione sui vantaggi statistici. Ma è un cambiamento della *struttura dati primaria* con effetti a cascata su tutto lo stack, per un sistema che non ha ancora una seconda strategia. Il rapporto costo/beneficio oggi è negativo. È però una nota legittima per la roadmap dati.

**Verdetto: 🟡 FUTURE-NOTE.** Una riga in roadmap: "valutare Dollar/Volume Bars quando il sistema avrà strategie validate (cfr. theory Ch.1.6)". Non un requisito.

---

## PUNTO 8 — Information Theory (IC, IR, Entropy, Alpha)

**Cosa dice il theory**: Capitolo intero: IC = corr(signal, return futuro); IR = mean(IC)/std(IC); entropia; test di significatività; `AlphaMonitor`.

**Cosa dice il masterplan**: Solo "alpha decay" nominale in Strato 7 e glossario. Nessun IC/IR/entropia.

**Cosa dice il codice**: Il sistema genera trade discreti da soglie, NON segnali continui. Non esiste un vettore `signals` da correlare con i rendimenti. Nessun calcolo di correlazione segnale-rendimento esiste. I trade per simbolo sono nell'ordine delle centinaia — insufficienti per IC statisticamente significativi (servono migliaia di osservazioni).

**Analisi**: IC/IR misurano la qualità predittiva di un segnale continuo in produzione. Prerequisiti mancanti: (a) segnale continuo (non abbiamo), (b) numerosità (non abbiamo), (c) fase di produzione/monitoraggio (non abbiamo — siamo in discovery). L'`AlphaMonitor` proposto sarebbe codice morto. L'alpha decay monitoring ha senso solo con strategie operative storicizzate.

**Verdetto: 🟡 FUTURE-NOTE.** "Quando esisteranno strategie in monitoraggio con segnali storicizzati, usare IC/IR (cfr. theory Ch.7)". Non una sezione, non codice oggi.

---

## PUNTO 9 — Meta-Labeling (modello a due livelli)

**Cosa dice il theory**: Livello 1 = strategia → segnale. Livello 2 = segnale + contesto → 0/1 (opera/non opera). Ponte tra discovery e uso.

**Cosa dice il masterplan**: Solo glossario + riferimenti. Nessuna architettura.

**Cosa dice il codice**: Non esiste il livello 1 (nessuna strategia validata come modulo). Il contesto (ADX, Hurst, volatilità) non è calcolato da nessuna parte. Le etichette per il livello 2 (trade profittevole sì/no su storico esteso) non esistono.

**Analisi**: Il meta-labeling richiede: strategia base funzionante + feature di contesto + storico etichettato. Zero dei tre esiste. È il passo N+2 quando siamo al passo 0. Il concetto è corretto ma l'implementazione è a valle di Fase 1 (Strategy), Fase 5 (contesto/regime) e di uno storico di trade.

**Verdetto: 🟡 FUTURE-NOTE.** "Dopo strategie validate + contesto disponibile, valutare meta-labeler come filtro (cfr. theory Ch.1.7)". Niente architettura oggi.

---

## PUNTO 10 — Ensemble Methods (Bagging, Stacking, RF)

**Cosa dice il theory**: Bias-variance decomposition; Bagging (bootstrap); RF feature importance; Stacking (meta-learner); Meta-Strategy framework.

**Cosa dice il masterplan**: RF citato in Fase 5 per feature importance; resto assente.

**Cosa dice il codice**: Nessun bootstrap, nessun ensemble, nessuna feature ingegnerizzata (solo OHLCV), nessun meta-learner. `sklearn` NON è nelle dipendenze.

**Analisi**: Vanno separati tre sottocasi. (a) Bagging per validazione: concettualmente ridondante con CPCV/Walk-Forward che danno già distribuzioni di PnL; aggiungere 100 backtest bootstrap per stimare robustezza quando il sistema fatica già con grid search è costo senza informazione nuova. (b) Stacking: richiede meta-learner ML + strategie multiple validate — zero prerequisiti. (c) RF feature importance: richiede feature ingegnerizzate (Fase 6) + `sklearn`. Solo (c) ha un futuro, a valle delle feature.

**Verdetto: 🔴 DROP Bagging e Stacking. 🟡 FUTURE-NOTE solo per RF feature importance** (dopo Fase 6, con sklearn). Non componenti architetturali oggi.

---

## PUNTO 11 — Regime Detection avanzato (HMM + CUSUM)

**Cosa dice il theory**: HMM a stati nascosti con probabilità morbide; CUSUM per change-point; selezione strategie pesata per probabilità di regime.

**Cosa dice il masterplan**: Soglie deterministiche (ADX>25 trending, ADX<20 ranging, Hurst, variance ratio). Niente HMM/CUSUM/probabilità.

**Cosa dice il codice**: Nessun calcolo di ADX, Hurst, volatilità realizzata esiste nel backtester. `hmmlearn` NON è nelle dipendenze. Il sistema è un backtester su storico, non un sistema realtime: non deve decidere "adesso che regime è?" durante l'esecuzione.

**Analisi**: Due problemi distinti. (A) Classificare il regime *a posteriori* per analizzare dove una strategia ha funzionato: utile, fattibile con soglie semplici, non richiede HMM. (B) Rilevare il regime *in tempo reale* in produzione: richiede HMM/CUSUM ma presuppone produzione. Le soglie deterministiche sono fragili ma sufficienti per (A) oggi; HMM è superiore ma richiede training, tuning, dipendenze e ha assunzioni distribuzionali (mistura gaussiana) dubbie su crypto. CUSUM richiede threshold calibrato su change-point storici che non abbiamo.

**Verdetto: 🟡 FUTURE-NOTE.** "Soglie semplici per analisi post-backtest oggi; HMM/CUSUM solo in ottica produzione futura (cfr. theory Ch.10)". Niente HMM nel sistema di discovery.

---

## PUNTO 12 — Reinforcement Learning (PPO, DDPG, SAC, TradeMaster)

**Cosa dice il theory**: Capitolo intero: MDP (S,A,P,R,γ); PPO on-policy stabile; DDPG/SAC off-policy sensibili al noise (Lu 2023); confronto BO vs RL; benchmark TradeMaster.

**Cosa dice il masterplan**: Praticamente nulla (glossario + riferimenti).

**Cosa dice il codice**: Nessun portafoglio. Nessuna policy. Nessun ambiente sequenziale azione→reward→stato. Nessuna rete neurale, nessun torch/tensorflow nelle dipendenze. Il theory stesso (Lu 2023) documenta che DDPG/SAC falliscono sul noise delle reward finanziarie.

**Analisi**: RL serve a gestire dinamicamente un portafoglio di strategie (pesi adattivi). Prerequisiti: portafoglio esistente + ambiente di simulazione sequenziale + milioni di step + infrastruttura ML. Zero presenti. BO (ottimizzazione parametri statici) e RL (policy adattive) risolvono problemi diversi; il nostro problema attuale è il primo. TradeMaster è un sistema intero, non una feature. Questo non è un "gap del masterplan" — è un altro progetto.

**Verdetto: 🔴 DROP completo.** Fuori scope. Non una nota futura del backtester; al massimo un progetto separato eventuale.

---

## PUNTO 13 — Genetic Programming (bloat, parsimony, VGP)

**Cosa dice il theory**: Koza 1992; crossover/mutation/selection; bloat problem + soluzioni (parsimony, size limit, pruning, ADF); VGP di Azzali et al. 2025 che batte GP standard su alberi.

**Cosa dice il masterplan**: Crossover/mutation di strategie e template (§5.4). Niente bloat/parsimony/VGP/ADF.

**Cosa dice il codice**: Nessun GP implementato. La "generazione" pianificata (Fase 4) è crossover/mutation di *parametri e template*, non evoluzione di *alberi di programma*.

**Analisi**: Il bloat è un problema specifico del GP su alberi (programmi che crescono senza migliorare fitness). La generazione parametrica non ha alberi → non ha bloat → non serve parsimony pressure. VGP opera su vettori per evolvere *strutture di programma*; noi evolviamo *valori di parametri*: domini diversi. Citare VGP come "alternativa superiore" è fuorviante perché risolve un problema che non abbiamo. Il crossover/mutation parametrico del masterplan resta valido senza aggiunte.

**Verdetto: 🔴 DROP (bloat, parsimony, VGP, ADF).** Non si applicano alla generazione parametrica. Nessuna modifica al §5.4 necessaria.

---

## PUNTO 14 — Sample Weighting (overlap, uniqueness, time decay)

**Cosa dice il theory**: AFML Ch.4: overlapping outcomes, concurrent labels, uniqueness weighting, time decay — perché le osservazioni finanziarie etichettate non sono indipendenti.

**Cosa dice il masterplan**: Zero. Mai menzionato.

**Cosa dice il codice**: Il sistema NON etichetta rendimenti futuri (niente Triple-Barrier). Ogni combinazione X/Y/Z è un backtest indipendente con proprio PnL. Non esistono "label condivise" né "concurrent labels". Non c'è nulla da pesare.

**Analisi**: Sample Weighting nasce per ML supervisionato con labeling a orizzonte (le etichette si sovrappongono temporalmente). Prerequisiti: labeling + overlap. Entrambi assenti. Diventerebbe rilevante solo se si introducesse Triple-Barrier labeling + CPCV (Fase 3+). Oggi è una tecnica senza oggetto.

**Verdetto: 🔴 DROP.** Da rivalutare solo se/quando si introdurrà labeling con overlap. Non un gap attuale.

---

## PUNTO 15 — CUSUM Change-Point Detection

**Cosa dice il theory**: Somma cumulativa delle deviazioni standardizzate; threshold → change-point rilevato. Page 1954.

**Cosa dice il masterplan**: Zero.

**Cosa dice il codice**: Nessun monitoraggio realtime. Il backtester analizza storico offline: i cambi di regime sono visibili nei dati, non serve un rilevatore online.

**Analisi**: CUSUM è un rilevatore *online* per flussi in produzione. Il backtester è *offline*. Il threshold va calibrato su change-point storici noti — non disponibili. Anche come analisi post-hoc, semplici statistiche rolling bastano. (Si veda anche punto 11: la parte CUSUM è coperta dalla stessa valutazione.)

**Verdetto: 🔴 DROP.** Tool di produzione realtime; nessun uso nel backtester.

---

## PUNTO 16 — Metriche aggiuntive (Sortino, Calmar, Kelly, Expectancy)

**Cosa dice il theory**: Appendice A: Sortino, Calmar, Profit Factor, Win Rate, Expectancy, Max DD, Kelly `f*=(bp-q)/b`.

**Cosa dice il masterplan**: Usa Sharpe, Win Rate, Profit Factor, Max DD, PnL. Manca il resto.

**Cosa dice il codice**: `metrics.py` calcola da `trades`: pnls, pnl_percents, win/loss counts, DD su equity cumulata, profit factor. TUTTI gli input per Sortino (downside std dei pnl), Calmar (return annuo/DD — DD esiste già), Expectancy (win_rate×avg_win − loss_rate×avg_loss) sono già disponibili. Servono solo `numpy` (già dipendenza). Kelly invece è un tool di *position sizing*, non una metrica di valutazione — il backtester non fa sizing.

**Analisi**: Questo è il punto con il miglior rapporto costo/beneficio di tutti i 25. Sortino/Calmar/Expectancy = ~30 righe di numpy puro, zero nuove dipendenze, informazione reale aggiuntiva (Sortino penalizza solo il downside — meglio di Sharpe per strategie asimmetriche; Calmar confronta strategie con DD diversi; Expectancy dice se il singolo trade medio è profittevole). Kelly va escluso dalla valutazione (è sizing, verrà con eventuale Bet Sizing futuro).

**Verdetto: 🟢 KEEP-NOW (Sortino, Calmar, Expectancy). 🔴 DROP Kelly come metrica.** Implementabile oggi in `metrics.py` senza nuove dipendenze.

---

## PUNTO 17 — Walk-Forward con test statistici (t-test, Shapiro-Wilk)

**Cosa dice il theory**: `WalkForwardValidator` con profitability rate + t-test + Shapiro + DSR + PBO + criterio `is_acceptable`.

**Cosa dice il masterplan**: Walk-Forward con solo profitability rate (>60% periodi → robusta).

**Cosa dice il codice**: Walk-Forward NON implementato (solo split 70/30 in `data_splitter.py`). `scipy` (necessario per ttest/shapiro) NON è nelle dipendenze.

**Analisi**: Tre problemi. (1) Prematurità: test su qualcosa che non esiste. (2) Violazione di assunzioni: i PnL dei periodi WF non sono indipendenti (training windows sovrapposte) → il t-test a un campione assume i.i.d., assunzione violata. (3) Potenza: Shapiro-Wilk su 5–10 periodi non ha potenza statistica. I test sarebbero decorativi. Quando il WF esisterà, DSR/PBO/profitability-rate bastano; i test parametrici aggiungono poco e richiedono assunzioni non soddisfatte.

**Verdetto: 🔴 DROP.** Non aggiungere t-test/Shapiro al piano WF. Mantenere profitability-rate + DSR + PBO come criteri (già previsti).

---

## PUNTO 18 — Soglie decisionali PBO (10% / 10-50% / >50%)

**Cosa dice il theory**: `<10%` solida, `10-50%` potenzialmente valida, `>50%` rigetta (AFML Ch.12.5).

**Cosa dice il masterplan**: Solo `>50% → rigetta`. Manca la granularità.

**Cosa dice il codice**: PBO non calcolato da nessuna parte (serve CPCV, Fase 3).

**Analisi**: Le soglie sono regole empiriche di López de Prado, non teoremi — vanno presentate come tali, non come verità matematiche. Detto questo, sono una guida decisionale utile e costano una tabella + 15 righe di `evaluate_pbo()`. Prerequisito: CPCV implementato. Quindi non codice oggi, ma documentazione valida da avere pronta per Fase 3. Il PBO del theory (n_negative/n_total) coincide con quello del masterplan — nessuna correzione di formula necessaria, solo granularità.

**Verdetto: 🟡 FUTURE-NOTE (pronta per Fase 3).** Aggiungere tabella + funzione come specifica, con disclaimer "soglie empiriche". Zero codice oggi.

---

## PUNTO 19 — Fractional Differentiation (formula ricorsiva, FFD, `fracdiff`)

**Cosa dice il theory**: Pesi ricorsivi ω_k, esempio numerico d=0.5, metodo FFD con ADF test, libreria `fracdiff` sklearn-compatibile.

**Cosa dice il masterplan**: Formula + `find_optimal_d`, ma senza esempio numerico né integrazione nel workflow.

**Cosa dice il codice**: Nessun modello ML consuma serie. `fracdiff`, `statsmodels` (ADF), `sklearn` NON sono dipendenze. FFD su serie da ~150M di punti (caso DCRUSDT) sarebbe computazionalmente pesante senza beneficiario.

**Analisi**: Stessa diagnosi del punto 2 (ne è il corollario operativo). Dettagli matematici corretti ma senza consumatore. L'esempio numerico e la libreria servono a chi implementa preprocessing ML — nessuno lo fa qui.

**Verdetto: 🔴 DROP.** Coperto dalla future-note del punto 2. Niente `fracdiff`, niente FFD nel workflow oggi.

---

## PUNTO 20 — Bibliografia completa (27 riferimenti)

**Cosa dice il theory**: 27 riferimenti completi con link arXiv/GitHub.

**Cosa dice il masterplan**: 5 riferimenti essenziali.

**Analisi**: Il theory è il documento di riferimento; il masterplan è il documento operativo. Duplicare 27 voci è ridondanza documentale. Un puntatore basta. Chi implementa `pip install purged-cv` non ha bisogno della citazione; chi vuole il contesto sa dove trovarla.

**Verdetto: 🔴 DROP.** Una riga di puntatore nel masterplan ("dettagli e bibliografia: docs/theory/"). Niente appendice duplicata.

---

## PUNTO 21 — Paradosso di Sisifo (naming esplicito)

**Cosa dice il theory**: Ciclo trova-pattern → backtest → migliora → overfitting → produzione → fallimento; soluzione = Meta-Strategy Paradigm.

**Cosa dice il masterplan**: §4.2 "testare vs scoprire" esprime lo stesso concetto senza il nome.

**Analisi**: Dare il nome non cambia nessuna decisione, nessuna formula, nessuna riga di codice, nessuna priorità. È retorica. Il concetto è già presente e operativo ("il sistema è la macchina che genera strategie valide"). Il naming ha valore didattico nel theory, non nel piano operativo.

**Verdetto: 🔴 DROP.** Nessuna sezione. Il principio resta già espresso.

---

## PUNTO 22 — GPU multi-strategy (schedulazione kernel)

**Cosa dice il theory**: TradeMaster come evidenza che regime detection + architettura modulare contano (benchmark, non soluzione).

**Cosa dice il masterplan**: §6.1 con 4 soluzioni (dispatch CPU, kernel parametrizzato con switch, kernel multipli per archetipo, CPU-selezione/GPU-valutazione). Raccomanda batch separati o CPU-selezione.

**Cosa dice il codice**: Verificato: `gpu_simulator.py` ha kernel hardcoded Momentum+Drop, `tid = blockDim.x*blockIdx.x + threadIdx.x` con un thread per combinazione, parametri passati come array. ZERO dispatch: nessuna `strategy_type`, nessuno `switch`. Appena si aggiunge la seconda strategia (Fase 1), questo file va toccato. Lo `switch(strategy_type)` nel kernel causerebbe warp divergence reale (thread dello stesso warp su rami diversi → serializzazione). La soluzione "kernel per archetipo + batch separati" evita il problema alla radice. Requisiti utente espliciti: efficienza computazionale fin da subito.

**Analisi**: Questo punto è diverso dagli altri 24: non introduce dipendenze, modelli, o paradigmi — è un *vincolo di design* a costo zero oggi che evita un refactor doloroso domani. Progettare l'interfaccia Strategy (Fase 1) ignorando come i kernel la eseguiranno significa rischiare un'astrazione CPU-centrica che la GPU non può eseguire efficientemente (es. signal objects Python → non trasferibili su kernel). Il principio da fissare ora: (1) un kernel compilato per archetipo, (2) batch omogenei per archetipo, (3) CPU seleziona strategia+parametri, GPU valuta solo parametri, (4) niente branch su strategy_type dentro il kernel. Il dettaglio CUDA a basso livello resta implementazione futura, ma il principio vincola correttamente la Fase 1.

**Verdetto: 🟢 KEEP-NOW come principio di design (non come implementazione).** 10 righe di vincoli architetturali nel masterplan §6.1 + un vincolo esplicito in Fase 1 ("l'interfaccia Strategy deve essere GPU-compatibile: parametri come array tipizzati, niente oggetti Python nel path GPU"). Nessun codice CUDA oggi.

---

## PUNTO 23 — Feature Importance by Regime (RF per regime)

**Cosa dice il theory**: RF per capire quali feature predicono (es. close_lag_5 15% vs volume 2%).

**Cosa dice il masterplan**: RF in Fase 5 generica, non collegata ai regimi.

**Cosa dice il codice**: Zero feature ingegnerizzate (solo OHLCV grezzo). Zero label di regime (regime detection non implementato). `sklearn` assente.

**Analisi**: Richiede feature (Fase 6) × regime labels (Fase 5) × sklearn. Zero dei tre. È il prodotto cartesiano di due future-note. Non ha esistenza autonoma oggi.

**Verdetto: 🔴 DROP come voce autonoma.** Resta implicito nelle future-note di Fase 5/6. Nessuna voce separata.

---

## PUNTO 24 — Alpha Decay quantitativo (IC decay rate, test significatività)

**Cosa dice il theory**: `decay = (IC_w1 − IC_w2)/IC_w1`; soglia Sharpe −30%; `is_alpha_significant` con t-stat su IC; `should_retire_strategy`.

**Cosa dice il masterplan**: Concetto nominale in Strato 7, senza formule né criteri.

**Cosa dice il codice**: Nessuna strategia in produzione, nessuno storico IC, nessun segnale continuo (vedi punto 8). Nulla da misurare.

**Analisi**: L'alpha decay si misura su strategie operative storicizzate. Siamo in discovery pre-validazione. Le formule sono corrette ma senza oggetto. Quando esisteranno IC storicizzati (a valle del punto 8), questo framework si attacca naturalmente.

**Verdetto: 🔴 DROP come componente; 🟡 assorbito nella future-note del punto 8.** Nessuna voce separata, nessun codice.

---

## PUNTO 25 — Production Chain come checklist di validazione tra fasi

**Cosa dice il theory**: I 10 anelli come sequenza obbligata (se uno fallisce, tutto inaffidabile).

**Cosa dice il masterplan**: Piano Fasi 0–8 senza checklist incrociata.

**Analisi**: È il punto 1 riciclato in forma operativa. Se la Production Chain non è il framework (verdetto punto 1: DROP), non può essere nemmeno la checklist. Le Fasi 0–8 hanno già dipendenze naturali (non fai BO senza Strategy, non fai CPCV senza backtest). Aggiungere una matrice di mappatura anelli×fasi è burocrazia documentale.

**Verdetto: 🔴 DROP.** Ridondante con punto 1.

---

## 📊 CONTEGGIO FINALE VERIFICATO

| Verdetto | Punti | Dettaglio |
|---|---|---|
| 🟢 KEEP-NOW | 3 | #16 (Sortino/Calmar/Expectancy in `metrics.py`, solo numpy), #22 (principio GPU-per-archetipo come vincolo Fase 1), #3 (nota doc DSR: riconciliare le due formulazioni, prerequisito Sharpe+scipy) |
| 🟡 FUTURE-NOTE | 7 | #2 (stazionarietà), #7 (Dollar/Volume bars), #8 (IC/IR, assorbe #24), #9 (meta-labeling), #10c (RF importance post-feature), #11 (HMM/CUSUM produzione), #18 (soglie PBO per Fase 3) |
| 🔴 DROP | 15 | #1, #4, #5, #6, #10a/b, #12, #13, #14, #15, #17, #19, #20, #21, #23, #25 |

3 + 7 + 15 = 25 ✓

## 🎯 RISPOSTA ALLA DOMANDA "solo 6 di 25?"

No. La conta onesta è **3 attuabili ora, 7 note future, 15 da scartare**. Ero stato troppo generoso prima ("6") e troppo distruttivo poi ("2"). I 3 keep-now costano complessivamente: ~40 righe di numpy in `metrics.py` + ~10 righe di vincoli nel masterplan + 5 righe di nota DSR. Zero nuove dipendenze. Tutto il resto è o futuro o fuori contesto — e ora ogni voce ha l'evidenza scritta sopra.

> Nota di onestà: il documento di teoria resta valido come riferimento culturale. Questa rivalutazione non dice "la teoria sbaglia" — dice "la teoria si applica quando i prerequisiti esistono". Oggi, per 15 punti su 25, non esistono.
