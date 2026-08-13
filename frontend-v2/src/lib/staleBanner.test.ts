import { describe, it, expect } from 'vitest'
import { buildStaleBanner } from './staleBanner'

const NOW = new Date('2026-07-17T09:00:00Z')

describe('buildStaleBanner', () => {
    it('fresh: sealed edition IS served — states what + how old + next attempt, no failure language', () => {
        const b = buildStaleBanner({
            sealedAt: '2026-07-17T02:30:00Z',
            editionDate: '2026-07-17',
            servedFromSeal: true,
            reasonCodes: [],
            now: NOW,
        })
        expect(b.tone).toBe('fresh')
        expect(b.served).toBe('sealed')
        expect(b.edition).toBe("Today's sealed edition · Jul 17")
        expect(b.age).toBe('sealed 6 hours ago')
        expect(b.nextAttempt).toBe('next seal attempt 02:30')
        // no "did not complete" alarm on a healthy sealed edition
        expect(b.sentence).not.toMatch(/did not complete/i)
        expect(b.sentence).toContain('Jul 17')
        expect(b.sentence).toContain('next seal attempt 02:30')
    })

    it('stale: sealed edition failed, live is served — says WHAT edition, WHY, live-below, WHEN', () => {
        const b = buildStaleBanner({
            sealedAt: '2026-07-15T02:30:00Z',
            editionDate: '2026-07-15',
            servedFromSeal: false,
            reasonCodes: ['edition_degraded', 'candidate_universe_incomplete'],
            now: NOW,
        })
        expect(b.tone).toBe('stale')
        expect(b.served).toBe('live')
        expect(b.edition).toBe('Sealed edition from Jul 15')
        expect(b.age).toBe('sealed 2 days ago')
        expect(b.why).toBe('last night’s edition did not finish building')
        expect(b.liveNote).toBe('live view below is current')
        expect(b.nextAttempt).toBe('next seal attempt 02:30')
        expect(b.sentence).toBe(
            'Sealed edition from Jul 15 · sealed 2 days ago · last night’s edition did not finish building · live view below is current · next seal attempt 02:30',
        )
    })

    it('none: no sealed edition ever — honest live-only, no invented age', () => {
        const b = buildStaleBanner({
            sealedAt: null,
            editionDate: null,
            servedFromSeal: false,
            reasonCodes: ['edition_unavailable'],
            now: NOW,
        })
        expect(b.tone).toBe('none')
        expect(b.served).toBe('live')
        expect(b.edition).toBe('No sealed edition yet')
        expect(b.age).toBeNull()
        expect(b.sentence).toBe(
            'No sealed edition yet · live view below is current · next seal attempt 02:30',
        )
    })

    it('age humanizes minutes / hours / days honestly', () => {
        const at = (iso: string) =>
            buildStaleBanner({ sealedAt: iso, editionDate: '2026-07-17', servedFromSeal: true, now: NOW }).age
        expect(at('2026-07-17T08:58:00Z')).toBe('sealed just now')
        expect(at('2026-07-17T08:20:00Z')).toBe('sealed 40 minutes ago')
        expect(at('2026-07-17T08:00:00Z')).toBe('sealed 1 hour ago')
        expect(at('2026-07-17T00:00:00Z')).toBe('sealed 9 hours ago')
        expect(at('2026-07-16T09:00:00Z')).toBe('sealed 1 day ago')
        expect(at('2026-07-14T09:00:00Z')).toBe('sealed 3 days ago')
    })

    it('why phrase reflects the dominant failure reason honestly', () => {
        const why = (codes: string[], sealedAt = '2026-07-15T02:30:00Z') =>
            buildStaleBanner({ sealedAt, editionDate: '2026-07-15', servedFromSeal: false, reasonCodes: codes, now: NOW }).why
        expect(why(['contract_mismatch'])).toBe('last night’s edition could not be opened')
        expect(why(['candidate_universe_incomplete'])).toBe('last night’s edition did not finish checking its own story list')
        expect(why(['edition_degraded'])).toBe('last night’s edition did not finish building')
        // stale by age with no explicit reason still reads honestly
        expect(why([])).toBe('last night’s edition did not finish building')
    })

    // X4 (2026-08-13) — blind college C5. "the sealed edition carried no
    // stories" was a named witness: four of eight personas could not parse the
    // page's own vocabulary. The FACT is unchanged; the words are the reader's.
    it('says what an empty seal means in words a non-analyst can read', () => {
        const b = buildStaleBanner({
            sealedAt: '2026-07-15T02:30:00Z', editionDate: '2026-07-15',
            servedFromSeal: false, reasonCodes: ['no_story_nodes'], now: NOW,
        })
        expect(b.why).toBe('last night’s edition was assembled empty')
        // The live escape stays in the same sentence — the reader's next
        // question ("so what am I looking at?") is answered where they are.
        expect(b.sentence).toContain('live view below is current')
    })

    it('keeps every why-phrase free of the page’s internal vocabulary', () => {
        const codes = [
            'contract_mismatch', 'no_story_nodes', 'seal_stale',
            'seal_time_unknown', 'edition_degraded', 'candidate_universe_incomplete',
        ]
        for (const code of codes) {
            const { why } = buildStaleBanner({
                sealedAt: '2026-07-15T02:30:00Z', editionDate: '2026-07-15',
                servedFromSeal: false, reasonCodes: [code], now: NOW,
            })
            // "sealed"/"seal" is the machine's word for the nightly build and
            // it is what the panel stumbled on. The banner's own label still
            // carries the dated "Sealed edition from Jul 15" — that one has a
            // date beside it and reads; this clause has to stand alone.
            expect(why.toLowerCase()).not.toContain('seal')
            expect(why.toLowerCase()).not.toContain('publication')
            expect(why.toLowerCase()).not.toContain('reconcil')
        }
    })

    it('accepts a custom next-seal time', () => {
        const b = buildStaleBanner({
            sealedAt: null, editionDate: null, servedFromSeal: false, now: NOW, nextSealLocal: '03:00',
        })
        expect(b.nextAttempt).toBe('next seal attempt 03:00')
    })
})

