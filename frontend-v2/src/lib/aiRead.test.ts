import { describe, expect, it, vi, afterEach } from 'vitest'
import {
  crossFindingLabel, crossFindingLabelLong, independenceTip,
  fetchCrossRead, fetchLeads, fetchReadings, readProvenance,
} from './aiRead'

afterEach(() => { vi.unstubAllGlobals() })

const A = 'https://x.com/a'
const B = 'https://x.com/b'

describe('fetchReadings', () => {
  it('maps readings by url and drops non-http inputs', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ readings: { [A]: { claims: [], actors: [], numbers: [], gaps: [] } } }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const m = await fetchReadings([A, 'javascript:x', ''])
    expect(m.has(A)).toBe(true)
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).urls).toEqual([A])
  })
  it('degrades to empty on failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    expect((await fetchReadings([A])).size).toBe(0)
  })
})

describe('fetchCrossRead', () => {
  it('requires two urls', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    expect(await fetchCrossRead([A])).toBeNull()
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('fetchLeads', () => {
  it('posts urls + pinned ids', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ leads: [], suppressed: [] }) })
    vi.stubGlobal('fetch', fetchMock)
    await fetchLeads([A, B], ['dynamic-topic-1'])
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body.urls).toEqual([A, B])
    expect(body.pinned_ids).toEqual(['dynamic-topic-1'])
  })
})

// corroborate-v2 R2 (G-HAARETZ): the backend now distinguishes DERIVATION —
// three rewrites of one Haaretz report, or two accounts built from the same
// quote set — from wire syndication. The render must not call either one
// "one wire source echoing itself".
describe('cross-read finding labels', () => {
  it('names the derivation reason, not a generic same-source', () => {
    expect(crossFindingLabel('shared_source', 'same_primary_source'))
      .toBe('⊘ 1 primary source (attributed)')
    expect(crossFindingLabel('shared_source', 'shared_quotes'))
      .toBe('⊘ same underlying quotes')
    // pre-v2 reasons keep their wording
    expect(crossFindingLabel('shared_source', 'same_wire')).toBe('⊘ same source (not independent)')
    expect(crossFindingLabel('shared_source')).toBe('⊘ same source (not independent)')
    expect(crossFindingLabel('tension')).toBe('⚠ possible tension')
    expect(crossFindingLabel('corroboration')).toBe('✓ corroboration')
  })

  it('spells the same distinction out for the export', () => {
    expect(crossFindingLabelLong('shared_source', 'same_primary_source'))
      .toBe('1 primary source (attributed) — not independent corroboration')
    expect(crossFindingLabelLong('shared_source', 'shared_quotes'))
      .toBe('Same underlying quotes — not independent corroboration')
    expect(crossFindingLabelLong('shared_source', 'same_wire'))
      .toBe('Same source (not independent corroboration)')
    expect(crossFindingLabelLong('tension')).toBe('Possible tension')
    expect(crossFindingLabelLong('corroboration')).toBe('Corroboration')
  })

  it('tips explain WHY each non-independent finding is not corroboration', () => {
    expect(independenceTip({ independent: true, reason: 'independent', label: '2 independent sources' }))
      .toContain('independent')
    expect(independenceTip({ independent: false, reason: 'same_primary_source', label: 'x' }))
      .toContain('attribut')
    expect(independenceTip({ independent: false, reason: 'shared_quotes', label: 'x' }))
      .toContain('quotes')
    // the pre-v2 wire wording survives for the reason it was written for
    expect(independenceTip({ independent: false, reason: 'same_wire', label: 'x' }))
      .toContain('wire')
  })
})

describe('readProvenance', () => {
  it('names model and date, never bare AI', () => {
    expect(readProvenance({ model: 'deepseek-chat', read_at: '2026-07-20T10:00:00Z' }))
      .toBe('AI READ · deepseek-chat · 2026-07-20')
    expect(readProvenance(null)).toBe('AI READ')
  })
})
