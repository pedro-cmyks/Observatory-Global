import { describe, it, expect } from 'vitest'
import {
  parseHealthPayload,
  platformLiveness,
  livenessIsStale,
  formatLagBehind,
  LIVENESS_MAX_AGE_MS,
  type HealthEvidence,
} from './platformLiveness'

const healthyPayload = {
  status: 'healthy',
  db_ok: true,
  timestamp: '2026-08-13T18:00:00+00:00',
  last_ingest_ts: '2026-08-13T17:58:00+00:00',
  ingest_lag_minutes: 2.0,
  rows_ingested_last_15m: 412,
  total_signals: 1200000,
  error_count_last_15m: 0,
}

describe('parseHealthPayload', () => {
  it('reads the two ingest fields from a healthy payload', () => {
    const ev = parseHealthPayload(healthyPayload)
    expect(ev).not.toBeNull()
    expect(ev!.rowsIngestedLast15m).toBe(412)
    expect(ev!.ingestLagMinutes).toBe(2.0)
    expect(ev!.measurementFailed).toBe(false)
  })

  it('flags a fallback payload (message present) as a failed measurement, not data', () => {
    const ev = parseHealthPayload({
      status: 'degraded',
      db_ok: true,
      message: 'pool busy',
      ingest_lag_minutes: null,
      rows_ingested_last_15m: 0,
    })
    expect(ev).not.toBeNull()
    expect(ev!.measurementFailed).toBe(true)
  })

  it('keeps a measured null lag as null (older than the measurement window)', () => {
    const ev = parseHealthPayload({
      status: 'degraded',
      db_ok: true,
      ingest_lag_minutes: null,
      rows_ingested_last_15m: 0,
    })
    expect(ev).not.toBeNull()
    expect(ev!.ingestLagMinutes).toBeNull()
    expect(ev!.measurementFailed).toBe(false)
  })

  it('rejects a body that is not an object', () => {
    expect(parseHealthPayload(null)).toBeNull()
    expect(parseHealthPayload('ok')).toBeNull()
    expect(parseHealthPayload(42)).toBeNull()
  })

  it('rejects a body missing the rows field — broken contract is not evidence', () => {
    expect(parseHealthPayload({ status: 'healthy', ingest_lag_minutes: 2 })).toBeNull()
  })

  it('treats a non-numeric lag as null rather than coercing garbage', () => {
    const ev = parseHealthPayload({ ...healthyPayload, ingest_lag_minutes: '--' })
    expect(ev).not.toBeNull()
    expect(ev!.ingestLagMinutes).toBeNull()
  })
})

describe('platformLiveness', () => {
  const served = (over: Partial<HealthEvidence>): HealthEvidence => ({
    ingestLagMinutes: 2,
    rowsIngestedLast15m: 400,
    measurementFailed: false,
    ...over,
  })

  it('pending: first paint never asserts live', () => {
    const s = platformLiveness('pending', null)
    expect(s.claimsLive).toBe(false)
    expect(s.tone).toBe('checking')
    expect(s.pillText).toBe('DATA · CHECKING')
  })

  it('unanswered: health unreachable → STATUS UNKNOWN, never live', () => {
    const s = platformLiveness('unanswered', null)
    expect(s.claimsLive).toBe(false)
    expect(s.tone).toBe('unknown')
    expect(s.pillText).toBe('STATUS UNKNOWN')
    expect(s.tip).toMatch(/did not answer/i)
  })

  it('served with no parseable evidence is unknown, not live (defensive)', () => {
    const s = platformLiveness('served', null)
    expect(s.claimsLive).toBe(false)
    expect(s.tone).toBe('unknown')
  })

  it('a fallback measurement (pool busy / error) is unknown, not "behind"', () => {
    const s = platformLiveness('served', served({ measurementFailed: true, ingestLagMinutes: null, rowsIngestedLast15m: 0 }))
    expect(s.claimsLive).toBe(false)
    expect(s.tone).toBe('unknown')
    expect(s.pillText).toBe('STATUS UNKNOWN')
    expect(s.tip).toMatch(/could not measure/i)
  })

  it('rows in the last 15m → the only LIVE branch, and the tip carries the number', () => {
    const s = platformLiveness('served', served({ rowsIngestedLast15m: 412 }))
    expect(s.claimsLive).toBe(true)
    expect(s.tone).toBe('live')
    expect(s.pillText).toBe('LIVE DATA')
    expect(s.tip).toContain('412')
  })

  it('zero rows with a finite lag → DATA · Nm BEHIND', () => {
    const s = platformLiveness('served', served({ rowsIngestedLast15m: 0, ingestLagMinutes: 38.2 }))
    expect(s.claimsLive).toBe(false)
    expect(s.tone).toBe('behind')
    expect(s.pillText).toBe('DATA · 38M BEHIND')
    expect(s.tip).toMatch(/38m/i)
  })

  it('lag over an hour renders in hours', () => {
    const s = platformLiveness('served', served({ rowsIngestedLast15m: 0, ingestLagMinutes: 95 }))
    expect(s.pillText).toBe('DATA · 1H BEHIND')
  })

  it('a measured null lag means older than the 2h measurement window', () => {
    const s = platformLiveness('served', served({ rowsIngestedLast15m: 0, ingestLagMinutes: null }))
    expect(s.claimsLive).toBe(false)
    expect(s.tone).toBe('behind')
    expect(s.pillText).toBe('DATA · >2H BEHIND')
  })

  it('claimsLive is true in exactly one branch across the state space', () => {
    const evidences: (HealthEvidence | null)[] = [
      null,
      served({}),
      served({ rowsIngestedLast15m: 0, ingestLagMinutes: 30 }),
      served({ rowsIngestedLast15m: 0, ingestLagMinutes: null }),
      served({ measurementFailed: true }),
    ]
    const lanes = ['pending', 'unanswered', 'served'] as const
    let liveCount = 0
    for (const lane of lanes) {
      for (const ev of evidences) {
        const s = platformLiveness(lane, ev)
        if (s.claimsLive) {
          liveCount++
          // The live branch requires served + measured + rows.
          expect(lane).toBe('served')
          expect(ev!.measurementFailed).toBe(false)
          expect(ev!.rowsIngestedLast15m).toBeGreaterThan(0)
        }
      }
    }
    // served × [served({}), served({measurementFailed:true — rows>0 but failed})]
    // Only the measured one may claim live.
    expect(liveCount).toBe(1)
  })
})

describe('formatLagBehind', () => {
  it('rounds minutes under an hour', () => {
    expect(formatLagBehind(38.2)).toBe('38M')
  })
  it('crosses to hours at 60 after rounding', () => {
    expect(formatLagBehind(59.6)).toBe('1H')
    expect(formatLagBehind(125)).toBe('2H')
  })
  it('clamps negatives to zero rather than inventing time travel', () => {
    expect(formatLagBehind(-3)).toBe('0M')
  })
})

describe('livenessIsStale', () => {
  it('never-fetched is stale', () => {
    expect(livenessIsStale(null, 1000)).toBe(true)
  })
  it('fresh within the max age is not stale', () => {
    expect(livenessIsStale(1000, 1000 + LIVENESS_MAX_AGE_MS - 1)).toBe(false)
  })
  it('at or past the max age is stale', () => {
    expect(livenessIsStale(1000, 1000 + LIVENESS_MAX_AGE_MS)).toBe(true)
  })
})
