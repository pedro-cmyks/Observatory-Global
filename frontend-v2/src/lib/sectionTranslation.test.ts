import { describe, expect, it } from 'vitest'
import {
    SECTION_TRANSLATION_DEFAULT,
    nextSectionState,
    resolveShowOriginal,
    sectionControlCopy,
    shouldRetryFetch,
} from './sectionTranslation'

describe('section translation state machine', () => {
    it('default is auto/0 — byte-compatible with no provider at all', () => {
        expect(SECTION_TRANSLATION_DEFAULT).toEqual({ mode: 'auto', epoch: 0 })
    })

    it('control cycles auto → translated → original → translated, bumping epoch each click', () => {
        const s1 = nextSectionState(SECTION_TRANSLATION_DEFAULT)
        expect(s1).toEqual({ mode: 'translated', epoch: 1 })
        const s2 = nextSectionState(s1)
        expect(s2).toEqual({ mode: 'original', epoch: 2 })
        const s3 = nextSectionState(s2)
        expect(s3).toEqual({ mode: 'translated', epoch: 3 })
    })

    it('resolveShowOriginal: section mode drives when the item was not touched', () => {
        expect(resolveShowOriginal(null, 'auto')).toBe(false)
        expect(resolveShowOriginal(null, 'translated')).toBe(false)
        expect(resolveShowOriginal(null, 'original')).toBe(true)
    })

    it('resolveShowOriginal: the per-item toggle always wins over the section mode', () => {
        expect(resolveShowOriginal(true, 'translated')).toBe(true)
        expect(resolveShowOriginal(false, 'original')).toBe(false)
    })

    it('retry fires only on an explicit section Translate', () => {
        expect(shouldRetryFetch(SECTION_TRANSLATION_DEFAULT)).toBe(false)
        expect(shouldRetryFetch({ mode: 'translated', epoch: 1 })).toBe(true)
        expect(shouldRetryFetch({ mode: 'original', epoch: 2 })).toBe(false)
    })

    it('control copy inverts with the mode', () => {
        expect(sectionControlCopy('auto').label).toBe('Translate all')
        expect(sectionControlCopy('translated').label).toBe('Show originals')
        expect(sectionControlCopy('original').label).toBe('Translate all')
    })
})
