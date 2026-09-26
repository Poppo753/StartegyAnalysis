/**
 * jsonLogger.ts — Structured JSON logging for machine-readable output.
 *
 * Human-readable logs stay on `logger` (console with timestamps).
 * JSON logs go to stderr as single-line JSON objects, compatible
 * with ELK / Splunk / CloudWatch / jq.
 *
 * Format:
 *   {"timestamp":"2026-01-01T00:00:00.000Z","level":"info","service":"ohlc-pipeline","message":"...","meta":{...}}
 *
 * Design decisions:
 * - stderr (not stdout) so piped CSV/JSONL data on stdout is never polluted.
 * - `meta` defaults to {} and must be JSON-serializable; circular refs are
 *   guarded with a safe-stringify fallback.
 * - Level filtering via LOG_LEVEL env (debug < info < warn < error). Default: info.
 *   DEBUG=true legacy flag still enables debug level.
 */

export type JsonLogLevel = 'debug' | 'info' | 'warn' | 'error';

const SERVICE = process.env.LOG_SERVICE || 'ohlc-pipeline';

const LEVEL_ORDER: Record<JsonLogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
};

function activeLevel(): JsonLogLevel {
  const raw = (process.env.LOG_LEVEL || '').toLowerCase();
  if (raw === 'debug' || raw === 'info' || raw === 'warn' || raw === 'error') {
    return raw;
  }
  if (process.env.DEBUG === 'true') return 'debug';
  return 'info';
}

function shouldEmit(level: JsonLogLevel): boolean {
  return LEVEL_ORDER[level] >= LEVEL_ORDER[activeLevel()];
}

function safeMeta(meta: unknown): object {
  if (meta === undefined || meta === null) return {};
  if (typeof meta === 'object') return meta as object;
  return { value: meta };
}

export function jsonLog(level: JsonLogLevel, message: string, meta?: unknown): void {
  if (!shouldEmit(level)) return;
  const entry = {
    timestamp: new Date().toISOString(),
    level,
    service: SERVICE,
    message,
    meta: safeMeta(meta),
  };
  let line: string;
  try {
    line = JSON.stringify(entry);
  } catch {
    // Circular reference fallback — never crash the pipeline for logging.
    line = JSON.stringify({
      ...entry,
      meta: { stringifyError: 'non-serializable meta' },
    });
  }
  process.stderr.write(line + '\n');
}

export function jsonDebug(message: string, meta?: unknown): void {
  jsonLog('debug', message, meta);
}

export function jsonInfo(message: string, meta?: unknown): void {
  jsonLog('info', message, meta);
}

export function jsonWarn(message: string, meta?: unknown): void {
  jsonLog('warn', message, meta);
}

export function jsonError(message: string, meta?: unknown): void {
  jsonLog('error', message, meta);
}

/** Object-style API used by `logger.json.*`. */
export const jsonLogger = {
  log: jsonLog,
  debug: jsonDebug,
  info: jsonInfo,
  warn: jsonWarn,
  error: jsonError,
};
