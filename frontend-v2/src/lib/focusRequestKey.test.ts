import { describe, expect, it } from 'vitest'
import { buildFocusRequestKey } from './focusRequestKey'

describe('FocusData request key', () => {
  it('includes the active focus value so stale global responses differ from scoped responses', () => {
    expect(buildFocusRequestKey({
      isActive: false,
      focusType: null,
      focusValue: null,
    })).toBe('focus=global')

    expect(buildFocusRequestKey({
      isActive: true,
      focusType: 'country',
      focusValue: 'SD',
    })).toBe('focus=country:SD')
  })

  it('ignores inactive focus values', () => {
    expect(buildFocusRequestKey({
      isActive: false,
      focusType: 'theme',
      focusValue: 'MEDIA_SOCIAL',
    })).toBe('focus=global')
  })
})
