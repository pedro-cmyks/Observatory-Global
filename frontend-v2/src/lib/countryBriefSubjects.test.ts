import { describe, it, expect } from 'vitest'
import { classifySubject, buildKeySubjects } from './countryBriefSubjects'

describe('classifySubject (#176 reframe)', () => {
  it('types real people as person', () => {
    expect(classifySubject('gustavo petro')).toBe('person')
    expect(classifySubject('Luis Diaz')).toBe('person')
  })

  it('reclassifies geo leaks as place, not person', () => {
    expect(classifySubject('america latin')).toBe('place')        // GDELT truncation
    expect(classifySubject('republica dominicana')).toBe('place')
    expect(classifySubject('saudi arabia')).toBe('place')
    expect(classifySubject('estados unidos')).toBe('place')
  })

  it('types climate patterns as event', () => {
    expect(classifySubject('el niño')).toBe('event')
    expect(classifySubject('la niña')).toBe('event')
  })

  it('types teams / institutions as organization', () => {
    expect(classifySubject('bafana bafana')).toBe('organization')
    expect(classifySubject('naciones unidas')).toBe('organization')
  })

  it('drops unclassifiable noise', () => {
    expect(classifySubject('dar una patada')).toBeNull()
    expect(classifySubject('trump')).toBeNull()  // single token
    expect(classifySubject('')).toBeNull()
  })
})

describe('buildKeySubjects', () => {
  it('keeps El Niño as event instead of discarding it', () => {
    const out = buildKeySubjects([
      { name: 'El Niño', count: 30 },
      { name: 'Gustavo Petro', count: 10 },
    ])
    const types = Object.fromEntries(out.map(s => [s.name, s.type]))
    expect(types['El Niño']).toBe('event')
    expect(types['Gustavo Petro']).toBe('person')
  })

  it('does not surface geo as people', () => {
    const out = buildKeySubjects([
      { name: 'america latin', count: 99 },
      { name: 'Luis Diaz', count: 40 },
    ])
    expect(out.find(s => s.name === 'america latin')?.type).toBe('place')
    expect(out.some(s => s.type === 'person' && /latin/i.test(s.name))).toBe(false)
  })

  it('respects count order and limit, drops noise', () => {
    const out = buildKeySubjects([
      { name: 'dar una patada', count: 100 },     // dropped
      { name: 'Gustavo Petro', count: 50 },
      { name: 'Dina Boluarte', count: 40 },
    ], 1)
    expect(out).toHaveLength(1)
    expect(out[0].name).toBe('Gustavo Petro')
  })
})
