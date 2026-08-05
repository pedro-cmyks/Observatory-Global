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
    expect(freshnessSummary({ sealedHoursAgo: 11, fullTextOk: 1, fullTextTotal: 48 }))
      .toBe('sealed 11h ago · full text 1/48')
  })
  it('omits the yield when it is unknown', () => {
    expect(freshnessSummary({ sealedHoursAgo: 3, fullTextOk: null, fullTextTotal: null }))
      .toBe('sealed 3h ago')
  })
  it('says so honestly when the seal age is unknown', () => {
    expect(freshnessSummary({ sealedHoursAgo: null, fullTextOk: 2, fullTextTotal: 40 }))
      .toBe('seal time unknown · full text 2/40')
  })
})
