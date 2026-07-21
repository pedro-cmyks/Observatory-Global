import { describe, it, expect } from 'vitest'
import { threadPin, personPin, countryPin, receiptFrom } from './capturePayloads'

describe('capturePayloads', () => {
  it('threadPin from a universe/neighbor node', () => {
    expect(threadPin('dynamic-topic-9', 'Gaza ceasefire')).toEqual({
      id: 'theme-dynamic-topic-9', type: 'theme', title: 'Gaza ceasefire', urlParams: '?theme=dynamic-topic-9',
    })
  })
  it('personPin encodes names with spaces/diacritics', () => {
    expect(personPin('José Ramírez')).toEqual({
      id: 'person-José Ramírez', type: 'person', title: 'José Ramírez', urlParams: '?person=Jos%C3%A9%20Ram%C3%ADrez',
    })
  })
  it('countryPin', () => {
    expect(countryPin('US', 'United States')).toEqual({
      id: 'country-US', type: 'country', title: 'United States', urlParams: '?country=US',
    })
  })
  it('receiptFrom defaults gateStatus unknown and decodes the headline', () => {
    const c = receiptFrom({ headline: '&amp;H', source: 'X', url: 'u', publishedDate: '2026-07-01' })
    expect(c.gateStatus).toBe('unknown')
    expect(c.headline).toBe('&H')
    expect(c.url).toBe('u')
    expect(c.source).toBe('X')
  })
  it('receiptFrom accepts an explicit gateStatus and decodes numeric entities', () => {
    const c = receiptFrom({ headline: 'A&#x2019;B', gateStatus: 'verified' })
    expect(c.gateStatus).toBe('verified')
    expect(c.headline).toBe('A’B')
  })
})
