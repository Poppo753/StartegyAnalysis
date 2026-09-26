import fs from 'fs';
import path from 'path';
import { BinanceAggTrade, OhlcCandle } from '../binance/types';
import { logger } from '../utils/logger';
import { OHLCAggregator } from './ohlcAggregator';

export async function aggregateFileToOhlc1s(
  inputPath: string,
  outputPath: string
): Promise<number> {
  logger.info(`Streaming aggregation: ${inputPath}`);

  const candleCount = await new OHLCAggregator(30_000).fromStream(inputPath, outputPath);

  logger.info(`Streaming aggregation complete: ${candleCount.toLocaleString()} candles`);
  logger.info(`CSV written: ${outputPath}`);

  return candleCount;
}
