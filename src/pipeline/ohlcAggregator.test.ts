import { OHLCAggregator } from './ohlcAggregator';
import { BinanceAggTrade } from '../binance/types';

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
