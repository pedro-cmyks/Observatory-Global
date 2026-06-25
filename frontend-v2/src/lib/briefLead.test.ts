import { describe, it, expect } from 'vitest'
import { selectLeadThread } from './briefLead'

// Mirror of the prod payload shape that triggered the regression:
// top-ranked movers carry NO list-level evidence; only a small, low-ranked
// syndicated thread carries evidence_samples.
const prodLikeThreads = [
  { thread_id: 'ukraine', evidence_samples: [] },              // rank 0, top mover, no evidence
  { thread_id: 'heat-uk-fr', evidence_samples: [] },           // rank 1, top mover, no evidence
  { thread_id: 'pauline-hanson', evidence_samples: [{ id: '1', headline: 'opinion col' }] }, // rank 2, micro-thread WITH evidence
]

describe('selectLeadThread', () => {
  it('leads with the TOP-RANKED thread even when it carries no evidence', () => {
    const lead = selectLeadThread(prodLikeThreads, null)
    expect(lead?.thread_id).toBe('ukraine')
  })

  it('does NOT pick a lower-ranked evidence-carrying thread over a higher-ranked evidence-less one (regression)', () => {
    const lead = selectLeadThread(prodLikeThreads, null)
    // The bug led with 'pauline-hanson' because it was the first .find(evidence>0).
    expect(lead?.thread_id).not.toBe('pauline-hanson')
  })

  it('keeps the top thread when it does carry evidence', () => {
    const withEvidence = [
      { thread_id: 'a', evidence_samples: [{ id: '1', headline: 'h' }] },
      { thread_id: 'b', evidence_samples: [] },
    ]
    expect(selectLeadThread(withEvidence, null)?.thread_id).toBe('a')
  })

  it('returns null when a country filter is active (country view has no global lead)', () => {
    expect(selectLeadThread(prodLikeThreads, 'CO')).toBeNull()
  })

  it('returns null for empty or missing input without throwing', () => {
    expect(selectLeadThread([], null)).toBeNull()
    expect(selectLeadThread(null, null)).toBeNull()
    expect(selectLeadThread(undefined, null)).toBeNull()
  })
})
