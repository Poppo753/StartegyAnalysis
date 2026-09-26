import dotenv from 'dotenv';
import path from 'path';
import { loadConfig, AppConfig } from './config';

// Helper to set env vars for testing
function setEnv(vars: Record<string, string>) {
  for (const [key, value] of Object.entries(vars)) {
    process.env[key] = value;
  }
}

function clearEnv() {
  delete process.env.SYMBOLS;
  delete process.env.START_DATE;
  delete process.env.END_DATE;
  delete process.env.OUTPUT_DIR;
  delete process.env.BINANCE_BASE_URL;
  delete process.env.REQUEST_DELAY_MS;
  delete process.env.CONCURRENT_DAYS;
  delete process.env.CONCURRENT_BULK_DOWNLOADS;
  delete process.env.MAX_REQUESTS_PER_MINUTE;
}

afterEach(() => {
  clearEnv();
});

describe('loadConfig', () => {
  it('should load valid config', () => {
    setEnv({
      SYMBOLS: 'BTCUSDT,ETHUSDT',
      START_DATE: '2024-01-01',
      END_DATE: '2024-01-02',
      OUTPUT_DIR: './data',
    });
    const config = loadConfig();
    expect(config.symbols).toEqual(['BTCUSDT', 'ETHUSDT']);
    expect(config.startDate).toBe('2024-01-01');
  });

  it('should throw if SYMBOLS is missing', () => {
    setEnv({ START_DATE: '2024-01-01', END_DATE: '2024-01-02' });
    expect(() => loadConfig()).toThrow('Missing required environment variable: SYMBOLS');
  });

  it('should throw if dates are invalid', () => {
    setEnv({ SYMBOLS: 'BTCUSDT', START_DATE: 'invalid', END_DATE: '2024-01-02' });
    expect(() => loadConfig()).toThrow('YYYY-MM-DD format');
  });

  it('should throw if START_DATE >= END_DATE', () => {
    setEnv({ SYMBOLS: 'BTCUSDT', START_DATE: '2024-01-02', END_DATE: '2024-01-01' });
    expect(() => loadConfig()).toThrow('START_DATE must be before END_DATE');
  });

  it('should use defaults for optional fields', () => {
    setEnv({ SYMBOLS: 'BTCUSDT', START_DATE: '2024-01-01', END_DATE: '2024-01-02' });
    const config = loadConfig();
    expect(config.outputDir).toBe(path.resolve('./data'));
  });
});
