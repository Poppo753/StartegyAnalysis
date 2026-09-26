import { dateToTimestampMs, floorToSecond, splitIntoDays } from './dateUtils';

describe('dateToTimestampMs', () => {
  it('should convert YYYY-MM-DD to UTC timestamp in ms', () => {
    const result = dateToTimestampMs('2024-01-01');
    expect(result).toBe(new Date('2024-01-01T00:00:00.000Z').getTime());
  });

  it('should throw for invalid date', () => {
    expect(() => dateToTimestampMs('invalid')).toThrow();
  });
});

describe('floorToSecond', () => {
  it('should floor timestamp to nearest second', () => {
    expect(floorToSecond(1700000000500)).toBe(1700000000000);
    expect(floorToSecond(1700000000000)).toBe(1700000000000);
  });
});

describe('splitIntoDays', () => {
  it('should split a date range into individual days', () => {
    const days = splitIntoDays('2024-01-01', '2024-01-03');
    expect(days).toHaveLength(2);
    expect(days[0].start).toBe('2024-01-01');
    expect(days[1].start).toBe('2024-01-02');
  });
});
