import { describe, it, expect } from 'vitest'
import { freezeThreadOrder } from './threadOrder'

const t = (id: string) => ({ thread_id: id })

describe('freezeThreadOrder (council N5)', () => {
    it('returns the live order unchanged when not frozen (null)', () => {
        const live = [t('a'), t('b'), t('c')]
        expect(freezeThreadOrder(live, null).map(n => n.thread_id)).toEqual(['a', 'b', 'c'])
    })

    it('returns the live order unchanged when frozen list is empty', () => {
        const live = [t('a'), t('b')]
        expect(freezeThreadOrder(live, []).map(n => n.thread_id)).toEqual(['a', 'b'])
    })

    it('pins rows to the frozen order even when the live order re-sorts', () => {
        // pointer froze [a,b,c]; a relation sort then wants [c,a,b] — must NOT move
        const live = [t('c'), t('a'), t('b')]
        const out = freezeThreadOrder(live, ['a', 'b', 'c'])
        expect(out.map(n => n.thread_id)).toEqual(['a', 'b', 'c'])
    })

    it('appends threads that arrived while frozen at the end, in live order', () => {
        // froze [a,b]; poll added d then c ahead of them in the live sort
        const live = [t('d'), t('c'), t('a'), t('b')]
        const out = freezeThreadOrder(live, ['a', 'b'])
        expect(out.map(n => n.thread_id)).toEqual(['a', 'b', 'd', 'c'])
    })

    it('drops frozen ids whose thread disappeared from the live set', () => {
        // froze [a,b,c]; b left the feed
        const live = [t('a'), t('c')]
        const out = freezeThreadOrder(live, ['a', 'b', 'c'])
        expect(out.map(n => n.thread_id)).toEqual(['a', 'c'])
    })

    it('does not mutate the input array', () => {
        const live = [t('c'), t('a'), t('b')]
        const snapshot = live.map(n => n.thread_id)
        freezeThreadOrder(live, ['a', 'b', 'c'])
        expect(live.map(n => n.thread_id)).toEqual(snapshot)
    })
})
