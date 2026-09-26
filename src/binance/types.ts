/**
 * Binance Aggregate Trade response object.
 * Docs: https://binance-docs.github.io/apidocs/spot/en/#compressed-aggregate-trades-list
 */
export interface BinanceAggTrade {
  a: number;   // Aggregate trade ID
  p: string;   // Price
  q: string;   // Quantity
  f: number;   // First trade ID
  l: number;   // Last trade ID
  T: number;   // Timestamp in milliseconds
  m: boolean;  // Was the buyer the maker?
  M: boolean;  // Was the trade the best price match?
}

/**
 * OHLCV candle at 1-second resolution.
 */
export interface OhlcCandle {
  timestamp: string;   // ISO 8601 format
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  tradeCount: number;
}

/**
 * Parameters for the aggTrades endpoint.
 */
export interface AggTradesParams {
  symbol: string;
  startTime?: number;
  endTime?: number;
  fromId?: number;
  limit?: number;
}