import fs from 'fs';
import path from 'path';
import readline from 'readline';
import { createGunzip } from 'zlib';
import { loadConfig } from './config/config';
import { BinanceAggTrade } from './binance/types';
import { floorToSecond, timestampMsToIso, dateToTimestampMs } from './utils/dateUtils';
import { logger } from './utils/logger';
import { OHLCAggregator } from './pipeline/ohlcAggregator';

async function main(): Promise<void> {
  try {
    const args = parseArgs();
    const config = loadConfig();

    const symbol = args.symbol || config.symbols[0];
    const startDate = args.start || config.startDate;
    const endDate = args.end || config.endDate;

    const startMs = dateToTimestampMs(startDate);
    const endMs = dateToTimestampMs(endDate);

    logger.info(`Extract range: ${symbol} from ${startDate} to ${endDate}`);

    const rawDir = path.join(config.outputDir, symbol, 'raw');
    if (!fs.existsSync(rawDir)) {
      throw new Error(`Raw directory not found: ${rawDir}`);
    }

    const jsonlFiles = selectBestFiles(rawDir, startDate, endDate);

    if (jsonlFiles.length === 0) {
      throw new Error(`No JSONL files covering the requested range in ${rawDir}`);
    }

    logger.info(`Selected ${jsonlFiles.length} raw file(s): ${jsonlFiles.map((f) => path.basename(f)).join(', ')}`);

    const ohlcDir = path.join(config.outputDir, symbol, 'ohlc');
    fs.mkdirSync(ohlcDir, { recursive: true });
    const outputPath = path.join(ohlcDir, `ohlc_1s_${startDate}_${endDate}.csv`);

    const writeStream = fs.createWriteStream(outputPath, { encoding: 'utf-8' });
    writeStream.write('timestamp,open,high,low,close,volume,tradeCount\n');

    let candleCount = 0;
    let tradeCount = 0;
    let skippedCount = 0;

    let currentSecond: number | null = null;
    let bucketOpen = 0;
    let bucketHigh = -Infinity;
    let bucketLow = Infinity;
    let bucketClose = 0;
    let bucketVolume = 0;
    let bucketTradeCount = 0;

    let lastLogAt = Date.now();

    for (const filePath of jsonlFiles) {
      logger.info(`Scanning: ${path.basename(filePath)}`);

      const isGz = filePath.endsWith('.gz');
      const readStream = fs.createReadStream(filePath);
      let inputStream: NodeJS.ReadableStream = readStream;

      if (isGz) {
        const gunzip = createGunzip();
        readStream.pipe(gunzip);
        inputStream = gunzip;
      }

      const rl = readline.createInterface({ input: inputStream as unknown as NodeJS.ReadableStream, crlfDelay: Infinity });

      for await (const line of rl) {
        if (line.trim() === '') continue;

        let trade: BinanceAggTrade;
        try {
          trade = JSON.parse(line);
        } catch {
          continue;
        }

        const timestampMs = OHLCAggregator.normalizeTimestamp(trade.T);

        if (timestampMs < startMs || timestampMs >= endMs) {
          skippedCount++;
          continue;
        }

        const price = OHLCAggregator.priceToNumber(trade.p);
        const quantity = OHLCAggregator.quantityToNumber(trade.q);
        const secondKey = floorToSecond(timestampMs);

        if (currentSecond === null) {
          currentSecond = secondKey;
          bucketOpen = price;
          bucketHigh = price;
          bucketLow = price;
          bucketClose = price;
          bucketVolume = quantity;
          bucketTradeCount = 1;
        } else if (secondKey === currentSecond) {
          if (price > bucketHigh) bucketHigh = price;
          if (price < bucketLow) bucketLow = price;
          bucketClose = price;
          bucketVolume += quantity;
          bucketTradeCount++;
        } else {
          writeCandleLine(writeStream, currentSecond, bucketOpen, bucketHigh, bucketLow, bucketClose, bucketVolume, bucketTradeCount);
          candleCount++;
          currentSecond = secondKey;
          bucketOpen = price;
          bucketHigh = price;
          bucketLow = price;
          bucketClose = price;
          bucketVolume = quantity;
          bucketTradeCount = 1;
        }

        tradeCount++;

        if (Date.now() - lastLogAt > 5_000) {
          logger.info(`  Progress: ${tradeCount.toLocaleString()} trades in range, ${skippedCount.toLocaleString()} skipped, ${candleCount.toLocaleString()} candles`);
          lastLogAt = Date.now();
        }
      }
    }

    if (currentSecond !== null) {
      writeCandleLine(writeStream, currentSecond, bucketOpen, bucketHigh, bucketLow, bucketClose, bucketVolume, bucketTradeCount);
      candleCount++;
    }

    await new Promise<void>((resolve, reject) => {
      writeStream.end(() => resolve());
      writeStream.on('error', reject);
    });

    logger.info(`\nDone!`);
    logger.info(`  Trades in range: ${tradeCount.toLocaleString()}`);
    logger.info(`  Trades skipped:  ${skippedCount.toLocaleString()}`);
    logger.info(`  Candles written: ${candleCount.toLocaleString()}`);
    logger.info(`  Output: ${outputPath}`);

    process.exit(0);
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    logger.error(`Fatal: ${msg}`);
    process.exit(1);
  }
}

