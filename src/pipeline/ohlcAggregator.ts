import fs from 'fs';
import readline from 'readline';
import path from 'path';
import { createReadStream } from 'fs';
import { createGunzip } from 'zlib';
import { pipeline } from 'stream/promises';
import { BinanceAggTrade, OhlcCandle } from '../binance/types';
import { floorToSecond, timestampMsToIso } from '../utils/dateUtils';

export class OHLCAggregator {
  private currentSecond: number | null = null;
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

  constructor(logIntervalMs: number = 30_000) {
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
   * Aggregate trades from a JSONL file into 1-second OHLCV candles using streaming.
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
   * Aggregate trades from an array into OHLCV candles.
   */
  static fromArray(trades: BinanceAggTrade[]): OhlcCandle[] {
    const sorted = [...trades].sort((a, b) => a.T - b.T || a.a - b.a);
    const buckets = new Map<number, BinanceAggTrade[]>();

    for (const trade of sorted) {
      const secondKey = floorToSecond(OHLCAggregator.normalizeTimestamp(trade.T));
      const bucket = buckets.get(secondKey);
      if (bucket) {
        bucket.push(trade);
      } else {
        buckets.set(secondKey, [trade]);
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
    const secondKey = floorToSecond(timestampMs);

    this.lineCount++;

    if (this.currentSecond === null) {
      this.currentSecond = secondKey;
      this.bucketOpen = price;
      this.bucketHigh = price;
      this.bucketLow = price;
      this.bucketClose = price;
      this.bucketVolume = quantity;
      this.bucketTradeCount = 1;
    } else if (secondKey === this.currentSecond) {
      if (price > this.bucketHigh) this.bucketHigh = price;
      if (price < this.bucketLow) this.bucketLow = price;
      this.bucketClose = price;
      this.bucketVolume += quantity;
      this.bucketTradeCount++;
    } else {
      this.writeCandle(writeStream, this.currentSecond);
      this.currentSecond = secondKey;
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

  private writeCandle(writeStream: fs.WriteStream, secondMs: number): void {
    const line = `${timestampMsToIso(secondMs)},${OHLCAggregator.fmt(this.bucketOpen)},${OHLCAggregator.fmt(this.bucketHigh)},${OHLCAggregator.fmt(this.bucketLow)},${OHLCAggregator.fmt(this.bucketClose)},${OHLCAggregator.fmt(this.bucketVolume)},${this.bucketTradeCount}\n`;
    writeStream.write(line);
    this.candleCount++;
  }

  private flush(writeStream: fs.WriteStream): void {
    if (this.currentSecond !== null) {
      this.writeCandle(writeStream, this.currentSecond);
      this.candleCount++;
    }
    writeStream.end();
  }
}
