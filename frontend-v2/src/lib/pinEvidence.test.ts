import { describe, it, expect } from 'vitest'
import {
  enrichmentWithoutEvidence,
  extractSnapshotEvidence,
  freezeVisibleEvidence,
} from './pinEvidence'
import { PIN_EVIDENCE_FREEZE_CAP } from './workbench'

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

describe('P0.3 — evidence dates survive freezing', () => {
  it('extracts an ISO day from timestamp-bearing rows', () => {
    const out = extractSnapshotEvidence({
      signals: [{ headline: 'H', source: 'S', timestamp: '2026-07-08T14:02:11Z' }],
    })
    expect(out[0].date).toBe('2026-07-08')
  })
  it('leaves date undefined when no timestamp exists', () => {
    const out = extractSnapshotEvidence({ signals: [{ headline: 'H' }] })
    expect(out[0].date).toBeUndefined()
  })
})

// ── Council R4 N25: freeze what the analyst SAW ─────────────────────────────
// The theme/thread pin used to freeze evidence via an async RE-FETCH; when that
// fetch missed (different window, country scope dropped, query-thread id, 429,
// offline) the pin landed metadata-only and the dossier declared an evidence
// gap on a thread that had 35 rows on screen. `freezeVisibleEvidence` freezes
// the rows the panel was DISPLAYING, in display order, with no network.
describe('freezeVisibleEvidence (N25)', () => {
  it('freezes the visible rows in DISPLAY order (never re-ranked)', () => {
    const out = freezeVisibleEvidence([
      { headline: 'row one', source: 'BBC', url: 'https://x/1', timestamp: '2026-08-01T10:00:00Z' },
      { title: 'row two', domain: 'reuters.com', link: 'https://x/2' },
    ])
    expect(out).toEqual([
      { headline: 'row one', source: 'BBC', url: 'https://x/1', date: '2026-08-01' },
      { headline: 'row two', source: 'reuters.com', url: 'https://x/2', date: undefined },
    ])
  })

  it('caps at PIN_EVIDENCE_FREEZE_CAP (localStorage 5MB reality)', () => {
    const rows = Array.from({ length: 35 }, (_, i) => ({ headline: `h${i}`, url: `https://x/${i}` }))
    const out = freezeVisibleEvidence(rows)
    expect(out).toHaveLength(PIN_EVIDENCE_FREEZE_CAP)
    expect(out[0].headline).toBe('h0')
    expect(freezeVisibleEvidence(rows, 3)).toHaveLength(3)
  })

  it('drops headline-less rows and de-duplicates syndicated repeats', () => {
    const out = freezeVisibleEvidence([
      { headline: 'A', url: 'https://x/1' },
      { country: 'US' },
      { headline: 'A copy', url: 'https://x/1' }, // same url = same receipt
      { headline: 'a' },                           // same headline, no url
      { headline: 'A' },
      { headline: 'B' },
    ])
    expect(out.map(e => e.headline)).toEqual(['A', 'a', 'B'])
  })

  it('decodes entity-encoded headlines (freeze what was rendered)', () => {
    expect(freezeVisibleEvidence([{ headline: 'Odesa &amp; Kyiv' }])[0].headline).toBe('Odesa & Kyiv')
  })

  it('tolerates a missing/!array payload (pin never blocks on evidence)', () => {
    expect(freezeVisibleEvidence(undefined)).toEqual([])
    expect(freezeVisibleEvidence(null)).toEqual([])
    expect(freezeVisibleEvidence({} as unknown)).toEqual([])
  })
})

describe('enrichmentWithoutEvidence (N25 precedence)', () => {
  it('strips evidence so a late re-fetch never overwrites the visible freeze', () => {
    const out = enrichmentWithoutEvidence({
      capturedAt: 'x', summary: 's', metrics: { total: 35 },
      evidence: [{ headline: 'drifted row' }],
    })
    expect(out).toEqual({ capturedAt: 'x', summary: 's', metrics: { total: 35 } })
    expect('evidence' in out).toBe(false)
  })
})
