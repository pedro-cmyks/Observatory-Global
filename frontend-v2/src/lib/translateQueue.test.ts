import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
    __configureTranslateQueue,
    __resetTranslateQueue,
    classifyBatchRow,
    classifyTextResponse,
    describeUnavailable,
    failureFromStatus,
    flushTranslateQueue,
    isTranslateCircuitOpen,
    translateFreeText,
    translateSignal,
    translateRetryAfterSeconds,
} from './translateQueue'
import { browserLanguage, setPageLanguage } from './pageLanguage'

type FetchMock = ReturnType<typeof vi.fn>

function jsonResponse(body: unknown, init?: { status?: number; headers?: Record<string, string> }) {
    const status = init?.status ?? 200
    return {
        ok: status >= 200 && status < 300,
        status,
        headers: { get: (k: string) => init?.headers?.[k.toLowerCase()] ?? null },
        json: async () => body,
    }
}

function batchRows(ids: number[], text = 'translated!') {
    return { translations: ids.map(id => ({ signal_id: id, translated: `${text} ${id}` })) }
}

let fetchMock: FetchMock

beforeEach(() => {
    __resetTranslateQueue()
    // flushMs 0 keeps the coalescing window but lets flushTranslateQueue drive.
    __configureTranslateQueue({ flushMs: 5 })
    fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
    vi.unstubAllGlobals()
    __resetTranslateQueue()
})

describe('signal lane — coalescing (the fix for the 20/300s paid bucket)', () => {
    it('collapses N concurrent headline requests into ONE batch POST', async () => {
        fetchMock.mockResolvedValue(jsonResponse(batchRows([1, 2, 3])))
        const p = Promise.all([
            translateSignal(1, 'en'),
            translateSignal(2, 'en'),
            translateSignal(3, 'en'),
        ])
        await flushTranslateQueue()
        const out = await p

        expect(fetchMock).toHaveBeenCalledTimes(1)
        const [url, init] = fetchMock.mock.calls[0]
        expect(url).toBe('/api/v2/translate/batch')
        expect(JSON.parse(init.body)).toEqual({ signal_ids: [1, 2, 3], to: 'en' })
        expect(out).toEqual([
            { status: 'ok', text: 'translated! 1' },
            { status: 'ok', text: 'translated! 2' },
            { status: 'ok', text: 'translated! 3' },
        ])
    })

    it('de-dupes the same signal id requested twice in one window', async () => {
        fetchMock.mockResolvedValue(jsonResponse(batchRows([7])))
        const p = Promise.all([translateSignal(7, 'en'), translateSignal(7, 'en')])
        await flushTranslateQueue()
        const [a, b] = await p
        expect(JSON.parse(fetchMock.mock.calls[0][1].body).signal_ids).toEqual([7])
        expect(a).toEqual(b)
    })

    it('splits into separate batches per target language', async () => {
        fetchMock.mockImplementation(async (_u: string, init: { body: string }) => {
            const ids = JSON.parse(init.body).signal_ids as number[]
            return jsonResponse(batchRows(ids))
        })
        const p = Promise.all([translateSignal(1, 'en'), translateSignal(2, 'es')])
        await flushTranslateQueue()
        await p
        expect(fetchMock).toHaveBeenCalledTimes(2)
        const langs = fetchMock.mock.calls.map(c => JSON.parse(c[1].body).to).sort()
        expect(langs).toEqual(['en', 'es'])
    })

    it('chunks above the server max_length so a big edition never 422s', async () => {
        fetchMock.mockImplementation(async (_u: string, init: { body: string }) => {
            const ids = JSON.parse(init.body).signal_ids as number[]
            expect(ids.length).toBeLessThanOrEqual(32)
            return jsonResponse(batchRows(ids))
        })
        const ids = Array.from({ length: 70 }, (_, i) => i + 1)
        const p = Promise.all(ids.map(id => translateSignal(id, 'en')))
        await flushTranslateQueue()
        const out = await p
        expect(fetchMock).toHaveBeenCalledTimes(3)
        expect(out.every(o => o.status === 'ok')).toBe(true)
    })
})

