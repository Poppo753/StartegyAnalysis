/**
 * Convert a date string (YYYY-MM-DD) to UTC timestamp in milliseconds.
 */
export function dateToTimestampMs(dateStr: string): number {
  const date = new Date(`${dateStr}T00:00:00.000Z`);
  if (isNaN(date.getTime())) {
    throw new Error(`Invalid date string: ${dateStr}`);
  }
  return date.getTime();
}

/**
 * Format a timestamp (ms) as ISO 8601 string.
 */
export function timestampMsToIso(timestampMs: number): string {
  return new Date(timestampMs).toISOString();
}

/**
 * Format a timestamp (ms) as YYYY-MM-DD string.
 */
export function timestampMsToDate(timestampMs: number): string {
  return new Date(timestampMs).toISOString().split('T')[0];
}

/**
 * Get the start of a second (floor to nearest second) from a ms timestamp.
 */
export function floorToSecond(timestampMs: number): number {
  return Math.floor(timestampMs / 1000) * 1000;
}

/**
 * Split a date range into individual days.
 * Returns array of { start: 'YYYY-MM-DD', end: 'YYYY-MM-DD' } pairs
 * where end is the next day (exclusive).
 */
export function splitIntoDays(
  startDate: string,
  endDate: string
): Array<{ start: string; end: string }> {
  const days: Array<{ start: string; end: string }> = [];
  const endMs = dateToTimestampMs(endDate);
  let currentMs = dateToTimestampMs(startDate);

  while (currentMs < endMs) {
    const nextDayMs = currentMs + 24 * 60 * 60 * 1000;
    const effectiveEnd = Math.min(nextDayMs, endMs);

    days.push({
      start: timestampMsToDate(currentMs),
      end: timestampMsToDate(effectiveEnd),
    });

    currentMs = nextDayMs;
  }

  return days;
}