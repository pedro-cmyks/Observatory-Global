// Reader theme (R1 reader re-skin foundation).
//
// The reader pages (Brief / Landing / Docs) carry their own emerald identity,
// SCOPED to a page wrapper: <div className="atlas-reader" data-rtheme="dark">.
// Tokens live in src/styles/readerTheme.css. This module owns WHICH theme the
// wrapper gets:
//
//   stored manual override (localStorage atlas-reader-theme)  — always wins
//   > local clock: 19:00-06:59 is night -> dark
//   > OS prefers-color-scheme: dark     -> dark
//   > otherwise                          -> light
//
// CRITICAL: never write tokens or data attributes on :root/documentElement —
// the keep-alive shell mounts the console (Intel-Noir dark, ThemeContext) and
// the reader in the SAME document. Everything here is scoped state the page
// wrapper consumes.

import { useCallback, useEffect, useRef, useState } from 'react'

export type ReaderTheme = 'light' | 'dark'

export const READER_THEME_STORAGE_KEY = 'atlas-reader-theme'

/** Night window: [DARK_START_HOUR, 24) ∪ [0, DARK_END_HOUR). */
export const DARK_START_HOUR = 19
export const DARK_END_HOUR = 7

function isNight(now: Date): boolean {
  const h = now.getHours()
  return h >= DARK_START_HOUR || h < DARK_END_HOUR
}

/**
 * Pure resolution: stored override wins; else the local clock makes
 * 19:00-06:59 dark; else the OS preference is respected; else light.
 */
export function resolveReaderTheme(
  now: Date,
  prefersDark: boolean,
  stored: ReaderTheme | null,
): ReaderTheme {
  if (stored === 'light' || stored === 'dark') return stored
  return isNight(now) || prefersDark ? 'dark' : 'light'
}

/** Read the persisted manual override; anything but 'light'/'dark' -> null. */
export function readStoredReaderTheme(): ReaderTheme | null {
  try {
    const raw = localStorage.getItem(READER_THEME_STORAGE_KEY)
    return raw === 'light' || raw === 'dark' ? raw : null
  } catch {
    return null // storage unavailable (private mode / SSR): fall to auto
  }
}

/** Persist a manual override (survives reloads; wins over clock and OS). */
export function storeReaderTheme(theme: ReaderTheme): void {
  try {
    localStorage.setItem(READER_THEME_STORAGE_KEY, theme)
  } catch {
    // storage unavailable: the in-memory state still flips for this session
  }
}

/** The flip toggle() applies then persists. */
export function toggledReaderTheme(theme: ReaderTheme): ReaderTheme {
  return theme === 'dark' ? 'light' : 'dark'
}

const DARK_QUERY = '(prefers-color-scheme: dark)'

function osPrefersDark(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia(DARK_QUERY).matches
    : false
}

export interface ReaderThemeState {
  theme: ReaderTheme
  /** Flip and persist the choice (becomes a manual override). */
  toggle: () => void
}

/**
 * Page-level hook. Call ONCE per reader page and stamp the result on the
 * wrapper: <div className="atlas-reader" data-rtheme={theme}>. Pass theme +
 * toggle down to <ReaderThemeToggle/> in the masthead.
 *
 * Follows the OS prefers-color-scheme live — but only while the user has no
 * stored override (their pick is never fought).
 */
export function useReaderTheme(): ReaderThemeState {
  const [theme, setTheme] = useState<ReaderTheme>(() =>
    resolveReaderTheme(new Date(), osPrefersDark(), readStoredReaderTheme()),
  )
  // Ref so the media listener sees the current override state without rebinding.
  const hasOverrideRef = useRef<boolean>(readStoredReaderTheme() !== null)

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    const mq = window.matchMedia(DARK_QUERY)
    const onChange = (e: MediaQueryListEvent) => {
      if (hasOverrideRef.current) return
      setTheme(resolveReaderTheme(new Date(), e.matches, null))
    }
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const toggle = useCallback(() => {
    setTheme((prev) => {
      const next = toggledReaderTheme(prev)
      storeReaderTheme(next)
      hasOverrideRef.current = true
      return next
    })
  }, [])

  return { theme, toggle }
}

export interface ReaderThemeToggleProps {
  theme: ReaderTheme
  onToggle: () => void
}

/**
 * Masthead chip: ☀ in dark mode ("switch to light"), ☾ in light mode.
 * Props-driven (the page owns the hook) so multiple renders never desync.
 */
export function ReaderThemeToggle({ theme, onToggle }: ReaderThemeToggleProps) {
  const toLight = theme === 'dark'
  return (
    <button
      type="button"
      className="reader-chip reader-theme-toggle"
      onClick={onToggle}
      aria-label={toLight ? 'Switch to light theme' : 'Switch to dark theme'}
      aria-pressed={theme === 'dark'}
    >
      <span aria-hidden="true">{toLight ? '☀' : '☾'}</span>
      <span>{toLight ? 'Light' : 'Dark'}</span>
    </button>
  )
}
