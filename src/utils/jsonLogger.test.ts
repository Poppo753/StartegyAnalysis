import { jsonLog, jsonInfo, jsonWarn, jsonError, jsonLogger } from './jsonLogger';

describe('jsonLogger', () => {
  let writeSpy: jest.SpyInstance;
  let lines: string[];

  beforeEach(() => {
    lines = [];
    writeSpy = jest.spyOn(process.stderr, 'write').mockImplementation((chunk: any) => {
      lines.push(String(chunk));
      return true;
    });
    delete process.env.LOG_LEVEL;
    delete process.env.DEBUG;
  });

  afterEach(() => {
    writeSpy.mockRestore();
    delete process.env.LOG_LEVEL;
    delete process.env.DEBUG;
  });

  it('emits single-line JSON with timestamp/level/service/message/meta', () => {
    jsonInfo('hello', { symbol: 'BTCUSDT' });
    expect(lines).toHaveLength(1);
    const entry = JSON.parse(lines[0]);
    expect(entry.level).toBe('info');
    expect(entry.message).toBe('hello');
    expect(entry.service).toBeDefined();
    expect(entry.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(entry.meta).toEqual({ symbol: 'BTCUSDT' });
  });

  it('defaults meta to {} and never throws on circular refs', () => {
    const circular: any = {};
    circular.self = circular;
    expect(() => jsonError('boom', circular)).not.toThrow();
    const entry = JSON.parse(lines[0]);
    expect(entry.level).toBe('error');
    expect(entry.meta).toBeDefined();
  });

  it('respects LOG_LEVEL filtering', () => {
    process.env.LOG_LEVEL = 'warn';
    jsonInfo('suppressed');
    jsonWarn('kept');
    expect(lines).toHaveLength(1);
    expect(JSON.parse(lines[0]).level).toBe('warn');
  });

  it('exposes object API used by logger.json.*', () => {
    jsonLogger.warn('via-object', { k: 1 });
    expect(lines).toHaveLength(1);
    expect(JSON.parse(lines[0]).message).toBe('via-object');
  });

  it('jsonLog validates level ordering debug<info<warn<error', () => {
    process.env.LOG_LEVEL = 'error';
    jsonLog('debug', 'no');
    jsonLog('info', 'no');
    jsonLog('warn', 'no');
    jsonLog('error', 'yes');
    expect(lines).toHaveLength(1);
    expect(JSON.parse(lines[0]).level).toBe('error');
  });
});
