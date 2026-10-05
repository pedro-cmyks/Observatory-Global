/** Static edition (2026-10-05): the path rule and the fetch shim. */
import { describe, it, expect } from 'vitest'
import { createStaticFetch, editionPathFor, isStaticEdition } from './staticEdition'


// The same examples live in backend/tests/test_build_static_edition.py —
// change both or the page asks for files the generator never wrote.
const EXAMPLES: Array<[string, string | null]> = [
    ['/api/v2/briefing?hours=24', '/edition/api/v2/briefing__hours=24.json'],
    ['/api/v2/country-edition?hours=24&cc=CO', '/edition/api/v2/country-edition__cc=CO&hours=24.json'],
    ['/api/v2/country-edition?cc=CO&hours=24', '/edition/api/v2/country-edition__cc=CO&hours=24.json'],
    ['/api/v2/nodes?focus_type=country&focus_value=US&hours=24&limit=5',
        '/edition/api/v2/nodes__focus_type=country&focus_value=US&hours=24&limit=5.json'],
    ['/api/v2/delight', '/edition/api/v2/delight.json'],
    ['/api/v2/investigation/daily-publication', '/edition/api/v2/investigation/daily-publication.json'],
    ['/api/v2/search/unified?q=hello%20world&hours=24', '/edition/api/v2/search/unified__hours=24&q=hello-world.json'],
    ['/health', '/edition/health.json'],
    ['/assets/flag.svg', null],
    ['https://example.com/api/v2/briefing', null],
]

describe('editionPathFor', () => {
    it.each(EXAMPLES)('%s → %s', (url, want) => {
        expect(editionPathFor(url)).toBe(want)
    })
})

describe('isStaticEdition', () => {
    it('is on only when the build flag is exactly "1"', () => {
        expect(isStaticEdition({ VITE_STATIC_EDITION: '1' })).toBe(true)
        expect(isStaticEdition({ VITE_STATIC_EDITION: 'true' })).toBe(false)
        expect(isStaticEdition({})).toBe(false)
    })
})

describe('createStaticFetch', () => {
    function fakeFetch(routes: Record<string, number>) {
        const calls: string[] = []
        const orig = (async (input: RequestInfo | URL) => {
            const url = typeof input === 'string' ? input : input.toString()
            calls.push(url)
            const status = routes[url] ?? 404
            return new Response(status === 200 ? '{"ok":true}' : '', { status, headers: { 'content-type': 'application/json' } })
        }) as typeof fetch
        return { calls, fetch: createStaticFetch(orig) }
    }

    it('routes API GETs to the snapshot file', async () => {
        const f = fakeFetch({ '/edition/api/v2/briefing__hours=24.json': 200 })
        const res = await f.fetch('/api/v2/briefing?hours=24')
        expect(res.status).toBe(200)
        expect(await res.json()).toEqual({ ok: true })
        expect(f.calls).toEqual(['/edition/api/v2/briefing__hours=24.json'])
    })

    it('answers a missing file with an honest 503, not a 404 HTML page', async () => {
        const f = fakeFetch({})
        const res = await f.fetch('/api/v2/theme/dynamic-topic-1?hours=24')
        expect(res.status).toBe(503)
        expect(await res.json()).toMatchObject({ error: 'static_edition', reason: 'not_in_edition' })
    })

    it('never sends a POST anywhere', async () => {
        const f = fakeFetch({})
        const res = await f.fetch('/api/v2/telemetry', { method: 'POST', body: '{}' })
        expect(res.status).toBe(503)
        expect(await res.json()).toMatchObject({ reason: 'no_server' })
        expect(f.calls).toEqual([])
    })

    it('leaves non-API requests alone', async () => {
        const f = fakeFetch({ '/assets/x.svg': 200 })
        await f.fetch('/assets/x.svg')
        expect(f.calls).toEqual(['/assets/x.svg'])
    })
})
