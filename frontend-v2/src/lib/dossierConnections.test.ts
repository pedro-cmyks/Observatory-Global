import { describe, it, expect } from 'vitest'
import {
  deriveClusters, layoutInvestigativeUniverse, edgeReason, connectionsSummaryLines,
  connectionTopicIds, deOverlapLabels,
  edgeStrength, clusterStrength, sharedBasisNames,
  type ConnectionNode, type ConnectionEdge, type ConnectionsData, type LabelItem,
} from './dossierConnections'
import type { Investigation } from './workbench'

function node(id: string, over: Partial<ConnectionNode> = {}): ConnectionNode {
  return {
    id, base_id: id, label: id.toUpperCase(), category: 'crisis',
    pos: null, countries: [], persons: [], languages: [], sentiment: null,
    roleCounts: { evidence: 5, discussion: 0, mood: 0 }, timeline: [],
    has_centroid: false, n: 5, ...over,
  }
}
function edge(a: string, b: string, over: Partial<ConnectionEdge> = {}): ConnectionEdge {
  return { a, b, basis: ['semantic'], weight: 0.9, semantic_sim: 0.9, shared_countries: [], shared_persons: [], ...over }
}

describe('deriveClusters', () => {
  it('groups connected pins into sub-narratives and flags isolated ones', () => {
    const nodes = [node('a'), node('b'), node('c'), node('d')]
    // a-b connected, c-d connected, no cross-link → two clusters, 0 isolated
    const edges = [edge('a', 'b'), edge('c', 'd')]
    const r = deriveClusters(nodes, edges)
    expect(r.clusters.length).toBe(2)
    expect(r.isolated.length).toBe(0)
  })

  it('marks a pin with no edges as isolated', () => {
    const nodes = [node('a'), node('b'), node('lonely')]
    const edges = [edge('a', 'b')]
    const r = deriveClusters(nodes, edges)
    expect(r.clusters.length).toBe(1)
    expect(r.isolated.map(n => n.id)).toEqual(['lonely'])
    expect(r.clusterOf.get('lonely')).toBe(-1)
    expect(r.clusterOf.get('a')).toBe(0)
  })

  it('transitively merges a chain into one cluster', () => {
    const nodes = [node('a'), node('b'), node('c')]
    const edges = [edge('a', 'b'), edge('b', 'c')]
    const r = deriveClusters(nodes, edges)
    expect(r.clusters.length).toBe(1)
    expect(r.clusters[0].length).toBe(3)
  })

  it('ignores edges to unknown ids', () => {
    const nodes = [node('a'), node('b')]
    const r = deriveClusters(nodes, [edge('a', 'ghost')])
    expect(r.isolated.length).toBe(2)
  })
})

describe('layoutInvestigativeUniverse', () => {
  it('places every node within the padded box', () => {
    const nodes = [
      node('a', { pos: { x: 0.1, y: 0.2 } }),
      node('b', { pos: { x: 0.9, y: 0.8 } }),
      node('c'), // no pos → settles to neighbor
    ]
    const edges = [edge('a', 'c'), edge('b', 'c')]
    const placed = layoutInvestigativeUniverse(nodes, edges, 640, 380, 30)
    expect(placed.length).toBe(3)
    for (const p of placed) {
      expect(p.px).toBeGreaterThanOrEqual(0)
      expect(p.px).toBeLessThanOrEqual(640)
      expect(p.py).toBeGreaterThanOrEqual(0)
      expect(p.py).toBeLessThanOrEqual(380)
    }
  })

  it('is deterministic', () => {
    const nodes = [node('a', { pos: { x: 0.3, y: 0.3 } }), node('b')]
    const edges = [edge('a', 'b')]
    const p1 = layoutInvestigativeUniverse(nodes, edges, 640, 380)
    const p2 = layoutInvestigativeUniverse(nodes, edges, 640, 380)
    expect(p1.map(n => [n.px, n.py])).toEqual(p2.map(n => [n.px, n.py]))
  })

  it('maps a backend pos to padded panel coords', () => {
    const placed = layoutInvestigativeUniverse([node('a', { pos: { x: 0, y: 1 } }), node('b', { pos: { x: 1, y: 0 } }), node('c', { pos: { x: 0.5, y: 0.5 } })], [], 640, 380, 30)
    const a = placed.find(n => n.id === 'a')!
    expect(a.px).toBeCloseTo(30, 5)      // x=0 → left pad
    expect(a.py).toBeCloseTo(380 - 30, 5) // y=1 → bottom pad
  })
})

