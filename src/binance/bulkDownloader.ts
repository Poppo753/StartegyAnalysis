import axios from 'axios';
import fs from 'fs';
import path from 'path';
import { createWriteStream } from 'fs';
import { pipeline } from 'stream/promises';
import JSZip from 'jszip';
import { getBulkDownloadUrl } from './bulkAvailability';
import { BinanceAggTrade } from './types';
import { logger } from '../utils/logger';

export async function downloadBulkDay(
  symbol: string,
  date: string,
  tempDir: string,
  useGzip: boolean = true
): Promise<BinanceAggTrade[]> {
  const url = getBulkDownloadUrl(symbol, date);
  const zipPath = path.join(tempDir, `${symbol}-aggTrades-${date}.zip`);
  const csvPath = path.join(tempDir, `${symbol}-aggTrades-${date}.csv`);

  try {
    await downloadFile(url, zipPath);
    await unzipFile(zipPath, tempDir);
    const trades = parseBulkCsv(csvPath);

    logger.info(`${symbol} [${date}]: Bulk download complete. ${trades.length} trades`);

    cleanupFile(zipPath);
    cleanupFile(csvPath);

    return trades;
  } catch (error) {
    cleanupFile(zipPath);
    cleanupFile(csvPath);
    throw error;
  }
}

async function downloadFile(url: string, destPath: string): Promise<void> {
  const dir = path.dirname(destPath);
  fs.mkdirSync(dir, { recursive: true });

  const response = await axios.get(url, {
    responseType: 'stream',
    timeout: 120000,
  });

  const writer = createWriteStream(destPath);
  await pipeline(response.data, writer);
}

async function unzipFile(zipPath: string, targetDir: string): Promise<void> {
  fs.mkdirSync(targetDir, { recursive: true });

  const zipData = await fs.promises.readFile(zipPath);
  const zip = await JSZip.loadAsync(zipData);

  for (const [fileName, zipEntry] of Object.entries(zip.files)) {
    if ((zipEntry as any).dir) continue;

    const content = await (zipEntry as any).async('nodebuffer');
    const destPath = path.join(targetDir, fileName);
    const destDir = path.dirname(destPath);

    fs.mkdirSync(destDir, { recursive: true });
    await fs.promises.writeFile(destPath, content);
  }

  logger.info(`Unzipped ${Object.keys(zip.files).length} entries from ${path.basename(zipPath)}`);
}

function parseBulkCsv(csvPath: string): BinanceAggTrade[] {
  if (!fs.existsSync(csvPath)) {
    throw new Error(`CSV file not found after unzip: ${csvPath}`);
  }

  const content = fs.readFileSync(csvPath, 'utf-8');
  const lines = content.trim().split('\n');
  const trades: BinanceAggTrade[] = [];

  for (const line of lines) {
    if (line.trim() === '') continue;

    const parts = line.split(',');
    if (parts.length < 7) continue;

    if (parts[0] === 'agg_trade_id' || isNaN(Number(parts[0]))) continue;

    trades.push({
      a: parseInt(parts[0], 10),
      p: parts[1],
      q: parts[2],
      f: parseInt(parts[3], 10),
      l: parseInt(parts[4], 10),
      T: normalizeTimestamp(parseInt(parts[5], 10)),
      m: parts[6] === 'true' || parts[6] === 'True',
      M: parts.length > 7 ? (parts[7]?.trim() === 'true' || parts[7]?.trim() === 'True') : true,
    });
  }

  return trades;
}

function normalizeTimestamp(ts: number): number {
  if (ts > 9_999_999_999_999) {
    return Math.floor(ts / 1000);
  }
  return ts;
}

function cleanupFile(filePath: string): void {
  try {
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
  } catch {
    // Ignore cleanup errors
  }
}
