import fs from 'fs';
import os from 'os';
import path from 'path';
import readline from 'readline';
import { OHLCAggregator, aggregateToOhlc, aggregateToOhlc1s, floorToInterval, intervalToTimeframeLabel, timeframeLabelToInterval } from './ohlcAggregator';
import { BinanceAggTrade, OhlcCandle } from '../binance/types';
import { aggregateFileToOhlc } from './aggregateStreaming';
import { ohlcFilename, parseTimeframesArgv } from './runPipeline';

const makeTrade = (price: string, qty: string, timestampMs: number, extra: Partial<BinanceAggTrade> = {}): BinanceAggTrade => ({
  a: 1,
  p: price,
  q: qty,
  f: 1,
  l: 1,
  T: timestampMs,
  m: false,
  M: true,
  ...extra,
});

describe('OHLCAggregator.fromArray', () => {
  it('should aggregate trades into 1-second OHLCV candles', () => {
    const trades: BinanceAggTrade[] = [
      makeTrade('100', '1', 1700000000000),
      makeTrade('101', '2', 1700000000500),
      makeTrade('102', '1', 1700000001000),
    ];

    const candles = OHLCAggregator.fromArray(trades);
    expect(candles).toHaveLength(2);
    expect(candles[0].open).toBe(100);
    expect(candles[0].high).toBe(101);
    expect(candles[0].low).toBe(100);
    expect(candles[0].close).toBe(101);
    expect(candles[0].volume).toBe(3);
    expect(candles[0].tradeCount).toBe(2);
  });

  it('should return empty array for empty input', () => {
    const candles = OHLCAggregator.fromArray([]);
    expect(candles).toHaveLength(0);
  });

  it('should sort trades by timestamp before aggregating', () => {
    const trades: BinanceAggTrade[] = [
      makeTrade('102', '1', 1700000001000),
      makeTrade('100', '1', 1700000000000),
      makeTrade('101', '1', 1700000000500),
    ];

    const candles = OHLCAggregator.fromArray(trades);
    expect(candles).toHaveLength(2);
    expect(candles[0].open).toBe(100);
    expect(candles[1].open).toBe(102);
  });
});

describe('OHLCAggregator.normalizeTimestamp', () => {
  it('should convert microseconds to milliseconds', () => {
    expect(OHLCAggregator.normalizeTimestamp(1735689605179257)).toBe(1735689605179);
  });

  it('should pass through milliseconds', () => {
    expect(OHLCAggregator.normalizeTimestamp(1735689605179)).toBe(1735689605179);
  });
});

describe('OHLCAggregator.fmt', () => {
  it('should format numbers without scientific notation', () => {
    expect(OHLCAggregator.fmt(0.00000039)).toBe('0.00000039');
    expect(OHLCAggregator.fmt(100)).toBe('100');
    expect(OHLCAggregator.fmt(3.1400000000)).toBe('3.14');
  });
});

