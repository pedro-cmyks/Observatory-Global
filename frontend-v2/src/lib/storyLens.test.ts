import { describe, expect, it } from 'vitest'
import {
  buildLensSets,
  hasLensContent,
  lensTopicParam,
  threadLensRole,
  type StoryLensData,
} from './storyLens'

const data: StoryLensData = {
  contract: 'story-siblings-v1',
  generated_at: '2026-07-28T00:00:00Z',
  anchor: { id: 'dynamic-topic-1', label: 'Anchor', label_status: 'entailed', countries: ['IR'] },
  siblings: [
    { id: 'dynamic-topic-2', label: 'Sib A', weight: 0.7, degree: 1, kinship: 'hermano', through_blob: false, is_blob: false, via_parent: null, folded: ['dynamic-topic-9'], label_status: null, countries: ['IR'], reasons: [{ basis: 'whitened_cos', value: '0.70' }] },
    { id: 'dynamic-topic-3', label: 'Sib B', weight: 0.4, degree: 2, kinship: 'primo', through_blob: false, is_blob: true, via_parent: 'Sib A', folded: [], label_status: 'failed', countries: [], reasons: [{ basis: 'whitened_cos', value: '0.40' }] },
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