describe('default target — every lane aims at translationTarget() (panel-ciego 2026-08-18)', () => {
    afterEach(() => setPageLanguage(null))

    it('signal lane without an explicit target posts the PICKER choice, not the browser language', async () => {
        setPageLanguage('es') // navigator (node fallback) is en — es must win
        fetchMock.mockResolvedValue(jsonResponse(batchRows([11])))
        const p = translateSignal(11)
        await flushTranslateQueue()
        await p
        expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ signal_ids: [11], to: 'es' })
    })

    it('free-text lane without an explicit target posts the picker choice too', async () => {
        setPageLanguage('es')
        fetchMock.mockResolvedValue(jsonResponse({ translated: 'hola' }))
        await translateFreeText('bonjour tout le monde')
        expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
            text: 'bonjour tout le monde',
            target_lang: 'es',
        })
    })

    it('with no choice stored, the default target is the browser language (auto)', async () => {
        fetchMock.mockResolvedValue(jsonResponse(batchRows([12])))
        const p = translateSignal(12)
        await flushTranslateQueue()
        await p
        expect(JSON.parse(fetchMock.mock.calls[0][1].body).to).toBe(browserLanguage())
    })
})

describe('signal lane — honest outcomes', () => {
    it('a row the provider could not translate is UNAVAILABLE, not "no translation"', async () => {
        fetchMock.mockResolvedValue(jsonResponse({
            translations: [{ signal_id: 5, translated: null, error: 'translate_failed' }],
        }))
        const p = translateSignal(5, 'en')
        await flushTranslateQueue()
        expect(await p).toEqual({ status: 'unavailable', reason: 'provider' })
    })

    it('a permanently untranslatable row (not_found / no_headline) is a settled NONE', async () => {
        fetchMock.mockResolvedValue(jsonResponse({
            translations: [{ signal_id: 6, translated: null, error: 'not_found' }],
        }))
        const p = translateSignal(6, 'en')
        await flushTranslateQueue()
        expect(await p).toEqual({ status: 'none' })
    })

    it('a network throw is UNAVAILABLE/network', async () => {
        fetchMock.mockRejectedValue(new Error('offline'))
        const p = translateSignal(9, 'en')
        await flushTranslateQueue()
        expect(await p).toEqual({ status: 'unavailable', reason: 'network' })
    })

    it('a signal missing from the response is unavailable, never silently dropped', async () => {
        fetchMock.mockResolvedValue(jsonResponse({ translations: [] }))
        const p = translateSignal(11, 'en')
        await flushTranslateQueue()
        expect(await p).toEqual({ status: 'unavailable', reason: 'provider' })
    })
})

describe('circuit breaker — a 429 must not become a stampede', () => {
    it('429 resolves rate_limited AND blocks further network calls for Retry-After', async () => {
        fetchMock.mockResolvedValue(jsonResponse({ detail: 'rate limit exceeded' }, {
            status: 429, headers: { 'retry-after': '300' },
        }))
        const first = translateSignal(1, 'en')
        await flushTranslateQueue()
        expect(await first).toEqual({ status: 'unavailable', reason: 'rate_limited' })
        expect(isTranslateCircuitOpen()).toBe(true)
        expect(translateRetryAfterSeconds()).toBeGreaterThan(0)

        // Everything after resolves INSTANTLY from the open circuit — zero extra
        // requests. This is what turns a rate-limited page from a retry storm
        // (which keeps the bucket permanently drained) into an honest state.
        fetchMock.mockClear()
        const later = await translateSignal(2, 'en')
        const laterText = await translateFreeText('bonjour le monde', 'en')
        expect(fetchMock).not.toHaveBeenCalled()
        expect(later).toEqual({ status: 'unavailable', reason: 'rate_limited' })
        expect(laterText).toEqual({ status: 'unavailable', reason: 'rate_limited' })
    })

    it('the circuit closes again once Retry-After elapses', async () => {
        let clock = 1_000_000
        __configureTranslateQueue({ flushMs: 5, now: () => clock })
        fetchMock.mockResolvedValue(jsonResponse({}, { status: 429, headers: { 'retry-after': '30' } }))
        const p = translateSignal(1, 'en')
        await flushTranslateQueue()
        await p
        expect(isTranslateCircuitOpen()).toBe(true)

        clock += 31_000
        expect(isTranslateCircuitOpen()).toBe(false)
        expect(translateRetryAfterSeconds()).toBe(null)

        fetchMock.mockResolvedValue(jsonResponse(batchRows([1])))
        const p2 = translateSignal(1, 'en')
        await flushTranslateQueue()
        expect(await p2).toEqual({ status: 'ok', text: 'translated! 1' })
    })

    it('a non-429 server error does NOT open the circuit (it is per-request, not global)', async () => {
        fetchMock.mockResolvedValue(jsonResponse({}, { status: 503 }))
        const p = translateSignal(1, 'en')
        await flushTranslateQueue()
        expect(await p).toEqual({ status: 'unavailable', reason: 'provider' })
        expect(isTranslateCircuitOpen()).toBe(false)
    })
})