describe('deOverlapLabels', () => {
  it('separates two labels that overlap in x and y into distinct lanes', () => {
    const items: LabelItem[] = [
      { id: 'a', cx: 100, halfW: 40, y: 50 },
      { id: 'b', cx: 110, halfW: 40, y: 52 }, // overlaps a in x and y
    ]
    const r = deOverlapLabels(items, 11)
    expect(Math.abs(r.get('a')! - r.get('b')!)).toBeGreaterThanOrEqual(11)
  })

  it('leaves horizontally-disjoint labels at their desired y', () => {
    const items: LabelItem[] = [
      { id: 'a', cx: 50, halfW: 20, y: 50 },
      { id: 'b', cx: 200, halfW: 20, y: 50 }, // far apart in x → no collision
    ]
    const r = deOverlapLabels(items, 11)
    expect(r.get('a')).toBe(50)
    expect(r.get('b')).toBe(50)
  })

  it('only moves labels upward (never below the desired baseline)', () => {
    const items: LabelItem[] = [
      { id: 'a', cx: 100, halfW: 40, y: 50 },
      { id: 'b', cx: 100, halfW: 40, y: 50 },
      { id: 'c', cx: 100, halfW: 40, y: 50 },
    ]
    const r = deOverlapLabels(items, 11)
    for (const v of r.values()) expect(v).toBeLessThanOrEqual(50)
    // three stacked, all distinct
    expect(new Set(r.values()).size).toBe(3)
  })

  it('is deterministic', () => {
    const items: LabelItem[] = [
      { id: 'a', cx: 100, halfW: 40, y: 50 },
      { id: 'b', cx: 108, halfW: 40, y: 50 },
    ]
    const r1 = deOverlapLabels(items)
    const r2 = deOverlapLabels(items)
    expect([...r1.entries()]).toEqual([...r2.entries()])
  })
})

describe('edgeReason', () => {
  it('describes the strongest available basis', () => {
    expect(edgeReason(edge('a', 'b', { semantic_sim: 0.91 }))).toContain('semantic 91%')
    expect(edgeReason(edge('a', 'b', { basis: ['shared_country'], semantic_sim: null, shared_countries: ['CO'] }))).toContain('↔ CO')
    expect(edgeReason(edge('a', 'b', { basis: ['shared_person'], semantic_sim: null, shared_persons: ['petro'] }))).toContain('petro')
  })

  it('quotes the whitened (decision-space) sim when available, never the raw 99%', () => {
    // The synthesis was quoting "semantic similarity of 99%" — the raw cosine.
    // With whitened_sim present, the reason string must carry the decorrelated
    // number, labeled, and omit the misleading raw figure.
    const reason = edgeReason(edge('a', 'b', { semantic_sim: 0.99, whitened_sim: 0.55 }))
    expect(reason).toContain('decorrelated similarity 55%')
    expect(reason).not.toContain('99%')
  })

  it('falls back to raw semantic sim when whitened is absent or null', () => {
    expect(edgeReason(edge('a', 'b', { semantic_sim: 0.91, whitened_sim: null }))).toContain('semantic 91%')
    expect(edgeReason(edge('a', 'b', { semantic_sim: 0.91 }))).toContain('semantic 91%')
  })
})

describe('connectionsSummaryLines', () => {
  it('summarises sub-narratives, isolation and strongest links', () => {
    const nodes = [node('a'), node('b'), node('lonely')]
    const edges = [edge('a', 'b', { semantic_sim: 0.95 })]
    const data: ConnectionsData = {
      contract: 'dossier-connections-v0', nodes, edges,
      distributions: null, unresolved: ['some-atlas-slug'],
    }
    const cluster = deriveClusters(nodes, edges)
    const lines = connectionsSummaryLines(data, cluster).join('\n')
    expect(lines).toContain('Sub-narrative 1')
    expect(lines).toContain('Isolated')
    expect(lines).toContain('Strongest links')
    expect(lines).toContain('some-atlas-slug')
  })

  it('says so when nothing connects', () => {
    const nodes = [node('a'), node('b')]
    const data: ConnectionsData = { contract: 'x', nodes, edges: [], distributions: null, unresolved: [] }
    const cluster = deriveClusters(nodes, [])
    const lines = connectionsSummaryLines(data, cluster).join('\n')
    expect(lines).toContain('every pinned story is isolated')
  })
})

