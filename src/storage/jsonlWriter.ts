import fs from 'fs';
import path from 'path';
import { createGunzip } from 'zlib';
import { pipeline } from 'stream/promises';
import { BinanceAggTrade } from '../binance/types';
import { logger } from '../utils/logger';

export function getJsonlPath(basePath: string): string {
  return basePath.endsWith('.jsonl') ? basePath : `${basePath}.jsonl`;
}

export function getGzipPath(basePath: string): string {
  if (basePath.endsWith('.jsonl.gz')) return basePath;
  // Evita la doppia estensione: "aggTrades_X_Y.jsonl" -> "aggTrades_X_Y.jsonl.gz"
  if (basePath.endsWith('.jsonl')) return `${basePath}.gz`;
  return `${basePath}.jsonl.gz`;
}

export function isGzipPath(filePath: string): boolean {
  return filePath.endsWith('.gz');
}

/**
 * Write aggregate trades to a JSONL(.gz) file using streaming.
 * Supports appending to an existing file.
 */
export async function writeAggTradesJsonl(
  trades: BinanceAggTrade[],
  filePath: string,
  append: boolean = false
): Promise<void> {
  const dir = path.dirname(filePath);
  fs.mkdirSync(dir, { recursive: true });

  if (trades.length === 0) return;

  const useGzip = filePath.endsWith('.gz');
  const flags = append ? 'a' : 'w';

  const writeStream = fs.createWriteStream(filePath, { flags, encoding: 'utf-8' });

  if (useGzip) {
    const { pipeline } = await import('stream/promises');
    const { createGzip } = await import('zlib');
    const gzip = createGzip({ level: 6 });
    gzip.pipe(writeStream);
    for (const trade of trades) {
      gzip.write(JSON.stringify(trade) + '\n');
    }
    gzip.end();
    await new Promise<void>((resolve, reject) => {
      writeStream.on('finish', resolve);
      writeStream.on('error', reject);
    });
  } else {
    for (const trade of trades) {
      writeStream.write(JSON.stringify(trade) + '\n');
    }
    await new Promise<void>((resolve, reject) => {
      writeStream.end(() => resolve());
      writeStream.on('error', reject);
    });
  }

  logger.info(`JSONL ${append ? 'appended' : 'written'}: ${filePath} (${trades.length} trades)`);
}

/**
 * Maximum file size (on-disk bytes, as OOM proxy) allowed for full-RAM read.
 * Larger files must use readAggTradesJsonlStream.
 */
export const MAX_JSONL_FULL_READ_BYTES = 256 * 1024 * 1024; // 256MB

/**
 * Read aggregate trades from a JSONL(.gz) file using streaming.
 * Returns an array of trades. For very large files, use readAggTradesJsonlStream.
 */
export async function readAggTradesJsonl(
  filePath: string,
  maxBytes: number = MAX_JSONL_FULL_READ_BYTES
): Promise<BinanceAggTrade[]> {
  if (!fs.existsSync(filePath)) {
    return [];
  }

  const size = fs.statSync(filePath).size;
  if (size > maxBytes) {
    throw new Error(
      `Refusing to fully load ${filePath} (${size} bytes > ${maxBytes} bytes): ` +
        `use readAggTradesJsonlStream for large files to avoid OOM`
    );
  }

  const isGz = filePath.endsWith('.gz');
  const trades: BinanceAggTrade[] = [];

  const readStream = fs.createReadStream(filePath);

  let transformStream;
  if (isGz) {
    transformStream = createGunzip();
    readStream.pipe(transformStream);
  } else {
    transformStream = readStream;
  }

  const { createInterface } = await import('readline');
  const rl = createInterface({
    input: transformStream as unknown as NodeJS.ReadableStream,
    crlfDelay: Infinity,
  });

  for await (const line of rl) {
    if (line.trim() === '') continue;
    try {
      trades.push(JSON.parse(line) as BinanceAggTrade);
    } catch {
      continue;
    }
  }

  return trades;
}

/**
 * Stream lines from a JSONL(.gz) file.
 */
export async function* readAggTradesJsonlStream(
  filePath: string
): AsyncGenerator<BinanceAggTrade> {
  if (!fs.existsSync(filePath)) {
    return;
  }

  const isGz = filePath.endsWith('.gz');
  const readStream = fs.createReadStream(filePath);

  let transformStream;
  if (isGz) {
    const { pipeline } = await import('stream/promises');
    const { createGunzip } = await import('zlib');
    const gunzip = createGunzip();
    readStream.pipe(gunzip);
    transformStream = gunzip;
  } else {
    transformStream = readStream;
  }

  const { createInterface } = await import('readline');
  const rl = createInterface({
    input: transformStream as unknown as NodeJS.ReadableStream,
    crlfDelay: Infinity,
  });

  for await (const line of rl) {
    if (line.trim() === '') continue;
    try {
      yield JSON.parse(line) as BinanceAggTrade;
    } catch {
      continue;
    }
  }
}
