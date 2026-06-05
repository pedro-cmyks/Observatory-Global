import { describe, expect, it } from 'vitest'
import { buildPublicAttentionScopeLabel } from './publicAttentionScope'

describe('Public Attention scope label', () => {
  it('labels the panel as global media matching by default', () => {
    expect(buildPublicAttentionScopeLabel({ title: 'Backrooms film', hours: 24 })).toEqual({
      label: 'Global media match',
      detail: 'Comparing people-side attention for Backrooms film against global media signals in the last 24h.',
    })
  })

  it('keeps the originating country visible when attention was opened from a country context', () => {
    expect(buildPublicAttentionScopeLabel({
      title: 'Backrooms film',
      hours: 168,
      countryCode: 'CO',
      countryName: 'Colombia',
    })).toEqual({
      label: 'Country origin: Colombia',
      detail: 'Opened from Colombia. Media matches below are still global unless a country is selected.',
    })
  })
})
