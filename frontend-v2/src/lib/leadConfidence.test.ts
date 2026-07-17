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

describe('leadBlockReason', () => {
  it('returns null for a high-confidence, non-failed thread', () => {
    expect(leadBlockReason(t({ avg_confidence: 0.893 }))).toBeNull()
  })

  it('blocks below the floor as low-confidence', () => {
    expect(leadBlockReason(t({ avg_confidence: 0.214 }))).toBe('low-confidence')
    expect(leadBlockReason(t({ avg_confidence: 0.699 }))).toBe('low-confidence')
  })

  it('treats the floor as inclusive (>=)', () => {
    expect(leadBlockReason(t({ avg_confidence: 0.7 }))).toBeNull()
  })

  it('blocks a label-failed thread even when confidence is high', () => {
    expect(leadBlockReason(t({ avg_confidence: 0.99, label_status: 'failed' }))).toBe('label-failed')
  })

  it('label-failed takes precedence over low-confidence', () => {
    expect(leadBlockReason(t({ avg_confidence: 0.1, label_status: 'failed' }))).toBe('label-failed')
    expect(leadBlockReason(t({ label_status: 'failed' }))).toBe('label-failed')
  })

  it('does NOT block on partial or entailed statuses (only failed blocks)', () => {
    expect(leadBlockReason(t({ avg_confidence: 0.8, label_status: 'partial' }))).toBeNull()
    expect(leadBlockReason(t({ avg_confidence: 0.8, label_status: 'entailed' }))).toBeNull()
  })

  it('blocks an unscored thread (no confidence signal) as low-confidence', () => {
    expect(leadBlockReason(t())).toBe('low-confidence')
  })

  it('label_status null does not block a high-confidence thread (today’s live case)', () => {
    expect(leadBlockReason(t({ avg_confidence: 0.893, label_status: null }))).toBeNull()
  })
})

describe('isLeadEligible', () => {
  it('is true exactly when there is no block reason', () => {
    expect(isLeadEligible(t({ avg_confidence: 0.893 }))).toBe(true)
    expect(isLeadEligible(t({ avg_confidence: 0.214 }))).toBe(false)
    expect(isLeadEligible(t({ avg_confidence: 0.99, label_status: 'failed' }))).toBe(false)
    expect(isLeadEligible(t({ avg_confidence: 0.7 }))).toBe(true)
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

  it('re-reads label_status per call — a null-status high-confidence top thread still leads', () => {
    // Before the court runs, label_status is null and a high-confidence top
    // thread leads normally (no premature demotion).
    const sel = selectLiveLead([
      row('dt-565', { avg_confidence: 0.893, label_status: null }),
      row('venezuela-earthquake', { avg_confidence: 0.91, label_status: 'entailed' }),
    ])
    expect(sel.lead?.id).toBe('dt-565')
  })

  it('reports leadUnavailable when threads exist but none clears the bar (honest empty-lead)', () => {
    const sel = selectLiveLead([
      row('a', { avg_confidence: 0.214 }),
      row('b', { avg_confidence: 0.5, label_status: 'failed' }),
    ])
    expect(sel.lead).toBeNull()
    expect(sel.leadUnavailable).toBe(true)
    expect(sel.eligible).toEqual([])
  })

  it('leadUnavailable is false for an empty list (no threads is not an empty-lead)', () => {
    const sel = selectLiveLead<Row>([])
    expect(sel.lead).toBeNull()
    expect(sel.leadUnavailable).toBe(false)
  })
})
