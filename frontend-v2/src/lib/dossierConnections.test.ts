import { describe, it, expect } from 'vitest'
import {
  deriveClusters, layoutInvestigativeUniverse, edgeReason, connectionsSummaryLines,
  connectionTopicIds, deOverlapLabels,
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