describe('edgeStrength / clusterStrength (basis-weighting — the correlation guard)', () => {
  it('semantic-only is weak; shared actor is strong; coverage country is contextual', () => {
    expect(edgeStrength(edge('a', 'b'))).toBe('weak') // default = semantic-only
    expect(edgeStrength(edge('a', 'b', { basis: ['semantic', 'shared_person'], shared_persons: ['fujimori'] }))).toBe('strong')
    expect(edgeStrength(edge('a', 'b', { basis: ['shared_country'], semantic_sim: null, shared_countries: ['PE'] }))).toBe('context')
  })

  it('semantic-only is CAUTION, a coverage country is CONTEXT, and a shared actor is CONFIRMED', () => {
    const nodes = [node('a'), node('b'), node('c')]
    const semanticOnly = [edge('a', 'b', { semantic_sim: 0.94 }), edge('b', 'c', { semantic_sim: 0.92 })]
    expect(clusterStrength(nodes, semanticOnly)).toBe('caution')
    // add ONE shared-actor edge inside the cluster → confirmed
    const withActor = [...semanticOnly, edge('a', 'c', { basis: ['shared_person'], shared_persons: ['milei'] })]
    expect(clusterStrength(nodes, withActor)).toBe('confirmed')
  })

  it('sharedBasisNames exposes only actors that can support confirmation', () => {
    const nodes = [node('a'), node('b'), node('c')]
    const edges = [
      edge('a', 'b', { basis: ['shared_person'], shared_persons: ['fujimori'] }),
      edge('b', 'c', { basis: ['shared_person', 'shared_country'], shared_persons: ['fujimori'], shared_countries: ['PE'] }),
    ]
    expect(sharedBasisNames(nodes, edges)).toEqual(['fujimori'])
  })

  it('coverage-country overlap stays context-only, never confirmed', () => {
    const nodes = [node('a'), node('b')]
    const edges = [edge('a', 'b', {
      basis: ['shared_country'], semantic_sim: null, shared_countries: ['PE'],
    })]
    expect(clusterStrength(nodes, edges)).toBe('context')
    expect(connectionState(deriveClusters(nodes, edges), edges)).toBe('context-only')
  })
})

describe('connectionsSummaryLines — strength framing survives to export', () => {
  it('labels a semantic-only cluster SIMILAR ONLY with a hypothesis caveat', () => {
    const nodes = [node('a'), node('b')]
    const edges = [edge('a', 'b', { semantic_sim: 0.93 })] // semantic-only
    const data: ConnectionsData = { contract: 'x', nodes, edges, distributions: null, unresolved: [] }
    const lines = connectionsSummaryLines(data, deriveClusters(nodes, edges)).join('\n')
    expect(lines).toContain('SIMILAR ONLY')
    expect(lines).toContain('hypothesis')
    expect(lines).toContain('similarity-only')
  })

  it('labels a shared-actor cluster CONFIRMED with the linking actor', () => {
    const nodes = [node('a'), node('b')]
    const edges = [edge('a', 'b', { basis: ['shared_person'], shared_persons: ['fujimori'] })]
    const data: ConnectionsData = { contract: 'x', nodes, edges, distributions: null, unresolved: [] }
    const lines = connectionsSummaryLines(data, deriveClusters(nodes, edges)).join('\n')
    expect(lines).toContain('CONFIRMED')
    expect(lines).toContain('Linked via fujimori')
  })
})

describe('connectionTopicIds', () => {
  it('resolves thread/theme pins and dedupes', () => {
    const inv = {
      pins: [
        { anchorId: 'dynamic-topic-1', anchorType: 'thread', label: 'x', pinnedAt: '' },
        { anchorId: 'theme-armed-conflict', anchorType: 'theme', label: 'y', pinnedAt: '' },
        { anchorId: 'dynamic-topic-1', anchorType: 'thread', label: 'dup', pinnedAt: '' },
        { anchorId: 'country-US', anchorType: 'country', label: 'us', pinnedAt: '' },
      ],
    } as unknown as Investigation
    const ids = connectionTopicIds(inv)
    expect(ids).toContain('dynamic-topic-1')
    expect(ids).toContain('armed-conflict')
    expect(ids.filter(i => i === 'dynamic-topic-1').length).toBe(1)
  })
})

// ── Frank v2: text-mention tier + cross-refs + lens + umbrella guard + windows ──

import {
  labelKeyTokens, headlineMentionTerm, buildFrozenCrossRefs, coverageLensNote,
  umbrellaChildDivergence, UMBRELLA_DIVERGENCE_MAX,
  nodeStoryWindow, investigationStoryWindow, connectionState,
} from './dossierConnections'
import type { WorkbenchPin } from './workbench'

