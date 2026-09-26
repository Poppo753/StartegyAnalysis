import path from 'path';
import { loadConfig } from './config/config';
import { aggregateFileToOhlc1s } from './pipeline/aggregateStreaming';
import { getGzipPath } from './storage/jsonlWriter';
import { logger } from './utils/logger';

async function main(): Promise<void> {
  try {
    const config = loadConfig();

    for (const symbol of config.symbols) {
      const rawFilePath = getGzipPath(
        path.join(config.outputDir, symbol, 'raw', `aggTrades_${config.startDate}_${config.endDate}.jsonl`)
      );

      const ohlcFilePath = path.join(
        config.outputDir,
        symbol,
        'ohlc',
        `ohlc_1s_${config.startDate}_${config.endDate}.csv`
      );

      logger.info(`Aggregating ${symbol}: ${rawFilePath}`);
      const candleCount = await aggregateFileToOhlc1s(rawFilePath, ohlcFilePath);
      logger.info(`${symbol}: Done. ${candleCount} candles.`);
    }

    process.exit(0);
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    logger.error(`Fatal: ${msg}`);
    process.exit(1);
  }
}

main();
