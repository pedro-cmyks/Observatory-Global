import { describe, expect, it } from 'vitest'
import { threadCountryPresentation } from './threadGeography'

describe('threadCountryPresentation', () => {
  it('prefers independently verified subject geography over coverage geography', () => {
    expect(threadCountryPresentation({
      top_countries: ['SG', 'CD'],
      subject_countries: ['SN'],
      subject_country_names: ['Senegal'],
      subject_geography_status: 'verified',
    })).toEqual({
      kind: 'subject',
      label: 'Verified subject',
      codes: ['SN'],
      names: ['Senegal'],
    })
  })

  it('falls back explicitly to coverage when subject geography abstains', () => {
    expect(threadCountryPresentation({
      top_countries: ['CD'],
      top_country_names: ['DR Congo'],
      subject_countries: [],
      subject_geography_status: 'partial',
    })).toEqual({
      kind: 'coverage',
      label: 'Coverage',
      codes: ['CD'],
      names: ['DR Congo'],
    })
  })
})
