/**
 * Unit tests for utility functions (Story 10-2)
 * TDD: Tests written first, then implementation
 */
import { formatCost, formatDate, formatDuration, formatStatus } from '../lib/utils';

describe('formatCost', () => {
  it('formats zero cost as €0.0000', () => {
    expect(formatCost(0)).toBe('€0.0000');
  });

  it('formats small costs in cents', () => {
    // 1000 micros = €0.001 = 0.1 cents
    expect(formatCost(1000)).toBe('€0.0010');
  });

  it('formats costs less than 1 cent', () => {
    // 5000 micros = €0.005
    expect(formatCost(5000)).toBe('€0.0050');
  });

  it('formats costs in euros for amounts >= 1 cent', () => {
    // 10000 micros = €0.01
    expect(formatCost(10000)).toBe('€0.0100');
  });

  it('formats whole euro amounts', () => {
    // 1000000 micros = €1
    expect(formatCost(1000000)).toBe('€1.0000');
  });

  it('formats typical execution cost', () => {
    // 50000 micros = €0.05
    expect(formatCost(50000)).toBe('€0.0500');
  });

  it('formats large costs correctly', () => {
    // 12345678 micros = €12.3457 (rounded)
    expect(formatCost(12345678)).toBe('€12.3457');
  });

  it('handles null/undefined gracefully', () => {
    expect(formatCost(null as unknown as number)).toBe('€0.0000');
    expect(formatCost(undefined as unknown as number)).toBe('€0.0000');
  });
});

describe('formatDate', () => {
  it('formats ISO date string to readable format', () => {
    const result = formatDate('2024-01-15T10:30:00Z');
    // Should include date parts
    expect(result).toMatch(/Jan|January/);
    expect(result).toMatch(/15/);
    expect(result).toMatch(/2024/);
  });

  it('handles null date', () => {
    expect(formatDate(null)).toBe('-');
  });

  it('handles undefined date', () => {
    expect(formatDate(undefined)).toBe('-');
  });

  it('handles empty string', () => {
    expect(formatDate('')).toBe('-');
  });
});

describe('formatDuration', () => {
  it('formats zero seconds', () => {
    expect(formatDuration(0)).toBe('0s');
  });

  it('formats seconds only', () => {
    expect(formatDuration(45)).toBe('45s');
  });

  it('formats minutes and seconds', () => {
    expect(formatDuration(90)).toBe('1m 30s');
  });

  it('formats hours, minutes, and seconds', () => {
    expect(formatDuration(3661)).toBe('1h 1m 1s');
  });

  it('formats sub-second durations', () => {
    expect(formatDuration(0.5)).toBe('<1s');
  });

  it('rounds to whole seconds', () => {
    expect(formatDuration(45.7)).toBe('46s');
  });

  it('handles null duration', () => {
    expect(formatDuration(null)).toBe('-');
  });

  it('handles undefined duration', () => {
    expect(formatDuration(undefined)).toBe('-');
  });

  it('formats large durations (hours)', () => {
    expect(formatDuration(7200)).toBe('2h 0m 0s');
  });
});

describe('formatStatus', () => {
  it('formats queued status', () => {
    const result = formatStatus('queued');
    expect(result.label).toBe('Queued');
    expect(result.className).toContain('yellow');
  });

  it('formats running status', () => {
    const result = formatStatus('running');
    expect(result.label).toBe('Running');
    expect(result.className).toContain('blue');
  });

  it('formats completed status', () => {
    const result = formatStatus('completed');
    expect(result.label).toBe('Completed');
    expect(result.className).toContain('green');
  });

  it('formats failed status', () => {
    const result = formatStatus('failed');
    expect(result.label).toBe('Failed');
    expect(result.className).toContain('red');
  });

  it('handles unknown status gracefully', () => {
    const result = formatStatus('unknown' as unknown as Parameters<typeof formatStatus>[0]);
    expect(result.label).toBe('Unknown');
    expect(result.className).toContain('gray');
  });
});