describe('buildStaleBanner · seal_schedule truth (council N10)', () => {
    it('renders relative time to the REAL next attempt when the backend serves it', () => {
        const b = buildStaleBanner({
            sealedAt: '2026-07-17T02:30:00Z',
            editionDate: '2026-07-17',
            servedFromSeal: true,
            reasonCodes: [],
            now: NOW, // 09:00Z
            nextAttemptAt: '2026-07-17T14:00:00Z', // 5h away
        })
        expect(b.nextAttempt).toBe('next seal attempt in 5 h (02:30)')
        expect(b.sentence).toContain('next seal attempt in 5 h (02:30)')
    })

    it('uses minutes under an hour', () => {
        const b = buildStaleBanner({
            sealedAt: '2026-07-17T02:30:00Z',
            editionDate: '2026-07-17',
            servedFromSeal: true,
            now: NOW,
            nextAttemptAt: '2026-07-17T09:40:00Z',
        })
        expect(b.nextAttempt).toBe('next seal attempt in 40 min (02:30)')
    })

    it('says an attempt is likely in progress when the schedule window is open', () => {
        const b = buildStaleBanner({
            sealedAt: '2026-07-15T02:30:00Z',
            editionDate: '2026-07-15',
            servedFromSeal: false,
            reasonCodes: ['edition_degraded'],
            now: NOW,
            nextAttemptAt: '2026-07-18T07:30:00Z',
            attemptWindowOpen: true,
        })
        expect(b.nextAttempt).toBe('seal attempt likely in progress')
    })

    it('falls back to the 02:30 constant when the backend does not serve the schedule', () => {
        const b = buildStaleBanner({
            sealedAt: '2026-07-17T02:30:00Z',
            editionDate: '2026-07-17',
            servedFromSeal: true,
            now: NOW,
        })
        expect(b.nextAttempt).toBe('next seal attempt 02:30')
    })

    it('a past nextAttemptAt (clock skew / stale payload) falls back to the constant, never "in -2 h"', () => {
        const b = buildStaleBanner({
            sealedAt: '2026-07-17T02:30:00Z',
            editionDate: '2026-07-17',
            servedFromSeal: true,
            now: NOW,
            nextAttemptAt: '2026-07-17T07:30:00Z', // already passed
        })
        expect(b.nextAttempt).toBe('next seal attempt 02:30')
    })
})
