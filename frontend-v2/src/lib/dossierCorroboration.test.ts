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
  citationDay, citationDateText, citationAged, agedTip,
  corroborationWindowText, verdictFacets,
  type CorroborationData, type CorroborationCitation, type CorroborationPin,
  type CorroborationVerdict,
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

// ── V1 (tren B2): the honesty fields reach the page ──────────────────────────
// Frank's fresh test found corroborate-v2 fully implemented server-side and
// consumed by nobody: citations rendered no DATE (so an aged receipt was
// invisible), and the verdict block (template_matches / aged / window_days /
// official_corroborating) had zero frontend consumers.

describe('citation dates (Frank gap-3: an aged receipt was invisible)', () => {
  const cit = (over: Partial<CorroborationCitation>): CorroborationCitation =>
    ({ title: 't', url: 'https://x/y', outlet: 'x.com', ...over })

  it('parses the DOC 2.0 stamp and plain ISO alike', () => {
    expect(citationDay(cit({ seendate: '20260810T120000Z' }))).toBe('2026-08-10')
    expect(citationDay(cit({ seendate: '2026-08-10' }))).toBe('2026-08-10')
    expect(citationDay(cit({ seendate: '2026-08-10T09:31:00Z' }))).toBe('2026-08-10')
  })

  it('never invents a date it does not have', () => {
    expect(citationDay(cit({}))).toBeNull()
    expect(citationDay(cit({ seendate: null }))).toBeNull()
    expect(citationDay(cit({ seendate: 'sometime last week' }))).toBeNull()
    expect(citationDay(cit({ seendate: '20261332T120000Z' }))).toBeNull()
    expect(citationDateText(cit({}))).toBeNull()
  })

  it('renders the day short, like every other receipt in the report', () => {
    expect(citationDateText(cit({ seendate: '20260810T120000Z' }))).toBe('Aug 10')
  })
})

describe('per-row aged flag (R3: aged = context, never backing)', () => {
  const cit = (over: Partial<CorroborationCitation>): CorroborationCitation =>
    ({ title: 't', url: 'https://x/y', outlet: 'x.com', ...over })
  const measured = data({ measured_at: '2026-08-12T00:00:00Z', window_days: 7 })

  it('flags a receipt published outside the measured window', () => {
    expect(citationAged(cit({ seendate: '20260801T120000Z' }), measured)).toBe(true)
  })

  it('leaves receipts inside the window alone (boundary day counts as inside)', () => {
    expect(citationAged(cit({ seendate: '20260810T120000Z' }), measured)).toBe(false)
    expect(citationAged(cit({ seendate: '20260805T000000Z' }), measured)).toBe(false)
  })

  it('NEVER claims an undated receipt is aged — we do not measure what we lack', () => {
    expect(citationAged(cit({}), measured)).toBe(false)
    expect(citationAged(cit({ seendate: null }), measured)).toBe(false)
    expect(citationAged(cit({ lane: 'client-supplied' }), measured)).toBe(false)
  })

  it('says nothing when the measurement itself carries no window', () => {
    const noWindow = { ...measured, window_days: 0 } as CorroborationData
    expect(citationAged(cit({ seendate: '20250101T120000Z' }), noWindow)).toBe(false)
  })

  it('names the window in the tip', () => {
    expect(agedTip(7)).toContain('outside the 7-day window')
    expect(agedTip(7)).toContain('context')
  })
})

describe('window_days in the section header copy', () => {
  it('states the window as a sentence, not a bare number', () => {
    expect(corroborationWindowText(data({ window_days: 14 })))
      .toBe('receipts within the last 14 days')
    expect(corroborationWindowText(data({ window_days: 1 })))
      .toBe('receipts within the last 1 day')
  })
})

describe('verdictFacets (corroborate-v2 verdict block)', () => {
  const v = (over: Partial<CorroborationVerdict>): CorroborationVerdict => ({
    status: 'corroborated', corroborating: 7, contradicting: 0,
    official_corroborating: 0, note: 'corroborated by 7 source(s), none official/wire',
    template_matches: 5, aged: 0, window_days: 7, ...over,
  })

  it('renders the four v2 fields as inspectable facets', () => {
    const f = verdictFacets(v({ official_corroborating: 2, aged: 3 }))
    const labels = f.map(x => x.label)
    expect(labels).toContain('7 corroborating')
    expect(labels).toContain('2 official/wire')
    expect(labels).toContain('5 template-shaped set aside')
    expect(labels).toContain('3 outside the 7-day window')
  })

  it('says "none official/wire" rather than staying silent about it', () => {
    expect(verdictFacets(v({})).map(x => x.label)).toContain('none official/wire')
  })

  it('marks template + aged facets as set-aside so the render can mute them', () => {
    const f = verdictFacets(v({ aged: 1 }))
    expect(f.find(x => x.key === 'template')?.setAside).toBe(true)
    expect(f.find(x => x.key === 'aged')?.setAside).toBe(true)
    expect(f.find(x => x.key === 'corroborating')?.setAside).toBe(false)
  })

  it('shows contradictions when the verdict has them', () => {
    expect(verdictFacets(v({ contradicting: 2 })).map(x => x.label)).toContain('2 contradicting')
  })

  it('omits every zero and every field a pre-v2 verdict never carried', () => {
    const labels = verdictFacets({
      status: 'uncorroborated', corroborating: 0, contradicting: 0,
      official_corroborating: 0, note: 'no corroborating coverage found',
    }).map(x => x.label)
    expect(labels).not.toContain('none official/wire')   // nothing corroborated to qualify
    expect(labels.some(l => l.includes('template'))).toBe(false)
    expect(labels.some(l => l.includes('window'))).toBe(false)
  })

  it('returns nothing for an absent verdict — no verdict, no claim', () => {
    expect(verdictFacets(null)).toEqual([])
    expect(verdictFacets(undefined)).toEqual([])
  })
})

