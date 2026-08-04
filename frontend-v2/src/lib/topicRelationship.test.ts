import { describe, expect, it } from 'vitest'
import { parseTopicRelationship, relationshipChip } from './topicRelationship'

const payload = (over: Record<string, unknown> = {}) => ({
    contract: 'topic-relationship-v0',
    topic_id: 'dynamic-topic-42',
    relationship: 'media-led',
    evidence_count: 120,
    discussion_count: 4,
    mood_count: 0,
    rationale: 'evidence 120 outweighs discussion 4 (ratio 0.033)',
    ...over,
})

describe('parseTopicRelationship', () => {
    it('parses a live-shaped payload', () => {
        const rel = parseTopicRelationship(payload())
        expect(rel).toEqual({
            relationship: 'media-led',
            evidenceCount: 120,
            discussionCount: 4,
            moodCount: 0,
            rationale: 'evidence 120 outweighs discussion 4 (ratio 0.033)',
        })
    })

    it('rejects unknown relationship values and malformed payloads', () => {
        expect(parseTopicRelationship(payload({ relationship: 'astrology-led' }))).toBeNull()
        expect(parseTopicRelationship(payload({ relationship: 7 }))).toBeNull()
        expect(parseTopicRelationship(null)).toBeNull()
        expect(parseTopicRelationship('media-led')).toBeNull()
    })

    it('defaults missing counts to 0 without inventing values', () => {
        const rel = parseTopicRelationship(payload({ evidence_count: undefined, mood_count: 'x' }))
        expect(rel?.evidenceCount).toBe(0)
        expect(rel?.moodCount).toBe(0)
    })
})

describe('relationshipChip', () => {
    it('renders every type in full mode', () => {
        for (const [type, text] of [
            ['media-led', 'MEDIA-LED'],
            ['public-led', 'PUBLIC-LED'],
            ['social-led', 'SOCIAL-LED'],
            ['silent-risk', 'SILENT RISK'],
            ['uncoupled-attention', 'UNCOUPLED'],
        ] as const) {
            const chip = relationshipChip(parseTopicRelationship(payload({ relationship: type })))
            expect(chip?.text).toBe(text)
            expect(chip?.className).toMatch(/^rel-chip--/)
        }
    })

    it('compact mode renders only the differentiating classes', () => {
        const compact = (type: string) =>
            relationshipChip(parseTopicRelationship(payload({ relationship: type })), { compact: true })
        expect(compact('media-led')).toBeNull()
        expect(compact('uncoupled-attention')).toBeNull()
        expect(compact('public-led')?.text).toBe('PUBLIC-LED')
        expect(compact('social-led')?.text).toBe('SOCIAL-LED')
        expect(compact('silent-risk')?.text).toBe('SILENT RISK')
    })

    it('tip carries measured counts and the never-evidence honesty note', () => {
        const chip = relationshipChip(
            parseTopicRelationship(payload({ relationship: 'public-led', evidence_count: 2, discussion_count: 5, mood_count: 5 })),
        )
        expect(chip?.tip).toContain('press 2 · discussion 5 · mood 5')
        expect(chip?.tip).toContain('never counted as evidence')
    })

    it('null relationship renders nothing', () => {
        expect(relationshipChip(null)).toBeNull()
        expect(relationshipChip(undefined)).toBeNull()
    })
})
