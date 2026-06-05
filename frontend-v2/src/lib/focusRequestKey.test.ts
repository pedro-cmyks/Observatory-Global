import { describe, expect, it } from 'vitest'
import { buildFocusRequestKey } from './focusRequestKey'

describe('FocusData request key', () => {
  it('includes range and active focus value so stale global responses differ from scoped responses', () => {
    expect(buildFocusRequestKey({
      timeRange: '24h',
      isActive: false,
      focusType: null,
      focusValue: null,
    })).toBe('range=24h|focus=global')

    expect(buildFocusRequestKey({
      timeRange: '24h',
      isActive: true,
      focusType: 'country',
      focusValue: 'SD',
    })).toBe('range=24h|focus=country:SD')
  })

  it('changes when the time range changes even if the selected focus is the same', () => {
    expect(buildFocusRequestKey({
      timeRange: '1w',
      isActive: true,
      focusType: 'theme',
      focusValue: 'MEDIA_SOCIAL',
    })).toBe('range=1w|focus=theme:MEDIA_SOCIAL')
  })
})
