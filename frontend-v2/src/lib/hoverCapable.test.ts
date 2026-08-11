import { describe, it, expect } from 'vitest'
import { hoverIsAvailable } from './hoverCapable'

describe('hoverIsAvailable', () => {
  it('is true when the device reports a hover-capable pointer', () => {
    expect(hoverIsAvailable(() => ({ matches: true }))).toBe(true)
  })
  it('is false when the device reports (hover: none)', () => {
    expect(hoverIsAvailable(() => ({ matches: false }))).toBe(false)
  })
  it('defaults to true when matchMedia is unavailable', () => {
    expect(hoverIsAvailable(undefined)).toBe(true)
  })
})
