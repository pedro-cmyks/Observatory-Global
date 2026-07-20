import { describe, expect, it, vi, afterEach } from 'vitest'
import {
  extractSnapshotUrls, statesSettled, fullTextYield, stateTag,
  enqueueSnapshotFetch, fetchArticleStates, type ArticleState,
} from './articleEnrichment'

const A = 'https://example.com/a'
const B = 'https://example.com/b'

const st = (url: string, status: ArticleState['status']): ArticleState => ({ url, status })

afterEach(() => { vi.unstubAllGlobals() })

describe('extractSnapshotUrls', () => {
  it('dedupes, drops non-http and empty urls', () => {
    const urls = extractSnapshotUrls({ evidence: [
      { headline: 'h1', url: A }, { headline: 'h2', url: A },
      { headline: 'h3', url: ' ' }, { headline: 'h4' },
      { headline: 'h5', url: 'javascript:alert(1)' }, { headline: 'h6', url: B },
    ] })
    expect(urls).toEqual([A, B])
  })
  it('handles absent snapshots', () => {
    expect(extractSnapshotUrls(null)).toEqual([])
    expect(extractSnapshotUrls({ evidence: undefined })).toEqual([])
  })
})

describe('statesSettled', () => {
  it('unsettled while any url is unknown or in flight', () => {
    expect(statesSettled([A], new Map())).toBe(false)
    expect(statesSettled([A], new Map([[A, st(A, 'pending')]]))).toBe(false)
    expect(statesSettled([A], new Map([[A, st(A, 'queued')]]))).toBe(false)
  })
  it('settled on terminal states — including honest failures', () => {
    const m = new Map([[A, st(A, 'ok')], [B, st(B, 'paywall')]])
    expect(statesSettled([A, B], m)).toBe(true)
  })
})

describe('fullTextYield', () => {
  it('counts ok over attempted', () => {
    const m = new Map([[A, st(A, 'ok')], [B, st(B, 'error')]])
    expect(fullTextYield([A, B], m)).toEqual({ ok: 1, total: 2 })
  })
})

describe('stateTag', () => {
  it('is silent for ok, unknown and gate-rejected; honest for walls', () => {
    expect(stateTag(undefined)).toBeNull()
    expect(stateTag(st(A, 'ok'))).toBeNull()
    expect(stateTag(st(A, 'rejected'))).toBeNull()
    expect(stateTag(st(A, 'paywall'))).toMatch(/paywall/)
    expect(stateTag(st(A, 'robots'))).toMatch(/refused/)
    expect(stateTag(st(A, 'pending'))).toMatch(/fetching/)
  })
})

describe('network calls', () => {
  it('enqueueSnapshotFetch posts evidence urls, never throws on failure', () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error('down'))
    vi.stubGlobal('fetch', fetchMock)
    expect(() => enqueueSnapshotFetch({ evidence: [{ headline: 'h', url: A }] })).not.toThrow()
    expect(fetchMock).toHaveBeenCalledWith('/api/v2/research/articles/fetch', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ urls: [A] }),
    }))
  })
  it('enqueueSnapshotFetch no-ops without urls', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    enqueueSnapshotFetch({ evidence: [{ headline: 'no url' }] })
    expect(fetchMock).not.toHaveBeenCalled()
  })
  it('fetchArticleStates maps by url and degrades to empty on failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [{ url: A, status: 'ok', excerpt: 'x' }] }),
    }))
    const m = await fetchArticleStates([A, B])
    expect(m.get(A)?.status).toBe('ok')
    expect(m.has(B)).toBe(false)

    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    expect((await fetchArticleStates([A])).size).toBe(0)
  })
})
