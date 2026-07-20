import { describe, it, expect } from 'vitest'
import { coverageChipTip, COVERAGE_CHIP_LABEL } from './countryChips'

describe('countryChips honesty (council R2 N1)', () => {
  it('label never asserts origin — "covered from" was the lie class', () => {
    expect(COVERAGE_CHIP_LABEL.toLowerCase()).not.toContain('covered from')
    expect(COVERAGE_CHIP_LABEL.toLowerCase()).toContain('coverage')
  })
  it('tip says these are coverage-row countries, not verified outlet origin', () => {
    const tip = coverageChipTip('United States')
    expect(tip).toContain('United States')
    expect(tip).toMatch(/coverage/i)
    expect(tip).toMatch(/not a verified outlet origin/i)
    expect(tip).toMatch(/subject/i)
  })
})
