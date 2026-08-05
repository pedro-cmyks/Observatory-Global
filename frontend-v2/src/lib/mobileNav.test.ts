import { describe, it, expect } from 'vitest'
import { MOBILE_TABS, routeForTab, tabForRoute, consoleTabFor } from './mobileNav'

describe('MOBILE_TABS', () => {
  it('is exactly three tabs in reading order', () => {
    expect(MOBILE_TABS.map((t) => t.id)).toEqual(['brief', 'lens', 'live'])
  })
})

describe('routeForTab', () => {
  it('sends the Brief tab to its own route', () => {
    expect(routeForTab('brief')).toBe('/brief')
  })
  it('sends the console tabs to /app', () => {
    expect(routeForTab('lens')).toBe('/app')
    expect(routeForTab('live')).toBe('/app')
  })
})

describe('tabForRoute', () => {
  it('resolves the Brief route', () => {
    expect(tabForRoute('/brief', 'live')).toBe('brief')
  })
  it('keeps the remembered console tab on /app', () => {
    expect(tabForRoute('/app', 'live')).toBe('live')
    expect(tabForRoute('/app', 'lens')).toBe('lens')
  })
  it('falls back to the lens on an unknown route', () => {
    expect(tabForRoute('/docs', 'live')).toBe('lens')
  })
})

describe('consoleTabFor', () => {
  it('maps a bar tab to the console surface it shows', () => {
    expect(consoleTabFor('lens')).toBe('lens')
    expect(consoleTabFor('live')).toBe('live')
  })
  it('leaves the console on the lens while the Brief route is active', () => {
    expect(consoleTabFor('brief')).toBe('lens')
  })
})
