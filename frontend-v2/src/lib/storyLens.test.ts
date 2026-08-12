import { describe, expect, it } from 'vitest'
import {
  buildLensSets,
  hasLensContent,
  isLensAnchor,
  lensErrorCopy,
  lensTopicParam,
  siblingChipText,
  siblingKinshipSummary,
  threadLensRole,
  type StoryLensData,
  type StoryLensSibling,
} from './storyLens'

const data: StoryLensData = {
  contract: 'story-siblings-v1',
  generated_at: '2026-07-28T00:00:00Z',
  anchor: { id: 'dynamic-topic-1', label: 'Anchor', label_status: 'entailed', countries: ['IR'] },
  siblings: [
    { id: 'dynamic-topic-2', label: 'Sib A', weight: 0.7, degree: 1, kinship: 'hermano', through_blob: false, is_blob: false, via_parent: null, folded: ['dynamic-topic-9'], label_status: null, countries: ['IR'], reasons: [{ basis: 'whitened_cos', value: '0.70' }] },
    { id: 'dynamic-topic-3', label: 'Sib B', weight: 0.4, degree: 2, kinship: 'primo', through_blob: false, is_blob: true, blob_basis: 'confirmed', via_parent: 'Sib A', folded: [], label_status: 'failed', countries: [], reasons: [{ basis: 'whitened_cos', value: '0.40' }] },
  ],
  notes: [],
}

describe('buildLensSets / threadLensRole', () => {
  it('classifies anchor, sibling (incl. folded ids), and outsiders', () => {
    const sets = buildLensSets(data)
    expect(threadLensRole(undefined, 'dynamic-topic-1', sets)).toBe('anchor')
    expect(threadLensRole(undefined, 'dynamic-topic-2', sets)).toBe('sibling')
    expect(threadLensRole(undefined, 'dynamic-topic-9', sets)).toBe('sibling')
    expect(threadLensRole(undefined, 'dynamic-topic-99', sets)).toBeNull()
  })
  it('matches through anchor_topics union like the eclipse role does', () => {
    const sets = buildLensSets(data)
    expect(threadLensRole(['dynamic-topic-2'], 'thread-x', sets)).toBe('sibling')
  })
})

describe('siblingChipText', () => {
  it('flags a CONFIRMED blob sibling structurally — isBlob true, plain grab-bag marker', () => {
    const blobSibling = data.siblings[1] // is_blob: true, blob_basis: 'confirmed'
    const chip = siblingChipText(blobSibling)
    expect(chip.isBlob).toBe(true)
    expect(chip.text).toContain('⚠ grab-bag')
    expect(chip.text).not.toContain('⚠ grab-bag?')
    expect(chip.tooltip).toBeUndefined()
  })
  it('a non-blob sibling never carries the marker', () => {
    const plainSibling = data.siblings[0] // is_blob: false
    const chip = siblingChipText(plainSibling)
    expect(chip.isBlob).toBe(false)
    expect(chip.text).not.toContain('⚠ grab-bag')
  })
  it('a candidate_unconfirmed blob is qualified, not silently confirmed nor cleared', () => {
    // GC kill rule (docs/superpowers/plans/2026-07-29-identity-three-levers.md):
    // a candidate the confirmer could not evaluate must read DIFFERENTLY from
    // a structurally confirmed one — never identical (silently confirmed) and
    // never plain (silently cleaner).
    const degraded: StoryLensSibling = {
      ...data.siblings[1], blob_basis: 'candidate_unconfirmed',
    }
    const chip = siblingChipText(degraded)
    expect(chip.isBlob).toBe(true)
    expect(chip.text).toContain('⚠ grab-bag?')
    expect(chip.tooltip).toBe('entropy candidate — membership unconfirmed')
  })
})

describe('hasLensContent', () => {
  it('true for a populated payload, false for honest empties', () => {
    expect(hasLensContent(data)).toBe(true)
    expect(hasLensContent(null)).toBe(false)
    expect(hasLensContent({ ...data, anchor: null, siblings: [] })).toBe(false)
    expect(hasLensContent({ ...data, siblings: [] })).toBe(false)
  })
})