describe('free-text lane', () => {
    it('translates and reports ok', async () => {
        fetchMock.mockResolvedValue(jsonResponse({ translated: 'Hello world', same: false }))
        expect(await translateFreeText('Hola mundo', 'en')).toEqual({ status: 'ok', text: 'Hello world' })
        const [url, init] = fetchMock.mock.calls[0]
        expect(url).toBe('/api/v2/translate/text')
        expect(JSON.parse(init.body)).toEqual({ text: 'Hola mundo', target_lang: 'en' })
    })

    it('same:true settles as NONE (no toggle, no retry, no lie)', async () => {
        fetchMock.mockResolvedValue(jsonResponse({ translated: 'Hello world', same: true }))
        expect(await translateFreeText('Hello world', 'en')).toEqual({ status: 'none' })
    })

    it('degraded:true is UNAVAILABLE/provider — the endpoint 200s but did not translate', async () => {
        fetchMock.mockResolvedValue(jsonResponse({ translated: 'Hola mundo', same: true, degraded: true }))
        expect(await translateFreeText('Hola mundo', 'en')).toEqual({ status: 'unavailable', reason: 'provider' })
    })

    it('429 is rate_limited and opens the shared circuit', async () => {
        fetchMock.mockResolvedValue(jsonResponse({}, { status: 429 }))
        expect(await translateFreeText('Hola mundo', 'en')).toEqual({ status: 'unavailable', reason: 'rate_limited' })
        expect(isTranslateCircuitOpen()).toBe(true)
    })

    it('de-dupes concurrent identical text (the same label renders in many rows)', async () => {
        fetchMock.mockResolvedValue(jsonResponse({ translated: 'Hello', same: false }))
        const [a, b] = await Promise.all([
            translateFreeText('Hola', 'en'),
            translateFreeText('Hola', 'en'),
        ])
        expect(fetchMock).toHaveBeenCalledTimes(1)
        expect(a).toEqual(b)
    })
})

describe('pure classifiers', () => {
    it('failureFromStatus separates rate limiting from provider failure', () => {
        expect(failureFromStatus(429)).toBe('rate_limited')
        expect(failureFromStatus(500)).toBe('provider')
        expect(failureFromStatus(422)).toBe('provider')
    })

    it('classifyBatchRow', () => {
        expect(classifyBatchRow({ signal_id: 1, translated: ' hi ' })).toEqual({ status: 'ok', text: 'hi' })
        expect(classifyBatchRow({ signal_id: 1, translated: null, error: 'no_headline' })).toEqual({ status: 'none' })
        expect(classifyBatchRow({ signal_id: 1, translated: null, error: 'no_api_key' }))
            .toEqual({ status: 'unavailable', reason: 'provider' })
        expect(classifyBatchRow(undefined)).toEqual({ status: 'unavailable', reason: 'provider' })
    })

    it('classifyTextResponse', () => {
        expect(classifyTextResponse({ translated: 'x', same: false })).toEqual({ status: 'ok', text: 'x' })
        expect(classifyTextResponse({ translated: 'x', same: true })).toEqual({ status: 'none' })
        expect(classifyTextResponse({ translated: 'x', degraded: true }))
            .toEqual({ status: 'unavailable', reason: 'provider' })
        expect(classifyTextResponse(null)).toEqual({ status: 'unavailable', reason: 'provider' })
    })

    it('describeUnavailable names the real cause — never a generic shrug', () => {
        expect(describeUnavailable('rate_limited', 300)).toBe('translation unavailable — rate limited, retry in ~5 min')
        expect(describeUnavailable('rate_limited', null)).toBe('translation unavailable — rate limited')
        expect(describeUnavailable('provider', null)).toBe('translation unavailable — translator did not answer')
        expect(describeUnavailable('network', null)).toBe('translation unavailable — no connection')
    })
})

describe('X2 casualty-guard withholding is named, not blamed on the provider', () => {
  it('translation_unverified maps to its own reason with honest copy', () => {
    const out = classifyBatchRow({ signal_id: 1, translated: null, error: 'translation_unverified' } as never)
    expect(out).toEqual({ status: 'unavailable', reason: 'unverified' })
    expect(describeUnavailable('unverified', null)).toContain('withheld')
    expect(describeUnavailable('unverified', null)).not.toContain('did not answer')
  })
})
