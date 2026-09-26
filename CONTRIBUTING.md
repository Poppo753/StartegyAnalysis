# Contributing Guide — Binance OHLC Pipeline

## Struttura del Progetto

```
project-root/
├── src/                          # TypeScript pipeline (Node.js)
│   ├── binance/                  # Binance API client e download
│   ├── pipeline/                 # Pipeline di download e aggregazione
│   ├── storage/                  # Scrittura JSONL e CSV
│   ├── utils/                    # Utility (rate limiter, date, logger)
│   ├── config/                   # Configurazione
│   └── index.ts                  # Entry point
├── python-backtester/            # Python backtester
│   ├── src/                      # Moduli Python
│   │   ├── fast/                 # Motore Numba JIT
│   │   ├── gpu/                  # Motore GPU/Cupy
│   │   └── *.py                  # Core modules
│   ├── tests/                    # Test unitari pytest
│   └── main.py                   # Entry point
├── data/                         # Dati generati (in .gitignore)
├── docs/analysis/                # Documentazione analisi per caso
├── package.json                  # Dipendenze Node.js
├── tsconfig.json                 # Configurazione TypeScript
└── requirements.txt              # Dipendenze Python
```

## Setup Sviluppo

### TypeScript Pipeline
```bash
npm install
npm run build
npm run dev  # modalità sviluppo
npm test     # esegui test unitari
```

### Python Backtester
```bash
cd python-backtester
python -m venv .venv
source .venv/bin/activate  # o .venv\Scripts\activate su Windows
pip install -r requirements.txt
cp env.example .env
python -m pytest tests/      # esegui test unitari
python main.py
```

## Convenzioni

### TypeScript
- Usare `async/await` per operazioni asincrone
- Streaming per file grandi (>100MB)
- Usare `OHLCAggregator` per aggregazione OHLC
- Commenti JSDoc per tutte le funzioni pubbliche
- Type annotations ovunque

### Python
- Type hints per tutte le funzioni
- Docstring per tutte le classi/funzioni
- PEP 8 per formattazione
- Test con pytest in `tests/`

## Test

### TypeScript
```bash
npm test                   # tutti i test
npm run test:coverage      # con copertura
```

### Python
```bash
cd python-backtester
python -m pytest tests/ -v
```

## Modifiche Consigliate

1. **Sempre** testare prima di modificare
2. **Aggiornare** la documentazione in `docs/analysis/`
3. **Aggiornare** il `CHANGELOG.md`
4. **Non modificare** file senza creare un'issue
5. **Usare** il formato di branch: `fix/`, `feature/`, `refactor/`
