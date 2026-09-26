import { GlobalRateLimiter, delay, runWithConcurrency } from './rateLimiter';

describe('delay', () => {
  it('should resolve after the specified time', async () => {
    const start = Date.now();
    await delay(50);
    const elapsed = Date.now() - start;
    expect(elapsed).toBeGreaterThanOrEqual(45);
    expect(elapsed).toBeLessThan(100);
  });
});

describe('GlobalRateLimiter', () => {
  jest.setTimeout(70000);

  it('should allow requests up to the max limit', async () => {
    const limiter = new GlobalRateLimiter(5);
    await Promise.all([limiter.acquire(), limiter.acquire(), limiter.acquire()]);
    expect(limiter.getUsage().current).toBeLessThanOrEqual(5);
  });

  it('should throttle requests exceeding the max limit', async () => {
    const limiter = new GlobalRateLimiter(2);
    await limiter.acquire();
    await limiter.acquire();
    const start = Date.now();
    await limiter.acquire();
    const elapsed = Date.now() - start;
    expect(elapsed).toBeGreaterThanOrEqual(50);
  });

  it('should return usage info', () => {
    const limiter = new GlobalRateLimiter(100);
    const usage = limiter.getUsage();
    expect(usage.max).toBe(100);
    expect(usage.current).toBeGreaterThanOrEqual(0);
  });
});

describe('runWithConcurrency', () => {
  it('should execute all items with limited concurrency', async () => {
    const results = await runWithConcurrency([1, 2, 3, 4, 5], 2, async (x) => x * 2);
    expect(results).toEqual([2, 4, 6, 8, 10]);
  });

  it('should handle empty array', async () => {
    const results = await runWithConcurrency([], 2, async (x) => x);
    expect(results).toEqual([]);
  });
});
