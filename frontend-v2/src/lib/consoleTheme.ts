// Console theme resolution (R3 emerald foundation).
//
// The console default is AUTO day/night over the emerald preset pair,
// reusing the reader resolver semantics (src/lib/readerTheme.tsx):
//
//   stored manual override (localStorage atlas-console-theme) — always wins
//   > local clock: 19:00-06:59 is night -> emerald-dark
//   > OS prefers-color-scheme: dark     -> emerald-dark
//   > otherwise                          -> emerald-light
//
// The override key is the console's OWN — never shared with the reader's
// atlas-reader-theme (the two shells theme independently by design; the
// keep-alive shell mounts both in one document). Unlike the reader, the
// console override can be ANY registered theme id (Intel Noir stays a
// one-selection flip-back in Settings — the EE-map default-flip playbook).

import { resolveReaderTheme } from './readerTheme'
import { THEMES, type Theme } from '../styles/themes'

export const CONSOLE_THEME_STORAGE_KEY = 'atlas-console-theme'

export const AUTO_LIGHT_THEME_ID = 'emerald-light'
export const AUTO_DARK_THEME_ID = 'emerald-dark'

/**
 * Pure resolution: a stored VALID theme id always wins; otherwise the
 * reader's clock/OS auto logic picks the emerald day or night preset.
 */
export function resolveConsoleThemeId(
  now: Date,
  prefersDark: boolean,
  storedId: string | null,
  themes: Record<string, Theme> = THEMES,
): string {
  if (storedId && themes[storedId]) return storedId
  return resolveReaderTheme(now, prefersDark, null) === 'dark'
    ? AUTO_DARK_THEME_ID
    : AUTO_LIGHT_THEME_ID
}

/**
 * The sun/moon flip: any dark-scheme theme (emerald-dark, intel-noir,
 * retro-radar) goes to emerald day; the light theme goes to emerald night.
 */
export function toggledConsoleThemeId(current: Theme): string {
  return current.scheme === 'dark' ? AUTO_LIGHT_THEME_ID : AUTO_DARK_THEME_ID
}

/** Read the persisted manual override; unknown/invalid ids -> null (auto). */
export function readStoredConsoleThemeId(
  themes: Record<string, Theme> = THEMES,
): string | null {
  try {
    const raw = localStorage.getItem(CONSOLE_THEME_STORAGE_KEY)
    return raw && themes[raw] ? raw : null
  } catch {
    return null // storage unavailable (private mode / SSR): fall to auto
  }
}

/** Persist a manual override (survives reloads; wins over clock and OS). */
export function storeConsoleThemeId(id: string): void {
  try {
    localStorage.setItem(CONSOLE_THEME_STORAGE_KEY, id)
  } catch {
    // storage unavailable: the in-memory state still flips for this session
  }
}
