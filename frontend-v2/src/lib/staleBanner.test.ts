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
        expect(b.why).toBe('the last nightly publication did not complete')
        expect(b.liveNote).toBe('live view below is current')
        expect(b.nextAttempt).toBe('next seal attempt 02:30')
        expect(b.sentence).toBe(
            'Sealed edition from Jul 15 · sealed 2 days ago · the last nightly publication did not complete · live view below is current · next seal attempt 02:30',
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
        expect(why(['contract_mismatch'])).toBe('the sealed edition could not be read')
        expect(why(['candidate_universe_incomplete'])).toBe('the last nightly publication did not finish reconciling')
        expect(why(['edition_degraded'])).toBe('the last nightly publication did not complete')
        // stale by age with no explicit reason still reads honestly
        expect(why([])).toBe('the last nightly publication did not complete')
    })

    it('accepts a custom next-seal time', () => {
        const b = buildStaleBanner({
            sealedAt: null, editionDate: null, servedFromSeal: false, now: NOW, nextSealLocal: '03:00',
        })
        expect(b.nextAttempt).toBe('next seal attempt 03:00')
    })
})
