import dotenv from 'dotenv';
import path from 'path';

dotenv.config();

export interface AppConfig {
  symbols: string[];
  startDate: string;
  endDate: string;
  outputDir: string;
  binanceBaseUrl: string;
  requestDelayMs: number;
  concurrentDays: number;
  concurrentBulkDownloads: number;
  maxRequestsPerMinute: number;
  useGzip: boolean;
  jsonLogging: boolean;
}

function getEnvOrThrow(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

function getEnvOrDefault(key: string, defaultValue: string): string {
  return process.env[key] || defaultValue;
}

export function loadConfig(): AppConfig {
  const symbolsRaw = getEnvOrThrow('SYMBOLS');
  const symbols = symbolsRaw.split(',').map((s) => s.trim().toUpperCase());

  if (symbols.length === 0 || symbols.some((s) => s === '')) {
    throw new Error('SYMBOLS must contain at least one valid symbol');
  }

  const startDate = getEnvOrThrow('START_DATE');
  const endDate = getEnvOrThrow('END_DATE');

  // Validate date format
  const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
  if (!dateRegex.test(startDate) || !dateRegex.test(endDate)) {
    throw new Error('START_DATE and END_DATE must be in YYYY-MM-DD format');
  }

  if (new Date(startDate) >= new Date(endDate)) {
    throw new Error('START_DATE must be before END_DATE');
  }

  const outputDir = getEnvOrDefault('OUTPUT_DIR', './data');
  const binanceBaseUrl = getEnvOrDefault('BINANCE_BASE_URL', 'https://api.binance.com');
  const requestDelayMs = parseInt(getEnvOrDefault('REQUEST_DELAY_MS', '100'), 10);
  const concurrentDays = parseInt(getEnvOrDefault('CONCURRENT_DAYS', '5'), 10);
  const concurrentBulkDownloads = parseInt(getEnvOrDefault('CONCURRENT_BULK_DOWNLOADS', '10'), 10);
  const maxRequestsPerMinute = parseInt(getEnvOrDefault('MAX_REQUESTS_PER_MINUTE', '500'), 10);

  if (isNaN(requestDelayMs) || requestDelayMs < 0) {
    throw new Error('REQUEST_DELAY_MS must be a non-negative number');
  }
  if (isNaN(concurrentDays) || concurrentDays < 1) {
    throw new Error('CONCURRENT_DAYS must be at least 1');
  }
  if (isNaN(concurrentBulkDownloads) || concurrentBulkDownloads < 1) {
    throw new Error('CONCURRENT_BULK_DOWNLOADS must be at least 1');
  }
  if (isNaN(maxRequestsPerMinute) || maxRequestsPerMinute < 1) {
    throw new Error('MAX_REQUESTS_PER_MINUTE must be at least 1');
  }

  const useGzip = getEnvOrDefault('USE_GZIP', 'true').toLowerCase() === 'true';
  const jsonLogging = getEnvOrDefault('JSON_LOGGING', 'false').toLowerCase() === 'true';

  return {
    symbols,
    startDate,
    endDate,
    outputDir: path.resolve(outputDir),
    binanceBaseUrl,
    requestDelayMs,
    concurrentDays,
    concurrentBulkDownloads,
    maxRequestsPerMinute,
    useGzip,
    jsonLogging,
  };
}