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

  it('falls back to independent when older API responses have no family field', () => {
    expect(getSourceFamilyMeta(undefined)).toMatchObject({
      label: 'Independent',
      className: 'source-family-badge--independent',
    })
  })
})
