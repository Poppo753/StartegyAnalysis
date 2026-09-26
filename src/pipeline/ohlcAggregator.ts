import fs from 'fs';
import readline from 'readline';
import path from 'path';
import { createReadStream } from 'fs';
import { createGunzip } from 'zlib';
import { pipeline } from 'stream/promises';
import { BinanceAggTrade, OhlcCandle } from '../binance/types';
import { floorToSecond, timestampMsToIso } from '../utils/dateUtils';

/**
 * Intervals supported by the aggregator (F7-T01), in seconds.
 * Buckets are UTC epoch-anchored: 1m aligns to minute boundaries,
 * 1h to hour boundaries, 1d to UTC midnight.
 */
export const SUPPORTED_INTERVAL_SECONDS = [1, 60, 300, 3600, 86400] as const;
export type SupportedIntervalSeconds = (typeof SUPPORTED_INTERVAL_SECONDS)[number];

const TIMEFRAME_LABELS: Record<number, string> = {
  1: '1s',
  60: '1m',
  300: '5m',
  3600: '1h',
  86400: '1d',
};

const LABEL_TO_INTERVAL: Record<string, number> = {
  '1s': 1,
  '1m': 60,
  '5m': 300,
  '1h': 3600,
  '1d': 86400,
};

export function assertSupportedInterval(intervalSeconds: number): void {
  if (!(SUPPORTED_INTERVAL_SECONDS as readonly number[]).includes(intervalSeconds)) {
    throw new Error(
      `Unsupported OHLC interval: ${intervalSeconds}s (supported: ${SUPPORTED_INTERVAL_SECONDS.join(', ')})`
    );
  }
}

export function intervalToTimeframeLabel(intervalSeconds: number): string {
  assertSupportedInterval(intervalSeconds);
  return TIMEFRAME_LABELS[intervalSeconds];
}

export function timeframeLabelToInterval(label: string): number {
  const interval = LABEL_TO_INTERVAL[label];
  if (interval === undefined) {
    throw new Error(`Unsupported timeframe label: ${label} (supported: 1s, 1m, 5m, 1h, 1d)`);
  }
  return interval;
}

/**
 * Floor a ms timestamp to the start of its interval bucket (UTC, epoch-anchored).
 * For intervalSeconds === 1 this is exactly floorToSecond.
 */
export function floorToInterval(timestampMs: number, intervalSeconds: number): number {
  assertSupportedInterval(intervalSeconds);
  const bucketMs = intervalSeconds * 1000;
  return Math.floor(timestampMs / bucketMs) * bucketMs;
}

export class OHLCAggregator {
  private readonly intervalSeconds: number;
  private currentBucket: number | null = null;
  private bucketOpen = 0;
  private bucketHigh = -Infinity;
  private bucketLow = Infinity;
  private bucketClose = 0;
  private bucketVolume = 0;
  private bucketTradeCount = 0;
  private candleCount = 0;
  private lineCount = 0;
  private lastLogAt = Date.now();
  private readonly logIntervalMs: number;

  constructor(intervalSeconds: number = 1, logIntervalMs: number = 30_000) {
    assertSupportedInterval(intervalSeconds);
    this.intervalSeconds = intervalSeconds;
    this.logIntervalMs = logIntervalMs;
  }

  static fmt(value: number): string {
    return value.toFixed(10).replace(/\.?0+$/, '');
  }

  static normalizeTimestamp(timestampMs: number): number {
    if (timestampMs > 9_999_999_999_999) {
      return Math.floor(timestampMs / 1000);
    }
    return timestampMs;
  }

  static priceToNumber(priceStr: string): number {
    return parseFloat(priceStr);
  }

  static quantityToNumber(qtyStr: string): number {
    return parseFloat(qtyStr);
  }

  /**
   * Aggregate trades from a JSONL file into OHLCV candles at the configured
   * interval, using streaming (O(1) memory: one open bucket at a time).
   * Assumes trades are time-ordered (as written by the downloader).
   */
  async fromStream(inputPath: string, outputPath: string): Promise<number> {
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    const writeStream = fs.createWriteStream(outputPath, { encoding: 'utf-8' });
    writeStream.write('timestamp,open,high,low,close,volume,tradeCount\n');

    const isGz = inputPath.endsWith('.gz');
    const readStream = createReadStream(inputPath);
    let input: NodeJS.ReadableStream;

    if (isGz) {
      const gunzip = createGunzip();
      readStream.pipe(gunzip);
      input = gunzip;
    } else {
      input = readStream;
    }

    const rl = readline.createInterface({ input: input as unknown as NodeJS.ReadableStream, crlfDelay: Infinity });

    for await (const line of rl) {
      if (line.trim() === '') continue;

      let trade: BinanceAggTrade;
      try {
        trade = JSON.parse(line);
      } catch {
        continue;
      }

      this.processTrade(trade, writeStream);
    }

    this.flush(writeStream);
    return this.candleCount;
  }

