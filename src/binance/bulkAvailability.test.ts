import axios from 'axios';
import { checkBulkAvailability } from './bulkAvailability';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

function xmlWithKeys(keys: string[]): string {
  const entries = keys.map((k) => `<Contents><Key>${k}</Key></Contents>`).join('');
  return `<?xml version="1.0" encoding="UTF-8"?><ListBucketResult>${entries}</ListBucketResult>`;
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe('checkBulkAvailability', () => {
  it('valid XML: rileva i giorni presenti e ignora gli assenti', async () => {
    const symbol = 'BTCUSDT';
    const days = ['2024-01-01', '2024-01-02', '2024-01-03'];
    (mockedAxios.get as jest.Mock).mockResolvedValue({
      data: xmlWithKeys([
        `data/spot/daily/aggTrades/${symbol}/${symbol}-aggTrades-2024-01-01.zip`,
        `data/spot/daily/aggTrades/${symbol}/${symbol}-aggTrades-2024-01-02.zip`,
      ]),
    });

    const available = await checkBulkAvailability(symbol, days);

    expect(available.has('2024-01-01')).toBe(true);
    expect(available.has('2024-01-02')).toBe(true);
    expect(available.has('2024-01-03')).toBe(false);
    expect(available.size).toBe(2);
  });

  it('malformed XML: nessun match, fallback vuoto senza throw', async () => {
    (mockedAxios.get as jest.Mock).mockResolvedValue({ data: '<Invalid><xml' });

    const available = await checkBulkAvailability('BTCUSDT', ['2024-01-01']);

    expect(available.size).toBe(0);
  });

  it('empty listing: zero giorni disponibili', async () => {
    (mockedAxios.get as jest.Mock).mockResolvedValue({
      data: '<?xml version="1.0" encoding="UTF-8"?><ListBucketResult><Name>data.binance.vision</Name><IsTruncated>false</IsTruncated></ListBucketResult>',
    });

    const available = await checkBulkAvailability('BTCUSDT', ['2024-01-01', '2024-01-02']);

    expect(available.size).toBe(0);
  });

  it('axios timeout: fallback graceful a REST (set vuoto, nessun throw)', async () => {
    const timeoutErr = new Error('timeout of 15000ms exceeded') as Error & { code: string };
    timeoutErr.code = 'ECONNABORTED';
    (mockedAxios.get as jest.Mock).mockRejectedValue(timeoutErr);

    const available = await checkBulkAvailability('BTCUSDT', ['2024-01-01']);

    expect(available.size).toBe(0);
  });

  it('month listing near max-keys=100: 31 giorni daily tutti rilevati (nessun troncamento)', async () => {
    const symbol = 'BTCUSDT';
    const days: string[] = [];
    for (let d = 1; d <= 31; d++) {
      days.push(`2024-01-${String(d).padStart(2, '0')}`);
    }
    const keys = days.map(
      (day) => `data/spot/daily/aggTrades/${symbol}/${symbol}-aggTrades-${day}.zip`
    );
    (mockedAxios.get as jest.Mock).mockResolvedValue({ data: xmlWithKeys(keys) });

    const available = await checkBulkAvailability(symbol, days);

    expect(available.size).toBe(31);
    for (const day of days) {
      expect(available.has(day)).toBe(true);
    }
    // Verifica che la richiesta usi max-keys=100 (daily: max 31 file/mese, nessun troncamento atteso).
    expect(mockedAxios.get).toHaveBeenCalledTimes(1);
    const calledUrl = (mockedAxios.get as jest.Mock).mock.calls[0][0] as string;
    expect(calledUrl).toContain('max-keys=100');
  });
});
