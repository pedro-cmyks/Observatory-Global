import { describe, expect, it } from 'vitest'
import {
  confidenceBucketLabel,
  confidenceBucketWord,
  resolveConfidenceBucket,
  threadConfidencePresentation,
} from './threadConfidence'

describe('threadConfidencePresentation', () => {
  it('renders an unmeasured default as unscored without a bar', () => {
    const result = threadConfidencePresentation({
      avgConfidence: null,
      confidenceMeasured: false,
      trend: 'stable',
      crisisRelevant: false,
    })

    expect(result.bucket).toBeNull()
    expect(result.bucketSource).toBeNull()
    expect(result.confidenceLabel).toBe('unscored')
    expect(result.showConfidenceBar).toBe(false)
    expect(result.barPct).toBeNull()
    expect(result.trendColor).toBe('#60a5fa')
  })

  // Council R4 N14 (open three rounds): the live witness is "Biden Cancer
  // Spread" — avg_confidence 1.0 served under band "medium". The renderer must
  // read the band the payload actually ships.
  it('lets the served band govern, even when the raw number disagrees', () => {
    const result = threadConfidencePresentation({
      avgConfidence: 1.0,
      confidenceMeasured: true,
      trend: 'stable',
      crisisRelevant: false,
      band: 'medium',
    })

    expect(result.bucket).toBe('medium')
    expect(result.bucketSource).toBe('band')
    expect(result.confidenceLabel).toBe('medium confidence')
    expect(result.confidenceLabel).not.toContain('100')
    expect(result.showConfidenceBar).toBe(true)
  })

  it('sizes the bar from the bucket, never from the raw number', () => {
    const banded = threadConfidencePresentation({
      avgConfidence: 1.0,
      confidenceMeasured: true,
      trend: 'stable',
      crisisRelevant: false,
      band: 'medium',
    })

    // A raw 1.0 under a medium band must not paint a full bar either.
    expect(banded.barPct).toBe(65)
    expect(banded.barPct).not.toBe(100)
  })

  it('buckets the raw number when the payload ships no band', () => {
    const high = threadConfidencePresentation({
      avgConfidence: 0.806, confidenceMeasured: true, trend: 'stable', crisisRelevant: false,
    })
    const medium = threadConfidencePresentation({
      avgConfidence: 0.64, confidenceMeasured: true, trend: 'stable', crisisRelevant: false,
    })
    const low = threadConfidencePresentation({
      avgConfidence: 0.31, confidenceMeasured: true, trend: 'stable', crisisRelevant: false,
    })

    expect(high.bucket).toBe('high')
    expect(high.bucketSource).toBe('derived')
    expect(high.confidenceLabel).toBe('high confidence')
    expect(medium.confidenceLabel).toBe('medium confidence')
    expect(low.confidenceLabel).toBe('low confidence')
  })

  // The N14 residue verbatim: a raw 1.0 printed as "100% confidence".
  it('never prints a raw 1.0 as a percentage, band or no band', () => {
    const bands: Array<string | null | undefined> = [
      undefined, null, '', 'high', 'medium', 'thin', 'degraded', 'nonsense-band',
    ]
    for (const band of bands) {
      const result = threadConfidencePresentation({
        avgConfidence: 1.0, confidenceMeasured: true, trend: 'stable', crisisRelevant: false, band,
      })
      expect(result.confidenceLabel).not.toMatch(/\d/)
      expect(result.confidenceLabel).not.toContain('%')
    }
  })

  it('falls back to the derived bucket on an unknown band string', () => {
    const result = threadConfidencePresentation({
      avgConfidence: 0.9, confidenceMeasured: true, trend: 'stable', crisisRelevant: false,
      band: 'sparkling',
    })

    expect(result.bucket).toBe('high')
    expect(result.bucketSource).toBe('derived')
  })

  it('keeps a band-only row scored when no numeric confidence was measured', () => {
    const result = threadConfidencePresentation({
      avgConfidence: null, confidenceMeasured: false, trend: 'stable', crisisRelevant: false,
      band: 'degraded',
    })

    expect(result.bucket).toBe('low')
    expect(result.bucketSource).toBe('band')
    expect(result.confidenceLabel).toBe('low confidence')
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

describe('resolveConfidenceBucket', () => {
  it('maps every served band onto the three-tier bucket', () => {
    expect(resolveConfidenceBucket({ band: 'high' }).bucket).toBe('high')
    expect(resolveConfidenceBucket({ band: 'HIGH' }).bucket).toBe('high')
    expect(resolveConfidenceBucket({ band: 'medium' }).bucket).toBe('medium')
    expect(resolveConfidenceBucket({ band: 'thin' }).bucket).toBe('low')
    expect(resolveConfidenceBucket({ band: 'degraded' }).bucket).toBe('low')
  })

  it('returns an unscored null when there is nothing to bucket', () => {
    expect(resolveConfidenceBucket({}).bucket).toBeNull()
    expect(resolveConfidenceBucket({ avgConfidence: null }).source).toBeNull()
  })
})

describe('confidence bucket copy', () => {
  it('renders sentence copy and stat-tile copy from ONE bucket', () => {
    expect(confidenceBucketLabel('high')).toBe('high confidence')
    expect(confidenceBucketLabel(null)).toBe('unscored')
    expect(confidenceBucketWord('medium')).toBe('Medium')
    expect(confidenceBucketWord(null)).toBe('Unscored')
  })
})
