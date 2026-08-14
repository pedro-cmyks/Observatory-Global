import { describe, it, expect } from 'vitest'
import { threadRowKind, storyTitle, rowCountBase, categoryRowTip } from './threadRowKind'

const row = (thread_id: string, anchor_topics: string[] = []) => ({ thread_id, anchor_topics })

describe('threadRowKind — a CATEGORY row must be distinguishable from a STORY row', () => {
    it('types a dynamic leaf topic as a story', () => {
        expect(threadRowKind(row('dynamic-topic-242', ['dyn-2026-08-08T03:16:26-16000000']))).toBe('story')
    })

    it('types a dynamic topic with an umbrella identity_key as an umbrella', () => {
        // Measured live: /threads serves R2 umbrellas as top-level rows and their
        // identity_key is 'umbrella:<largest active child id>'.
        expect(threadRowKind(row('dynamic-topic-12927', ['umbrella:510']))).toBe('umbrella')
    })

    it('types an atlas slug thread_id as a category (the R3 lens)', () => {
        expect(threadRowKind(row('earthquake-volcano-disaster'))).toBe('category')
        expect(threadRowKind(row('armed-conflict-escalation'))).toBe('category')
    })

    it('types a country-scoped atlas slug (slug--CC) as a category', () => {
        expect(threadRowKind(row('earthquake-volcano-disaster--CO'))).toBe('category')
    })

    it('never types emergent clusters or query threads as categories', () => {
        expect(threadRowKind(row('emergent-cluster-17'))).toBe('story')
        expect(threadRowKind(row('cluster-17'))).toBe('story')
        expect(threadRowKind(row('query-thread::iran-water'))).toBe('story')
    })

    it('falls back to story for an unrecognised id rather than mislabelling it a category', () => {
        expect(threadRowKind(row(''))).toBe('story')
        expect(threadRowKind(row('WEIRD_ID'))).toBe('story')
    })

    it('reads the umbrella marker from any anchor position, not just [0]', () => {
        expect(threadRowKind(row('dynamic-topic-9', ['dyn-x', 'umbrella:5']))).toBe('umbrella')
    })
})

describe('rowCountBase — the number must state the basis it was counted on', () => {
    it('a category row counts signals across every story in the category', () => {
        expect(rowCountBase('category', { gated_signal_count: 40 })).toBe('category')
        // ...even when the atlas gate fields are absent
        expect(rowCountBase('category', {})).toBe('category')
    })

    it('a story row keeps the pre-existing raw/gated lineage split', () => {
        expect(rowCountBase('story', { gated_signal_count: 40 })).toBe('raw')
        expect(rowCountBase('story', {})).toBe('gated')
        expect(rowCountBase('umbrella', {})).toBe('gated')
    })
})

describe('categoryRowTip', () => {
    it('names the category and says the count is signals, not stories', () => {
        const tip = categoryRowTip('Earthquake or volcanic disaster', 80, '24h')
        expect(tip).toMatch(/category/i)
        expect(tip).toContain('Earthquake or volcanic disaster')
        expect(tip).toContain('80')
        expect(tip).toMatch(/signals/i)
        // The exact misreading being fixed: 80 is not one story's count.
        expect(tip).toMatch(/not one story/i)
    })
})

describe('storyTitle — the title must never collapse into its own category kicker', () => {
    const CAT = 'Earthquake or volcanic disaster'

    it('still strips a redundant trailing country from a specific headline', () => {
        // The behaviour stripCountrySuffix existed for: the country is already
        // rendered as a chip, so the tail is redundant.
        expect(storyTitle('7.4-Magnitude Earthquake Kills Dozens in Colombia', CAT))
            .toBe('7.4-Magnitude Earthquake Kills Dozens')
    })

    it('does NOT strip when the remainder would be a bare category word (Pedro live read)', () => {
        // "Earthquake in Colombia" rendered as "Earthquake" directly under a
        // "EARTHQUAKE OR VOLCANIC DISASTER" kicker — the row read as a category.
        expect(storyTitle('Earthquake in Colombia', CAT)).toBe('Earthquake in Colombia')
    })

    it('does NOT strip when the remainder is only two words (live: Houthi Attacks in Yemen)', () => {
        expect(storyTitle('Houthi Attacks in Yemen', 'Armed conflict escalation'))
            .toBe('Houthi Attacks in Yemen')
    })

    it('does NOT strip mid-sentence when the tail is prose, not a place (live: Nick Reiner)', () => {
        const label = 'Emerging (US): Grand jury indicts Nick Reiner in fatal stabbing of parents Rob and Michele Reiner'
        expect(storyTitle(label, 'Crime & Justice')).toBe(label)
    })

    it('does NOT strip when the remainder is contained in the category label', () => {
        // remainder is 3 words so the word-count guard alone would allow it.
        expect(storyTitle('Armed conflict escalation in Sudan', 'Armed conflict escalation'))
            .toBe('Armed conflict escalation in Sudan')
    })

    it('is case-insensitive when comparing the remainder to the category', () => {
        expect(storyTitle('DISEASE OUTBREAK in France', 'Disease outbreak'))
            .toBe('DISEASE OUTBREAK in France')
    })

    it('leaves labels with no " in " clause untouched', () => {
        expect(storyTitle('Russian Strikes on Ukraine, Drone Attacks on Russia', 'Armed conflict escalation'))
            .toBe('Russian Strikes on Ukraine, Drone Attacks on Russia')
    })

    it('strips only the LAST " in " clause, not the first', () => {
        expect(storyTitle('Floods in Villages Kill Dozens in Pakistan', 'Flood and landslide disaster'))
            .toBe('Floods in Villages Kill Dozens')
    })

    it('handles a null/absent category without throwing', () => {
        expect(storyTitle('7.4-Magnitude Earthquake Kills Dozens in Colombia', null))
            .toBe('7.4-Magnitude Earthquake Kills Dozens')
        expect(storyTitle('', null)).toBe('')
    })

    it('trims surrounding whitespace like the helper it replaces', () => {
        expect(storyTitle('  Ebola Outbreak Congo  ', 'Disease outbreak')).toBe('Ebola Outbreak Congo')
    })
})
