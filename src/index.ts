import { loadConfig } from './config/config';
import { runPipeline } from './pipeline/runPipeline';
import { logger } from './utils/logger';

async function main(): Promise<void> {
  try {
    logger.info('Binance OHLC Pipeline - Starting...');

    const config = loadConfig();
    await runPipeline(config);

    logger.info('Pipeline completed successfully.');
    process.exit(0);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    logger.error(`Fatal error: ${message}`);
    process.exit(1);
  }
}

main();