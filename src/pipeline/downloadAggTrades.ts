import path from 'path';
import fs from 'fs';
import { finished } from 'stream/promises';
import { once } from 'events';
import { createReadStream } from 'fs';
import { createGzip, createGunzip, Gzip, Gunzip } from 'zlib';
import { BinanceClient } from '../binance/binanceClient';
import { BinanceAggTrade } from '../binance/types';
import { checkBulkAvailability } from '../binance/bulkAvailability';
import { downloadBulkDay } from '../binance/bulkDownloader';
import { writeAggTradesJsonl } from '../storage/jsonlWriter';
import { dateToTimestampMs, splitIntoDays } from '../utils/dateUtils';
import { runWithConcurrency } from '../utils/rateLimiter';
import { logger } from '../utils/logger';

const BATCH_LIMIT = 1000;
const MAX_WINDOW_MS = 60 * 60 * 1000;

export interface DownloadOptions {
  symbol: string;
  startDate: string;
  endDate: string;
  outputDir: string;
  concurrentDays: number;
  concurrentBulkDownloads?: number;
  useGzip?: boolean;
}

export interface DownloadResult {
  filePath: string;
  totalTrades: number;
}

/**
 * Predicato di appartenenza di un trade alla finestra di download corrente.
 *
 * Le tre clausole NON sono ridondanti tra loro:
 * - `t >= startMs`: necessario nelle pagine paginate (`fromId` senza
 *   `startTime`): l'API restituisce da `fromId` in poi senza vincolo di start.
 * - `t < endMs`: confine di giornata (end esclusiva).
 * - `t <= windowEndMs`: confine di finestra da 1h. Ridondante SOLO per la
 *   prima pagina (dove l'API applica già `endTime`), ma necessario per le
 *   pagine successive (`fromId` senza `endTime`), che possono sforare.
 */
export function isTradeInWindow(
  tradeTimeMs: number,
  startMs: number,
  endMs: number,
  windowEndMs: number
): boolean {
  return tradeTimeMs >= startMs && tradeTimeMs < endMs && tradeTimeMs <= windowEndMs;
}

export async function downloadAggTrades(
  client: BinanceClient,
  options: DownloadOptions
): Promise<DownloadResult> {
  const { symbol, startDate, endDate, outputDir, concurrentDays, useGzip = true } = options;
  const concurrentBulk = options.concurrentBulkDownloads || 10;

  const rawDir = path.join(outputDir, symbol, 'raw');
  const tempDir = path.join(outputDir, symbol, 'temp');
  const ext = useGzip ? '.jsonl.gz' : '.jsonl';
  const finalFilePath = path.join(rawDir, `aggTrades_${startDate}_${endDate}${ext}`);

  fs.mkdirSync(tempDir, { recursive: true });

  logger.info(`Downloading aggTrades for ${symbol} from ${startDate} to ${endDate} (gzip=${useGzip})`);

  const days = splitIntoDays(startDate, endDate);
  const dayDates = days.map((d) => d.start);
  logger.info(`${symbol}: Split into ${days.length} day(s) to download`);

  logger.info(`${symbol}: Checking bulk data availability on data.binance.vision...`);
  const bulkAvailable = await checkBulkAvailability(symbol, dayDates);

  const bulkDays = days.filter((d) => bulkAvailable.has(d.start));
  const apiDays = days.filter((d) => !bulkAvailable.has(d.start));

  logger.info(`${symbol}: ${bulkDays.length} days via BULK, ${apiDays.length} days via REST API`);

  let bulkResults: Array<{ dayFilePath: string; start: string; trades: number }> = [];
  if (bulkDays.length > 0) {
    logger.info(`${symbol}: Starting bulk downloads (${concurrentBulk} concurrent)...`);
    bulkResults = await runWithConcurrency(
      bulkDays,
      concurrentBulk,
      async (day) => {
        try {
          const trades = await downloadBulkDay(symbol, day.start, tempDir, useGzip);
          const dayFilePath = path.join(rawDir, `aggTrades_${day.start}${ext}`);
          await writeAggTradesJsonl(trades, dayFilePath, false);
          return { dayFilePath, start: day.start, trades: trades.length };
        } catch (error) {
          const msg = error instanceof Error ? error.message : String(error);
          logger.warn(`${symbol} [${day.start}]: Bulk download failed (${msg}), falling back to REST API`);
          const dayFilePath = path.join(rawDir, `aggTrades_${day.start}${ext}`);
          const tradeCount = await downloadDayTrades(client, symbol, day.start, day.end, dayFilePath, useGzip);
          return { dayFilePath, start: day.start, trades: tradeCount };
        }
      }
    );
  }

  let apiResults: Array<{ dayFilePath: string; start: string; trades: number }> = [];
  if (apiDays.length > 0) {
    logger.info(`${symbol}: Starting REST API downloads (${concurrentDays} concurrent)...`);
    apiResults = await runWithConcurrency(
      apiDays,
      concurrentDays,
      async (day) => {
        const dayFilePath = path.join(rawDir, `aggTrades_${day.start}${ext}`);
        const tradeCount = await downloadDayTrades(client, symbol, day.start, day.end, dayFilePath, useGzip);
        return { dayFilePath, start: day.start, trades: tradeCount };
      }
    );
  }

  const allResults = [...bulkResults, ...apiResults];
  const totalTrades = await mergeDayFiles(allResults, finalFilePath);

  cleanupDir(tempDir);

  logger.info(`${symbol}: Download complete. Total trades: ${totalTrades}`);
  return { filePath: finalFilePath, totalTrades };
}

