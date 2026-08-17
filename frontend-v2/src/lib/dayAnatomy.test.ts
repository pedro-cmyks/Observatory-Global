import { describe, it, expect } from 'vitest'
import { composeDayAnatomy, changedRowsFromThreads, READER_ANATOMY } from './dayAnatomy'

const base = { nearCount: 0, changedCount: 0, oddCount: 0 }

describe('composeDayAnatomy', () => {
    it('fixed order, empty segments absent, world always last and always present', () => {
        expect(composeDayAnatomy({ nearCount: 2, changedCount: 1, oddCount: 3 })
            .map(s => s.id)).toEqual(['near', 'changed', 'odd', 'world'])
        expect(composeDayAnatomy({ ...base, changedCount: 1 })
            .map(s => s.id)).toEqual(['changed', 'world'])
        expect(composeDayAnatomy(base).map(s => s.id)).toEqual(['world'])
    })

    it('world survives even a fully empty day — the shared edition is the firewall', () => {
        const segs = composeDayAnatomy(base)
        expect(segs).toHaveLength(1)
        expect(segs[0].id).toBe('world')
    })

    it('carries counts through for the kicker labels', () => {
        expect(composeDayAnatomy({ ...base, nearCount: 2 })[0]).toEqual({ id: 'near', count: 2 })
    })
})

describe('changedRowsFromThreads', () => {
    const t = (id: string, sig: string | null) =>
        ({ thread_id: id, label: id, temporal_signature: sig })

    it('keeps only new and resurrected — continuous/recurrent/null are not "changes"', () => {
        const rows = changedRowsFromThreads([
            t('a', 'new'), t('b', 'recurrent'), t('c', 'resurrected'),
            t('d', 'continuous'), t('e', null),
        ])
        expect(rows.map(r => r.thread_id)).toEqual(['a', 'c'])
    })

    it('empty input → empty output, no fabrication', () => {
        expect(changedRowsFromThreads([])).toEqual([])
    })
})

describe('kill switch', () => {
    it('exists and is a boolean (one-line revert per spec discipline)', () => {
        expect(typeof READER_ANATOMY).toBe('boolean')
    })
})