describe('lensTopicParam', () => {
  it('joins anchor + siblings, capped, never empty string', () => {
    expect(lensTopicParam(data)).toBe('dynamic-topic-1,dynamic-topic-2,dynamic-topic-3')
    expect(lensTopicParam(data, 2)).toBe('dynamic-topic-1,dynamic-topic-2')
    expect(lensTopicParam(null)).toBeNull()
    expect(lensTopicParam({ ...data, anchor: null, siblings: [] })).toBeNull()
  })
})

describe('isLensAnchor', () => {
  // Frontend half of the backend's unsupported_anchor_type contract
  // (story.py:221) — v1 lens anchors are DYNAMIC topics only.
  it('accepts a dynamic-topic id, rejects atlas slugs and emergent clusters', () => {
    expect(isLensAnchor('dynamic-topic-5245')).toBe(true)
    expect(isLensAnchor('disease-outbreak--CO')).toBe(false)
    expect(isLensAnchor('emergent-cluster-17')).toBe(false)
  })
})

describe('siblingKinshipSummary', () => {
  // T11 gate fix (L2): the banner used to report every sibling as a
  // "hermano" regardless of `kinship`, erasing the direct-edge-vs-indirect-
  // walk distinction the design exists to carry.
  it('splits hermanos and primos, omitting a zero part', () => {
    expect(siblingKinshipSummary(data.siblings)).toBe('1 hermano · 1 primo')
  })
  it('pluralizes correctly and omits the missing kinship entirely', () => {
    const allHermanos: StoryLensSibling[] = [
      { ...data.siblings[0], id: 'a' },
      { ...data.siblings[0], id: 'b' },
    ]
    expect(siblingKinshipSummary(allHermanos)).toBe('2 hermanos')
    const onePrimo: StoryLensSibling[] = [{ ...data.siblings[1], id: 'c' }]
    expect(siblingKinshipSummary(onePrimo)).toBe('1 primo')
  })
  it('an anchor with no kin at all still reports a count, never a blank string', () => {
    expect(siblingKinshipSummary([])).toBe('0 hermanos')
  })
})

describe('lensErrorCopy', () => {
  // Internal codes must NEVER leak to the screen verbatim.
  const INTERNAL_CODES = ['db_unavailable', 'db_error', 'whitening_unavailable', 'internal_error']

  it('never lets an internal code reach the user-facing string', () => {
    for (const code of INTERNAL_CODES) {
      const copy = lensErrorCopy(code)
      expect(copy.toLowerCase()).not.toContain(code.toLowerCase())
      expect(copy.toLowerCase()).not.toContain('db_')
      expect(copy.toLowerCase()).not.toContain('internal_error')
      expect(copy.toLowerCase()).not.toContain('whitening_unavailable')
    }
  })

  it('a failed lookup never reads as a measured absence', () => {
    expect(lensErrorCopy('db_unavailable')).toBe('Neighborhood lookup failed — not a measured absence')
    expect(lensErrorCopy('db_error')).toBe('Neighborhood lookup failed — not a measured absence')
    expect(lensErrorCopy('whitening_unavailable')).toBe('Measurement space unavailable')
    expect(lensErrorCopy('internal_error')).toBe('Measurement space unavailable')
  })

  it('unsupported_anchor_type reads structural, not a failure', () => {
    const copy = lensErrorCopy('unsupported_anchor_type')
    expect(copy).toBe('No measured neighborhood for this story type yet')
    expect(copy.toLowerCase()).not.toContain('fail')
    expect(copy.toLowerCase()).not.toContain('error')
  })

  it('seed_not_found_or_no_centroid and invalid_thread_id map to their own honest copy', () => {
    expect(lensErrorCopy('seed_not_found_or_no_centroid')).toBe('Story not in the active measured field')
    expect(lensErrorCopy('invalid_thread_id')).toBe('Invalid story reference')
  })

  it('an unknown or absent code falls back to the honest default', () => {
    expect(lensErrorCopy('some_future_code_not_yet_mapped')).toBe('Neighborhood unavailable')
    expect(lensErrorCopy(null)).toBe('Neighborhood unavailable')
    expect(lensErrorCopy(undefined)).toBe('Neighborhood unavailable')
  })
})
