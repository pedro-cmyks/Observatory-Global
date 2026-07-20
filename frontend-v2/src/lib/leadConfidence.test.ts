import { describe, it, expect } from 'vitest'
import {
  LEAD_CONFIDENCE_FLOOR,
  resolveLeadConfidence,
  leadBlockReason,
  isLeadEligible,
  selectLiveLead,
  type LeadGateThread,
} from './leadConfidence'

const t = (over: Partial<LeadGateThread> = {}): LeadGateThread => ({ ...over })

describe('LEAD_CONFIDENCE_FLOOR', () => {
  it('is 0.70', () => {
    expect(LEAD_CONFIDENCE_FLOOR).toBe(0.7)
  })
})

describe('resolveLeadConfidence', () => {
  it('uses avg_confidence when it is a finite number', () => {
    expect(resolveLeadConfidence(t({ avg_confidence: 0.214 }))).toBe(0.214)
    expect(resolveLeadConfidence(t({ avg_confidence: 0.893 }))).toBe(0.893)
  })

  it('clamps avg_confidence into [0,1]', () => {
    expect(resolveLeadConfidence(t({ avg_confidence: 1.4 }))).toBe(1)
    expect(resolveLeadConfidence(t({ avg_confidence: -0.2 }))).toBe(0)
  })

  it('falls back to the confidence band when avg_confidence is absent/NaN', () => {
    expect(resolveLeadConfidence(t({ confidence: 'high' }))).toBeGreaterThanOrEqual(LEAD_CONFIDENCE_FLOOR)
    expect(resolveLeadConfidence(t({ confidence: 'degraded' }))).toBeLessThan(LEAD_CONFIDENCE_FLOOR)
    expect(resolveLeadConfidence(t({ confidence: 'medium' }))).toBeLessThan(LEAD_CONFIDENCE_FLOOR)
    expect(resolveLeadConfidence(t({ avg_confidence: NaN, confidence: 'high' }))).toBeGreaterThanOrEqual(LEAD_CONFIDENCE_FLOOR)
  })

  it('returns null when neither a number nor a known band is present', () => {
    expect(resolveLeadConfidence(t())).toBeNull()
    expect(resolveLeadConfidence(t({ confidence: 'mystery-band' }))).toBeNull()
  })

  it('reads the band case-insensitively', () => {
    expect(resolveLeadConfidence(t({ confidence: 'HIGH' }))).toBeGreaterThanOrEqual(LEAD_CONFIDENCE_FLOOR)
  })
})

describe('leadBlockReason (v2: the lead requires a STAMP)', () => {
  it('returns null for a high-confidence STAMPED thread (entailed or partial)', () => {
    expect(leadBlockReason(t({ avg_confidence: 0.893, label_status: 'entailed' }))).toBeNull()
    expect(leadBlockReason(t({ avg_confidence: 0.893, label_status: 'partial' }))).toBeNull()
  })

  it('blocks below the floor as low-confidence (even when stamped)', () => {
    expect(leadBlockReason(t({ avg_confidence: 0.214, label_status: 'entailed' }))).toBe('low-confidence')
    expect(leadBlockReason(t({ avg_confidence: 0.699, label_status: 'partial' }))).toBe('low-confidence')
  })

  it('treats the floor as inclusive (>=)', () => {
    expect(leadBlockReason(t({ avg_confidence: 0.7, label_status: 'entailed' }))).toBeNull()
  })

  it('blocks a label-failed thread even when confidence is high', () => {
    expect(leadBlockReason(t({ avg_confidence: 0.99, label_status: 'failed' }))).toBe('label-failed')
  })

  it('label-failed takes precedence over every other reason', () => {
    expect(leadBlockReason(t({ avg_confidence: 0.1, label_status: 'failed' }))).toBe('label-failed')
    expect(leadBlockReason(t({ label_status: 'failed' }))).toBe('label-failed')
  })

  it('UNSTAMPED (null/undefined status) blocks as awaiting-verification when confidence clears the floor', () => {
    // The council R2 N2 fold hole: new topics promote and serve BEFORE the
    // court runs. An unstamped label may not lead — v1 let null lead.
    expect(leadBlockReason(t({ avg_confidence: 0.893, label_status: null }))).toBe('awaiting-verification')
    expect(leadBlockReason(t({ avg_confidence: 1.0 }))).toBe('awaiting-verification')
  })

  it('below-floor wins over awaiting-verification (a stamp would not rescue it)', () => {
    expect(leadBlockReason(t({ avg_confidence: 0.214, label_status: null }))).toBe('low-confidence')
    expect(leadBlockReason(t())).toBe('low-confidence')
  })

  it('an unscored thread blocks as low-confidence even when entailed', () => {
    expect(leadBlockReason(t({ label_status: 'entailed' }))).toBe('low-confidence')
  })
})

