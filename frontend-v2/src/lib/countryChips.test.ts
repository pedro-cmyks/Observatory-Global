import { describe, it, expect } from 'vitest'
import { coverageChipTip, COVERAGE_CHIP_LABEL } from './countryChips'

describe('countryChips honesty', () => {
  it('labels chips as coverage geography, not subject', () => {
    expect(COVERAGE_CHIP_LABEL).toMatch(/cover/i)
  })
  it('tip explains these are where it is reported from', () => {
    const tip = coverageChipTip('United States')
    expect(tip).toMatch(/covered|reported|subject/i)
    expect(tip).toContain('United States')
  })
})
