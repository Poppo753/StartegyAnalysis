import fs from 'fs';
import path from 'path';
import { OhlcCandle } from '../binance/types';
import { logger } from '../utils/logger';
import { OHLCAggregator } from '../pipeline/ohlcAggregator';

export function writeOhlcCsv(candles: OhlcCandle[], filePath: string): void {
  const dir = path.dirname(filePath);
  fs.mkdirSync(dir, { recursive: true });

  const header = 'timestamp,open,high,low,close,volume,tradeCount';
  const lines = candles.map(
    (c) =>
      `${c.timestamp},${OHLCAggregator.fmt(c.open)},${OHLCAggregator.fmt(c.high)},${OHLCAggregator.fmt(c.low)},${OHLCAggregator.fmt(c.close)},${OHLCAggregator.fmt(c.volume)},${c.tradeCount}`
  );

  const content = [header, ...lines].join('\n') + '\n';
  fs.writeFileSync(filePath, content, 'utf-8');
  logger.info(`CSV written: ${filePath} (${candles.length} candles)`);
}
