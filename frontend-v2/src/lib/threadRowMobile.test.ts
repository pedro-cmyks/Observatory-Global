import { describe, it, expect } from 'vitest'
import { visibleEntities, MOBILE_ENTITY_CAP } from './threadRowMobile'

describe('visibleEntities', () => {
  const five = ['donald trump', 'abbas araghchi', 'takahiro asaoka', 'faisal ben', 'ali larijani']

  it('caps at 2', () => {
    expect(MOBILE_ENTITY_CAP).toBe(2)
  })

  it('shows every entity on desktop', () => {
    expect(visibleEntities(five, false)).toEqual({ shown: five, hiddenCount: 0 })
  })

  it('caps the list on mobile and reports the remainder', () => {
    // Hardcoded, not derived from the same slice/subtract the implementation
    // uses — this pins actual behaviour and would catch a cap change or an
    // ordering bug, not just mirror whatever the code already does.
    expect(visibleEntities(five, true)).toEqual({
      shown: ['donald trump', 'abbas araghchi'],
      hiddenCount: 3,
    })
  })

  it('never reports a negative remainder when the list is short', () => {
    expect(visibleEntities(['solo'], true)).toEqual({ shown: ['solo'], hiddenCount: 0 })
  })

  it('handles an empty list', () => {
    expect(visibleEntities([], true)).toEqual({ shown: [], hiddenCount: 0 })
  })
})
