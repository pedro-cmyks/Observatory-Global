import { describe, it, expect, vi, afterEach } from 'vitest'
import {
  resolveSourceCount,
  sourceCountClause,
  sourceCountTip,
  formatSourceCountWarning,
  logUnmeasuredSourceCount,
  UNMEASURED_SOURCES_LABEL,
  __resetSourceCountWarnings,
} from './briefSourceCount'

afterEach(() => {
  __resetSourceCountWarnings()
  vi.restoreAllMocks()
})

describe('resolveSourceCount', () => {
  it('returns null when the row carries no source_count at all (nothing renders)', () => {
    expect(resolveSourceCount({ thread_id: 'dynamic-topic-1', signal_count: 10 })).toBeNull()
    expect(
      resolveSourceCount({ thread_id: 'dynamic-topic-1', signal_count: 10, source_count: null }),
    ).toBeNull()
    expect(
      resolveSourceCount({ thread_id: 'dynamic-topic-1', signal_count: 10, source_count: undefined }),
    ).toBeNull()
  })

  it('reports a positive count as MEASURED', () => {
    const basis = resolveSourceCount({
      thread_id: 'dynamic-topic-12193',
      signal_count: 120,
      source_count: 22,
      evidence_samples: [{ headline: 'a', source: 'reuters.com' }],
    })
    // `population` rides along on every measured basis so the copy never has to
    // guess which sample the number came from (see the widening block below).
    expect(basis).toEqual({
      kind: 'measured', count: 22, population: 'receipt_sample', sampleSize: 1,
    })
  })

  // The witness: prod dynamic-topic-12138 served signal_count 116 / source_count 0
  // with an EMPTY receipt sample. "0 sources" was never a measurement — the
  // receipt lane returned nothing while the count lineage survived.
  it('never calls zero-with-no-receipts a measurement (the 116 / 0 witness)', () => {
    const basis = resolveSourceCount({
      thread_id: 'dynamic-topic-12138',
      signal_count: 116,
      source_count: 0,
      evidence_samples: [],
    })
    expect(basis).toEqual({
      kind: 'unmeasured',
      reason: 'no_receipts_carried',
      emptyField: 'evidence_samples',
    })
  })

  it('treats a missing evidence_samples field the same as an empty one', () => {
    const basis = resolveSourceCount({
      thread_id: 'dynamic-topic-12192',
      signal_count: 89,
      source_count: 0,
    })
    expect(basis).toMatchObject({ kind: 'unmeasured', reason: 'no_receipts_carried' })
  })

  it('distinguishes receipts-present-but-unattributed from no receipts at all', () => {
    const basis = resolveSourceCount({
      thread_id: 'dynamic-topic-77',
      signal_count: 40,
      source_count: 0,
      evidence_samples: [{ headline: 'a' }, { headline: 'b' }],
    })
    expect(basis).toEqual({
      kind: 'unmeasured',
      reason: 'receipts_carry_no_outlet',
      emptyField: 'source_name',
    })
  })

  it('is honest about zero even when the row itself carries no signals', () => {
    // A zero-signal row should not render anyway, but if it does, zero sources
    // still is not a measurement we can defend.
    const basis = resolveSourceCount({ thread_id: 'x', signal_count: 0, source_count: 0 })
    expect(basis?.kind).toBe('unmeasured')
  })

  it('does not fabricate a count from a negative or non-finite value', () => {
    expect(resolveSourceCount({ thread_id: 'x', signal_count: 5, source_count: -3 })?.kind)
      .toBe('unmeasured')
    expect(resolveSourceCount({ thread_id: 'x', signal_count: 5, source_count: NaN })?.kind)
      .toBe('unmeasured')
  })
})

describe('copy', () => {
  it('never prints a number in the degraded label', () => {
    expect(UNMEASURED_SOURCES_LABEL).toBe('sources not measured')
    expect(UNMEASURED_SOURCES_LABEL).not.toMatch(/\d/)
  })

  it('explains WHICH lane came back empty, and never asserts zero outlets', () => {
    const noReceipts = sourceCountTip({
      kind: 'unmeasured', reason: 'no_receipts_carried', emptyField: 'evidence_samples',
    })
    expect(noReceipts).toMatch(/receipt/i)
    expect(noReceipts).not.toMatch(/\b0 sources\b/)
    expect(noReceipts).not.toMatch(/no outlets/i)

    const unattributed = sourceCountTip({
      kind: 'unmeasured', reason: 'receipts_carry_no_outlet', emptyField: 'source_name',
    })
    expect(unattributed).toMatch(/outlet/i)
    expect(unattributed).not.toBe(noReceipts)
  })

  it('states the base for a measured count', () => {
    expect(sourceCountTip({ kind: 'measured', count: 22 })).toMatch(/22/)
  })
})

