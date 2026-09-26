import axios, { AxiosInstance, AxiosError } from 'axios';
import { BinanceAggTrade, AggTradesParams } from './types';
import { delay, GlobalRateLimiter } from '../utils/rateLimiter';
import { logger } from '../utils/logger';

const MAX_RETRIES = 5;
const RETRY_BASE_DELAY_MS = 1000;

export class BinanceClient {
  private client: AxiosInstance;
  private requestDelayMs: number;
  private rateLimiter: GlobalRateLimiter;

  constructor(baseUrl: string, requestDelayMs: number, rateLimiter: GlobalRateLimiter) {
    this.client = axios.create({
      baseURL: baseUrl,
      timeout: 30000,
    });
    this.requestDelayMs = requestDelayMs;
    this.rateLimiter = rateLimiter;
  }

  /**
   * Fetch aggregate trades with automatic retry on 429 and 5xx errors.
   * Implements exponential backoff: delay = RETRY_BASE_DELAY_MS * 2^(attempt-1).
   * Maximum of MAX_RETRIES retry attempts (MAX_RETRIES + 1 total attempts).
   */
  async getAggTrades(params: AggTradesParams): Promise<BinanceAggTrade[]> {
    const queryParams: Record<string, string | number> = {
      symbol: params.symbol,
      limit: params.limit || 1000,
    };

    if (params.startTime !== undefined) queryParams.startTime = params.startTime;
    if (params.endTime !== undefined) queryParams.endTime = params.endTime;
    if (params.fromId !== undefined) queryParams.fromId = params.fromId;

    for (let attempt = 1; attempt <= MAX_RETRIES + 1; attempt++) {
      try {
        await this.rateLimiter.acquire();
        await delay(this.requestDelayMs);

        const response = await this.client.get<BinanceAggTrade[]>('/api/v3/aggTrades', {
          params: queryParams,
        });

        return response.data;
      } catch (error) {
        const axiosError = error as AxiosError;
        const status = axiosError.response?.status;

        if (status === 429 || (status !== undefined && status >= 500)) {
          if (attempt > MAX_RETRIES) {
            logger.error(`Max retries (${MAX_RETRIES}) exceeded for ${params.symbol}`);
            throw error;
          }

          const retryDelay = RETRY_BASE_DELAY_MS * Math.pow(2, attempt - 1);
          logger.warn(
            `HTTP ${status} for ${params.symbol}. Retry ${attempt}/${MAX_RETRIES + 1} in ${retryDelay}ms...`
          );
          await delay(retryDelay);
        } else {
          throw error;
        }
      }
    }

    throw new Error(`Unreachable: failed to fetch ${params.symbol} after ${MAX_RETRIES + 1} attempts`);
  }
}