function writeCandleLine(
  stream: fs.WriteStream,
  secondMs: number,
  open: number,
  high: number,
  low: number,
  close: number,
  volume: number,
  tradeCount: number
): void {
  const line = `${timestampMsToIso(secondMs)},${OHLCAggregator.fmt(open)},${OHLCAggregator.fmt(high)},${OHLCAggregator.fmt(low)},${OHLCAggregator.fmt(close)},${OHLCAggregator.fmt(volume)},${tradeCount}\n`;
  stream.write(line);
}

function selectBestFiles(rawDir: string, requestStart: string, requestEnd: string): string[] {
  const allFiles = fs.readdirSync(rawDir)
    .filter((f) => f.endsWith('.jsonl') || f.endsWith('.jsonl.gz'))
    .sort();

  if (allFiles.length === 0) return [];

  interface FileInfo {
    path: string;
    name: string;
    start: string;
    end: string;
  }

  const fileInfos: FileInfo[] = [];

  for (const file of allFiles) {
    const name = file.replace('.jsonl', '').replace('.jsonl.gz', '').replace('aggTrades_', '');

    const rangeMatch = name.match(/^(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})$/);
    if (rangeMatch) {
      fileInfos.push({
        path: path.join(rawDir, file),
        name: file,
        start: rangeMatch[1],
        end: rangeMatch[2],
      });
      continue;
    }

    const dayMatch = name.match(/^(\d{4}-\d{2}-\d{2})$/);
    if (dayMatch) {
      const dayStart = dayMatch[1];
      const nextDay = new Date(dayStart + 'T00:00:00Z');
      nextDay.setUTCDate(nextDay.getUTCDate() + 1);
      const dayEnd = nextDay.toISOString().split('T')[0];
      fileInfos.push({
        path: path.join(rawDir, file),
        name: file,
        start: dayStart,
        end: dayEnd,
      });
      continue;
    }
  }

  if (fileInfos.length === 0) return [];

  const overlapping = fileInfos.filter(
    (f) => f.start < requestEnd && f.end > requestStart
  );

  if (overlapping.length === 0) return [];

  overlapping.sort((a, b) => {
    const sizeA = dateToTimestampMs(a.end) - dateToTimestampMs(a.start);
    const sizeB = dateToTimestampMs(b.end) - dateToTimestampMs(b.start);
    return sizeB - sizeA;
  });

  const selected: FileInfo[] = [];

  for (const file of overlapping) {
    const isRedundant = selected.some(
      (s) => s.start <= file.start && s.end >= file.end
    );
    if (!isRedundant) {
      selected.push(file);
    } else {
      logger.info(`  Skipping ${file.name} (covered by larger file)`);
    }
  }

  selected.sort((a, b) => a.start.localeCompare(b.start));

  return selected.map((f) => f.path);
}

function parseArgs(): { symbol?: string; start?: string; end?: string } {
  const args = process.argv.slice(2);
  const result: { symbol?: string; start?: string; end?: string } = {};

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--symbol' && args[i + 1]) {
      result.symbol = args[i + 1].toUpperCase();
      i++;
    } else if (args[i] === '--start' && args[i + 1]) {
      result.start = args[i + 1];
      i++;
    } else if (args[i] === '--end' && args[i + 1]) {
      result.end = args[i + 1];
      i++;
    }
  }

  return result;
}

main();