// The backend may now count a row's outlets over the FROZEN snapshot receipt
// sample (mig 097) instead of the ≤24 receipts the row renders — 12 of 40 live
// front-page rows, e.g. Thailand School Shooting at 132 outlets over 148 frozen
// receipts while the page shows 24. The number is wider and still a sample, so
// the copy has to say which population it counted and that the page shows less.
describe('widened counts name their population', () => {
  const widened = {
    thread_id: 'dynamic-topic-12193',
    signal_count: 1200,
    source_count: 132,
    source_count_basis: 'snapshot_receipts' as const,
    source_sample_size: 148,
    evidence_samples: new Array(24).fill({ headline: 'a', source: 'reuters.com' }),
  }

  it('carries the population and its sample size through the basis', () => {
    expect(resolveSourceCount(widened)).toEqual({
      kind: 'measured', count: 132, population: 'snapshot_receipts', sampleSize: 148,
    })
  })

  it('tells the reader the page shows fewer receipts than it counted', () => {
    const tip = sourceCountTip(resolveSourceCount(widened)!, { receiptsShown: 24 })
    expect(tip).toMatch(/132/)
    expect(tip).toMatch(/148/)
    expect(tip).toMatch(/24/)
    // Still a sample of Atlas's ingest: the wider number must not read as a
    // total, so "every outlet that published" may only appear NEGATED.
    expect(tip).toMatch(/not every outlet that published/)
    expect(tip.replace(/not every outlet that published/, '')).not.toMatch(/every outlet/)
    expect(tip).toMatch(/sample/i)
  })

  it('does not claim a hidden remainder when the row shows all it counted', () => {
    const tip = sourceCountTip(
      { kind: 'measured', count: 9, population: 'snapshot_receipts', sampleSize: 9 },
      { receiptsShown: 9 },
    )
    expect(tip).not.toMatch(/most recent/)
  })

  it('keeps the served-receipt wording when the count was not widened', () => {
    const served = resolveSourceCount({
      thread_id: 'dynamic-topic-1', signal_count: 30, source_count: 8,
      source_count_basis: 'receipt_sample', source_sample_size: 11,
      evidence_samples: new Array(11).fill({ headline: 'a', source: 'b.com' }),
    })!
    expect(served).toMatchObject({ population: 'receipt_sample' })
    expect(sourceCountTip(served)).toMatch(/resolved receipt sample/)
  })

  it('gives the threads rail a short clause that still names the population', () => {
    // The rail's row hint reads "N signals across M countries from X sources".
    // A widened X counted over a population the row does not render cannot go
    // in that sentence bare.
    expect(sourceCountClause(resolveSourceCount(widened)!))
      .toBe('132 sources in its latest clustering pass')
    expect(sourceCountClause({ kind: 'measured', count: 8 })).toBe('8 sources')
    expect(sourceCountClause({
      kind: 'unmeasured', reason: 'no_receipts_carried', emptyField: 'evidence_samples',
    })).toBe('sources not measured')
  })

  it('ignores an unknown basis rather than trusting it', () => {
    const basis = resolveSourceCount({
      thread_id: 'x', signal_count: 5, source_count: 3,
      source_count_basis: 'wishful_total' as never, source_sample_size: 999,
      evidence_samples: [{ headline: 'a', source: 'b.com' }],
    })
    expect(basis).toMatchObject({ population: 'receipt_sample', sampleSize: 1 })
  })
})

describe('logUnmeasuredSourceCount', () => {
  it('names the thread and the empty upstream field', () => {
    const line = formatSourceCountWarning('dynamic-topic-12138', {
      kind: 'unmeasured', reason: 'no_receipts_carried', emptyField: 'evidence_samples',
    })
    expect(line).toContain('dynamic-topic-12138')
    expect(line).toContain('evidence_samples')
    expect(line).toContain('no_receipts_carried')
  })

  it('warns once per thread, not once per render', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const basis = {
      kind: 'unmeasured' as const, reason: 'no_receipts_carried' as const, emptyField: 'evidence_samples',
    }
    logUnmeasuredSourceCount('dynamic-topic-12138', basis)
    logUnmeasuredSourceCount('dynamic-topic-12138', basis)
    logUnmeasuredSourceCount('dynamic-topic-12192', basis)
    expect(warn).toHaveBeenCalledTimes(2)
  })

  it('stays silent for a measured count', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    logUnmeasuredSourceCount('dynamic-topic-1', { kind: 'measured', count: 3 })
    expect(warn).not.toHaveBeenCalled()
  })
})
