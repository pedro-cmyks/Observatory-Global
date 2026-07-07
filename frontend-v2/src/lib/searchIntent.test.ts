import { describe, it, expect } from 'vitest'
import { classifyQuery, isInvestigativeQuery } from './searchIntent'

describe('classifyQuery', () => {
  it('bare country → country intent', () => {
    expect(classifyQuery({ raw: 'Venezuela', countryCode: 'VE', bareCountry: true }).intent).toBe('country')
  })

  it('country + topic → compound intent', () => {
    expect(classifyQuery({ raw: 'conflicto Venezuela', countryCode: 'VE', bareCountry: false }).intent).toBe('compound')
  })

  it('topic without country → topic intent', () => {
    expect(classifyQuery({ raw: 'elections', countryCode: null, bareCountry: false }).intent).toBe('topic')
  })

  it('too short → empty intent', () => {
    expect(classifyQuery({ raw: 'a', countryCode: null, bareCountry: false }).intent).toBe('empty')
  })
})

describe('isInvestigativeQuery', () => {
  it('a bare noun is not investigative', () => {
    expect(isInvestigativeQuery('elections')).toBe(false)
    expect(isInvestigativeQuery('Venezuela')).toBe(false)
  })

  it('a multi-word research phrase is investigative', () => {
    expect(isInvestigativeQuery('attacks on US bases in the region')).toBe(true)
  })

  it('a long single-clause phrase is investigative', () => {
    expect(isInvestigativeQuery('water and energy security crisis')).toBe(true)
  })

  it('classifyQuery carries the investigative flag', () => {
    expect(classifyQuery({ raw: 'water crisis in Iran and its neighbors', countryCode: 'IR', bareCountry: false }).isInvestigative).toBe(true)
  })
})
