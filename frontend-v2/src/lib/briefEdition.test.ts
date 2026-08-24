import { describe, it, expect } from 'vitest'
import { isCultureThread, splitEditionThreads, buildShareCaption, buildEditionFirstComment } from './briefEdition'

describe('isCultureThread', () => {
    it('trusts a served culture category', () => {
        expect(isCultureThread({ label: 'Anything', category: 'World Cup 2026' })).toBe(true)
        expect(isCultureThread({ label: 'Anything', category: 'sports-recruitment' })).toBe(true)
    })

    it('a served non-culture category wins over a culture-looking label', () => {
        // engine typed it — trust the engine, never re-classify by label
        expect(isCultureThread({ label: 'World Cup security operation', category: 'armed-conflict-escalation' })).toBe(false)
    })

    it('parent_domain works as the category carrier', () => {
        expect(isCultureThread({ label: 'x', parent_domain: 'celebrity-entertainment' })).toBe(true)
        expect(isCultureThread({ label: 'x', parent_domain: 'election-legitimacy' })).toBe(false)
    })

    it('falls back to label keywords only when no category is served', () => {
        expect(isCultureThread({ label: 'Mundial 2026: semifinales' })).toBe(true)
        expect(isCultureThread({ label: 'Sam Neill tribute — film culture' })).toBe(true)
        expect(isCultureThread({ label: 'Ceasefire talks stall' })).toBe(false)
    })
})

describe('splitEditionThreads', () => {
    it('partitions preserving order and dropping nothing', () => {
        const threads = [
            { thread_id: 'a', label: 'Ceasefire talks', category: 'armed-conflict-escalation' },
            { thread_id: 'b', label: 'World Cup semifinal', category: 'World Cup 2026' },
            { thread_id: 'c', label: 'Fuel subsidy unrest' },
            { thread_id: 'd', label: 'Festival season roundup' },
        ]
        const { world, culture } = splitEditionThreads(threads)
        expect(world.map(t => t.thread_id)).toEqual(['a', 'c'])
        expect(culture.map(t => t.thread_id)).toEqual(['b', 'd'])
        expect(world.length + culture.length).toBe(threads.length)
    })

    it('empty input -> two empty sections', () => {
        expect(splitEditionThreads([])).toEqual({ world: [], culture: [] })
    })
})

describe('buildShareCaption', () => {
    it('carries the lead and the measured base — and NO link', () => {
        const caption = buildShareCaption({
            leadLabel: 'Coalition force for Ukraine',
            signals: 150927,
            countries: 223,
            sources: 61336,
        })
        expect(caption).toContain('measured — not editorialized')
        expect(caption).toContain('Coalition force for Ukraine')
        expect(caption).toContain('150,927 signals')
        expect(caption).toContain('223 countries')
        // LinkedIn split: the caption never carries a link or placeholder —
        // the link goes in the first comment (buildEditionFirstComment).
        expect(caption).not.toContain('<your link>')
        expect(caption).not.toContain('Read today')
    })

    it('degrades honestly with no lead', () => {
        const caption = buildShareCaption({ leadLabel: null, signals: 10, countries: 2, sources: 3 })
        expect(caption).not.toContain('leads with')
        expect(caption).toContain('10 signals')
    })
})

describe('buildEditionFirstComment', () => {
    it('carries the caller-supplied link — the one place the link appears', () => {
        const comment = buildEditionFirstComment('https://atlas.example/brief')
        expect(comment).toBe('Read today\'s full Atlas Edition (free): https://atlas.example/brief')
    })
})
