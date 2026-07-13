import { describe, expect, it } from 'vitest'

import { researchLedgerSummary } from './researchPlan'

describe('research plan transparency ledger', () => {
  it('states that the complete candidate universe remains accessible', () => {
    expect(researchLedgerSummary({
      candidate_count: 597,
      shown_count: 12,
      primary_count: 12,
      downranked_count: 585,
      omitted_count: 0,
      accessible_count: 597,
      complete: true,
      semantic_ceiling: false,
      reason_codes: {},
    })).toBe(
      '597 candidates evaluated · 12 primary · 585 low confidence · 597 accessible · complete · no candidates excluded',
    )
  })

  it('does not claim completeness when a discovery lane degraded', () => {
    expect(researchLedgerSummary({
      candidate_count: 10,
      shown_count: 2,
      downranked_count: 8,
      omitted_count: 0,
      complete: false,
      reason_codes: { lane_degraded: 1 },
    })).toContain('partial ledger · lane degradation disclosed')
  })
})