describe('markdown export carries the same honesty fields as the screen', () => {
  it('prints citation dates and marks aged rows', () => {
    const md = corroborationMarkdown(data({
      measured_at: '2026-08-12T00:00:00Z',
      window_days: 7,
      pins: [{
        id: 'p', label: 'Bases deal', status: 'established',
        independent_outlets: 2, total_articles: 3, syndicated_clusters: 1,
        single_source: false, note: 'measured',
        citations: [
          { title: 'Fresh', url: 'https://a/1', outlet: 'a.com', seendate: '20260810T120000Z' },
          { title: 'Old', url: 'https://b/2', outlet: 'b.com', seendate: '20260701T120000Z' },
        ],
        queries: [],
      }],
    })).join('\n')
    expect(md).toContain('a.com, Aug 10')
    expect(md).toContain('b.com, Jul 1')
    expect(md).toContain('outside the 7-day window')
    expect(md).toContain('receipts within the last 7 days')
  })

  it('prints the verdict facets when a pin carries a verdict', () => {
    const md = corroborationMarkdown(data({
      pins: [{
        id: 'p', label: 'Bases deal', status: 'established',
        independent_outlets: 2, total_articles: 3, syndicated_clusters: 1,
        single_source: false, note: 'measured', citations: [], queries: [],
        verdict: {
          status: 'corroborated', corroborating: 7, contradicting: 0,
          official_corroborating: 0, template_matches: 5, aged: 0, window_days: 7,
          note: 'corroborated by 7 source(s), none official/wire; 5 template-shaped match(es) set aside',
        },
      }],
    })).join('\n')
    expect(md).toContain('5 template-shaped set aside')
    expect(md).toContain('none official/wire')
  })
})

// ── tren B2 V5: partial/throttled states are RENDERABLE facts ───────────────
import {
  pinSearchStatusText, corroborationCoverageText, startCorroboration,
  pollCorroboration, runCorroborationJob,
} from './dossierCorroboration'

const cpin = (over: Partial<CorroborationPin>): CorroborationPin => ({
  id: 'p1', label: 'Syria Russia Bases Deal', status: 'established',
  independent_outlets: 5, independent_voices: 4, state_collapsed: 1,
  total_articles: 12, syndicated_clusters: 2, single_source: false,
  citations: [], note: '4 independent voices', queries: ['syria russia bases'],
  ...over,
})

const cdata = (over: Partial<CorroborationData>): CorroborationData => ({
  contract: 'dossier-corroboration-v1', measured_at: '2026-08-12T10:00:00Z',
  search_available: true, search_source: 'gdelt-doc-2.0', window_days: 14,
  pins: [], coverage_asymmetry: null,
  ...over,
})

describe('pinSearchStatusText', () => {
  it('says nothing when the pin was fully measured', () => {
    expect(pinSearchStatusText(cpin({ search_status: 'ok' }))).toBeNull()
    expect(pinSearchStatusText(cpin({ search_status: 'not_applicable' }))).toBeNull()
  })

  it('names the rate limit rather than a generic failure', () => {
    const t = pinSearchStatusText(cpin({ search_status: 'throttled' }))
    expect(t).toMatch(/throttled/i)
  })

  it('reports how much of a partial pin was measured', () => {
    const t = pinSearchStatusText(cpin({
      search_status: 'partial', queries_run: 2, queries_answered: 1,
    }))
    expect(t).toMatch(/1 of 2/)
  })

  it('a timed-out pin says so, never reads as zero coverage', () => {
    expect(pinSearchStatusText(cpin({ search_status: 'timeout' }))).toMatch(/time budget/i)
  })

  it('a pre-V5 payload with no search_status stays silent', () => {
    expect(pinSearchStatusText(cpin({}))).toBeNull()
  })
})

