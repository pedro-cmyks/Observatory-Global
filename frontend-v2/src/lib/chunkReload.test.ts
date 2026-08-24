import { describe, it, expect } from 'vitest'
import {
  CHUNK_RELOAD_KEY,
  CHUNK_RELOAD_WINDOW_MS,
  isChunkLoadError,
  shouldAutoReload,
} from './chunkReload'

// vitest runs in node without jsdom (repo convention): the boundary's behavior
// is frozen through its pure model — the error-class detector and the
// reload-cycle guard. The impure half (sessionStorage/SW/reload) is a thin
// orchestration over these two.

describe('isChunkLoadError', () => {
  it('matches the production failure verbatim (Vite CSS preload)', () => {
    expect(isChunkLoadError('Unable to preload CSS for /assets/App-BK2cusDt.css')).toBe(true)
  })

  it('matches every browser spelling of a failed dynamic chunk import', () => {
    // Chromium
    expect(isChunkLoadError('Failed to fetch dynamically imported module: https://x/assets/App-abc.js')).toBe(true)
    // Safari
    expect(isChunkLoadError('Importing a module script failed.')).toBe(true)
    // Firefox
    expect(isChunkLoadError('error loading dynamically imported module: https://x/assets/App-abc.js')).toBe(true)
    // generic bundler spellings
    expect(isChunkLoadError('ChunkLoadError: Loading chunk 42 failed.')).toBe(true)
  })

  it('is case-insensitive', () => {
    expect(isChunkLoadError('UNABLE TO PRELOAD CSS for /assets/x.css')).toBe(true)
  })

  it('does NOT match ordinary runtime errors — those keep the state-reset retry', () => {
    expect(isChunkLoadError("Cannot read properties of undefined (reading 'map')")).toBe(false)
    expect(isChunkLoadError('NetworkError when attempting to fetch resource.')).toBe(false)
    expect(isChunkLoadError('')).toBe(false)
    expect(isChunkLoadError(null)).toBe(false)
    expect(isChunkLoadError(undefined)).toBe(false)
  })
})

function fakeStore(initial: Record<string, string> = {}) {
  const data = { ...initial }
  return {
    data,
    getItem: (k: string) => (k in data ? data[k] : null),
    setItem: (k: string, v: string) => {
      data[k] = v
    },
  }
}

describe('shouldAutoReload (cycle guard)', () => {
  it('first failure: allows the reload and stamps the attempt', () => {
    const store = fakeStore()
    expect(shouldAutoReload(store, 1_000)).toBe(true)
    expect(store.data[CHUNK_RELOAD_KEY]).toBe('1000')
  })

  it('a reload that did not cure (same failure right after) does NOT cycle', () => {
    const store = fakeStore({ [CHUNK_RELOAD_KEY]: '1000' })
    expect(shouldAutoReload(store, 1_000 + 5_000)).toBe(false)
    // the stamp is untouched by a refusal
    expect(store.data[CHUNK_RELOAD_KEY]).toBe('1000')
  })

  it('a LATER deploy in the same session (stamp older than the window) recovers again', () => {
    const store = fakeStore({ [CHUNK_RELOAD_KEY]: '1000' })
    const later = 1_000 + CHUNK_RELOAD_WINDOW_MS + 1
    expect(shouldAutoReload(store, later)).toBe(true)
    expect(store.data[CHUNK_RELOAD_KEY]).toBe(String(later))
  })

  it('a garbage stamp is treated as absent, not as a permanent block', () => {
    const store = fakeStore({ [CHUNK_RELOAD_KEY]: 'not-a-number' })
    expect(shouldAutoReload(store, 2_000)).toBe(true)
  })

  it('a throwing storage refuses auto-reload — no guard means no cycle safety', () => {
    const throwing = {
      getItem: () => {
        throw new Error('sessionStorage disabled')
      },
      setItem: () => {
        throw new Error('sessionStorage disabled')
      },
    }
    expect(shouldAutoReload(throwing, 1_000)).toBe(false)
  })
})
