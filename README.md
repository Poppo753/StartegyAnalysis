# Binance OHLC Pipeline

A modular TypeScript/Node.js pipeline to download historical aggregate trades from Binance Spot API and build 1-second OHLCV datasets.

## Features

- Downloads aggregate trades (`aggTrades`) from Binance REST API and data.binance.vision
- Supports multiple symbols (multi-asset pipeline)
- Builds 1-second OHLCV candles from raw trade data
- Saves raw data in **compressed JSONL.gz format** and aggregated data in CSV
- Automatic retry on HTTP 429 (rate limit) and 5xx errors with exponential backoff
- Configurable rate limiting between requests
- Cross-platform (no external `unzip` dependency — uses jszip)
- **Unit tests** included (Jest + pytest)
- Clean, modular TypeScript codebase with shared `OHLCAggregator`

## Project Structure

```
src/
├── config/
│   └── config.ts                  # Environment configuration loader
├── binance/
│   ├── binanceClient.ts           # Binance API client with retry logic (fixed)
│   ├── bulkAvailability.ts        # Bulk data availability check
│   ├── bulkDownloader.ts          # Zip download with jszip (no child_process)
│   └── types.ts                   # TypeScript interfaces
├── pipeline/
│   ├── ohlcAggregator.ts          # SHARED OHLCAggregator class (DRY)
│   ├── aggregateStreaming.ts      # Streaming OHLC aggregation
│   ├── aggregateToOhlc.ts         # Array-based OHLC aggregation
│   ├── downloadAggTrades.ts       # Download with gzip support
│   └── runPipeline.ts             # Pipeline orchestrator
├── storage/
│   ├── csvWriter.ts               # CSV file writer
│   └── jsonlWriter.ts             # JSONL(.gz) reader/writer with gzip support
├── utils/
│   ├── dateUtils.ts               # Date/time utilities
│   ├── rateLimiter.ts             # Rate limiting utility
│   ├── logger.ts                  # Console logger
│   └── gzipUtils.ts               # Gzip compression utilities
└── index.ts                       # Entry point
```

## Output Structure

```
data/
├── BTCUSDT/
│   ├── raw/
│   │   └── aggTrades_2026-05-01_2026-05-05.jsonl.gz  # Gzip compressed
│   └── ohlc/
│       └── ohlc_1s_2026-05-01_2026-05-05.csv
├── ETHUSDT/
│   ├── raw/
│   │   └── aggTrades_2026-05-01_2026-05-05.jsonl.gz
│   └── ohlc/
│       └── ohlc_1s_2026-05-01_2026-05-05.csv
└── ...
```

## Setup

### 1. Install dependencies

```bash
npm install
```

### 2. Install dev dependencies (for tests)

```bash
npm install --save-dev jest @types/jest ts-jest
```

### 3. Configure environment

Copy the example environment file and edit it:

```bash
cp env.example .env
```

Edit `.env` with your desired configuration:

```env
SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT
START_DATE=2024-01-01
END_DATE=2024-01-02
OUTPUT_DIR=./data
BINANCE_BASE_URL=https://api.binance.com
REQUEST_DELAY_MS=250
CONCURRENT_DAYS=5
CONCURRENT_BULK_DOWNLOADS=10
MAX_REQUESTS_PER_MINUTE=500
```

### 4. Run the pipeline

**Development mode** (with tsx, no compilation needed):

```bash
npm run dev
```

**Production mode** (compile first, then run):

```bash
npm run build
npm start
```

### 5. Run tests

```bash
npm test                   # Run all TypeScript tests
npm run test:coverage      # With coverage report
```

## Python Backtester

The `python-backtester/` directory contains a backtester for the generated OHLC data.

### Setup

```bash
cd python-backtester
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp env.example .env
```

### Run backtester

```bash
python main.py
```

### Run Python tests

```bash
python -m pytest tests/ -v
```

## Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `SYMBOLS` | Comma-separated trading pairs | Required |
| `START_DATE` | Start date (YYYY-MM-DD, UTC) | Required |
| `END_DATE` | End date (YYYY-MM-DD, UTC) | Required |
| `OUTPUT_DIR` | Output directory for data files | `./data` |
| `BINANCE_BASE_URL` | Binance API base URL | `https://api.binance.com` |
| `REQUEST_DELAY_MS` | Delay between API calls (ms) | `250` |
| `CONCURRENT_DAYS` | Days downloaded in parallel | `5` |
| `CONCURRENT_BULK_DOWNLOADS` | Concurrent bulk downloads | `10` |
| `MAX_REQUESTS_PER_MINUTE` | Global rate limit | `500` |

## CSV Output Format

The OHLCV CSV files contain these columns:

| Column | Description |
|--------|-------------|
| `timestamp` | ISO 8601 timestamp (start of second) |
| `open` | First trade price in the second |
| `high` | Highest price in the second |
| `low` | Lowest price in the second |
| `close` | Last trade price in the second |
| `volume` | Total quantity traded in the second |
| `tradeCount` | Number of aggregate trades in the second |

**Note:** Seconds with no trades are skipped (no synthetic candles).

## API Rate Limits

The pipeline respects Binance rate limits by:
- Adding a configurable delay between requests (`REQUEST_DELAY_MS`)
- Automatically retrying on HTTP 429 with exponential backoff
- Retrying on 5xx server errors

Recommended: Keep `REQUEST_DELAY_MS` at 250ms or higher for public API access.

## Fixes & Improvements

See [docs/CHANGELOG.md](docs/CHANGELOG.md) for a complete list of fixes and improvements applied to this repository.

## Notes

- This pipeline uses the **public** Binance Spot API — no API key required.
- `aggTrades` are compressed/aggregate trades, not raw individual trades.
- Raw data is stored as **gzip-compressed JSONL** (`.jsonl.gz`) to save ~80% storage space.
- The `OHLCAggregator` class is shared across the pipeline to eliminate code duplication.
- For very large date ranges, expect significant download times due to rate limiting.
- Data from `data.binance.vision` could be used as an alternative source in future versions.

## License

MIT