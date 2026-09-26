import fs from 'fs';
import os from 'os';
import path from 'path';
import {
  writeAggTradesJsonl,
  readAggTradesJsonl,
  readAggTradesJsonlStream,
  MAX_JSONL_FULL_READ_BYTES,
} from './jsonlWriter';
import { BinanceAggTrade } from '../binance/types';

function makeTrade(id: number): BinanceAggTrade {
  return { a: id, p: '100.5', q: '0.01', f: id, l: id, T: 1700000000000, m: false, M: true };
}

describe('readAggTradesJsonl size guard', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'jsonl-guard-'));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('default threshold is 256MB named constant', () => {
    expect(MAX_JSONL_FULL_READ_BYTES).toBe(256 * 1024 * 1024);
  });

  it('small file reads normally', async () => {
    const fp = path.join(tmpDir, 'small.jsonl');
    await writeAggTradesJsonl([makeTrade(1), makeTrade(2)], fp, false);
    const trades = await readAggTradesJsonl(fp);
    expect(trades).toHaveLength(2);
  });

  it('synthetic over-threshold file → explicit error, not crash', async () => {
    const fp = path.join(tmpDir, 'big.jsonl');
    await writeAggTradesJsonl([makeTrade(1), makeTrade(2), makeTrade(3)], fp, false);
    const size = fs.statSync(fp).size;
    expect(size).toBeGreaterThan(0);

    // Force the guard with a tiny threshold (avoids creating a real 256MB file).
    await expect(readAggTradesJsonl(fp, 10)).rejects.toThrow(
      /Refusing to fully load.*use readAggTradesJsonlStream/
    );

    // The streaming path must still handle the same file (historic-GB route).
    const streamed: BinanceAggTrade[] = [];
    for await (const t of readAggTradesJsonlStream(fp)) {
      streamed.push(t);
    }
    expect(streamed).toHaveLength(3);
  });
});
