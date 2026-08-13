import { describe, expect, it } from 'vitest'
import { isConsoleEntryRoute, showAppLoader } from './appLoaderGate'

describe('isConsoleEntryRoute', () => {
  it('is true only for the console path', () => {
    expect(isConsoleEntryRoute('/app')).toBe(true)
    expect(isConsoleEntryRoute('/brief')).toBe(false)
    expect(isConsoleEntryRoute('/')).toBe(false)
    expect(isConsoleEntryRoute('/docs')).toBe(false)
  })

  it('tolerates the shapes a real location hands it', () => {
    expect(isConsoleEntryRoute('/app/')).toBe(true)
    expect(isConsoleEntryRoute('/app?theme=dynamic-topic-11877&entry=brief')).toBe(true)
    expect(isConsoleEntryRoute('/app#top')).toBe(true)
    // Not the console: a path that merely starts with the same letters.
    expect(isConsoleEntryRoute('/apple')).toBe(false)
    expect(isConsoleEntryRoute('')).toBe(false)
  })
})

describe('showAppLoader', () => {
  it('gates a cold boot into the console until it is ready', () => {
    expect(showAppLoader({ appReady: false, entryPath: '/app' })).toBe(true)
    expect(showAppLoader({ appReady: true, entryPath: '/app' })).toBe(false)
  })

  // THE MEASURED BUG (W1). The phone's front door is /brief, so the console
  // mounts for the first time on a Lens/Live tab tap. The loader is
  // `position: fixed; inset: 0` at z-index 9999 — ABOVE the tab bar's 9500 —
  // and lifts only when /api/v2/nodes returns rows or after a 10s cap. Under
  // the 429s the reader was already hitting, that is ~11s of opaque nothing
  // with the three tabs unreachable underneath it: measured on prod at 375px,
  // `elementFromPoint` over the Brief tab returned `DIV.atlas-loader`.
  it('never gates a tab tap: the reader already has a painted page behind them', () => {
    expect(showAppLoader({ appReady: false, entryPath: '/brief' })).toBe(false)
    expect(showAppLoader({ appReady: true, entryPath: '/brief' })).toBe(false)
  })

  it('never gates an in-app entry from any other door', () => {
    for (const entry of ['/', '/docs', '/docs/method']) {
      expect(showAppLoader({ appReady: false, entryPath: entry })).toBe(false)
    }
  })
})