describe('isLeadEligible', () => {
  it('requires BOTH the stamp and the floor', () => {
    expect(isLeadEligible(t({ avg_confidence: 0.893, label_status: 'entailed' }))).toBe(true)
    expect(isLeadEligible(t({ avg_confidence: 0.7, label_status: 'partial' }))).toBe(true)
    expect(isLeadEligible(t({ avg_confidence: 0.893 }))).toBe(false) // unstamped
    expect(isLeadEligible(t({ avg_confidence: 0.214, label_status: 'entailed' }))).toBe(false)
    expect(isLeadEligible(t({ avg_confidence: 0.99, label_status: 'failed' }))).toBe(false)
  })

  it('the Greek-blob live case (0.214) is ineligible', () => {
    expect(isLeadEligible(t({ avg_confidence: 0.214, confidence: 'degraded' }))).toBe(false)
  })
})

describe('selectLiveLead', () => {
  interface Row extends LeadGateThread {
    id: string
  }
  const row = (id: string, over: Partial<LeadGateThread>): Row => ({ id, ...over })

  it('a high-confidence but court-FAILED top thread does NOT lead; a lower-ranked entailed thread wins', () => {
    // dt-565 "Job and Course Openings" — served top by rank, high confidence,
    // but the Label Court failed it. It must be skipped and the next entailed
    // thread (Venezuela Earthquake) becomes the lead.
    const threads = [
      row('dt-565', { avg_confidence: 0.893, label_status: 'failed' }),
      row('venezuela-earthquake', { avg_confidence: 0.91, label_status: 'entailed' }),
      row('us-iran-strikes', { avg_confidence: 0.88, label_status: 'entailed' }),
    ]
    const sel = selectLiveLead(threads)
    expect(sel.lead?.id).toBe('venezuela-earthquake')
    expect(sel.leadUnavailable).toBe(false)
    // The failed top thread is excluded from the eligible pool entirely.
    expect(sel.eligible.map(r => r.id)).toEqual(['venezuela-earthquake', 'us-iran-strikes'])
  })

  it('an UNSTAMPED high-confidence top thread does NOT lead — the next stamped thread wins (v2)', () => {
    // Council R2 N2: 31/37 served threads incl. ALL leads were unstamped —
    // the court runs behind promotion. Unstamped rows wait; stamped rows lead.
    const sel = selectLiveLead([
      row('dt-3667-unstamped', { avg_confidence: 1.0, label_status: null }),
      row('venezuela-earthquake', { avg_confidence: 0.91, label_status: 'entailed' }),
    ])
    expect(sel.lead?.id).toBe('venezuela-earthquake')
    expect(sel.awaitingVerification).toBe(false)
  })

  it('reports leadUnavailable when threads exist but none clears the bar (honest empty-lead)', () => {
    const sel = selectLiveLead([
      row('a', { avg_confidence: 0.214 }),
      row('b', { avg_confidence: 0.5, label_status: 'failed' }),
    ])
    expect(sel.lead).toBeNull()
    expect(sel.leadUnavailable).toBe(true)
    expect(sel.eligible).toEqual([])
    // Nothing here is merely waiting on a stamp — this is a true below-bar day.
    expect(sel.awaitingVerification).toBe(false)
  })

  it('flags awaitingVerification when the ONLY blocker is missing stamps (today’s live fold)', () => {
    const sel = selectLiveLead([
      row('iran-strikes', { avg_confidence: 1.0, label_status: null }),
      row('drone-strikes', { avg_confidence: 0.887, label_status: null }),
      row('greek-blob', { avg_confidence: 0.214 }),
    ])
    expect(sel.lead).toBeNull()
    expect(sel.leadUnavailable).toBe(true)
    expect(sel.awaitingVerification).toBe(true)
  })

  it('leadUnavailable is false for an empty list (no threads is not an empty-lead)', () => {
    const sel = selectLiveLead<Row>([])
    expect(sel.lead).toBeNull()
    expect(sel.leadUnavailable).toBe(false)
    expect(sel.awaitingVerification).toBe(false)
  })
})