describe('F7-T01 · aggregateToOhlc(interval_seconds)', () => {
  it('aggregateToOhlc1s should match fromArray default (backward compatibility)', () => {
    const trades: BinanceAggTrade[] = [
      makeTrade('100', '1', 1700000000000),
      makeTrade('101', '2', 1700000000500),
      makeTrade('102', '1', 1700000001000),
    ];
    expect(aggregateToOhlc1s(trades)).toEqual(OHLCAggregator.fromArray(trades));
    expect(aggregateToOhlc(trades, 1)).toEqual(OHLCAggregator.fromArray(trades, 1));
  });

  it('should aggregate trades into 1-minute buckets with aligned timestamps', () => {
    // 1700000000000 = 2023-11-14T22:13:20Z; minute floor = ...:13:00Z
    const trades: BinanceAggTrade[] = [
      makeTrade('100', '1', 1700000000000),
      makeTrade('105', '2', 1700000005000),
      makeTrade('99', '1', 1700000030000),
      makeTrade('101', '3', 1700000060000), // next minute
    ];
    const candles = aggregateToOhlc(trades, 60);
    expect(candles).toHaveLength(2);
    expect(candles[0].timestamp).toBe('2023-11-14T22:13:00.000Z');
    expect(candles[0].open).toBe(100);
    expect(candles[0].high).toBe(105);
    expect(candles[0].low).toBe(99);
    expect(candles[0].close).toBe(99);
    expect(candles[0].volume).toBe(4);
    expect(candles[0].tradeCount).toBe(3);
    expect(candles[1].timestamp).toBe('2023-11-14T22:14:00.000Z');
    expect(candles[1].open).toBe(101);
  });

  it('should support 5m/1h/1d bucket alignment', () => {
    const trades: BinanceAggTrade[] = [
      makeTrade('10', '1', Date.parse('2026-01-01T00:04:00.000Z')),
      makeTrade('12', '1', Date.parse('2026-01-01T00:06:00.000Z')),
      makeTrade('14', '1', Date.parse('2026-01-01T01:30:00.000Z')),
    ];
    const m5 = aggregateToOhlc(trades, 300);
    expect(m5).toHaveLength(3);
    expect(m5[0].timestamp).toBe('2026-01-01T00:00:00.000Z');
    expect(m5[1].timestamp).toBe('2026-01-01T00:05:00.000Z');

    const h1 = aggregateToOhlc(trades, 3600);
    expect(h1).toHaveLength(2);
    expect(h1[0].timestamp).toBe('2026-01-01T00:00:00.000Z');
    expect(h1[0].tradeCount).toBe(2);
    expect(h1[1].timestamp).toBe('2026-01-01T01:00:00.000Z');

    const d1 = aggregateToOhlc(trades, 86400);
    expect(d1).toHaveLength(1);
    expect(d1[0].timestamp).toBe('2026-01-01T00:00:00.000Z');
    expect(d1[0].tradeCount).toBe(3);
  });

  it('should reject unsupported intervals', () => {
    const trades = [makeTrade('100', '1', 1700000000000)];
    for (const bad of [2, 7, 30, 90, 0, -60]) {
      expect(() => aggregateToOhlc(trades, bad)).toThrow();
      expect(() => new OHLCAggregator(bad)).toThrow();
    }
    expect(() => timeframeLabelToInterval('2m')).toThrow();
    expect(() => parseTimeframesArgv(['--timeframes', '1s,2m'])).toThrow();
  });

  it('floorToInterval should be epoch-anchored', () => {
    expect(floorToInterval(1700000000500, 1)).toBe(1700000000000);
    const m = floorToInterval(1700000000500, 60);
    expect(m % 60000).toBe(0);
    expect(m).toBeLessThanOrEqual(1700000000500);
    expect(1700000000500 - m).toBeLessThan(60000);
    const d = floorToInterval(Date.parse('2026-03-15T13:45:22.000Z'), 86400);
    expect(d).toBe(Date.parse('2026-03-15T00:00:00.000Z'));
  });

  it('timeframe label mapping should round-trip', () => {
    expect(intervalToTimeframeLabel(1)).toBe('1s');
    expect(intervalToTimeframeLabel(60)).toBe('1m');
    expect(intervalToTimeframeLabel(300)).toBe('5m');
    expect(intervalToTimeframeLabel(3600)).toBe('1h');
    expect(intervalToTimeframeLabel(86400)).toBe('1d');
    for (const tf of ['1s', '1m', '5m', '1h', '1d']) {
      expect(intervalToTimeframeLabel(timeframeLabelToInterval(tf))).toBe(tf);
    }
  });
});