describe('text-mention edge tier (Frank v2 blocker 1)', () => {
  it('edgeStrength: text_mention sits between strong and weak', () => {
    expect(edgeStrength(edge('a', 'b', { basis: ['semantic', 'text_mention'], text_mentions: ['nato summit'] }))).toBe('text')
    expect(edgeStrength(edge('a', 'b', { shared_persons: ['tayyip erdogan'], basis: ['shared_person', 'text_mention'], text_mentions: ['x'] }))).toBe('strong')
    expect(edgeStrength(edge('a', 'b'))).toBe('weak')
  })

  it('clusterStrength: text-linked cluster is neither confirmed nor caution', () => {
    const nodes = [node('a'), node('b')]
    expect(clusterStrength(nodes, [edge('a', 'b', { basis: ['text_mention'], text_mentions: ['nato summit'] })])).toBe('text')
  })

  it('connectionState maps a single text cluster to text-linked', () => {
    const nodes = [node('a'), node('b')]
    const edges = [edge('a', 'b', { basis: ['text_mention'], text_mentions: ['nato summit'] })]
    expect(connectionState(deriveClusters(nodes, edges), edges)).toBe('text-linked')
  })

  it('edgeReason quotes the mention term', () => {
    expect(edgeReason(edge('a', 'b', { basis: ['text_mention'], semantic_sim: null, text_mentions: ['nato summit'] })))
      .toContain('evidence text mentions “nato summit”')
  })
})

describe('labelKeyTokens / headlineMentionTerm', () => {
  it('drops stopwords and short tokens', () => {
    expect(labelKeyTokens('NATO Summit Ankara')).toEqual(['nato', 'summit', 'ankara'])
    expect(labelKeyTokens('The News of the Day')).toEqual(['day'])
  })

  it('finds the NATO-summit case, needs >=2 tokens for multi-token labels', () => {
    const tokens = labelKeyTokens('NATO Summit Ankara')
    expect(headlineMentionTerm('Trump orders cutoff of U.S. trade with Spain during NATO summit', tokens))
      .toBe('nato summit')
    expect(headlineMentionTerm('Leaders gather for climate summit in Belem', tokens)).toBeNull()
  })

  it('single-token label fires on one match', () => {
    expect(headlineMentionTerm('Protests spread across Venezuela', labelKeyTokens('Venezuela'))).toBe('venezuela')
  })
})

describe('buildFrozenCrossRefs (the killer blocker, frozen side)', () => {
  const pin = (anchorId: string, label: string, headlines: string[]): WorkbenchPin => ({
    anchorId, anchorType: 'thread', label, pinnedAt: '2026-07-08T00:00:00Z',
    snapshot: { capturedAt: '2026-07-08T00:00:00Z', evidence: headlines.map(h => ({ headline: h })) },
  })
  const dataOf = (nodes: ConnectionNode[], edges: ConnectionEdge[]): ConnectionsData => ({
    contract: 'dossier-connections-v1', nodes, edges, distributions: null, unresolved: [],
  })

  it('flags an isolated pin whose frozen headline mentions another pin label', () => {
    const pins = [
      pin('dynamic-topic-390', 'Trump Tariff Orders', ['Trump orders cutoff of U.S. trade with Spain during NATO summit']),
      pin('theme-dynamic-topic-2044', 'NATO Summit Ankara', ['Ankara hosts alliance leaders']),
    ]
    const refs = buildFrozenCrossRefs(pins, dataOf([node('dynamic-topic-390'), node('dynamic-topic-2044')], []))
    expect(refs).toHaveLength(1)
    expect(refs[0].pinLabel).toBe('Trump Tariff Orders')
    expect(refs[0].otherLabel).toBe('NATO Summit Ankara')
    expect(refs[0].term).toBe('nato summit')
  })

  it('skips pairs the measured graph already links', () => {
    const pins = [
      pin('dynamic-topic-1', 'Trump Tariff Orders', ['Trade cutoff during NATO summit']),
      pin('dynamic-topic-2', 'NATO Summit Ankara', []),
    ]
    const linked = dataOf(
      [node('dynamic-topic-1'), node('dynamic-topic-2')],
      [edge('dynamic-topic-1', 'dynamic-topic-2', { basis: ['text_mention'], text_mentions: ['nato summit'] })],
    )
    expect(buildFrozenCrossRefs(pins, linked)).toHaveLength(0)
  })
})

describe('coverageLensNote (Frank v2 blocker 6)', () => {
  it('names a dominant non-English language with its share', () => {
    const note = coverageLensNote([{ lang: 'en', n: 24 }, { lang: 'ro', n: 19 }])
    expect(note).toContain('Romanian-language sources (44%)')
    expect(note).toContain('findings reflect that vantage')
  })
  it('flags an overwhelmingly English lens too', () => {
    expect(coverageLensNote([{ lang: 'en', n: 90 }, { lang: 'es', n: 5 }])).toContain('English-language')
  })
  it('stays silent on balanced or thin coverage', () => {
    expect(coverageLensNote([{ lang: 'en', n: 3 }, { lang: 'ro', n: 2 }])).toBeNull()
    expect(coverageLensNote([{ lang: 'en', n: 40 }, { lang: 'es', n: 20 }, { lang: 'fr', n: 20 }, { lang: 'de', n: 20 }])).toBeNull()
  })
})

