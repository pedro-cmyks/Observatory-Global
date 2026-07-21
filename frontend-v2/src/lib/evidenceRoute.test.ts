import { describe, expect, it } from 'vitest'
import { buildEvidenceRoute } from './evidenceRoute'

describe('Evidence Route breadcrumb builder (#173)', () => {
  it('builds the full funnel Country -> Source Mix -> Atlas Topics -> Narrative Threads -> Evidence Signals', () => {
    const steps = buildEvidenceRoute({
      countryName: 'Colombia',
      outletCount: 34,
      foreignSourcePct: 18,
      atlasTopicCount: 12,
      narrativeThreadCount: 5,
      evidenceSignalCount: 1240,
    })

    expect(steps.map(s => s.key)).toEqual([
      'country',
      'sources',
      'topics',
      'threads',
      'signals',
    ])
    expect(steps.map(s => s.label)).toEqual([
      'Colombia',
      'Source Mix',
      'Atlas Topics',
      'Narrative Threads',
      'Evidence Signals',
    ])
    expect(steps.map(s => s.count)).toEqual([null, 34, 12, 5, 1240])
  })

  it('carries each real count from the payload — no fabrication', () => {
    const steps = buildEvidenceRoute({
      countryName: 'Peru',
      outletCount: 7,
      atlasTopicCount: 3,
      narrativeThreadCount: 1,
      evidenceSignalCount: 43,
    })
    const byKey = Object.fromEntries(steps.map(s => [s.key, s.count]))
    expect(byKey.sources).toBe(7)
    expect(byKey.topics).toBe(3)
    expect(byKey.threads).toBe(1)
    expect(byKey.signals).toBe(43)
  })

  it('shows the % foreign detail only when the payload carries it', () => {
    const withPct = buildEvidenceRoute({ countryName: 'Iran', foreignSourcePct: 96 })
    expect(withPct.find(s => s.key === 'sources')?.detail).toBe('96% foreign')

    const withoutPct = buildEvidenceRoute({ countryName: 'Iran' })
    expect(withoutPct.find(s => s.key === 'sources')?.detail).toBeNull()
  })

  it('renders an absent count as null (-> "—"), never a fabricated 0-that-looks-real', () => {
    const steps = buildEvidenceRoute({
      countryName: 'Somalia',
      outletCount: null,
      atlasTopicCount: undefined,
      narrativeThreadCount: null,
      evidenceSignalCount: 0,
    })
    const byKey = Object.fromEntries(steps.map(s => [s.key, s.count]))
    expect(byKey.sources).toBeNull()
    expect(byKey.topics).toBeNull()
    expect(byKey.threads).toBeNull()
    // 0 is a real measured value, not absence — it is kept.
    expect(byKey.signals).toBe(0)
  })

  it('the country step has no count and points at the header', () => {
    const [country] = buildEvidenceRoute({ countryName: 'Brazil', evidenceSignalCount: 10 })
    expect(country.count).toBeNull()
    expect(country.detail).toBeNull()
    expect(country.targetId).toBe('cb-header')
  })

  it('gives every step a scroll target', () => {
    const steps = buildEvidenceRoute({ countryName: 'Nigeria' })
    expect(steps.map(s => s.targetId)).toEqual([
      'cb-header',
      'cb-sources',
      'cb-threads',
      'cb-threads',
      'cb-signals',
    ])
  })

  it('rounds fractional counts (defensive against float inputs)', () => {
    const steps = buildEvidenceRoute({
      countryName: 'Chile',
      foreignSourcePct: 18.6,
      outletCount: 12,
    })
    expect(steps.find(s => s.key === 'sources')?.detail).toBe('19% foreign')
  })
})
