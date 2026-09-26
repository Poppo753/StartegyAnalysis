/**
 * Simple delay utility for rate limiting.
 */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Global rate limiter using a sliding window approach.
 * Ensures we don't exceed maxRequests within the rolling windowMs.
 */
export class GlobalRateLimiter {
  private timestamps: number[] = [];
  private maxRequests: number;
  private windowMs: number;

  constructor(maxRequestsPerMinute: number) {
    this.maxRequests = maxRequestsPerMinute;
    this.windowMs = 60_000; // 1 minute window
  }

  /**
   * Wait until we can make a request without exceeding the rate limit.
   */
  async acquire(): Promise<void> {
    while (true) {
      const now = Date.now();
      // Remove timestamps older than the window
      this.timestamps = this.timestamps.filter((t) => now - t < this.windowMs);

      if (this.timestamps.length < this.maxRequests) {
        this.timestamps.push(now);
        return;
      }

      // Wait until the oldest request exits the window
      const oldestInWindow = this.timestamps[0];
      const waitTime = oldestInWindow + this.windowMs - now + 1;
      await delay(waitTime);
    }
  }

  /**
   * Get current usage info for logging.
   */
  getUsage(): { current: number; max: number } {
    const now = Date.now();
    this.timestamps = this.timestamps.filter((t) => now - t < this.windowMs);
    return { current: this.timestamps.length, max: this.maxRequests };
  }
}

/**
 * Run async tasks with limited concurrency.
 * Processes items from the array with at most `concurrency` tasks running at once.
 */
export async function runWithConcurrency<T, R>(
  items: T[],
  concurrency: number,
  fn: (item: T) => Promise<R>
): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let index = 0;

  async function worker(): Promise<void> {
    while (true) {
      const i = index++;
      if (i >= items.length) return;
      results[i] = await fn(items[i]);
    }
  }

  const workers = Array.from(
    { length: Math.min(concurrency, items.length) },
    () => worker()
  );

  await Promise.all(workers);
  return results;
}