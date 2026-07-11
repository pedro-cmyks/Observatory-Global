import { describe, it, expect } from 'vitest'
import { extractSnapshotEvidence } from './pinEvidence'

describe('extractSnapshotEvidence', () => {
  it('extracts headline/source/url from the first headline-shaped array', () => {
    const out = extractSnapshotEvidence({
      total: 42,
      signals: [
        { headline: 'H1', source: 'BBC', url: 'https://x/1' },
        { title: 'H2', domain: 'reuters.com', link: 'https://x/2' },
        { headline: 'H3' },
        { headline: 'H4' },
      ],
    })
    expect(out).toHaveLength(3)
    expect(out[0]).toEqual({ headline: 'H1', source: 'BBC', url: 'https://x/1' })
    expect(out[1]).toEqual({ headline: 'H2', source: 'reuters.com', url: 'https://x/2' })
  })

  it('prefers gate-verified/core rows over merely-recent ones', () => {
    // The thread pin froze the 3 most RECENT members (drift) — verified rows
    // must outrank ungated ones regardless of payload (recency) order.
    const out = extractSnapshotEvidence({
      signals: [
        { headline: 'recent drift', gateKept: false, gateScore: 0.2 },
        { headline: 'extended', tier: 'extended', gateScore: 0.8 },
        { headline: 'core A', gateKept: true, gateScore: 0.97 },
        { headline: 'core B', tier: 'verified', gateScore: 0.99 },
      ],
    })
    expect(out.map(e => e.headline)).toEqual(['core B', 'core A', 'extended'])
  })

  it('keeps payload order when rows carry no gate/score fields (dynamic path)', () => {
    const out = extractSnapshotEvidence({
      signals: [{ headline: 'first' }, { headline: 'second' }, { headline: 'third' }, { headline: 'fourth' }],
    })
    expect(out.map(e => e.headline)).toEqual(['first', 'second', 'third'])
  })

  it('skips non-array and headline-less keys, returns [] when nothing matches', () => {
    expect(extractSnapshotEvidence({ signalSample: 12, signals: [{ n: 1 }] })).toEqual([])
    expect(extractSnapshotEvidence({})).toEqual([])
  })
})
