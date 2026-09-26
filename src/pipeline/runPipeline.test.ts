import { AppConfig } from '../config/config';
import { downloadAggTrades } from './downloadAggTrades';
import { runPipeline } from './runPipeline';

jest.mock('./downloadAggTrades', () => ({ downloadAggTrades: jest.fn() }));

it('rejects when a symbol download fails instead of reporting success', async () => {
  jest.mocked(downloadAggTrades).mockRejectedValueOnce(new Error('download failed'));
  const config = {
    symbols: ['BTCUSDT'],
    startDate: '2026-01-01',
    endDate: '2026-01-02',
    outputDir: 'unused',
    maxRequestsPerMinute: 60,
    requestDelayMs: 0,
    concurrentDays: 1,
    concurrentBulkDownloads: 1,
    binanceBaseUrl: 'https://example.invalid',
    useGzip: false,
    jsonLogging: false,
  } as AppConfig;

  await expect(runPipeline(config, { timeframes: ['1s'] })).rejects.toThrow(
    'Pipeline failed for 1 of 1 symbol(s)'
  );
});
