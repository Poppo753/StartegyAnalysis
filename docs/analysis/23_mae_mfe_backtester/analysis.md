# Caso #23 — MAE/MFE nel Backtester (standard + fast)

## 🔍 Analisi del Problema

### Codice originale (trade senza escursione registrata)

Prima dell'intervento, `Trade` non registrava quanto il prezzo si fosse mosso a favore/contro durante la posizione: impossibile distinguere un'entry pulita da una recuperata per caso, o calibrare stop-loss e take-profit sui dati. L'implementazione attuale copre 4 punti di integrazione verificati nel codice.

**1. `simulator.py` — `_execute_trade` calcola `mae_pct`/`mfe_pct` (linee 258-266, 268-285):**

```python
mae_pct = 0.0
mfe_pct = 0.0
if entry_price > 0:
    if params.direction == "short":
        mae_pct = (max_price - entry_price) / entry_price * 100.0  # avverso = salita
        mfe_pct = (entry_price - min_price) / entry_price * 100.0  # favorevole = discesa
    else:  # long / signal-only
        mae_pct = (entry_price - min_price) / entry_price * 100.0
        mfe_pct = (max_price - entry_price) / entry_price * 100.0

return Trade(..., mae_pct=mae_pct, mfe_pct=mfe_pct)
```

`max_price`/`min_price` includono entry ed exit (aggiornati nel loop linee 203-205 e al ramo `end-of-data` linee 233-234).

**2. `strategy.py` — campi su `Trade` e `BacktestResult` (linee 48-49, 69-70):**

```python
@dataclass
class Trade:
    ...
    mae_pct: float = 0.0      # Maximum Adverse Excursion (%)
    mfe_pct: float = 0.0      # Maximum Favorable Excursion (%)

@dataclass
class BacktestResult:
    ...
    avg_mae: float = 0.0
    avg_mfe: float = 0.0
```

**3. `metrics.py` — aggregazione medie (linee 83-84):**

```python
result.avg_mae = float(np.mean([t.mae_pct for t in trades])) if trades else 0.0
result.avg_mfe = float(np.mean([t.mfe_pct for t in trades])) if trades else 0.0
```

**4. `fast_metrics.py` — versione direction-aware su array (linee 105-123):**

```python
# Colonne trades_array: [2]=entry, [4]=max_during, [5]=min_during
with np.errstate(divide="ignore", invalid="ignore"):
    valid = entry_prices > 0
    if direction == 2:  # short: avverso=salita, favorevole=discesa
        mae = np.where(valid, (max_prices - entry_prices) / ... * 100.0, 0.0)
        mfe = np.where(valid, (entry_prices - min_prices) / ... * 100.0, 0.0)
    else:  # long / signal-only
        mae = np.where(valid, (entry_prices - min_prices) / ... * 100.0, 0.0)
        mfe = np.where(valid, (max_prices - entry_prices) / ... * 100.0, 0.0)
mae = np.clip(mae, 0.0, None)
mfe = np.clip(mfe, 0.0, None)
metrics["avg_mae"] = round(float(np.mean(mae)), 4)   # + max_mae / avg_mfe / max_mfe
```

Integrazione aggiuntiva verificata in `gpu_runner.py`: `_add_advanced_metrics` (linee 310, 361-367) calcola `avg_mae`/`max_mae`, propagati nelle righe train/val dei summary CSV (linee 593-598) e come `mae_percent` per-trade nei CSV (linee 644-655).

### Bug Identificati

1. **Metriche cieche alla qualità di entry** — senza MAE/MFE, due strategie con stesso PnL sono indistinguibili: una con entry pulite (MAE basso) e una che sopravvive a drawdown profondi (MAE alto, fragile a slippage/spread reali).
2. **Inversione long/short** — definire "avverso" senza considerare `direction` inverte MAE↔MFE per gli short (prezzo che sale è avverso allo short). Entrambe le implementazioni (`simulator.py` linea 261, `fast_metrics.py` linea 112) commutano esplicitamente sul ramo short.
3. **Divisioni e valori degeneri** — `entry_price == 0` o `max < entry` per artefatti float produrrebbero negativi/NaN che avvelenano le medie. Mitigati da guardia `entry_price > 0` / maschera `valid`, `np.errstate` e `clip(0, None)` nel path fast.

### Analisi Approfondita delle Alternative

#### Soluzione A — MAE/MFE direction-aware in `Trade` + medie in `metrics`/`fast_metrics` (scelta)
- **Pro**: per-trade nei CSV (diagnosi), aggregati nei summary (screening); i due path (oggetti e array) usano la stessa definizione commutata su direction; `clip ≥ 0` garantisce medie interpretabili.
- **Contro**: `metrics.py` aggrega solo le medie (no max), mentre `fast_metrics.py` fornisce anche `max_mae`/`max_mfe` — asimmetria nota tra engine standard e fast.

#### Soluzione B — Solo post-hoc in `trade_profile.py`
- **Pro**: nessun tocco ai motori.
- **Contro**: MAE/MFE non disponibili durante screening/filtri GPU (che lavorano su array, mai su CSV); due definizioni che possono divergere.

#### Soluzione C — MAE/MFE assoluti (USDT) invece che percentuali
- **Pro**: direttamente confrontabili con `position_size`.
- **Contro**: non confrontabili tra simboli con prezzi diversi; le percentuali sono invarianti di scala e coerenti con `x/z_percent`.

### Soluzione Scelta

**Soluzione A** — percentuali direction-aware calcolate alla fonte (motori standard e fast) e propagate fino ai CSV. Chiave interpretativa: vincitore con MAE basso/MFE alto = entry tempestiva; perdente con MFE alto = uscita tardiva (segnale per ritarare `Z`/hold).

### Impatto

- **Previene**: selezione di strategie fragili a parità di PnL, miscalibrazione di stop-loss senza dati di escursione, inversione delle metriche sugli short.
- **Rischio del cambiamento**: basso — campi additivi con default `0.0`, nessuna alterazione del PnL o delle regole di exit.
- **Test richiesti**: long con solo salita → `mae ≈ 0, mfe > 0`; short speculare; `entry_price = 0` → `0.0` senza warning; parità `avg_mae/avg_mfe` tra `calculate_metrics` e `calculate_fast_metrics` sullo stesso dataset.
