import { describe, it, expect } from 'vitest'
import { resolveThemeCountMeta } from './themeDetailCount'

// Timeout-as-absence (cc0bf804 class) + the stale loading window word.
// Contract: a degraded payload (total: null + degraded flag) renders
// "not measured", NEVER 0; while the first fetch is in flight the header
// prints no window word (the old branch stamped "Last 24h" beside "…").

describe('resolveThemeCountMeta', () => {
    it('first fetch in flight: ellipsis and NO window word', () => {
        const meta = resolveThemeCountMeta({ loading: true, hasData: false, hours: 24 })
        expect(meta.countText).toBe('…')
        expect(meta.windowLabel).toBeNull()
        expect(meta.unmeasured).toBe(false)
        expect(meta.notice).toBeNull()
    })

    it('degraded payload renders not measured, never 0', () => {
        const meta = resolveThemeCountMeta({
            loading: false, hasData: true, total: null,
            degraded: true, degradedReason: 'db_timeout', hours: 24,
        })
        expect(meta.countText).toBe('not measured')
        expect(meta.unmeasured).toBe(true)
        expect(meta.windowLabel).toBeNull()
        expect(meta.notice).toMatch(/timed out/i)
        expect(meta.notice).toMatch(/not zero/i)
    })

    it('db_error reason gets its own honest copy without driver internals', () => {
        const meta = resolveThemeCountMeta({
            loading: false, hasData: true, total: null,
            degraded: true, degradedReason: 'db_error', hours: 24,
        })
        expect(meta.unmeasured).toBe(true)
        expect(meta.notice).toMatch(/not zero/i)
        expect(meta.notice).not.toMatch(/db_error/)
    })

    it('null total without a flag is still unmeasured (defensive)', () => {
        const meta = resolveThemeCountMeta({
            loading: false, hasData: true, total: null, hours: 24,
        })
        expect(meta.countText).toBe('not measured')
        expect(meta.unmeasured).toBe(true)
        expect(meta.windowLabel).toBeNull()
    })

    it('a measured zero stays an honest 0 with its window', () => {
        const meta = resolveThemeCountMeta({
            loading: false, hasData: true, total: 0, hours: 24,
        })
        expect(meta.countText).toBe('0')
        expect(meta.unmeasured).toBe(false)
        expect(meta.windowLabel).toBe('Last 24h')
        expect(meta.notice).toBeNull()
    })

    it('normal payload formats the count and carries the requested window', () => {
        const meta = resolveThemeCountMeta({
            loading: false, hasData: true, total: 3659, hours: 48,
        })
        expect(meta.countText).toBe('3,659')
        expect(meta.windowLabel).toBe('Last 48h')
        expect(meta.unmeasured).toBe(false)
    })

    it('refetch over existing data keeps the previous honest render', () => {
        // loading=true but data from the prior window still on screen —
        // keep rendering it (stale-while-revalidate), not an ellipsis.
        const meta = resolveThemeCountMeta({
            loading: true, hasData: true, total: 12, hours: 24,
        })
        expect(meta.countText).toBe('12')
        expect(meta.windowLabel).toBe('Last 24h')
    })
})
