import { describe, expect, it, vi, afterEach } from 'vitest'
import { fetchCrossRead, fetchLeads, fetchReadings, readProvenance } from './aiRead'

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

describe('readProvenance', () => {
  it('names model and date, never bare AI', () => {
    expect(readProvenance({ model: 'deepseek-chat', read_at: '2026-07-20T10:00:00Z' }))
      .toBe('AI READ · deepseek-chat · 2026-07-20')
    expect(readProvenance(null)).toBe('AI READ')
  })
})
