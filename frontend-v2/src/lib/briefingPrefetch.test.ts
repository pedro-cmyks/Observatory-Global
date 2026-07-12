import { readFileSync } from 'node:fs'
import { describe, it, expect, beforeEach } from 'vitest'
import { readBriefingCache } from './briefingPrefetch'

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

describe('BriefNewspaper cache wiring', () => {
  const source = readFileSync(new URL('../pages/BriefNewspaper.tsx', import.meta.url), 'utf8')

  it('keeps stale data visible while revalidating and offers retry on failure', () => {
    expect(source).toContain('readBriefingCache(h, { allowStale: true })')
    expect(source).toContain('Showing cached brief')
    expect(source).toContain('onClick={() => fetchData(hours)}')
  })
})
