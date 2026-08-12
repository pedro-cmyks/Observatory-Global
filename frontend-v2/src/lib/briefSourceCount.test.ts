import { describe, it, expect, vi, afterEach } from 'vitest'
import {
  resolveSourceCount,
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
    expect(basis).toEqual({ kind: 'measured', count: 22 })
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
