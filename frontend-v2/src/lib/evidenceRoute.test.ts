import { describe, expect, it } from 'vitest'
import { buildEvidenceRoute } from './evidenceRoute'

describe('Evidence Route breadcrumb builder (#173)', () => {
  it('builds the full funnel Country -> Source Mix -> Atlas Topics -> Stories -> Evidence Signals', () => {
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
      'Stories',
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

import { buildPersonEvidenceRoute, buildSignalEvidenceRoute, buildSourceEvidenceRoute, buildTopicEvidenceRoute } from './evidenceRoute'

describe('cross-context Evidence Routes (#173, 2026-08-03)', () => {
  it('topic route: Thread -> Raw -> Gate-verified -> Countries -> Source Mix -> Evidence', () => {
    const steps = buildTopicEvidenceRoute({
      topicLabel: 'Ceuta Migration Crisis',
      rawAssignedCount: 502,
      verifiedCount: 347,
      countryCount: 9,
      outletCount: 22,
      sourcedEvidenceCount: 120,
    })
    expect(steps.map(s => s.key)).toEqual(['topic', 'raw', 'verified', 'countries', 'sources', 'signals'])
    expect(steps.map(s => s.count)).toEqual([null, 502, 347, 9, 22, 120])
    expect(steps.every(s => s.targetId.startsWith('td-'))).toBe(true)
  })

  it('topic route: missing rawTotal renders honest absence, never a fabricated number', () => {
    const steps = buildTopicEvidenceRoute({ topicLabel: 'X', verifiedCount: 10 })
    expect(steps.find(s => s.key === 'raw')?.count).toBeNull()
  })

  // X4 (2026-08-13) — blind college C5. "Raw assigned / Gate-verified" was a
  // named witness. The engine's terms stay as the step labels (the analyst
  // reads the funnel by them); the plain reading rides in the detail slot the
  // breadcrumb already renders, so each step says what its number MEANS.
  it('topic route: the two funnel steps say what they mean in plain words', () => {
    const steps = buildTopicEvidenceRoute({
      topicLabel: 'Ceuta Migration Crisis', rawAssignedCount: 502, verifiedCount: 347,
    })
    expect(steps.find(s => s.key === 'raw')?.detail).toBe('mentioned it')
    expect(steps.find(s => s.key === 'verified')?.detail).toBe('passed verification')
    // The technical labels survive — this is translation, not replacement.
    expect(steps.find(s => s.key === 'raw')?.label).toBe('Raw assigned')
    expect(steps.find(s => s.key === 'verified')?.label).toBe('Gate-verified')
  })

  it('person route includes the threads step only when the context measures it', () => {
    const person = buildPersonEvidenceRoute({
      personName: 'Malhar Jammu',
      signalCount: 6,
      countryCount: 2,
      threadCount: 3,
      keySubjectCount: 4,
    })
    expect(person.map(s => s.key)).toEqual(['person', 'signals', 'countries', 'threads', 'subjects'])
    expect(person.find(s => s.key === 'threads')?.count).toBe(3)

    const themeEntity = buildPersonEvidenceRoute({
      personName: 'water-stress',
      signalCount: 40,
      countryCount: 7,
      keySubjectCount: 5,
    })
    expect(themeEntity.map(s => s.key)).toEqual(['person', 'signals', 'countries', 'subjects'])
  })

  it('signal route carries the measured stream lane as the source-class detail', () => {
    const steps = buildSignalEvidenceRoute({
      lane: 'analyst',
      connectedThreadCount: 2,
      semanticNeighborCount: 8,
      gdeltThemeCount: 5,
    })
    expect(steps.map(s => s.key)).toEqual(['signal', 'threads', 'neighbors', 'taxonomy'])
    expect(steps[0].detail).toBe('analyst lane')
    expect(steps.map(s => s.count)).toEqual([null, 2, 8, 5])
  })

  it('signal route while context is still loading: counts are absent, not zero', () => {
    const steps = buildSignalEvidenceRoute({ gdeltThemeCount: 3 })
    expect(steps.find(s => s.key === 'threads')?.count).toBeNull()
    expect(steps.find(s => s.key === 'neighbors')?.count).toBeNull()
  })
})

describe('source Evidence Route (#173, 2026-08-11 — the fifth acceptance context)', () => {
  it('source route: Source (tier) -> Signals -> Countries -> Thematic Focus', () => {
    const steps = buildSourceEvidenceRoute({
      domain: 'russian.rt.com',
      tierLabel: 'STATE',
      signalCount: 481,
      countryCount: 34,
      themeCount: 8,
    })
    expect(steps.map(s => s.key)).toEqual(['source', 'signals', 'countries', 'themes'])
    expect(steps.map(s => s.count)).toEqual([null, 481, 34, 8])
    // the tier is the head chip's source-class fact — the acceptance's
    // "distinguish reporting / wire / state" requirement
    expect(steps[0].detail).toBe('STATE')
    expect(steps.every(s => s.targetId.startsWith('sp-'))).toBe(true)
  })

  it('source route while the profile is still loading: counts absent, never zero', () => {
    const steps = buildSourceEvidenceRoute({ domain: 'example.org', tierLabel: 'UNKNOWN' })
    expect(steps.find(s => s.key === 'signals')?.count).toBeNull()
    expect(steps.find(s => s.key === 'countries')?.count).toBeNull()
    expect(steps.find(s => s.key === 'themes')?.count).toBeNull()
  })
})
