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
  pinCountsText, citationTierChip, citationTierClass, citationCollapseNote,
  type CorroborationData, type CorroborationCitation, type CorroborationPin,
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
    expect(req.pins[0].anchor_type).toBe('thread')
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

  it('preserves every pin and tolerates missing snapshot/nodes', () => {
    const pins = Array.from({ length: 10 }, (_, i) => pin({ anchorId: `dt-${i}` }))
    const req = buildCorroborationRequest(pins, null)
    expect(req.pins).toHaveLength(10)
    expect(req.pins[0].actors).toEqual([])
    expect(req.pins[0].evidence).toEqual([])
  })
})

describe('statusChip', () => {
  it('maps every corroboration status', () => {
    expect(statusChip('established')).toBe('✓ established')
    expect(statusChip('contested')).toBe('⚠ contested')
    expect(statusChip('unverified')).toBe('? unverified')
    expect(statusChip('not_applicable')).toBe('— not applicable')
  })
})

const data = (over: Partial<CorroborationData>): CorroborationData => ({
  contract: 'dossier-corroboration-v1',
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

  // corroborate-v2 R1: the bar is independent VOICES (ownership-collapsed).
  // ria + tass + rt each writing their own copy = 3 outlets, 1 voice.
  it('reports VOICES and names the ownership collapse when the backend measured one', () => {
    const md = corroborationMarkdown(data({
      pins: [{
        id: 'dynamic-topic-1', label: 'Depot strike', status: 'unverified',
        independent_outlets: 4, independent_voices: 2, state_collapsed: 2,
        total_articles: 9, syndicated_clusters: 1, single_source: false,
        note: 'only 2 independent voice(s) (4 outlets; same-state outlets counted as one voice) — insufficient corroboration; treat as single-sourced',
        citations: [
          {
            title: 'Strikes hit depot overnight', url: 'https://ria.ru/x', outlet: 'ria.ru',
            ownership_group: 'state:ru',
            credibility: { tier: 5, label: 'state', provenance: 'domain-list' },
          },
          { title: 'Depot fire after raid', url: 'https://cnn.com/y', outlet: 'cnn.com', ownership_group: null },
        ],
        queries: ['depot strike'],
      }],
    })).join('\n')
    expect(md).toContain('2 independent voices')
    expect(md).toContain('4 outlets')
    expect(md).toContain('same-owner outlets counted as one voice')
    expect(md).toContain('ria.ru [STATE]')
    // the un-grouped outlet carries no chip it did not earn
    expect(md).toContain('— cnn.com\n')
  })

  it('keeps a pre-v2 payload (no voices/ownership fields) rendering exactly as before', () => {
    const md = corroborationMarkdown(data({})).join('\n')
    expect(md).toContain('4 independent · 12 articles · 2 syndicated clusters')
    expect(md).not.toContain('voices')
  })

  it('degrades honestly when the search lane is unavailable', () => {
    const md = corroborationMarkdown(data({
      search_available: false, search_source: null, coverage_asymmetry: null,
      pins: [{
        id: 'country-ir', label: 'Iran', status: 'not_applicable',
        independent_outlets: 0, total_articles: 0, syndicated_clusters: 0,
        single_source: false, note: 'metadata-only context pin — no frozen evidence claim to corroborate',
        citations: [], queries: [],
      }],
      meta: { search_note: 'no server-side web-search path answered' },
    })).join('\n')
    expect(md).toContain('no server-side web-search path answered')
    expect(md).toContain('— not applicable — Iran')
  })
})

describe('citation credibility + ownership (corroborate-v2 R1)', () => {
  const cit = (over: Partial<CorroborationCitation>): CorroborationCitation =>
    ({ title: 't', url: 'https://x/y', outlet: 'x.com', ...over })

  it('shows only the tier the backend measured', () => {
    expect(citationTierChip(cit({ credibility: { tier: 5, label: 'state' } }))).toBe('[STATE]')
    expect(citationTierChip(cit({ credibility: { tier: 2, label: 'wire' } }))).toBe('[WIRE]')
    // absence over guess: no block, or an explicit unknown, shows nothing
    expect(citationTierChip(cit({}))).toBeNull()
    expect(citationTierChip(cit({ credibility: null }))).toBeNull()
    expect(citationTierChip(cit({ credibility: { tier: 4, label: 'unknown' } }))).toBeNull()
  })

  it('maps the backend tier vocabulary onto the shared chip classes', () => {
    expect(citationTierClass(cit({ credibility: { tier: 5, label: 'state' } }))).toBe('state')
    expect(citationTierClass(cit({ credibility: { tier: 2, label: 'wire' } }))).toBe('wire')
    // 'mainstream'/'reference' have no chip colour of their own — they reuse the
    // established major/wire hues rather than rendering an unstyled chip.
    expect(citationTierClass(cit({ credibility: { tier: 3, label: 'mainstream' } }))).toBe('major')
    expect(citationTierClass(cit({ credibility: { tier: 1, label: 'reference' } }))).toBe('wire')
    expect(citationTierClass(cit({}))).toBeNull()
  })

  it('explains the ownership collapse in plain words, and stays silent otherwise', () => {
    expect(citationCollapseNote(cit({ ownership_group: 'state:ru' })))
      .toContain('Same state apparatus (RU)')
    expect(citationCollapseNote(cit({ ownership_group: null }))).toBeNull()
    expect(citationCollapseNote(cit({}))).toBeNull()
  })

  it('pinCountsText: singular voice reads as one, plural as many', () => {
    const base: CorroborationPin = {
      id: 'p', label: 'l', status: 'unverified', independent_outlets: 3,
      total_articles: 5, syndicated_clusters: 1, single_source: false,
      citations: [], note: '', queries: [],
    }
    expect(pinCountsText({ ...base, independent_voices: 1, state_collapsed: 2 }))
      .toContain('1 independent voice ·')
    expect(pinCountsText({ ...base, independent_voices: 3, state_collapsed: 0 }))
      .not.toContain('same-owner')
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