describe('corroborationCoverageText', () => {
  it('is null on a complete run', () => {
    expect(corroborationCoverageText(cdata({
      partial: false, pins_measured: 2, pins_applicable: 2,
    }))).toBeNull()
  })

  it('names the throttle and the measured fraction', () => {
    const t = corroborationCoverageText(cdata({
      partial: true, pins_measured: 1, pins_applicable: 3,
      pins: [cpin({ search_status: 'throttled' }), cpin({ id: 'p2', search_status: 'ok' })],
    }))
    expect(t).toMatch(/throttled/i)
    expect(t).toMatch(/1 of 3/)
    expect(t).toMatch(/2 pins not reached are shown/)
  })

  it('agrees with itself when exactly one pin was not reached', () => {
    const t = corroborationCoverageText(cdata({
      partial: true, pins_measured: 1, pins_applicable: 2,
      pins: [cpin({ search_status: 'throttled' }), cpin({ id: 'p2', search_status: 'ok' })],
    }))
    expect(t).toMatch(/the pin not reached is shown/)
  })

  it('a partially measured pin counts as measured AND says it was partial', () => {
    // Never a 0 next to an `established` verdict built on real receipts.
    const t = corroborationCoverageText(cdata({
      partial: true, pins_measured: 2, pins_partial: 1, pins_applicable: 3,
      pins: [cpin({ search_status: 'partial' }), cpin({ id: 'p2', search_status: 'ok' }),
             cpin({ id: 'p3', search_status: 'throttled' })],
    }))
    expect(t).toMatch(/2 of 3/)
    expect(t).toMatch(/1 of them only partially/)
  })

  it('never refers to a rest that does not exist', () => {
    const t = corroborationCoverageText(cdata({
      partial: true, pins_measured: 2, pins_partial: 2, pins_applicable: 2,
      pins: [cpin({ search_status: 'partial' }), cpin({ id: 'p2', search_status: 'partial' })],
    }))
    expect(t).not.toMatch(/the rest/)
    expect(t).toMatch(/all 2 evidence pins measured/)
  })

  it('a pre-V5 payload (no partial field) shows no banner', () => {
    expect(corroborationCoverageText(cdata({ pins: [cpin({})] }))).toBeNull()
  })
})

describe('job + poll', () => {
  beforeEach(() => { vi.restoreAllMocks() })

  it('start returns the job snapshot', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: true, json: async () => ({ job_id: 'abc', status: 'running', progress: { queries_done: 0, queries_total: 4 }, result: null }),
    })) as never)
    const started = await startCorroboration({ pins: [], days: 14 } as never, false)
    expect(started?.job_id).toBe('abc')
    expect(started?.status).toBe('running')
  })

  it('a cached start comes back done with the result inline', async () => {
    const result = cdata({ pins: [cpin({})] })
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: true, json: async () => ({ job_id: null, status: 'done', progress: {}, result }),
    })) as never)
    const started = await startCorroboration({ pins: [], days: 14 } as never, false)
    expect(started?.status).toBe('done')
    expect(started?.result?.pins).toHaveLength(1)
  })

  it('polls until done and returns the payload', async () => {
    const result = cdata({ pins: [cpin({})] })
    let calls = 0
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (String(url).includes('/start')) {
        return { ok: true, json: async () => ({ job_id: 'j1', status: 'running', progress: { queries_done: 0, queries_total: 2 }, result: null }) }
      }
      calls += 1
      return calls < 2
        ? { ok: true, json: async () => ({ job_id: 'j1', status: 'running', progress: { queries_done: 1, queries_total: 2 }, result: null }) }
        : { ok: true, json: async () => ({ job_id: 'j1', status: 'done', progress: { queries_done: 2, queries_total: 2 }, result }) }
    }) as never)
    const seen: number[] = []
    const out = await runCorroborationJob({ pins: [], days: 14 } as never, false, {
      pollMs: 1, onProgress: p => seen.push(p.queries_done ?? 0),
    })
    expect(out?.pins).toHaveLength(1)
    expect(seen.length).toBeGreaterThan(0)
  })

  it('a lost job resolves to null — never a fabricated empty result', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => (
      String(url).includes('/start')
        ? { ok: true, json: async () => ({ job_id: 'gone', status: 'running', progress: {}, result: null }) }
        : { ok: true, json: async () => ({ job_id: 'gone', status: 'unknown', progress: {}, result: null }) }
    )) as never)
    const out = await runCorroborationJob({ pins: [], days: 14 } as never, false, { pollMs: 1 })
    expect(out).toBeNull()
  })

  it('poll returns the snapshot as-is', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: true, json: async () => ({ job_id: 'j', status: 'running', progress: { queries_done: 1, queries_total: 3 }, result: null }),
    })) as never)
    const snap = await pollCorroboration('j')
    expect(snap?.progress.queries_total).toBe(3)
  })
})

describe('markdown carries the degraded state', () => {
  it('prints the coverage line when the run was partial', () => {
    const md = corroborationMarkdown(cdata({
      partial: true, pins_measured: 1, pins_applicable: 2,
      pins: [cpin({ search_status: 'throttled', note: 'web lane throttled' })],
    })).join('\n')
    expect(md).toMatch(/throttled/i)
    expect(md).toMatch(/1 of 2/)
  })
})
