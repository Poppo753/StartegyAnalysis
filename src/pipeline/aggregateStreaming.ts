import fs from 'fs';
import path from 'path';
import { BinanceAggTrade, OhlcCandle } from '../binance/types';
import { logger } from '../utils/logger';
import { OHLCAggregator } from './ohlcAggregator';

export async function aggregateFileToOhlc(
  inputPath: string,
  outputPath: string,
  intervalSeconds: number = 1
): Promise<number> {
  logger.info(`Streaming aggregation (${intervalSeconds}s): ${inputPath}`);

  const candleCount = await new OHLCAggregator(intervalSeconds, 30_000).fromStream(inputPath, outputPath);

  logger.info(`Streaming aggregation complete: ${candleCount.toLocaleString()} candles`);
  logger.info(`CSV written: ${outputPath}`);

  return candleCount;
}

export async function aggregateFileToOhlc1s(
  inputPath: string,
  outputPath: string
): Promise<number> {
  return aggregateFileToOhlc(inputPath, outputPath, 1);
}
