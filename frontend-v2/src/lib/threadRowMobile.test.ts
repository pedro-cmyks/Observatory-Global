import { describe, it, expect } from 'vitest'
import { visibleEntities, MOBILE_ENTITY_CAP } from './threadRowMobile'

describe('visibleEntities', () => {
  const five = ['donald trump', 'abbas araghchi', 'takahiro asaoka', 'faisal ben', 'ali larijani']

  it('shows every entity on desktop', () => {
    expect(visibleEntities(five, false)).toEqual({ shown: five, hiddenCount: 0 })
  })

  it('caps the list on mobile and reports the remainder', () => {
    expect(visibleEntities(five, true)).toEqual({
      shown: five.slice(0, MOBILE_ENTITY_CAP),
      hiddenCount: five.length - MOBILE_ENTITY_CAP,
    })
  })

  it('never reports a negative remainder when the list is short', () => {
    expect(visibleEntities(['solo'], true)).toEqual({ shown: ['solo'], hiddenCount: 0 })
  })

  it('handles an empty list', () => {
    expect(visibleEntities([], true)).toEqual({ shown: [], hiddenCount: 0 })
  })
})
