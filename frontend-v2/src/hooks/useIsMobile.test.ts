import { describe, it, expect } from 'vitest'
import { isMobileWidth, MOBILE_MAX } from './useIsMobile'

describe('isMobileWidth', () => {
  it('is false on desktop width', () => {
    expect(isMobileWidth(1280)).toBe(false)
    expect(isMobileWidth(769)).toBe(false)
  })
  it('is true at/below the mobile breakpoint', () => {
    expect(isMobileWidth(MOBILE_MAX)).toBe(true)
    expect(isMobileWidth(375)).toBe(true)
  })
  it('respects a custom max', () => {
    expect(isMobileWidth(900, 1024)).toBe(true)
    expect(isMobileWidth(1100, 1024)).toBe(false)
  })
})
