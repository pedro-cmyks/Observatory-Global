/**
 * Static edition (2026-10-05).
 *
 * Atlas no longer has a server behind the public page. The author runs the
 * pipeline on his own machine and publishes a snapshot: the frontend bundle
 * plus the JSON the Brief needs, as plain files under /edition/. This module
 * is the frontend half of that contract — the backend half is
 * backend/scripts/build_static_edition.py, which writes the files using the
 * SAME path rule (keep the two in lockstep; both are tested against the same
 * examples).
 *
 * Path rule: `/api/v2/country-edition?hours=24&cc=CO`
 *         → `/edition/api/v2/country-edition__cc=CO&hours=24.json`
 *   - query params sorted by key, then value;
 *   - values keep [A-Za-z0-9_.-]; anything else becomes `-`;
 *   - no query → no `__` suffix: `/edition/api/v2/delight.json`;
 *   - `/health` (the landing counter) → `/edition/health.json`.
 *
 * Honesty: anything the edition does not carry — a POST, a parameter
 * combination that was not snapshotted — gets a 503 with reason
 * `static_edition`, never a silent empty payload. The page's existing error
 * states render that as "unavailable", which is the truth.
 */

export const EDITION_PREFIX = '/edition'
export const META_PATH = `${EDITION_PREFIX}/meta.json`

export interface EditionMeta {
    /** ISO moment the snapshot was generated. */
    generated_at: string
    /** ISO moment of the newest signal in the data behind the snapshot. */
    data_through: string | null
    /** Country codes that have a country edition in this snapshot. */
    countries: string[]
    /** Snapshot contract version. */
    version: string
}

export function isStaticEdition(env: Record<string, unknown> = import.meta.env as unknown as Record<string, unknown>): boolean {
    return env.VITE_STATIC_EDITION === '1'
}

function sanitize(value: string): string {
    return value.replace(/[^A-Za-z0-9_.-]/g, '-')
}

/**
 * The file an API GET resolves to in the published snapshot, or null when the
 * URL is not an API call (same-origin assets, external sites).
 */
export function editionPathFor(url: string): string | null {
    let parsed: URL
    try {
        parsed = new URL(url, 'http://atlas.local')
    } catch {
        return null
    }
    if (parsed.origin !== 'http://atlas.local' && !url.startsWith('/')) return null
    // /health is the one non-/api call the pages make (the landing counter).
    if (!parsed.pathname.startsWith('/api/') && parsed.pathname !== '/health') return null
    const path = parsed.pathname.replace(/\/+$/, '')
    const params = Array.from(parsed.searchParams.entries())
        .map(([k, v]) => [sanitize(k), sanitize(v)] as const)
        .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0))
    const query = params.map(([k, v]) => `${k}=${v}`).join('&')
    return `${EDITION_PREFIX}${path}${query ? `__${query}` : ''}.json`
}

function unavailable(reason: string): Response {
    return new Response(
        JSON.stringify({ error: 'static_edition', reason, detail: 'Not part of the published edition.' }),
        { status: 503, headers: { 'content-type': 'application/json', 'x-atlas-static': reason } },
    )
}

/**
 * The fetch that routes every API call to the snapshot, built over the real
 * one. Pure factory so it is testable without a DOM.
 */
export function createStaticFetch(orig: typeof fetch): typeof fetch {
    return (async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
        const target = editionPathFor(url)
        if (target === null) return orig(input as RequestInfo, init)
        const method = (init?.method ?? (typeof input === 'object' && 'method' in input ? (input as Request).method : 'GET')).toUpperCase()
        if (method !== 'GET') return unavailable('no_server')
        const res = await orig(target, { signal: init?.signal, headers: { accept: 'application/json' } })
        if (res.status === 404) return unavailable('not_in_edition')
        return res
    }) as typeof fetch
}

/**
 * Install on window. Must run BEFORE the warm-cache shim so the cache's
 * "real" fetch is this one. Idempotent.
 */
export function installStaticEdition(opts: { enabled?: boolean } = {}): void {
    const enabled = opts.enabled ?? isStaticEdition()
    if (!enabled || typeof window === 'undefined') return
    const w = window as unknown as { __atlasStaticEdition?: boolean; fetch: typeof fetch }
    if (w.__atlasStaticEdition) return
    w.__atlasStaticEdition = true
    w.fetch = createStaticFetch(w.fetch.bind(window))
}
