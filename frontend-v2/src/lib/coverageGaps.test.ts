import { describe, it, expect } from 'vitest'
import {
  coverageGapsUrl,
  maxGapRaw,
  parseCoverageGaps,
  type CoverageGap,
} from './coverageGaps'

const GAP: CoverageGap = {
  slug: 'telecom-shutdown',
  label: 'Telecom or internet shutdown',
  raw_signals: 280,
  verified: 0,
  scored: 280,
  status: 'none_verified',
  extended_receipts: [],
}

describe('coverageGapsUrl', () => {
  it('omits country when global', () => {
    expect(coverageGapsUrl(null, 24)).toBe('/api/v2/attention/coverage-gaps?hours=24')
  })

  it('includes country when scoped', () => {
    expect(coverageGapsUrl('CO', 24)).toBe('/api/v2/attention/coverage-gaps?country=CO&hours=24')
  })
})

describe('parseCoverageGaps', () => {
  it('accepts the v0 contract', () => {
    const parsed = parseCoverageGaps({
      contract: 'coverage-gaps-v0', scope: 'global', country: null, hours: 24,
      status: 'ok', floor: 20, gaps: [GAP],
    })
    expect(parsed?.gaps).toHaveLength(1)
    expect(parsed?.scope).toBe('global')
    expect(parsed?.status).toBe('ok')
    expect(parsed?.floor).toBe(20)
  })

  it('rejects a foreign contract', () => {
    expect(parseCoverageGaps({ contract: 'something-else', gaps: [GAP] })).toBeNull()
  })

  it('rejects null / non-object payloads', () => {
    expect(parseCoverageGaps(null)).toBeNull()
    expect(parseCoverageGaps('nope')).toBeNull()
  })

  it('defaults a missing gaps array to empty', () => {
    const parsed = parseCoverageGaps({ contract: 'coverage-gaps-v0', scope: 'global' })
    expect(parsed?.gaps).toEqual([])
  })

  it('carries an explicit empty status through', () => {
    const parsed = parseCoverageGaps({
      contract: 'coverage-gaps-v0', scope: 'country', country: 'CO',
      status: 'empty', floor: 8, gaps: [],
    })
    expect(parsed?.status).toBe('empty')
    expect(parsed?.floor).toBe(8)
  })

  it('carries a degraded status through', () => {
    const parsed = parseCoverageGaps({
      contract: 'coverage-gaps-v0', scope: 'global', status: 'degraded', gaps: [],
    })
    expect(parsed?.status).toBe('degraded')
    expect(parsed?.floor).toBeNull()
  })

  it('treats a missing status with no gaps as degraded, never as honest-empty', () => {
    const parsed = parseCoverageGaps({ contract: 'coverage-gaps-v0', scope: 'global', gaps: [] })
    expect(parsed?.status).toBe('degraded')
  })

  it('treats a missing status with gaps as ok', () => {
    const parsed = parseCoverageGaps({ contract: 'coverage-gaps-v0', scope: 'global', gaps: [GAP] })
    expect(parsed?.status).toBe('ok')
  })

  it('rejects an unknown status value rather than trusting it', () => {
    const parsed = parseCoverageGaps({
      contract: 'coverage-gaps-v0', scope: 'global', status: 'fine', gaps: [],
    })
    expect(parsed?.status).toBe('degraded')
  })
})

describe('maxGapRaw', () => {
  it('is at least 1 so the bar never divides by zero', () => {
    expect(maxGapRaw([])).toBe(1)
  })

  it('returns the largest raw count', () => {
    expect(maxGapRaw([GAP, { ...GAP, slug: 'b', raw_signals: 33 }])).toBe(280)
  })
})
