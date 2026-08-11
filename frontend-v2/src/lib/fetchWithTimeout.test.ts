/** Council R4 DESKTOP-N26 — the bound that only 8 of the app's fetch sites had. */
import { describe, it, expect, vi, afterEach } from 'vitest'
import {
    DEFAULT_FETCH_TIMEOUT_MS,
    fetchJsonWithTimeout,
    fetchWithTimeout,
} from './fetchWithTimeout'

const realFetch = globalThis.fetch

afterEach(() => {
    globalThis.fetch = realFetch
    vi.useRealTimers()
})

/** A fetch that never settles unless its signal aborts — the hang this
 *  module exists to bound. */
function hangingFetch(): typeof globalThis.fetch {
    return ((_url: string, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
            init?.signal?.addEventListener('abort', () =>
                reject(Object.assign(new Error('aborted'), { name: 'AbortError' })))
        })) as unknown as typeof globalThis.fetch
}

describe('fetchWithTimeout', () => {
    it('rejects a hanging request instead of hanging forever', async () => {
        vi.useFakeTimers()
        globalThis.fetch = hangingFetch()
        const p = fetchWithTimeout('/api/v2/focus', { timeoutMs: 5000 })
        const assertion = expect(p).rejects.toThrow()
        await vi.advanceTimersByTimeAsync(5001)
        await assertion
    })

    it('passes a successful response straight through', async () => {
        globalThis.fetch = (async () => new Response('{"ok":1}', { status: 200 })) as typeof globalThis.fetch
        const res = await fetchWithTimeout('/x', { timeoutMs: 1000 })
        expect(res.status).toBe(200)
    })

    it('aborts when the parent signal aborts — the bounds compose', async () => {
        globalThis.fetch = hangingFetch()
        const parent = new AbortController()
        const p = fetchWithTimeout('/x', { timeoutMs: 60000, parentSignal: parent.signal })
        parent.abort()
        await expect(p).rejects.toThrow()
    })

    it('aborts immediately when the parent signal is already aborted', async () => {
        globalThis.fetch = hangingFetch()
        const parent = new AbortController()
        parent.abort()
        await expect(fetchWithTimeout('/x', { parentSignal: parent.signal })).rejects.toThrow()
    })

    it('has a default bound well under a user giving up', () => {
        expect(DEFAULT_FETCH_TIMEOUT_MS).toBeLessThanOrEqual(15000)
    })
})

describe('fetchJsonWithTimeout', () => {
    it('returns the fallback on timeout rather than never resolving', async () => {
        vi.useFakeTimers()
        globalThis.fetch = hangingFetch()
        const p = fetchJsonWithTimeout('/x', { items: [] }, { timeoutMs: 3000 })
        await vi.advanceTimersByTimeAsync(3001)
        expect(await p).toEqual({ items: [] })
    })

    it('returns the fallback on a non-2xx response', async () => {
        globalThis.fetch = (async () => new Response('nope', { status: 500 })) as typeof globalThis.fetch
        expect(await fetchJsonWithTimeout('/x', { items: [] })).toEqual({ items: [] })
    })

    it('returns parsed JSON on success', async () => {
        globalThis.fetch = (async () => new Response('{"items":[1,2]}', { status: 200 })) as typeof globalThis.fetch
        expect(await fetchJsonWithTimeout<{ items: number[] }>('/x', { items: [] })).toEqual({ items: [1, 2] })
    })
})