async function downloadDayTrades(
  client: BinanceClient,
  symbol: string,
  startDate: string,
  endDate: string,
  filePath: string,
  useGzip: boolean = true
): Promise<number> {
  const startMs = dateToTimestampMs(startDate);
  const endMs = dateToTimestampMs(endDate);

  let totalTrades = 0;
  let currentStartMs = startMs;
  let isFirstBatch = true;

  while (currentStartMs < endMs) {
    const windowEndMs = Math.min(currentStartMs + MAX_WINDOW_MS, endMs);

    let lastTradeId: number | undefined;
    let windowDone = false;

    while (!windowDone) {
      const trades: BinanceAggTrade[] = await client.getAggTrades({
        symbol,
        startTime: lastTradeId === undefined ? currentStartMs : undefined,
        endTime: lastTradeId === undefined ? windowEndMs : undefined,
        fromId: lastTradeId !== undefined ? lastTradeId + 1 : undefined,
        limit: BATCH_LIMIT,
      });

      if (trades.length === 0) {
        windowDone = true;
        break;
      }

      const filteredTrades = trades.filter((t) => isTradeInWindow(t.T, startMs, endMs, windowEndMs));

      if (filteredTrades.length > 0) {
        await writeAggTradesJsonl(filteredTrades, filePath, !isFirstBatch);
        isFirstBatch = false;
        totalTrades += filteredTrades.length;
      }

      if (trades.length < BATCH_LIMIT) {
        windowDone = true;
      } else {
        const lastTrade = trades[trades.length - 1];
        if (lastTrade.T >= windowEndMs || lastTrade.T >= endMs) {
          windowDone = true;
        } else {
          lastTradeId = lastTrade.a;
        }
      }

      logger.debug(
        `${symbol} [${startDate}]: fetched ${trades.length} trades, day total: ${totalTrades}`
      );
    }

    currentStartMs = windowEndMs;
  }

  logger.info(`${symbol} [${startDate}]: Day complete. ${totalTrades} trades`);
  return totalTrades;
}

/**
 * Pompa il contenuto (decompresso se `.gz`) di un file dentro un writable
 * condiviso, SENZA chiuderlo: il chiamante resta proprietario del sink e lo
 * chiude una sola volta alla fine.
 *
 * Perché non `pipeline(src, sink)` in loop: `pipeline` chiude il destination
 * al completamento, quindi il secondo file fallirebbe con write-after-end.
 */