describe('F7-T03 · edge cases (time gaps, missing seconds, zero volumes, partial last bucket)', () => {
  it('time gaps: distant trades produce sparse candles, no filler', () => {
    const trades: BinanceAggTrade[] = [
      makeTrade('100', '1', 1700000000000),
      makeTrade('200', '1', 1700000000000 + 3600 * 1000), // 1h later
    ];
    const candles1s = aggregateToOhlc(trades, 1);
    expect(candles1s).toHaveLength(2);
    expect(candles1s[1].open).toBe(200);

    const candles1m = aggregateToOhlc(trades, 60);
    expect(candles1m).toHaveLength(2);
    // No filler buckets between the two distant trades
    expect(candles1m[1].timestamp > candles1m[0].timestamp).toBe(true);
  });

  it('missing seconds: gap seconds are absent from output', () => {
    const base = 1700000000000;
    const trades: BinanceAggTrade[] = [
      makeTrade('100', '1', base),
      makeTrade('101', '1', base + 1000),
      makeTrade('102', '1', base + 2000),
      // seconds base+3s .. base+9s missing
      makeTrade('110', '1', base + 10000),
      makeTrade('111', '1', base + 11000),
    ];
    const candles = aggregateToOhlc(trades, 1);
    expect(candles).toHaveLength(5);
    const timestamps = candles.map((c) => c.timestamp);
    expect(timestamps).toEqual([
      new Date(base).toISOString(),
      new Date(base + 1000).toISOString(),
      new Date(base + 2000).toISOString(),
      new Date(base + 10000).toISOString(),
      new Date(base + 11000).toISOString(),
    ]);
  });

  it('zero volumes: zero-quantity trades still form a candle with volume 0', () => {
    const trades: BinanceAggTrade[] = [
      makeTrade('100', '0', 1700000000000),
      makeTrade('101', '0', 1700000000500),
    ];
    const candles = aggregateToOhlc(trades, 1);
    expect(candles).toHaveLength(1);
    expect(candles[0].volume).toBe(0);
    expect(candles[0].tradeCount).toBe(2);
    expect(candles[0].open).toBe(100);
    expect(candles[0].close).toBe(101);
  });

  it('partial last bucket: streaming flushes an incomplete trailing bucket', async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ohlc-partial-'));
    const inputPath = path.join(dir, 'trades.jsonl');
    const outputPath = path.join(dir, 'out_1m.csv');
    // Two trades in the same minute, minute never "completes" (stream ends)
    const lines = [
      JSON.stringify({ a: 1, p: '50', q: '2', f: 1, l: 1, T: 1700000000000, m: false, M: true }),
      JSON.stringify({ a: 2, p: '52', q: '3', f: 2, l: 2, T: 1700000020000, m: false, M: true }),
    ].join('\n') + '\n';
    fs.writeFileSync(inputPath, lines, 'utf-8');

    await new OHLCAggregator(60).fromStream(inputPath, outputPath);
    const csv = await waitForFileContent(outputPath, 2, 10000);
    const rows = csv.trim().split('\n');
    expect(rows[0]).toBe('timestamp,open,high,low,close,volume,tradeCount');
    expect(rows).toHaveLength(2); // header + flushed partial bucket
    const cols = rows[1].split(',');
    expect(cols[0]).toBe('2023-11-14T22:13:00.000Z');
    expect(cols[1]).toBe('50');
    expect(cols[4]).toBe('52');
    expect(cols[5]).toBe('5');
    expect(cols[6]).toBe('2');
    fs.rmSync(dir, { recursive: true, force: true });
  }, 30000);
});

describe('F7-T02 · pipeline integration (timeframes flag, filenames, idempotency)', () => {
  it('parseTimeframesArgv should default to 1s and parse the flag', () => {
    expect(parseTimeframesArgv([])).toEqual(['1s']);
    expect(parseTimeframesArgv(['--timeframes', '1s,1m,5m,1h,1d'])).toEqual(['1s', '1m', '5m', '1h', '1d']);
    expect(parseTimeframesArgv(['--timeframes=5m,1h'])).toEqual(['5m', '1h']);
    expect(parseTimeframesArgv(['--timeframes', '1m,1m,1s'])).toEqual(['1m', '1s']); // dedupe
  });

  it('ohlcFilename should follow the ohlc_{tf}_{range}.csv contract', () => {
    expect(ohlcFilename('1s', '2026-01-01', '2026-01-02')).toBe('ohlc_1s_2026-01-01_2026-01-02.csv');
    expect(ohlcFilename('1m', '2026-01-01', '2026-01-02')).toBe('ohlc_1m_2026-01-01_2026-01-02.csv');
  });

  it('two timeframes on a fixture produce two coherent CSV sets (exhaustive)', async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ohlc-2tf-'));
    const inputPath = path.join(dir, 'trades.jsonl');
    // 3 minutes of trades, 1 trade every 10s, price ramps 100 -> 117
    const lines: string[] = [];
    let id = 1;
    for (let s = 0; s < 180; s += 10) {
      lines.push(
        JSON.stringify({ a: id, p: String(100 + s / 10), q: '1', f: id, l: id, T: 1700000000000 + s * 1000, m: false, M: true })
      );
      id++;
    }
    fs.writeFileSync(inputPath, lines.join('\n') + '\n', 'utf-8');

    const csv1s = path.join(dir, 'ohlc_1s.csv');
    const csv1m = path.join(dir, 'ohlc_1m.csv');
    await aggregateFileToOhlc(inputPath, csv1s, 1);
    await aggregateFileToOhlc(inputPath, csv1m, 60);
    const [candles1s, candles1m] = await Promise.all([
      readOhlcCsv(waitForFileContent(csv1s, 19, 10000)),
      readOhlcCsv(waitForFileContent(csv1m, 5, 10000)),
    ]);
    expect(candles1s).toHaveLength(18);
    expect(candles1m).toHaveLength(4);
    expectMinuteCoherence(candles1s, candles1m);
    fs.rmSync(dir, { recursive: true, force: true });
  }, 60000);
});

