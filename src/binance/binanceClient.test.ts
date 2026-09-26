import axios from 'axios';
import { BinanceClient } from './binanceClient';
import { GlobalRateLimiter } from '../utils/rateLimiter';

jest.mock('axios');
jest.mock('../utils/rateLimiter', () => {
  const actual = jest.requireActual('../utils/rateLimiter');
  return {
    ...actual,
    delay: jest.fn().mockResolvedValue(undefined),
  };
});

const mockedAxios = axios as jest.Mocked<typeof axios>;

function axiosErrorWithStatus(status: number) {
  const err = new Error(`Request failed with status code ${status}`) as Error & {
    response: { status: number };
  };
  err.response = { status };
  return err;
}

describe('BinanceClient.getAggTrades retry semantics', () => {
  let mockGet: jest.Mock;

  beforeEach(() => {
    mockGet = jest.fn();
    (mockedAxios.create as jest.Mock).mockReturnValue({ get: mockGet });
    jest.clearAllMocks();
    // re-apply create mock after clearAllMocks
    (mockedAxios.create as jest.Mock).mockReturnValue({ get: mockGet });
  });

  function makeClient() {
    return new BinanceClient('https://example.com', 0, new GlobalRateLimiter(10000));
  }

  it('(a) 429 then success → succeeds after 2 attempts', async () => {
    const trades = [{ a: 1, p: '100', q: '1', f: 1, l: 1, T: 1700000000000, m: false, M: true }];
    mockGet.mockRejectedValueOnce(axiosErrorWithStatus(429)).mockResolvedValueOnce({ data: trades });

    const client = makeClient();
    const result = await client.getAggTrades({ symbol: 'BTCUSDT' });

    expect(result).toEqual(trades);
    expect(mockGet).toHaveBeenCalledTimes(2);
  });

  it('(b) persistent 500 → throws after exhaustion (1 + 5 attempts)', async () => {
    mockGet.mockRejectedValue(axiosErrorWithStatus(500));

    const client = makeClient();
    await expect(client.getAggTrades({ symbol: 'BTCUSDT' })).rejects.toThrow();

    // total attempts = 1 + MAX_RETRIES (5) = 6
    expect(mockGet).toHaveBeenCalledTimes(6);
  });

  it('(c) non-retryable 4xx → immediate throw, no retry', async () => {
    mockGet.mockRejectedValue(axiosErrorWithStatus(400));

    const client = makeClient();
    await expect(client.getAggTrades({ symbol: 'BTCUSDT' })).rejects.toThrow();

    expect(mockGet).toHaveBeenCalledTimes(1);
  });
});