async function pumpDecodedFile(
  inputPath: string,
  sink: fs.WriteStream | Gzip,
  sinkFailed: () => Error | null
): Promise<void> {
  const rs = createReadStream(inputPath);
  let gunzip: Gunzip | null = null;
  let src: NodeJS.ReadableStream = rs;

  if (inputPath.endsWith('.gz')) {
    gunzip = createGunzip();
    // Inoltra gli errori del file al gunzip: senza questo, un rs fallito
    // lascerebbe il gunzip appeso e il for-await non terminerebbe mai.
    rs.on('error', (e: Error) => gunzip?.destroy(e));
    rs.pipe(gunzip);
    src = gunzip;
  }

  try {
    for await (const chunk of src as AsyncIterable<Buffer>) {
      const err = sinkFailed();
      if (err) throw err;
      const data = chunk as Buffer;
      if (!sink.write(data)) {
        // Backpressure: attende drain, ma un errore del sink nel frattempo
        // deve interrompere l'attesa (altrimenti hang infinito).
        await Promise.race([
          once(sink, 'drain'),
          once(sink, 'error').then((args: unknown[]) => {
            throw args[0] as Error;
          }),
        ]);
      }
    }
    const err = sinkFailed();
    if (err) throw err;
  } finally {
    rs.destroy();
    gunzip?.destroy();
  }
}

/** Scrive un gzip valido ma vuoto (un `.gz` a zero byte non è decomprimibile). */
async function writeEmptyGzip(filePath: string): Promise<void> {
  const fileOut = fs.createWriteStream(filePath, { flags: 'w' });
  fileOut.on('error', () => {});
  const gzip = createGzip({ level: 6 });
  gzip.on('error', (e: Error) => fileOut.destroy(e));
  gzip.pipe(fileOut);
  gzip.end();
  await finished(fileOut);
}

export async function mergeDayFiles(
  dayResults: Array<{ dayFilePath: string; start: string; trades: number }>,
  finalFilePath: string
): Promise<number> {
  const dir = path.dirname(finalFilePath);
  fs.mkdirSync(dir, { recursive: true });

  const sorted = [...dayResults].sort((a, b) => a.start.localeCompare(b.start));

  let totalTrades = 0;
  const validResults = sorted.filter((d) => d.trades > 0 && fs.existsSync(d.dayFilePath));

  if (validResults.length === 0) {
    if (finalFilePath.endsWith('.gz')) {
      await writeEmptyGzip(finalFilePath);
    } else {
      fs.writeFileSync(finalFilePath, '', 'utf-8');
    }
    return 0;
  }

  const isGz = finalFilePath.endsWith('.gz');
  const fileOut = fs.createWriteStream(finalFilePath, { flags: 'w' });
  // Handler noop anti-crash: l'osservatore reale è `finished()` alla fine.
  // Senza listener, un errore a metà pump causerebbe un throw non gestito.
  fileOut.on('error', () => {});

  // Per output .gz i byte decompressi dei giorni vengono RICOMPRESSI in
  // un unico membro gzip (prima il merge scriveva testo piano in un file
  // chiamato .gz, illeggibile dal gunzip a valle).
  const gzip: Gzip | null = isGz ? createGzip({ level: 6 }) : null;
  const sink: fs.WriteStream | Gzip = gzip ?? fileOut;
  let sinkError: Error | null = null;
  sink.on('error', (e: Error) => {
    sinkError = e;
  });
  if (gzip) {
    gzip.on('error', (e: Error) => fileOut.destroy(e));
    gzip.pipe(fileOut);
  }
  const sinkFailed = (): Error | null => sinkError;

  try {
    for (const day of validResults) {
      await pumpDecodedFile(day.dayFilePath, sink, sinkFailed);
      totalTrades += day.trades;

      if (day.dayFilePath !== finalFilePath) {
        try {
          fs.unlinkSync(day.dayFilePath);
        } catch {
          logger.warn(`Could not delete temp file: ${day.dayFilePath}`);
        }
      }
    }
  } catch (error) {
    try {
      sink.destroy();
    } catch {
      // best effort
    }
    fileOut.destroy();
    throw error;
  }

  if (gzip) {
    gzip.end();
  } else {
    fileOut.end();
  }
  await finished(fileOut);

  logger.info(`Merged ${validResults.length} day file(s) into ${finalFilePath}`);
  return totalTrades;
}

function cleanupDir(dirPath: string): void {
  try {
    if (fs.existsSync(dirPath)) {
      fs.rmSync(dirPath, { recursive: true, force: true });
    }
  } catch {
    // Ignore cleanup errors
  }
}
