/**
 * Warm-cache fetch shim (#239 slice 1, 2026-07-04).
 *
 * Pedro's pain: Brief↔App route switches unmount the whole tree, so every
 * console fetch re-fires and the user stares at loaders for data that is
 * seconds old. This shim gives the console a memory:
 *
 *   - GET responses for whitelisted /api/v2/* endpoints are cached
 *     (in-memory Map + sessionStorage mirror so full reloads warm too).
 *   - Only the FIRST request of each URL after a route change is served
 *     from cache (instant paint) — a real fetch still fires in the
 *     BACKGROUND to refresh the cache (stale-while-revalidate).
 *   - Every subsequent request for that URL (polls, refreshes) passes
 *     through untouched — LIVE data stays live, poll cadence unchanged.
 *
 * Honesty bounds: cache TTL 10 min (older entries are ignored), so the
 * instant paint is never older than the window a returning user expects;
 * the background revalidation replaces it within one poll cycle.
 */

const TTL_MS = 10 * 60 * 1000
const MAX_ENTRY_BYTES = 400_000 // skip giant payloads for the sessionStorage mirror
const SS_PREFIX = 'atlas_warm:'

const WHITELIST = /^\/api\/v2\/(nodes|flows|threads|anomalies|correlation|conflict-markers|disasters|briefing|universe|voice-mix|stats|heat\/countries|public-attention)([/?]|$)/

type Entry = { t: number; body: string; status: number; contentType: string }

const memCache = new Map<string, Entry>()
const seenThisGen = new Set<string>()

/** Route changed → the next request per URL may paint from cache again. */
export function bumpWarmCacheGeneration(): void {
    seenThisGen.clear()
}

function ssRead(url: string): Entry | null {
    try {
        const raw = sessionStorage.getItem(SS_PREFIX + url)
        return raw ? (JSON.parse(raw) as Entry) : null
    } catch { return null }
}

function ssWrite(url: string, e: Entry): void {
    try {
        if (e.body.length <= MAX_ENTRY_BYTES) sessionStorage.setItem(SS_PREFIX + url, JSON.stringify(e))
    } catch { /* quota — memory cache still works */ }
}

function getFresh(url: string): Entry | null {
    const e = memCache.get(url) ?? ssRead(url)
    if (!e) return null
    if (Date.now() - e.t > TTL_MS) return null
    return e
}

function store(url: string, e: Entry): void {
    memCache.set(url, e)
    ssWrite(url, e)
}

/** Install once (main.tsx). Idempotent. */
export function installWarmCache(): void {
    const w = window as unknown as { __atlasWarmCache?: boolean; fetch: typeof fetch }
    if (w.__atlasWarmCache) return
    w.__atlasWarmCache = true
    const orig = w.fetch.bind(window)

    w.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
        const method = (init?.method ?? (typeof input === 'object' && 'method' in input ? (input as Request).method : 'GET')).toUpperCase()

        if (method !== 'GET' || !WHITELIST.test(url)) return orig(input as RequestInfo, init)

        const firstThisGen = !seenThisGen.has(url)
        seenThisGen.add(url)

        const revalidate = () => orig(input as RequestInfo, init).then(async res => {
            if (res.ok) {
                const clone = res.clone()
                const body = await clone.text()
                store(url, { t: Date.now(), body, status: res.status, contentType: res.headers.get('content-type') ?? 'application/json' })
            }
            return res
        })

        if (firstThisGen) {
            const cached = getFresh(url)
            if (cached) {
                // instant paint from cache; refresh lands in the background
                revalidate().catch(() => { /* background refresh failure is silent */ })
                return new Response(cached.body, {
                    status: cached.status,
                    headers: { 'content-type': cached.contentType, 'x-atlas-warm-cache': '1' },
                })
            }
        }
        return revalidate()
    }) as typeof fetch
}
