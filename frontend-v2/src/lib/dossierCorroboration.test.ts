// P0.6b web corroboration — request builder, chips, markdown, cache.
import { describe, it, expect, beforeEach, vi } from 'vitest'

// vitest runs in node: back localStorage with a Map.
const backing = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (k: string) => backing.get(k) ?? null,
  setItem: (k: string, v: string) => void backing.set(k, String(v)),
  removeItem: (k: string) => void backing.delete(k),
  clear: () => backing.clear(),
})

import {
  buildCorroborationRequest, statusChip, corroborationMarkdown,
  loadCachedCorroboration, saveCorroboration, clearCorroboration,
  type CorroborationData,
} from './dossierCorroboration'
import type { WorkbenchPin } from './workbench'
import type { ConnectionNode } from './dossierConnections'

const pin = (over: Partial<WorkbenchPin>): WorkbenchPin => ({
  anchorId: 'dynamic-topic-390',
  anchorType: 'thread',
  label: 'NATO Summit Ankara',
  pinnedAt: '2026-07-11T00:00:00Z',
  ...over,
})

const node = (over: Partial<ConnectionNode>): ConnectionNode => ({
  id: 'dynamic-topic-390', base_id: 'dynamic-topic-390', label: 'NATO Summit Ankara',
  category: null, pos: null, countries: [], persons: [], languages: [],
  sentiment: null, roleCounts: { evidence: 0, discussion: 0, mood: 0 },
  timeline: [], has_centroid: true, n: 10,
  ...over,
})

describe('buildCorroborationRequest', () => {
  it('carries id, label, frozen evidence with attribution', () => {
    const req = buildCorroborationRequest([pin({
      snapshot: {
        capturedAt: '2026-07-11T00:00:00Z',
        evidence: [{ headline: 'Erdogan opens summit', source: 'aljazeera.com', date: '2026-07-08' }],
      },
    })])
    expect(req.pins).toHaveLength(1)
    expect(req.pins[0].id).toBe('dynamic-topic-390')
    expect(req.pins[0].evidence[0]).toBe('Erdogan opens summit — aljazeera.com, 2026-07-08')
    expect(req.days).toBe(14)
  })

  it('pulls measured actors from the matching connection node', () => {
    const req = buildCorroborationRequest(
      [pin({})],
      [node({ persons: ['recep tayyip erdogan', 'donald trump', 'mark rutte', 'extra'] })],
    )
    expect(req.pins[0].actors).toEqual(['recep tayyip erdogan', 'donald trump', 'mark rutte'])
  })

  it('matches umbrella nodes via collapsed_from', () => {
    const req = buildCorroborationRequest(
      [pin({ anchorId: 'dynamic-topic-999' })],
      [node({ id: 'dynamic-topic-1', base_id: 'dynamic-topic-1', collapsed_from: ['dynamic-topic-999'], persons: ['erdogan'] })],
    )
    expect(req.pins[0].actors).toEqual(['erdogan'])
  })

  it('caps at 8 pins and tolerates missing snapshot/nodes', () => {
    const pins = Array.from({ length: 10 }, (_, i) => pin({ anchorId: `dt-${i}` }))
    const req = buildCorroborationRequest(pins, null)
    expect(req.pins).toHaveLength(8)
    expect(req.pins[0].actors).toEqual([])
    expect(req.pins[0].evidence).toEqual([])
  })
})

describe('statusChip', () => {
  it('maps the three statuses', () => {
    expect(statusChip('established')).toBe('✓ established')
    expect(statusChip('contested')).toBe('⚠ contested')
    expect(statusChip('unverified')).toBe('? unverified')
  })
})

const data = (over: Partial<CorroborationData>): CorroborationData => ({
  contract: 'dossier-corroboration-v0',
  measured_at: new Date().toISOString(),
  search_available: true,
  search_source: 'gdelt-doc-2.0',
  window_days: 14,
  pins: [{
    id: 'dynamic-topic-390', label: 'NATO Summit Ankara', status: 'established',
    independent_outlets: 4, total_articles: 12, syndicated_clusters: 2,
    single_source: false, note: '4 independently-operated outlets (syndicated copies collapsed)',
    citations: [{ title: 'Erdogan hosts 36th NATO summit', url: 'https://nato.int/x', outlet: 'nato.int' }],
    queries: ['nato summit ankara'],
  }],
  coverage_asymmetry: { note: 'Web leads with Trump drama; pins lead with Erdogan.', provider: 'deepseek' },
  ...over,
})

describe('corroborationMarkdown', () => {
  it('renders the labeled section with chips, citations, asymmetry', () => {
    const md = corroborationMarkdown(data({})).join('\n')
    expect(md).toContain('## Web corroboration — measured')
    expect(md).toContain('independent sources weighted')
    expect(md).toContain('✓ established — NATO Summit Ankara')
    expect(md).toContain('[Erdogan hosts 36th NATO summit](https://nato.int/x) — nato.int')
    expect(md).toContain('Coverage asymmetry')
    expect(md).toContain('Web leads with Trump drama')
  })

  it('degrades honestly when the search lane is unavailable', () => {
    const md = corroborationMarkdown(data({
      search_available: false, search_source: null, pins: [], coverage_asymmetry: null,
      meta: { search_note: 'no server-side web-search path answered' },
    })).join('\n')
    expect(md).toContain('no server-side web-search path answered')
    expect(md).not.toContain('✓')
  })
})

describe('corroboration cache', () => {
  beforeEach(() => localStorage.clear())

  it('round-trips per investigation', () => {
    const d = data({})
    saveCorroboration('inv-1', d)
    expect(loadCachedCorroboration('inv-1')?.pins[0].label).toBe('NATO Summit Ankara')
    expect(loadCachedCorroboration('inv-2')).toBeNull()
    clearCorroboration('inv-1')
    expect(loadCachedCorroboration('inv-1')).toBeNull()
  })

  it('expires stale entries (>24h)', () => {
    const stale = data({ measured_at: new Date(Date.now() - 25 * 3600 * 1000).toISOString() })
    saveCorroboration('inv-1', stale)
    expect(loadCachedCorroboration('inv-1')).toBeNull()
  })
})