describe('F7-T03 · 1s→1m coherence on real data (UNIUSDT sample)', () => {
  it('each 1m candle aggregates its enclosed 1s candles (exhaustive)', async () => {
    const rawPath = 'D:/Documents/Projects/Trading/New/data/UNIUSDT/raw/aggTrades_2026-01-01_2026-01-30.jsonl';
    const trades = await readFirstTrades(rawPath, 20000);
    expect(trades.length).toBeGreaterThan(0);

    const candles1s = aggregateToOhlc(trades, 1);
    const candles1m = aggregateToOhlc(trades, 60);
    expect(candles1s.length).toBeGreaterThan(60);
    expect(candles1m.length).toBeGreaterThan(1);
    // Minute timestamps are aligned to :00
    for (const c of candles1m) {
      expect(new Date(c.timestamp).getUTCSeconds()).toBe(0);
      expect(new Date(c.timestamp).getUTCMilliseconds()).toBe(0);
    }
    expectMinuteCoherence(candles1s, candles1m);
  }, 120000);
});

/** Group 1s candles by minute and check every 1m candle against them (both directions). */
function expectMinuteCoherence(candles1s: OhlcCandle[], candles1m: OhlcCandle[]): void {
  const byMinute = new Map<number, OhlcCandle[]>();
  for (const c of candles1s) {
    const minute = Math.floor(Date.parse(c.timestamp) / 60000) * 60000;
    const group = byMinute.get(minute);
    if (group) group.push(c);
    else byMinute.set(minute, [c]);
  }
  expect(candles1m).toHaveLength(byMinute.size);
  for (const m of candles1m) {
    const minute = Date.parse(m.timestamp);
    const enclosed = byMinute.get(minute);
    expect(enclosed).toBeDefined();
    const ordered = [...enclosed!].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
    expect(m.open).toBe(ordered[0].open);
    expect(m.high).toBe(Math.max(...ordered.map((c) => c.high)));
    expect(m.low).toBe(Math.min(...ordered.map((c) => c.low)));
    expect(m.close).toBe(ordered[ordered.length - 1].close);
    expect(m.volume).toBeCloseTo(
      ordered.reduce((sum, c) => sum + c.volume, 0),
      8
    );
    expect(m.tradeCount).toBe(ordered.reduce((sum, c) => sum + c.tradeCount, 0));
    byMinute.delete(minute);
  }
  // Every 1s candle was enclosed in exactly one 1m candle
  expect(byMinute.size).toBe(0);
}

async function readFirstTrades(filePath: string, maxLines: number): Promise<BinanceAggTrade[]> {
  const trades: BinanceAggTrade[] = [];
  const rl = readline.createInterface({ input: fs.createReadStream(filePath), crlfDelay: Infinity });
  for await (const line of rl) {
    if (line.trim() === '') continue;
    try {
      trades.push(JSON.parse(line));
    } catch {
      continue;
    }
    if (trades.length >= maxLines) break;
  }
  rl.close();
  return trades;
}

async function readOhlcCsv(contentPromise: Promise<string>): Promise<OhlcCandle[]> {
  const content = await contentPromise;
  return content
    .trim()
    .split('\n')
    .slice(1)
    .filter((l) => l.trim() !== '')
    .map((line) => {
      const [timestamp, open, high, low, close, volume, tradeCount] = line.split(',');
      return {
        timestamp,
        open: parseFloat(open),
        high: parseFloat(high),
        low: parseFloat(low),
        close: parseFloat(close),
        volume: parseFloat(volume),
        tradeCount: parseInt(tradeCount, 10),
      };
    });
}

/**
 * fromStream ends the write stream without awaiting 'finish', so poll until
 * the file holds at least minLines lines (header included) or time out.
 */
async function waitForFileContent(filePath: string, minLines: number, timeoutMs: number): Promise<string> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    try {
      const content = fs.readFileSync(filePath, 'utf-8');
      if (content.trim().split('\n').length >= minLines) return content;
    } catch {
      // file not visible yet
    }
    if (Date.now() > deadline) {
      throw new Error(`Timed out waiting for ${minLines} lines in ${filePath}`);
    }
    await new Promise((r) => setTimeout(r, 50));
  }
}
