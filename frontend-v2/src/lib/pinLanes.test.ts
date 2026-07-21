import { describe, it, expect } from 'vitest'
import { pinLane, groupPinsByLane } from './pinLanes'

describe('pinLane', () => {
  it('WHO for person and source', () => {
    expect(pinLane('person')).toBe('who')
    expect(pinLane('source')).toBe('who')
  })
  it('WHERE for country, and for event/anomaly that carry a countryCode', () => {
    expect(pinLane('country')).toBe('where')
    expect(pinLane('event', { countryCode: 'US' })).toBe('where')
    expect(pinLane('event', {})).toBe('what')
  })
  it('WHAT for theme/thread/connections and unknown strings', () => {
    expect(pinLane('theme')).toBe('what')
    expect(pinLane('thread')).toBe('what')
    expect(pinLane('totally-new-kind')).toBe('what')
  })
  it('groups a pin list by lane preserving order', () => {
    const pins = [
      { anchorType: 'person', label: 'A' },
      { anchorType: 'country', label: 'B' },
      { anchorType: 'theme', label: 'C' },
    ] as any
    const g = groupPinsByLane(pins)
    expect(g.who.map((p: any) => p.label)).toEqual(['A'])
    expect(g.where.map((p: any) => p.label)).toEqual(['B'])
    expect(g.what.map((p: any) => p.label)).toEqual(['C'])
  })
})
