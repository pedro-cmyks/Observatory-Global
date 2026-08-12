import { describe, it, expect } from 'vitest'
import {
  COVERAGE_START_MAX_AGE_MS,
  coverageStartIsStale,
  coverageStartLabel,
  formatCoverageStart,
  parseSignalTimestamp,
} from './dataCoverageStart'

// Cold-user probe 2026-08-12 §4: `FROM 9 AUG 2026` on desktop, `FROM 5 AUG 2026`
// on mobile, same site, same moment, ONE renderer.
describe('parseSignalTimestamp', () => {
  it('reads an offset-less timestamp as UTC, not as device-local time', () => {
    // The ±1-day device split: parsed as local, this lands on Aug 4 west of UTC.
    const dt = parseSignalTimestamp('2026-08-05T00:30:00')
    expect(dt?.toISOString()).toBe('2026-08-05T00:30:00.000Z')
  })

  it('respects an explicit Z', () => {
    expect(parseSignalTimestamp('2026-08-05T10:10:14+00:00')?.toISOString()).toBe(
      '2026-08-05T10:10:14.000Z',
    )
  })

  it('respects a non-UTC offset instead of forcing UTC onto it', () => {
    expect(parseSignalTimestamp('2026-08-05T12:00:00+02:00')?.toISOString()).toBe(
      '2026-08-05T10:00:00.000Z',
    )
  })

  it('accepts a space-separated Postgres rendering', () => {
    expect(parseSignalTimestamp('2026-08-05 10:10:14')?.toISOString()).toBe(
      '2026-08-05T10:10:14.000Z',
    )
  })

  it('returns null for junk rather than an Invalid Date', () => {
    expect(parseSignalTimestamp('not a date')).toBeNull()
    expect(parseSignalTimestamp(null)).toBeNull()
    expect(parseSignalTimestamp(undefined)).toBeNull()
    expect(parseSignalTimestamp('')).toBeNull()
    expect(parseSignalTimestamp(12345)).toBeNull()
  })
})

describe('formatCoverageStart', () => {
  it('formats in UTC so two devices print the same day', () => {
    // 23:30 UTC is already "the next day" east of UTC and "the same day" west.
    const dt = new Date('2026-08-05T23:30:00Z')
    expect(formatCoverageStart(dt)).toBe('5 Aug 2026')
  })

  it('returns null for a missing or invalid date', () => {
    expect(formatCoverageStart(null)).toBeNull()
    expect(formatCoverageStart(new Date('nope'))).toBeNull()
  })

  it('coverageStartLabel composes parse + format end to end', () => {
    expect(coverageStartLabel('2026-08-05T10:10:14+00:00')).toBe('5 Aug 2026')
    expect(coverageStartLabel('garbage')).toBeNull()
  })
})

describe('coverageStartIsStale', () => {
  const now = 1_800_000_000_000

  it('treats a never-fetched value as stale', () => {
    expect(coverageStartIsStale(null, now)).toBe(true)
  })

  it('keeps a freshly fetched value', () => {
    expect(coverageStartIsStale(now - 1000, now)).toBe(false)
  })

  it('expires a value older than the max age', () => {
    expect(coverageStartIsStale(now - COVERAGE_START_MAX_AGE_MS - 1, now)).toBe(true)
  })

  it('expires the multi-day PWA session that caused the bug', () => {
    const fourDays = 4 * 24 * 60 * 60 * 1000
    expect(coverageStartIsStale(now - fourDays, now)).toBe(true)
  })
})