describe('umbrellaChildDivergence (Frank v2 blocker 5)', () => {
  const umb = (label: string, childLabels: string[]): ConnectionNode => node('u1', {
    label, is_umbrella: true, child_count: childLabels.length,
    facets: [{ facet: 'core', topic_count: childLabels.length, evidence_n: 1, countries: [], topics: childLabels.map((l, i) => ({ id: `c${i}`, label: l })) }],
  })

  it('coherent fold: children share the parent key tokens', () => {
    const u = umb('Venezuela Earthquake', ['Venezuela Earthquake Death Toll', 'Venezuela Earthquake Rescues'])
    expect(umbrellaChildDivergence(u)).toBe(0)
  })

  it('garbage fold: Khamenei Funeral under Trump-Putin Talks diverges', () => {
    const u = umb('Trump-Putin Talks on Ukraine', ['Khamenei Funeral', 'France Heatwave and Violence', 'Germany Policy Changes', 'Trump Putin Ukraine Ceasefire'])
    const d = umbrellaChildDivergence(u)!
    expect(d).toBeGreaterThan(UMBRELLA_DIVERGENCE_MAX)
  })

  it('one shared token does not make a long child coherent (live NATO-Ankara fold)', () => {
    // the exact prod fold Frank flagged: only the self-named child is coherent.
    const u = umb('Trump-Putin Talks on Ukraine', [
      'France Heatwave and Violence', 'Trump-Putin Talks on Ukraine',
      'Germany Policy Changes', 'Khamenei Funeral and Trump Threats',
    ])
    expect(umbrellaChildDivergence(u)!).toBeGreaterThan(UMBRELLA_DIVERGENCE_MAX)
  })

  it('null when no child labels', () => {
    expect(umbrellaChildDivergence(node('x', { is_umbrella: true, facets: [] }))).toBeNull()
  })
})

describe('story windows (P0.3 dates)', () => {
  it('nodeStoryWindow prefers first_seen, ends at last evidence day', () => {
    const n = node('a', { first_seen: '2026-06-12T08:00:00Z', timeline: [{ day: '2026-07-01', n: 2 }, { day: '2026-07-08', n: 1 }] })
    expect(nodeStoryWindow(n)).toEqual({ first: '2026-06-12', last: '2026-07-08' })
  })
  it('falls back to the first evidence day; null without any dates', () => {
    expect(nodeStoryWindow(node('a', { timeline: [{ day: '2026-07-02', n: 1 }] }))).toEqual({ first: '2026-07-02', last: '2026-07-02' })
    expect(nodeStoryWindow(node('a'))).toBeNull()
  })
  it('investigationStoryWindow spans all nodes', () => {
    const w = investigationStoryWindow([
      node('a', { timeline: [{ day: '2026-07-02', n: 1 }] }),
      node('b', { first_seen: '2026-06-10', timeline: [{ day: '2026-07-09', n: 1 }] }),
    ])
    expect(w).toEqual({ first: '2026-06-10', last: '2026-07-09' })
  })
})

describe('connectionsSummaryLines carries the new honesty layers', () => {
  it('exports lens note, story window, text-linked tag and cross-ref warnings', () => {
    const nodes = [
      node('a', { label: 'Trump Tariff Orders', timeline: [{ day: '2026-07-08', n: 1 }] }),
      node('b', { label: 'NATO Summit Ankara', timeline: [{ day: '2026-07-05', n: 2 }] }),
    ]
    const edges = [edge('a', 'b', { basis: ['text_mention'], text_mentions: ['nato summit'] })]
    const data: ConnectionsData = { contract: 'v1', nodes, edges, distributions: null, unresolved: [] }
    const lines = connectionsSummaryLines(data, deriveClusters(nodes, edges), {
      lensNote: 'Coverage lens: this investigation\'s evidence leans Romanian-language sources (44%) — findings reflect that vantage.',
      crossRefs: [{ pinLabel: 'X', otherLabel: 'Y', term: 'nato summit', headline: 'h' }],
    }).join('\n')
    expect(lines).toContain('Romanian-language sources')
    expect(lines).toContain('Story windows:')
    expect(lines).toContain('TEXT-LINKED')
    expect(lines).toContain('Verify before calling “X” unrelated')
  })
})
