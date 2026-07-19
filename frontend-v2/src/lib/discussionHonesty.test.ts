// #248 discussion-attach relevance honesty — pure display helpers.
import { describe, expect, it } from 'vitest'
import { formatAttachSimilarity, laneTag, truncationNote } from './discussionHonesty'

describe('formatAttachSimilarity', () => {
    it('renders the measured similarity as a percent', () => {
        expect(formatAttachSimilarity(0.9312)).toBe('93% match')
        expect(formatAttachSimilarity(0.895)).toBe('90% match')
    })
    it('returns null when the engine recorded no similarity — never fakes one', () => {
        expect(formatAttachSimilarity(undefined)).toBeNull()
        expect(formatAttachSimilarity(null)).toBeNull()
    })
    it('rejects out-of-range garbage rather than rendering nonsense', () => {
        expect(formatAttachSimilarity(-0.2)).toBeNull()
        expect(formatAttachSimilarity(1.7)).toBeNull()
        expect(formatAttachSimilarity(Number.NaN)).toBeNull()
    })
})

describe('laneTag', () => {
    it('uppercases known noise lanes for the chip', () => {
        expect(laneTag('hobby')).toBe('HOBBY')
        expect(laneTag('sports')).toBe('SPORTS')
    })
    it('returns null for untagged (news-y) items', () => {
        expect(laneTag(undefined)).toBeNull()
        expect(laneTag('')).toBeNull()
    })
})

describe('truncationNote', () => {
    it('states how many of the total are shown when truncated', () => {
        expect(truncationNote(10, 17)).toBe('showing 10 of 17')
    })
    it('is silent when everything is shown', () => {
        expect(truncationNote(6, 6)).toBeNull()
        expect(truncationNote(10, 4)).toBeNull()
    })
})