  /**
   * Aggregate trades from an array into OHLCV candles at the given interval.
   * Defaults to 1 second (backward-compatible with the pre-F7 behavior).
   */
  static fromArray(trades: BinanceAggTrade[], intervalSeconds: number = 1): OhlcCandle[] {
    assertSupportedInterval(intervalSeconds);
    const sorted = [...trades].sort((a, b) => a.T - b.T || a.a - b.a);
    const buckets = new Map<number, BinanceAggTrade[]>();

    for (const trade of sorted) {
      const timestampMs = OHLCAggregator.normalizeTimestamp(trade.T);
      const bucketKey =
        intervalSeconds === 1 ? floorToSecond(timestampMs) : floorToInterval(timestampMs, intervalSeconds);
      const bucket = buckets.get(bucketKey);
      if (bucket) {
        bucket.push(trade);
      } else {
        buckets.set(bucketKey, [trade]);
      }
    }

    const candles: OhlcCandle[] = [];
    const sortedKeys = Array.from(buckets.keys()).sort((a, b) => a - b);

    for (const key of sortedKeys) {
      const bucketTrades = buckets.get(key)!;
      const prices = bucketTrades.map((t) => OHLCAggregator.priceToNumber(t.p));
      const quantities = bucketTrades.map((t) => OHLCAggregator.quantityToNumber(t.q));

      candles.push({
        timestamp: timestampMsToIso(key),
        open: parseFloat(prices[0].toFixed(8)),
        high: parseFloat(Math.max(...prices).toFixed(8)),
        low: parseFloat(Math.min(...prices).toFixed(8)),
        close: parseFloat(prices[prices.length - 1].toFixed(8)),
        volume: parseFloat(quantities.reduce((sum, q) => sum + q, 0).toFixed(8)),
        tradeCount: bucketTrades.length,
      });
    }

    return candles;
  }

  /**
   * Process a single trade and write candle to stream if needed.
   */
  private processTrade(trade: BinanceAggTrade, writeStream: fs.WriteStream): void {
    const price = OHLCAggregator.priceToNumber(trade.p);
    const quantity = OHLCAggregator.quantityToNumber(trade.q);
    const timestampMs = OHLCAggregator.normalizeTimestamp(trade.T);
    const bucketKey =
      this.intervalSeconds === 1 ? floorToSecond(timestampMs) : floorToInterval(timestampMs, this.intervalSeconds);

    this.lineCount++;

    if (this.currentBucket === null) {
      this.currentBucket = bucketKey;
      this.bucketOpen = price;
      this.bucketHigh = price;
      this.bucketLow = price;
      this.bucketClose = price;
      this.bucketVolume = quantity;
      this.bucketTradeCount = 1;
    } else if (bucketKey === this.currentBucket) {
      if (price > this.bucketHigh) this.bucketHigh = price;
      if (price < this.bucketLow) this.bucketLow = price;
      this.bucketClose = price;
      this.bucketVolume += quantity;
      this.bucketTradeCount++;
    } else {
      this.writeCandle(writeStream, this.currentBucket);
      this.currentBucket = bucketKey;
      this.bucketOpen = price;
      this.bucketHigh = price;
      this.bucketLow = price;
      this.bucketClose = price;
      this.bucketVolume = quantity;
      this.bucketTradeCount = 1;
    }

    if (Date.now() - this.lastLogAt > this.logIntervalMs) {
      console.log(`  Progress: ${this.lineCount.toLocaleString()} trades, ${this.candleCount.toLocaleString()} candles`);
      this.lastLogAt = Date.now();
    }
  }

  private writeCandle(writeStream: fs.WriteStream, bucketMs: number): void {
    const line = `${timestampMsToIso(bucketMs)},${OHLCAggregator.fmt(this.bucketOpen)},${OHLCAggregator.fmt(this.bucketHigh)},${OHLCAggregator.fmt(this.bucketLow)},${OHLCAggregator.fmt(this.bucketClose)},${OHLCAggregator.fmt(this.bucketVolume)},${this.bucketTradeCount}\n`;
    writeStream.write(line);
    this.candleCount++;
  }

  private flush(writeStream: fs.WriteStream): void {
    if (this.currentBucket !== null) {
      this.writeCandle(writeStream, this.currentBucket);
      this.candleCount++;
    }
    writeStream.end();
  }
}

/**
 * Aggregate trades into OHLCV candles at an arbitrary supported interval
 * (1/60/300/3600/86400 seconds). Array-based (in-memory) variant.
 */
export function aggregateToOhlc(trades: BinanceAggTrade[], intervalSeconds: number): OhlcCandle[] {
  return OHLCAggregator.fromArray(trades, intervalSeconds);
}

/**
 * Backward-compatible 1-second wrapper (pre-F7 behavior).
 */
export function aggregateToOhlc1s(trades: BinanceAggTrade[]): OhlcCandle[] {
  return OHLCAggregator.fromArray(trades, 1);
}
