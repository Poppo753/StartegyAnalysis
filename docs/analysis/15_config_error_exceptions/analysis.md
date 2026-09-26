# Caso #15 — ConfigError al posto di print/exit in config.py

## 🔍 Analisi del Problema

### Codice originale (`python-backtester/src/config.py` — raise-only, nessun print)

Il modulo di configurazione solleva esclusivamente `ConfigError` (sottoclasse di `ValueError`, linee 17-19) e non contiene alcun `print()` né `sys.exit()` — verificato via grep: zero occorrenze in `config.py`. Ogni vincolo solleva con messaggio operativo:

```python
# src/config.py, linee 17-19 e 143-147
class ConfigError(ValueError):
    """Eccezione personalizzata per errori di configurazione."""
    pass

symbols_str = os.getenv("SYMBOLS", "")
if not symbols_str.strip():
    raise ConfigError("SYMBOLS non configurato nel .env")
```

Le ~30 sedi di `raise ConfigError` coprono: formato range `start:end:step` e step `> 0` (`_parse_range`, linee 85-120), date `YYYY-MM-DD`, valori numerici non validi, `DIRECTION`/`BACKTEST_ENGINE` fuori dominio, `TRAIN_RATIO + VALIDATION_RATIO > 1.01`, e tutti i vincoli di `_validate_config` (linee 282-323: `POSITION_SIZE > 0`, `X/Y/Z > 0`, ecc.). L'unico punto che stampa ed esce è il boundary CLI in `main.py`:

```python
# main.py, linee 108-112 e 139-143 — unico punto dove exit è lecito
try:
    config = load_config()
except ConfigError as e:
    print(f"❌ ERRORE configurazione: {e}")
    sys.exit(1)
```

### Bug Identificati

1. **`sys.exit()` dentro codice libreria (pattern precedente)** — terminare il processo da `load_config()` rendeva l'errore non catturabile: impossibile `try/except` nei test (`pytest.raises(ConfigError)` fallirebbe per `SystemExit`) e impossibile riusare il loader in contesti composti (notebook, orchestratore multi-simbolo).
2. **Doppia segnalazione print + raise (anti-pattern intermedio)** — stampare nel modulo E sollevare duplica l'output quando il boundary CLI stampa a sua volta (una riga dal modulo, una dal `catch`), e inquina stdout dei tool che parsano l'output. Il codice reale stampa una sola volta, nel `catch` di `main.py`.
3. **Perdita dello stack trace** — `print + sys.exit(1)` produce exit code senza traceback né contesto su quale vincolo è fallito; `raise ConfigError(...) from e` (es. linee 178, 200, 205) preserva la causa originale per il debug.

### Analisi Approfondita delle Alternative

#### Soluzione A — `raise ConfigError` nel modulo + singolo catch al boundary CLI (scelta)
- **Pro**: testabile (`pytest.raises`), componibile, singolo punto di stampa, traceback completo con `from e`; `ConfigError ⊂ ValueError` resta catturabile anche da handler generici.
- **Contro**: richiede che OGNI entry point catturi `ConfigError`, altrimenti traceback grezzo all'utente — mitigato dal catch centralizzato in `main()`.

#### Soluzione B — `print()` + `sys.exit(1)` nel modulo
- **Pro**: messaggio immediato, nessuna gestione eccezioni da scrivere.
- **Contro**: non testabile, non componibile, nessun traceback, comportamento diverso tra CLI e import come libreria.

#### Soluzione C — Error code / `Optional[Config]` con log
- **Pro**: nessun raise.
- **Contro**: ogni chiamante deve controllare il codice di errore (facile da ignorare → `None` usato come config valida); peggiora tutti i call-site senza benefici.

### Soluzione Scelta

**Soluzione A** — `config.py` segnala soltanto (raise tipizzato, mai print/exit), `main.py` decide la policy CLI (stampa una riga + `sys.exit(1)`). Lo stesso contratto è applicato a `DataLoadError` in `trade_utils.py` (caso #11): eccezioni tipizzate nella libreria, exit solo al boundary.

### Impatto

- **Previene**: test impossibili su config invalida, doppi messaggi di errore, debug senza stack trace, riuso bloccato del loader.
- **Rischio del cambiamento**: basso — a parità di `.env` invalido il processo termina comunque con codice 1 e messaggio equivalente; cambia solo il meccanismo (eccezione vs exit diretto).
- **Test richiesti**: `pytest.raises(ConfigError)` per ogni vincolo (range malformato, step ≤ 0, date non `YYYY-MM-DD`, `DIRECTION`/`BACKTEST_ENGINE` invalidi, somme ratio > 1, liste vuote, `Y_VALUES` vuoto con `Y_DYNAMIC=false`); verificare che `config.py` non contenga `print(`/`sys.exit` (grep vuoto).
