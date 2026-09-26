import axios from 'axios';
import { logger } from '../utils/logger';

const S3_BASE_URL = 'https://s3-ap-northeast-1.amazonaws.com/data.binance.vision';

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Check which days have bulk aggTrades data available on data.binance.vision.
 * Returns a Set of date strings (YYYY-MM-DD) that are available for bulk download.
 */
export async function checkBulkAvailability(
  symbol: string,
  days: string[]
): Promise<Set<string>> {
  const available = new Set<string>();

  // Group days by month prefix to minimize S3 list requests
  const monthPrefixes = new Map<string, string[]>();
  for (const day of days) {
    const monthPrefix = day.substring(0, 7); // "2024-01"
    const existing = monthPrefixes.get(monthPrefix) || [];
    existing.push(day);
    monthPrefixes.set(monthPrefix, existing);
  }

  for (const [monthPrefix, monthDays] of monthPrefixes) {
    try {
      const prefix = `data/spot/daily/aggTrades/${symbol}/${symbol}-aggTrades-${monthPrefix}`;
      const url = `${S3_BASE_URL}?prefix=${prefix}&max-keys=100`;

      const response = await axios.get(url, { timeout: 15000 });
      const xml = response.data as string;

      // Parse available files from XML response
      for (const day of monthDays) {
        const zipFile = `${symbol}-aggTrades-${day}.zip`;
        const keyPattern = new RegExp('<Key>' + escapeRegex(zipFile) + '</Key>');
        if (keyPattern.test(xml)) {
          available.add(day);
        }
      }
    } catch (error) {
      // If we can't check, assume not available — will fall back to REST API
      logger.warn(`Could not check bulk availability for ${symbol} ${monthPrefix}`);
    }
  }

  logger.info(
    `${symbol}: Bulk availability check complete. ${available.size}/${days.length} days available in bulk.`
  );

  return available;
}

/**
 * Get the download URL for a bulk aggTrades file.
 */
export function getBulkDownloadUrl(symbol: string, date: string): string {
  return `https://data.binance.vision/data/spot/daily/aggTrades/${symbol}/${symbol}-aggTrades-${date}.zip`;
}