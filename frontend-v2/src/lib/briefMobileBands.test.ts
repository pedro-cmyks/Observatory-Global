import { describe, it, expect } from 'vitest'
import { freshnessSummary, bandStartsCollapsed } from './briefMobileBands'

describe('bandStartsCollapsed', () => {
  it('collapses the secondary bands on mobile', () => {
    expect(bandStartsCollapsed('markets', true)).toBe(true)
    expect(bandStartsCollapsed('freshness', true)).toBe(true)
  })
  it('never collapses anything on desktop', () => {
    expect(bandStartsCollapsed('markets', false)).toBe(false)
    expect(bandStartsCollapsed('freshness', false)).toBe(false)
  })
})

describe('freshnessSummary', () => {
  it('states seal age and full-text yield in one line', () => {
    expect(freshnessSummary({ sealedAge: '11 hours ago', fullTextOk: 1, fullTextTotal: 48 }))
      .toBe('sealed 11 hours ago · full text 1/48')
  })
  it('omits the yield when it is unknown', () => {
    expect(freshnessSummary({ sealedAge: '3 hours ago', fullTextOk: null, fullTextTotal: null }))
      .toBe('sealed 3 hours ago')
  })
  it('says so honestly when the seal age is unknown', () => {
    expect(freshnessSummary({ sealedAge: null, fullTextOk: 2, fullTextTotal: 40 }))
      .toBe('seal time unknown · full text 2/40')
  })
  // Both ends of the range the review caught missing: a module that FORMATS
  // (rather than computes) a sentence must be exercised on the exact strings
  // its source (staleBanner.humanizeAge) actually produces, sub-hour and
  // multi-day alike — the bug this replaced only showed up outside [1h, 24h).
  it('passes through a sub-hour age verbatim, never inventing an hour count', () => {
    expect(freshnessSummary({ sealedAge: 'just now', fullTextOk: null, fullTextTotal: null }))
      .toBe('sealed just now')
  })
  it('passes through a multi-day age verbatim, never truncating to hours', () => {
    expect(freshnessSummary({ sealedAge: '3 days ago', fullTextOk: 5, fullTextTotal: 48 }))
      .toBe('sealed 3 days ago · full text 5/48')
  })
})
