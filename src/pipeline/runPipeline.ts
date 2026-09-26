import path from 'path';
import { AppConfig } from '../config/config';
import { BinanceClient } from '../binance/binanceClient';
import { downloadAggTrades } from './downloadAggTrades';
import { aggregateFileToOhlc1s } from './aggregateStreaming';
import { GlobalRateLimiter } from '../utils/rateLimiter';
import { logger } from '../utils/logger';

const log = (config: AppConfig) => config.jsonLogging ? logger.json : logger;

export async function runPipeline(config: AppConfig): Promise<void> {
  const rateLimiter = new GlobalRateLimiter(config.maxRequestsPerMinute);
  const client = new BinanceClient(config.binanceBaseUrl, config.requestDelayMs, rateLimiter);

  const _log = log(config);

  _log.info(`Pipeline starting for ${config.symbols.length} symbol(s): ${config.symbols.join(', ')}`);
  _log.info(`Date range: ${config.startDate} to ${config.endDate}`);
  _log.info(`Output directory: ${config.outputDir}`);
  _log.info(`Concurrency: ${config.concurrentDays} days/symbol | Rate limit: ${config.maxRequestsPerMinute} req/min`);
  _log.info(`Gzip compression: ${config.useGzip ? 'enabled' : 'disabled'}`);

  const symbolPromises = config.symbols.map((symbol) =>
    processSymbol(client, symbol, config)
  );

  const results = await Promise.allSettled(symbolPromises);

  let succeeded = 0;
  let failed = 0;
  for (let i = 0; i < results.length; i++) {
    const result = results[i];
    if (result.status === 'fulfilled') {
      succeeded++;
    } else {
      failed++;
      _log.error(`${config.symbols[i]}: ${result.reason}`);
    }
  }

  _log.info(`\nPipeline finished. Success: ${succeeded}, Failed: ${failed}`);
}

async function processSymbol(
  client: BinanceClient,
  symbol: string,
  config: AppConfig
): Promise<void> {
  const _log = log(config);

  _log.info(`${'='.repeat(60)}`);
  _log.info(`Processing symbol: ${symbol}`);
  _log.info(`${'='.repeat(60)}`);

  const { filePath: rawFilePath, totalTrades } = await downloadAggTrades(client, {
    symbol,
    startDate: config.startDate,
    endDate: config.endDate,
    outputDir: config.outputDir,
    concurrentDays: config.concurrentDays,
    concurrentBulkDownloads: config.concurrentBulkDownloads,
    useGzip: config.useGzip,
  });

  if (totalTrades === 0) {
    _log.warn(`${symbol}: No trades found in the specified range. Skipping aggregation.`);
    return;
  }

  const ohlcDir = path.join(config.outputDir, symbol, 'ohlc');
  const ohlcFilePath = path.join(
    ohlcDir,
    `ohlc_1s_${config.startDate}_${config.endDate}.csv`
  );

  const candleCount = await aggregateFileToOhlc1s(rawFilePath, ohlcFilePath);

  _log.info(`${symbol}: Pipeline complete. ${candleCount} candles written.`);
}
