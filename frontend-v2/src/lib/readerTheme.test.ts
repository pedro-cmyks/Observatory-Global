// Reader theme resolution (R1 reader re-skin foundation). Rules under test:
// - a stored manual override ALWAYS wins (user intent beats clock and OS)
// - no override: the local clock makes 19:00-06:59 dark
// - no override, daytime: OS prefers-color-scheme dark is respected -> dark
// - no override, daytime, no OS dark preference -> light
// - toggling persists the choice to localStorage (atlas-reader-theme) so the
//   next visit resolves to the user's pick.
//
// vitest runs in node: back localStorage with a Map (workbench.test.ts pattern).
import { describe, it, expect, vi, beforeEach } from 'vitest'

const store = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => void store.set(k, String(v)),
  removeItem: (k: string) => void store.delete(k),
  clear: () => store.clear(),
})

import {
  READER_THEME_STORAGE_KEY,
  resolveReaderTheme,
  readStoredReaderTheme,
  storeReaderTheme,
  toggledReaderTheme,
} from './readerTheme'

const at = (hour: number, minute = 0) => new Date(2026, 6, 15, hour, minute)

beforeEach(() => localStorage.clear())

describe('resolveReaderTheme', () => {
  it('stored override wins over clock and OS preference', () => {
    // Night + OS dark, but the user chose light: light wins.
    expect(resolveReaderTheme(at(20), true, 'light')).toBe('light')
    // Day + OS light, but the user chose dark: dark wins.
    expect(resolveReaderTheme(at(10), false, 'dark')).toBe('dark')
  })

  it('20:00 with no store resolves dark (clock 19-7 is night)', () => {
    expect(resolveReaderTheme(at(20), false, null)).toBe('dark')
  })

  it('10:00 with no store and no OS dark preference resolves light', () => {
    expect(resolveReaderTheme(at(10), false, null)).toBe('light')
  })

  it('prefers-dark at 10:00 with no store resolves dark (OS preference respected)', () => {
    expect(resolveReaderTheme(at(10), true, null)).toBe('dark')
  })

  it('night window boundaries: 19:00 and 06:59 are dark, 07:00 is light', () => {
    expect(resolveReaderTheme(at(19), false, null)).toBe('dark')
    expect(resolveReaderTheme(at(6, 59), false, null)).toBe('dark')
    expect(resolveReaderTheme(at(7), false, null)).toBe('light')
  })
})

describe('persistence (the toggle path)', () => {
  it('storeReaderTheme persists under atlas-reader-theme and readStoredReaderTheme round-trips', () => {
    expect(readStoredReaderTheme()).toBe(null)
    storeReaderTheme('dark')
    expect(localStorage.getItem(READER_THEME_STORAGE_KEY)).toBe('dark')
    expect(readStoredReaderTheme()).toBe('dark')
  })

  it('toggledReaderTheme flips the theme (what toggle() applies then persists)', () => {
    expect(toggledReaderTheme('light')).toBe('dark')
    expect(toggledReaderTheme('dark')).toBe('light')
  })

  it('toggle persists: after storing the flip, a later resolve honors it over clock/OS', () => {
    // User is reading at night (auto-dark), toggles to light:
    const before = resolveReaderTheme(at(21), true, readStoredReaderTheme())
    expect(before).toBe('dark')
    storeReaderTheme(toggledReaderTheme(before))
    expect(resolveReaderTheme(at(21), true, readStoredReaderTheme())).toBe('light')
  })

  it('readStoredReaderTheme ignores garbage values', () => {
    localStorage.setItem(READER_THEME_STORAGE_KEY, 'sepia')
    expect(readStoredReaderTheme()).toBe(null)
  })
})
