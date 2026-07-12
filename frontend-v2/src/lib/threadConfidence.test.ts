import { describe, expect, it } from 'vitest'
import { threadConfidencePresentation } from './threadConfidence'

describe('threadConfidencePresentation', () => {
  it('renders an unmeasured default as unscored without a bar', () => {
    expect(threadConfidencePresentation({
      avgConfidence: null,
      confidenceMeasured: false,
      trend: 'stable',
      crisisRelevant: false,
    })).toEqual({
      confidencePct: null,
      confidenceLabel: 'unscored',
      showConfidenceBar: false,
      trendColor: '#60a5fa',
    })
  })

  it('renders a measured confidence as a whole percent', () => {
    const result = threadConfidencePresentation({
      avgConfidence: 0.806,
      confidenceMeasured: true,
      trend: 'stable',
      crisisRelevant: false,
    })

    expect(result.confidencePct).toBe(81)
    expect(result.confidenceLabel).toBe('81% confidence')
    expect(result.showConfidenceBar).toBe(true)
  })

  it('uses crisis red only for accelerating crisis stories', () => {
    const neutral = threadConfidencePresentation({
      avgConfidence: 0.8,
      confidenceMeasured: true,
      trend: 'accelerating',
      crisisRelevant: false,
    })
    const crisis = threadConfidencePresentation({
      avgConfidence: 0.8,
      confidenceMeasured: true,
      trend: 'accelerating',
      crisisRelevant: true,
    })

    expect(neutral.trendColor).toBe('#34d399')
    expect(crisis.trendColor).toBe('#ef4444')
  })
})
