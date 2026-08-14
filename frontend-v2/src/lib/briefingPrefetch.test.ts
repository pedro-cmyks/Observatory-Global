import { readFileSync } from 'node:fs'
import { UI_COPY } from './uiCopy'
import { describe, it, expect, beforeEach } from 'vitest'
import { clearBriefingCache, readBriefingCache, updateCachedInsight, writeBriefingCache } from './briefingPrefetch'

const store: Record<string, string> = {}
globalThis.sessionStorage = {
  getItem: (k: string) => store[k] ?? null,
  setItem: (k: string, v: string) => { store[k] = v },
  removeItem: (k: string) => { delete store[k] },
  clear: () => { for (const k in store) delete store[k] },
  length: 0,
  key: () => null,
} as unknown as Storage

const CACHE_KEY = 'atlas_brief_prefetch'

beforeEach(() => sessionStorage.clear())

describe('readBriefingCache', () => {
  it('returns null when sessionStorage is empty', () => {
    expect(readBriefingCache(24)).toBeNull()
  })

  it('returns null when hours mismatch', () => {
    const payload = { briefing: { stats: {} }, insight: null, fetchedAt: Date.now(), hours: 24 }
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload))
    expect(readBriefingCache(168)).toBeNull()
  })

  it('returns null when cache is older than 4 minutes', () => {
    const payload = {
      briefing: { stats: {} },
      insight: 'test',
      fetchedAt: Date.now() - 5 * 60 * 1000,
      hours: 24,
    }
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload))
    expect(readBriefingCache(24)).toBeNull()
  })

  it('returns a stale-but-usable cache when explicitly allowed', () => {
    const briefing = { stats: { total_signals: 80 } }
    const payload = {
      briefing,
      insight: 'cached insight',
      fetchedAt: Date.now() - 5 * 60 * 1000,
      hours: 24,
    }
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload))

    expect(readBriefingCache(24, { allowStale: true })).toEqual({
      briefing,
      insight: 'cached insight',
      insightGeneratedAt: null,
      isStale: true,
    })
  })

  it('rejects cache older than the 24-hour stale ceiling', () => {
    const payload = {
      briefing: { stats: {} },
      insight: null,
      fetchedAt: Date.now() - 25 * 60 * 60 * 1000,
      hours: 24,
    }
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload))

    expect(readBriefingCache(24, { allowStale: true })).toBeNull()
  })

  it('returns cached data when fresh and hours match', () => {
    const briefing = { stats: { total_signals: 100 } }
    const payload = { briefing, insight: 'some insight', fetchedAt: Date.now(), hours: 24 }
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload))
    const result = readBriefingCache(24)
    expect(result).not.toBeNull()
    expect(result!.insight).toBe('some insight')
    expect(result!.briefing).toEqual(briefing)
    expect(result!.isStale).toBe(false)
  })

  it('returns null when sessionStorage contains malformed JSON', () => {
    sessionStorage.setItem(CACHE_KEY, '{bad json}')
    expect(readBriefingCache(24)).toBeNull()
  })
})

describe('updateCachedInsight — the analysis stops flickering', () => {
  it('folds a late insight into a cache that was written without one', () => {
    writeBriefingCache(24, { stats: {} })
    expect(readBriefingCache(24)!.insight).toBeNull()

    updateCachedInsight(24, 'the reading', '2026-08-13T09:00:00Z')

    const after = readBriefingCache(24)!
    expect(after.insight).toBe('the reading')
    expect(after.insightGeneratedAt).toBe('2026-08-13T09:00:00Z')
    expect(after.briefing).toEqual({ stats: {} })
  })

  it('never overwrites a held reading with nothing', () => {
    writeBriefingCache(24, { stats: {} }, 'held reading', '2026-08-13T09:00:00Z')
    updateCachedInsight(24, null)
    expect(readBriefingCache(24)!.insight).toBe('held reading')
  })

  it('does not cross windows', () => {
    writeBriefingCache(24, { stats: {} })
    updateCachedInsight(168, 'wrong window')
    expect(readBriefingCache(24)!.insight).toBeNull()
  })

  it('survives a corrupt cache without throwing into a render', () => {
    sessionStorage.setItem(CACHE_KEY, '{bad json}')
    expect(() => updateCachedInsight(24, 'x')).not.toThrow()
  })
})

describe('clearBriefingCache — retry means the network, not the cache', () => {
  it('drops the entry so a forced refetch cannot be short-circuited', () => {
    writeBriefingCache(24, { stats: {} }, 'reading')
    clearBriefingCache()
    expect(readBriefingCache(24, { allowStale: true })).toBeNull()
  })
})

describe('BriefNewspaper cache wiring', () => {
  const source = readFileSync(new URL('../pages/BriefNewspaper.tsx', import.meta.url), 'utf8')

  it('keeps stale data visible while revalidating and offers retry on failure', () => {
    expect(source).toContain('readBriefingCache(h, { allowStale: true })')
    // The notice itself now lives in the UI-copy catalogue (lib/uiCopy), so the
    // witness follows it there — and checks BOTH languages say the same thing,
    // which the bare English grep could not.
    expect(source).toContain("tr('brief.cache.stale')")
    expect(UI_COPY['brief.cache.stale'].en).toContain('cached brief')
    expect(UI_COPY['brief.cache.stale'].es).toContain('en caché')
    expect(source).toContain('onClick={() => fetchData(hours)}')
  })

  it('re-requests the insight when the cached payload never got one', () => {
    // Otherwise the cache hit is exactly the state that makes the analysis
    // vanish for the rest of the TTL.
    expect(source).toContain('fetchInsight')
  })
})
