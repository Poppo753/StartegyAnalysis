import fs from 'fs';
import os from 'os';
import path from 'path';
import { isTradeInWindow, mergeDayFiles } from './downloadAggTrades';
import { writeAggTradesJsonl, readAggTradesJsonl } from '../storage/jsonlWriter';
import { BinanceAggTrade } from '../binance/types';

describe('isTradeInWindow', () => {
  const startMs = 1_700_000_000_000;
  const endMs = startMs + 24 * 3_600_000; // +1 giorno
  const windowEndMs = startMs + 3_600_000; // +1h

  it('accetta trade dentro giornata e finestra', () => {
    expect(isTradeInWindow(startMs, startMs, endMs, windowEndMs)).toBe(true);
    expect(isTradeInWindow(windowEndMs, startMs, endMs, windowEndMs)).toBe(true);
    expect(isTradeInWindow(startMs + 1_000, startMs, endMs, windowEndMs)).toBe(true);
  });

  it('scarta trade prima di startMs (pagine paginate senza startTime)', () => {
    expect(isTradeInWindow(startMs - 1, startMs, endMs, windowEndMs)).toBe(false);
  });

  it('scarta trade oltre windowEndMs (pagine fromId senza endTime)', () => {
    expect(isTradeInWindow(windowEndMs + 1, startMs, endMs, windowEndMs)).toBe(false);
  });

  it('scarta trade a endMs (confine giornata esclusivo)', () => {
    expect(isTradeInWindow(endMs, startMs, endMs, windowEndMs)).toBe(false);
  });

  it('finestra che coincide con fine giornata: entrambe le guardie coerenti', () => {
    const wEnd = endMs;
    expect(isTradeInWindow(endMs - 1, startMs, endMs, wEnd)).toBe(true);
    expect(isTradeInWindow(endMs, startMs, endMs, wEnd)).toBe(false);
  });
});

function makeTrade(id: number, timeMs: number): BinanceAggTrade {
  return {
    a: id,
    p: '100.5',
    q: '0.01',
    f: id,
    l: id,
    T: timeMs,
    m: false,
    M: true,
  };
}

describe('mergeDayFiles', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'merge-test-'));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('fonde 3 file .gz in un unico .gz valido e ordinato', async () => {
    const base = 1_700_000_000_000;
    const days = ['2024-01-03', '2024-01-01', '2024-01-02']; // volutamente non ordinati
    const results = [];
    for (let d = 0; d < days.length; d++) {
      const fp = path.join(tmpDir, `aggTrades_${days[d]}.jsonl.gz`);
      const trades = [makeTrade(d * 10 + 1, base + d * 1000), makeTrade(d * 10 + 2, base + d * 1000 + 500)];
      await writeAggTradesJsonl(trades, fp, false);
      results.push({ dayFilePath: fp, start: days[d], trades: trades.length });
    }

    const finalFp = path.join(tmpDir, 'aggTrades_2024-01-01_2024-01-04.jsonl.gz');
    const total = await mergeDayFiles(results, finalFp);

    expect(total).toBe(6);
    // Il merge di 3 file richiedeva 3 pipeline sullo stesso sink: prima del
    // fix falliva dal secondo file (write-after-end).
    const merged = await readAggTradesJsonl(finalFp);
    expect(merged).toHaveLength(6);
    // Ordinati per giorno: 2024-01-01 (id 11,12), 01-02 (21,22), 01-03 (1,2)
    expect(merged.map((t) => t.a)).toEqual([11, 12, 21, 22, 1, 2]);
  });

  it('fonde 2 file piani in un unico .jsonl', async () => {
    const fp1 = path.join(tmpDir, 'a.jsonl');
    const fp2 = path.join(tmpDir, 'b.jsonl');
    await writeAggTradesJsonl([makeTrade(1, 1000)], fp1, false);
    await writeAggTradesJsonl([makeTrade(2, 2000), makeTrade(3, 3000)], fp2, false);

    const finalFp = path.join(tmpDir, 'merged.jsonl');
    const total = await mergeDayFiles(
      [
        { dayFilePath: fp1, start: '2024-01-01', trades: 1 },
        { dayFilePath: fp2, start: '2024-01-02', trades: 2 },
      ],
      finalFp
    );

    expect(total).toBe(3);
    const merged = await readAggTradesJsonl(finalFp);
    expect(merged.map((t) => t.a)).toEqual([1, 2, 3]);
  });

  it('caso vuoto: .gz finale valido e leggibile', async () => {
    const finalFp = path.join(tmpDir, 'empty.jsonl.gz');
    const total = await mergeDayFiles([], finalFp);
    expect(total).toBe(0);
    const merged = await readAggTradesJsonl(finalFp);
    expect(merged).toEqual([]);
  });
});
