import { describe, it, expect } from 'vitest'
import {
  resolveConsoleThemeId,
  toggledConsoleThemeId,
  CONSOLE_THEME_STORAGE_KEY,
  AUTO_LIGHT_THEME_ID,
  AUTO_DARK_THEME_ID,
} from './consoleTheme'
import { THEMES } from '../styles/themes'

// Console default = auto day/night over the EMERALD pair, reusing the reader
// resolver semantics (stored override wins > clock 19-7 > prefers-dark).
// The override key is the console's OWN (atlas-console-theme) — never shared
// with the reader's atlas-reader-theme.

const noon = new Date('2026-07-15T12:00:00')
const night = new Date('2026-07-15T21:30:00')
const earlyMorning = new Date('2026-07-15T06:59:00')
const sevenAm = new Date('2026-07-15T07:00:00')

describe('resolveConsoleThemeId', () => {
  it('daytime, no OS dark preference, no override -> emerald-light', () => {
    expect(resolveConsoleThemeId(noon, false, null)).toBe(AUTO_LIGHT_THEME_ID)
  })

  it('night hours (>=19:00) -> emerald-dark even without OS preference', () => {
    expect(resolveConsoleThemeId(night, false, null)).toBe(AUTO_DARK_THEME_ID)
  })

  it('early morning (<07:00) -> emerald-dark; 07:00 flips to light', () => {
    expect(resolveConsoleThemeId(earlyMorning, false, null)).toBe(AUTO_DARK_THEME_ID)
    expect(resolveConsoleThemeId(sevenAm, false, null)).toBe(AUTO_LIGHT_THEME_ID)
  })

  it('daytime but OS prefers dark -> emerald-dark', () => {
    expect(resolveConsoleThemeId(noon, true, null)).toBe(AUTO_DARK_THEME_ID)
  })

  it('stored override ALWAYS wins (any valid theme id, any clock/OS state)', () => {
    expect(resolveConsoleThemeId(noon, false, 'intel-noir')).toBe('intel-noir')
    expect(resolveConsoleThemeId(night, true, 'emerald-light')).toBe('emerald-light')
    expect(resolveConsoleThemeId(noon, false, 'retro-radar')).toBe('retro-radar')
  })

  it('unknown stored id falls back to auto (never a broken theme)', () => {
    expect(resolveConsoleThemeId(noon, false, 'not-a-theme')).toBe(AUTO_LIGHT_THEME_ID)
    expect(resolveConsoleThemeId(night, false, 'not-a-theme')).toBe(AUTO_DARK_THEME_ID)
  })
})

describe('toggledConsoleThemeId (sun/moon flip)', () => {
  it('any dark-scheme theme flips to emerald-light', () => {
    expect(toggledConsoleThemeId(THEMES['emerald-dark'])).toBe(AUTO_LIGHT_THEME_ID)
    expect(toggledConsoleThemeId(THEMES['intel-noir'])).toBe(AUTO_LIGHT_THEME_ID)
    expect(toggledConsoleThemeId(THEMES['retro-radar'])).toBe(AUTO_LIGHT_THEME_ID)
  })

  it('the light theme flips to emerald-dark', () => {
    expect(toggledConsoleThemeId(THEMES['emerald-light'])).toBe(AUTO_DARK_THEME_ID)
  })
})

describe('theme registry contract', () => {
  it('both emerald presets exist with the right scheme', () => {
    expect(THEMES[AUTO_LIGHT_THEME_ID]?.scheme).toBe('light')
    expect(THEMES[AUTO_DARK_THEME_ID]?.scheme).toBe('dark')
  })

  it('intel-noir stays registered and selectable (flip-back playbook)', () => {
    expect(THEMES['intel-noir']).toBeDefined()
    expect(THEMES['intel-noir'].scheme).toBe('dark')
  })

  it('console storage key is its own, never the reader key', () => {
    expect(CONSOLE_THEME_STORAGE_KEY).toBe('atlas-console-theme')
    expect(CONSOLE_THEME_STORAGE_KEY).not.toBe('atlas-reader-theme')
  })
})
