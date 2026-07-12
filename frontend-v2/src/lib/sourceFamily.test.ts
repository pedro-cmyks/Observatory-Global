import { describe, expect, it } from 'vitest'
import { getSourceFamilyMeta } from './sourceFamily'

describe('getSourceFamilyMeta', () => {
  it('maps backend source families to analyst-facing badge labels', () => {
    expect(getSourceFamilyMeta('state')).toMatchObject({
      label: 'State',
      className: 'source-family-badge--state',
    })
    expect(getSourceFamilyMeta('wire')).toMatchObject({
      label: 'Wire',
      className: 'source-family-badge--wire',
    })
    expect(getSourceFamilyMeta('independent')).toMatchObject({
      label: 'Independent',
      className: 'source-family-badge--independent',
    })
  })

  // 2026-07-11 dataviz audit: an outlet with no family field must not wear a
  // confident "Independent" badge — unknown reads as unclassified, not as a claim.
  it('falls back to an honest Unclassified badge when the family field is missing', () => {
    expect(getSourceFamilyMeta(undefined)).toMatchObject({
      label: 'Unclassified',
      className: 'source-family-badge--unknown',
    })
    expect(getSourceFamilyMeta('something-new')).toMatchObject({
      label: 'Unclassified',
    })
  })
})
