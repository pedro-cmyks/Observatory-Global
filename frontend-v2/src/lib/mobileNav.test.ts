import { describe, it, expect } from 'vitest'
import {
  MOBILE_TABS,
  routeForTab,
  tabForRoute,
  consoleTabFor,
  showsMobileTabBar,
  surfaceFor,
  fieldVisible,
} from './mobileNav'

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
  // Brief is a ROUTE, not a console surface. It has no answer here, and
  // returning one would be a lie: the component deliberately preserves
  // whichever console surface the user last chose, so that coming back from
  // the Brief lands where they left.
  it('returns null for Brief, which changes no console surface', () => {
    expect(consoleTabFor('brief')).toBeNull()
  })
})

describe('showsMobileTabBar', () => {
  it('shows on the two keep-alive panes', () => {
    expect(showsMobileTabBar('/app')).toBe(true)
    expect(showsMobileTabBar('/brief')).toBe(true)
  })
  it('stays off every other route', () => {
    expect(showsMobileTabBar('/')).toBe(false)
    expect(showsMobileTabBar('/docs')).toBe(false)
    expect(showsMobileTabBar('/docs/api')).toBe(false)
    expect(showsMobileTabBar('/whatever-ships-next')).toBe(false)
  })
})

describe('surfaceFor', () => {
  it('Live is the stream whatever is focused — the tab decides, focus only steers the Lens', () => {
    expect(surfaceFor('live', true)).toBe('live')
    expect(surfaceFor('live', false)).toBe('live')
  })
  it('the Lens is the focused thing, or the field when nothing is focused', () => {
    expect(surfaceFor('lens', true)).toBe('lens-focused')
    expect(surfaceFor('lens', false)).toBe('lens-field')
  })
  // The C1 invariant, pinned: tapping a tab must ALWAYS change what is on
  // screen. A regression here means the bar can show an active tab over
  // content that did not move.
  it('never resolves the two tabs to the same surface, in any focus state', () => {
    for (const focused of [true, false]) {
      expect(surfaceFor('live', focused)).not.toBe(surfaceFor('lens', focused))
    }
  })
})

describe('fieldVisible', () => {
  it('is the Lens field and nothing else', () => {
    expect(fieldVisible('lens-field')).toBe(true)
    expect(fieldVisible('lens-focused')).toBe(false)
    expect(fieldVisible('live')).toBe(false)
  })
  // The read pane serves two surfaces. If it were hidden under either of
  // them, one tab would go blank — and pausing it on the wrong surface would
  // freeze the pane the user is looking at.
  it('leaves the read pane showing under both of its surfaces', () => {
    expect(fieldVisible('lens-focused')).toBe(false)
    expect(fieldVisible('live')).toBe(false)
  })
})
