// P0.6a publishable mini-article — pure helper tests.
import { describe, expect, it } from 'vitest'
import { buildSynthesisRequest, isArticle, splitCitations, synthesisMarkdown, type DossierSynthesis } from './dossierSynthesis'
import type { DossierModel } from './dossier'

const base: DossierSynthesis = {
  contract: 'dossier-synthesis-v2',
  headline: null, lede: null, body: null, unknowns: null, citations: null,
  synthesis: null, gap: null, provider: 'deepseek', error: null,
}

describe('splitCitations', () => {
  it('splits inline [n] markers into text + cite parts', () => {
    expect(splitCitations('ordered the cutoff [2], per Reuters [1][4].')).toEqual([
      { kind: 'text', text: 'ordered the cutoff ' },
      { kind: 'cite', n: 2 },
      { kind: 'text', text: ', per Reuters ' },
      { kind: 'cite', n: 1 },
      { kind: 'cite', n: 4 },
      { kind: 'text', text: '.' },
    ])
  })
  it('plain text passes through untouched', () => {
    expect(splitCitations('no receipts here')).toEqual([{ kind: 'text', text: 'no receipts here' }])
  })
})

describe('isArticle', () => {
  it('article shape when lede or body present; legacy otherwise', () => {
    expect(isArticle({ ...base, lede: 'A dated lede. [1]' })).toBe(true)
    expect(isArticle({ ...base, body: ['para [1]'] })).toBe(true)
    expect(isArticle({ ...base, synthesis: 'old shape' })).toBe(false)
  })
})

describe('synthesisMarkdown', () => {
  it('article shape → lede, body, unknowns, numbered receipts', () => {
    const md = synthesisMarkdown({
      ...base,
      headline: 'NATO summit collides with US aid cutoff',
      lede: 'On Jul 7, Erdogan hosted the summit [1].',
      body: ['Washington ordered the cutoff [2].'],
      unknowns: ['No public/forum voice measured.', 'Evidence leans Romanian-language sources.'],
      citations: [
        { n: 1, headline: 'Erdogan hosts summit', source: 'AA', date: '2026-07-07', url: 'http://x/1', pin: 'Summit' },
        { n: 2, headline: 'US orders cutoff', source: 'Reuters', date: null, url: null, pin: 'Aid' },
      ],
    }).join('\n')
    expect(md).toContain('**NATO summit collides with US aid cutoff**')
    expect(md).toContain('*On Jul 7, Erdogan hosted the summit [1].*')
    expect(md).toContain('Washington ordered the cutoff [2].')
    expect(md).toContain("**What we don't know**")
    expect(md).toContain('- Evidence leans Romanian-language sources.')
    expect(md).toContain('1. [Erdogan hosts summit](http://x/1) — AA, 2026-07-07 *(Summit)*')
    expect(md).toContain('2. US orders cutoff — Reuters *(Aid)*')
    expect(md).toContain('measured at generation time (deepseek)')
  })
  it('legacy shape still renders the old block', () => {
    const md = synthesisMarkdown({ ...base, headline: 'H', synthesis: 'S.', gap: 'G.' }).join('\n')
    expect(md).toContain('**H**')
    expect(md).toContain('S.')
    expect(md).toContain('*Key gap: G.*')
    expect(md).not.toContain('Receipts')
  })
  it('empty synthesis → no block', () => {
    expect(synthesisMarkdown(base)).toEqual([])
  })
})

describe('buildSynthesisRequest', () => {
  it('preserves the complete frozen evidence set instead of silently taking six', () => {
    const dossier = {
      title: 'Test', queries: [], generatedAt: '2026-07-12T12:00:00Z', pinCount: 1,
      summary: '', timeline: [], gaps: [], categoryGroups: [],
      pins: [{
        anchorId: 'dynamic-topic-1', anchorType: 'thread', label: 'Thread',
        pinnedAt: '2026-07-12T12:00:00Z',
        snapshot: {
          capturedAt: '2026-07-12T12:00:00Z',
          evidence: Array.from({ length: 9 }, (_, i) => ({ headline: `Receipt ${i + 1}` })),
        },
      }],
    } as DossierModel

    const request = buildSynthesisRequest(dossier, null)

    expect(request.pins[0].evidence_items).toHaveLength(9)
    expect(request.pins[0].evidence).toHaveLength(9)
  })

  // Frank 2026-08-12: the cross-read measured a tension the synthesis then
  // contradicted. The measured tensions must REACH the synthesis request —
  // the backend guard is unreachable otherwise.
  const onePin = {
    title: 'Syria Russia bases deal', queries: [], generatedAt: '2026-08-12T12:00:00Z',
    pinCount: 1, summary: '', timeline: [], gaps: [], categoryGroups: [],
    pins: [{
      anchorId: 'dynamic-topic-12280', anchorType: 'thread', label: 'Syria Russia Bases Deal',
      pinnedAt: '2026-08-12T12:00:00Z',
      snapshot: { capturedAt: '2026-08-12T12:00:00Z', evidence: [{ headline: 'Deal reached' }] },
    }],
  } as DossierModel

  it('carries measured cross-read TENSIONS (and only tensions) into the request', () => {
    const crossRead = {
      articles_read: 3, articles_with_claims: 3,
      findings: [
        {
          kind: 'tension' as const,
          a: { id: 'c10', url: 'https://naharnet/1', outlet: 'naharnet.com', text: '', quote: 'Russia has yet to officially comment on the agreement.' },
          b: { id: 'c1', url: 'https://algemeiner/1', outlet: 'algemeiner.com', text: '', quote: "Russia's Foreign Ministry said on Tuesday that a deal would boost ties" },
          note: 'c10 asserts Russia has not commented, while c1 attributes a statement to it.',
        },
        {
          kind: 'corroboration' as const,
          a: { id: 'c5', url: 'https://a/1', outlet: 'a.com', text: '', quote: 'three months' },
          b: { id: 'c8', url: 'https://b/1', outlet: 'b.com', text: '', quote: 'no more than three months' },
          note: 'both name the same window',
        },
      ],
    }

    const request = buildSynthesisRequest(onePin, null, crossRead)
    const tensions = request.tensions as Array<Record<string, string | null>>

    expect(tensions).toHaveLength(1)
    expect(tensions[0].a_quote).toContain('yet to officially comment')
    expect(tensions[0].a_outlet).toBe('naharnet.com')
    expect(tensions[0].b_outlet).toBe('algemeiner.com')
  })

  it('sends an empty tension list when no cross-read has been run', () => {
    expect(buildSynthesisRequest(onePin, null).tensions).toEqual([])
    expect(buildSynthesisRequest(onePin, null, null).tensions).toEqual([])
  })
})
