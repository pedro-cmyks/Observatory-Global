import { describe, it, expect } from 'vitest'
import { EVERGREEN_FACTS, buildRotation, factLabel, parseFacts, type DelightFact } from './delight'

const measured = (id: string): DelightFact => ({
    id, kind: 'measured', text: `fact ${id}`, window_hours: 24,
    measured_at: new Date().toISOString(),
})

describe('parseFacts', () => {
    it('accepts a valid payload and drops junk entries', () => {
        const payload = {
            contract: 'loading-delight-v0',
            facts: [
                measured('pulse'),
                { id: 'bad', kind: 'measured' }, // no text
                { id: 42, kind: 'measured', text: 'nope' }, // bad id
                { id: 'huge', kind: 'measured', text: 'x'.repeat(500) }, // too long
            ],
        }
        const facts = parseFacts(payload)
        expect(facts.map(f => f.id)).toEqual(['pulse'])
    })

    it('returns empty on garbage', () => {
        expect(parseFacts(null)).toEqual([])
        expect(parseFacts('nope')).toEqual([])
        expect(parseFacts({ facts: 'nope' })).toEqual([])
    })
})

describe('buildRotation', () => {
    it('is deterministic for a given seed and differs across seeds', () => {
        const m = [measured('a'), measured('b'), measured('c')]
        const r1 = buildRotation(m, EVERGREEN_FACTS, 20281)
        const r2 = buildRotation(m, EVERGREEN_FACTS, 20281)
        const r3 = buildRotation(m, EVERGREEN_FACTS, 20282)
        expect(r1.map(f => f.id)).toEqual(r2.map(f => f.id))
        expect(r1.map(f => f.id)).not.toEqual(r3.map(f => f.id))
    })

    it('contains every fact exactly once and leads with measured', () => {
        const m = [measured('a'), measured('b')]
        const rotation = buildRotation(m, EVERGREEN_FACTS, 7)
        expect(rotation).toHaveLength(m.length + EVERGREEN_FACTS.length)
        expect(new Set(rotation.map(f => f.id)).size).toBe(rotation.length)
        expect(rotation[0].kind).toBe('measured')
    })

    it('works with no measured facts (evergreen-only fallback)', () => {
        const rotation = buildRotation([], EVERGREEN_FACTS, 7)
        expect(rotation).toHaveLength(EVERGREEN_FACTS.length)
        expect(rotation.every(f => f.kind === 'evergreen')).toBe(true)
    })
})

describe('factLabel', () => {
    it('labels evergreen as about Atlas', () => {
        expect(factLabel(EVERGREEN_FACTS[0])).toBe('about Atlas')
    })

    it('labels fresh measured facts with the window', () => {
        expect(factLabel(measured('a'))).toBe('measured · last 24 h')
    })

    it('labels day-old measured facts as yesterday', () => {
        const f = measured('a')
        const now = Date.parse(f.measured_at!) + 30 * 60 * 60 * 1000
        expect(factLabel(f, now)).toBe('measured yesterday · 24 h window')
    })
})
