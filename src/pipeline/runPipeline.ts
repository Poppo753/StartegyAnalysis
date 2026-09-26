import fs from 'fs';
import path from 'path';
import { AppConfig } from '../config/config';
import { BinanceClient } from '../binance/binanceClient';
import { downloadAggTrades } from './downloadAggTrades';
import { aggregateFileToOhlc } from './aggregateStreaming';
import { timeframeLabelToInterval } from './ohlcAggregator';
import { GlobalRateLimiter } from '../utils/rateLimiter';
import { logger } from '../utils/logger';

export const SUPPORTED_TIMEFRAMES = ['1s', '1m', '5m', '1h', '1d'] as const;
export type SupportedTimeframe = (typeof SUPPORTED_TIMEFRAMES)[number];

export interface RunPipelineOptions {
  timeframes?: string[];
}

/**
 * Minimal argv parsing for `--timeframes 1s,1m,5m,1h,1d`
 * (also accepts `--timeframes=...`). Unknown labels throw.
 * Defaults to ['1s'] (pre-F7 behavior) when the flag is absent.
 */
export function parseTimeframesArgv(argv: string[] = process.argv.slice(2)): string[] {
  let raw: string | undefined;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--timeframes' && argv[i + 1] !== undefined) {
      raw = argv[i + 1];
      i++;
    } else if (argv[i].startsWith('--timeframes=')) {
      raw = argv[i].slice('--timeframes='.length);
    }
  }
  if (raw === undefined || raw.trim() === '') return ['1s'];

  const seen = new Set<string>();
  const timeframes: string[] = [];
  for (const part of raw.split(',')) {
    const tf = part.trim();
    if (tf === '') continue;
    timeframeLabelToInterval(tf); // throws on unsupported label
    if (!seen.has(tf)) {
      seen.add(tf);
      timeframes.push(tf);
    }
  }
  if (timeframes.length === 0) return ['1s'];
  return timeframes;
}

export function ohlcFilename(timeframe: string, startDate: string, endDate: string): string {
  return `ohlc_${timeframe}_${startDate}_${endDate}.csv`;
}

const log = (config: AppConfig) => config.jsonLogging ? logger.json : logger;

export async function runPipeline(config: AppConfig, options: RunPipelineOptions = {}): Promise<void> {
  const timeframes = options.timeframes ?? parseTimeframesArgv();
  const rateLimiter = new GlobalRateLimiter(config.maxRequestsPerMinute);
  const client = new BinanceClient(config.binanceBaseUrl, config.requestDelayMs, rateLimiter);

  const _log = log(config);

  _log.info(`Pipeline starting for ${config.symbols.length} symbol(s): ${config.symbols.join(', ')}`);
  _log.info(`Date range: ${config.startDate} to ${config.endDate}`);
  _log.info(`Timeframes: ${timeframes.join(', ')}`);
  _log.info(`Output directory: ${config.outputDir}`);
  _log.info(`Concurrency: ${config.concurrentDays} days/symbol | Rate limit: ${config.maxRequestsPerMinute} req/min`);
  _log.info(`Gzip compression: ${config.useGzip ? 'enabled' : 'disabled'}`);

  const symbolPromises = config.symbols.map((symbol) =>
    processSymbol(client, symbol, config, timeframes)
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
  if (failed > 0) {
    throw new Error(`Pipeline failed for ${failed} of ${config.symbols.length} symbol(s)`);
  }
}

async function processSymbol(
  client: BinanceClient,
  symbol: string,
  config: AppConfig,
  timeframes: string[]
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

  for (const timeframe of timeframes) {
    const ohlcFilePath = path.join(
      ohlcDir,
      ohlcFilename(timeframe, config.startDate, config.endDate)
    );

    if (fs.existsSync(ohlcFilePath)) {
      _log.info(`${symbol} [${timeframe}]: Output already present, skipping (${ohlcFilePath})`);
      continue;
    }

    const candleCount = await aggregateFileToOhlc(
      rawFilePath,
      ohlcFilePath,
      timeframeLabelToInterval(timeframe)
    );

    _log.info(`${symbol} [${timeframe}]: ${candleCount} candles written.`);
  }

  _log.info(`${symbol}: Pipeline complete.`);
}
