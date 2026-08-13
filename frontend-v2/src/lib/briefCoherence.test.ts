import { describe, it, expect } from 'vitest'
import {
  frontPageScope,
  censusBridge,
  deskCensusNote,
  CATEGORY_INDEX_BASIS,
  CONSOLE_LINK_LABEL,
  type CensusRow,
} from './briefCoherence'

// The judge's two witnesses, verbatim from the prod payload of 2026-08-13.
const CENSUS: CensusRow[] = [
  { category: 'Armed conflict escalation', topics: 203, signals: 4754 },
  { category: 'Crime & Justice', topics: 209, signals: 2670 },
  { category: 'Politics & Governance', topics: 187, signals: 2215 },
  { category: 'Crime & Public Safety', topics: 142, signals: 1864 },
  { category: 'Sports', topics: 110, signals: 1398 },
  { category: 'Business & Markets', topics: 116, signals: 1325 },
]

describe('frontPageScope — the front page names which population it is showing', () => {
  it('names the LIVE rank as its basis when the seal was not served', () => {
    const s = frontPageScope({ servedFromSeal: false, shown: 10, cap: 10 })
    expect(s.basis).toBe('live')
    expect(s.sentence).toMatch(/live rank/i)
    expect(s.sentence).toContain('10')
  })

  it('names the SEALED edition as its basis when the seal was served', () => {
    const s = frontPageScope({ servedFromSeal: true, shown: 12, cap: 10 })
    expect(s.basis).toBe('sealed')
    expect(s.sentence).toMatch(/sealed edition/i)
    expect(s.sentence).toContain('12')
  })

  // The count delta, proven rather than invented: a list served AT its cap is
  // truncated by construction, so "there are more" is a measured claim. Below
  // the cap it is not, and we must not imply one.
  it('claims the rank continues ONLY when the list is served at its cap', () => {
    expect(frontPageScope({ servedFromSeal: false, shown: 10, cap: 10 }).truncated).toBe(true)
    expect(frontPageScope({ servedFromSeal: false, shown: 7, cap: 10 }).truncated).toBe(false)
  })

  it('never asserts a console count it cannot prove', () => {
    const s = frontPageScope({ servedFromSeal: false, shown: 10, cap: 10 })
    // No fabricated "the console ranks N" — only the front-page count is numeric.
    expect(s.sentence.match(/\d+/g)).toEqual(['10'])
  })

  it('does not claim the rank continues past a short list', () => {
    const s = frontPageScope({ servedFromSeal: false, shown: 3, cap: 10 })
    expect(s.sentence).not.toMatch(/continues/i)
  })

  it('is defensive about nonsense inputs rather than printing NaN', () => {
    const s = frontPageScope({ servedFromSeal: false, shown: 0, cap: 10 })
    expect(s.sentence).not.toMatch(/NaN|undefined/)
    expect(s.truncated).toBe(false)
  })

  it('offers the console as the fuller list, never as a contradiction', () => {
    expect(CONSOLE_LINK_LABEL).toMatch(/console/i)
    const s = frontPageScope({ servedFromSeal: false, shown: 10, cap: 10 })
    expect(s.consoleNote).toMatch(/same/i)
    expect(s.consoleNote).not.toMatch(/disagree|wrong|conflict/i)
  })
})

describe('censusBridge — reconciles the category index with a desk', () => {
  it('sums the census rows belonging to a family, using the SAME classifier as the desks', () => {
    const b = censusBridge({ rows: CENSUS, family: 'culture' })
    expect(b).not.toBeNull()
    expect(b!.topics).toBe(110)
    expect(b!.signals).toBe(1398)
    expect(b!.categories).toEqual(['Sports'])
  })

  it('sums MULTIPLE categories of the same family', () => {
    const b = censusBridge({
      rows: [...CENSUS, { category: 'Entertainment', topics: 40, signals: 600 }],
      family: 'culture',
    })
    expect(b!.topics).toBe(150)
    expect(b!.signals).toBe(1998)
    expect(b!.categories).toEqual(['Sports', 'Entertainment'])
  })

  it('returns null when the family is absent from the index — no bridge to draw', () => {
    expect(censusBridge({ rows: CENSUS, family: 'culture' })).not.toBeNull()
    expect(censusBridge({ rows: [], family: 'culture' })).toBeNull()
    expect(censusBridge({ rows: CENSUS, family: 'health' })).toBeNull()
  })

  it('ignores rows with no measurable signal rather than counting a zero as presence', () => {
    expect(censusBridge({ rows: [{ category: 'Sports', topics: 0, signals: 0 }], family: 'culture' }))
      .toBeNull()
  })
})

describe('deskCensusNote — the sentence that stops the page contradicting itself', () => {
  it('names BOTH bases and BOTH numbers in one sentence', () => {
    const note = deskCensusNote({ rows: CENSUS, family: 'culture', deskName: 'this desk' })
    expect(note).not.toBeNull()
    expect(note!).toContain('1,398')
    expect(note!).toContain('110')
    expect(note!).toContain('Sports')
    // The reconciliation itself: raw census vs ranked front page.
    expect(note!).toMatch(/raw signal/i)
    expect(note!).toMatch(/rank|front page/i)
  })

  it('never claims the gate ruled against the census — the desk simply did not rank them', () => {
    const note = deskCensusNote({ rows: CENSUS, family: 'culture', deskName: 'this desk' })!
    expect(note).not.toMatch(/rejected|failed the gate|unimportant/i)
  })

  it('is absent when there is nothing to reconcile', () => {
    expect(deskCensusNote({ rows: [], family: 'culture', deskName: 'this desk' })).toBeNull()
  })

  it('thousand-separates so the two numbers read against each other', () => {
    const note = deskCensusNote({
      rows: [{ category: 'Sports', topics: 1200, signals: 24500 }],
      family: 'culture',
      deskName: 'this desk',
    })!
    expect(note).toContain('24,500')
    expect(note).toContain('1,200')
  })
})

describe('CATEGORY_INDEX_BASIS — the chart declares what it counts', () => {
  it('says it counts every tracked story, not this page', () => {
    expect(CATEGORY_INDEX_BASIS).toMatch(/every active story|all tracked|tracked stor/i)
    expect(CATEGORY_INDEX_BASIS).toMatch(/raw signal/i)
  })

  it('warns that a large row can still put nothing on the page', () => {
    expect(CATEGORY_INDEX_BASIS).toMatch(/not\b.*(this page|the desks|front page)/i)
  })
})
