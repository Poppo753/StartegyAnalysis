import { jsonLogger } from './jsonLogger';

/**
 * Simple console logger with timestamps and log levels.
 * Human-readable on stdout/stderr; structured JSON via `logger.json.*` on stderr.
 */
export const logger = {
  info(message: string): void {
    if (process.env.JSON_LOGGING === 'true') {
      jsonLogger.info(message);
      return;
    }
    console.log(`[${timestamp()}] [INFO]  ${message}`);
  },

  warn(message: string): void {
    if (process.env.JSON_LOGGING === 'true') {
      jsonLogger.warn(message);
      return;
    }
    console.warn(`[${timestamp()}] [WARN]  ${message}`);
  },

  error(message: string): void {
    if (process.env.JSON_LOGGING === 'true') {
      jsonLogger.error(message);
      return;
    }
    console.error(`[${timestamp()}] [ERROR] ${message}`);
  },

  debug(message: string): void {
    if (process.env.DEBUG === 'true') {
      console.debug(`[${timestamp()}] [DEBUG] ${message}`);
    }
  },

  json: {
    info(message: string, meta?: object): void {
      jsonLogger.info(message, meta);
    },
    warn(message: string, meta?: object): void {
      jsonLogger.warn(message, meta);
    },
    error(message: string, meta?: object): void {
      jsonLogger.error(message, meta);
    },
  },
};

function timestamp(): string {
  return new Date().toISOString();
}
