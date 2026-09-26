import { loadConfig } from './config/config';
import { parseTimeframesArgv, runPipeline } from './pipeline/runPipeline';
import { logger } from './utils/logger';

async function main(): Promise<void> {
  try {
    logger.info('Binance OHLC Pipeline - Starting...');

    const config = loadConfig();
    const timeframes = parseTimeframesArgv();
    await runPipeline(config, { timeframes });

    logger.info('Pipeline completed successfully.');
    process.exit(0);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    logger.error(`Fatal error: ${message}`);
    process.exit(1);
  }
}

main();