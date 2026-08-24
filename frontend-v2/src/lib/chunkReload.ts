// Chunk-load failure recovery (2026-08-24).
//
// THE CLASS: after a deploy, the page (or the PWA service worker) still holds
// the previous index.html, which references content-hashed chunks that no
// longer exist — the lazy import of the console/Docs chunk rejects with
// "Unable to preload CSS for /assets/App-<hash>.css" (Vite's __vitePreload) or
// the browser's dynamically-imported-module failure. React.lazy CACHES that
// rejection in the module graph, so an error-boundary retry that merely resets
// state re-throws the exact same error: the TRY AGAIN button was dead. The
// only real cure is a document reload against the fresh index + service
// worker — which is why this module exists and why the boundary routes this
// error class to a reload instead of a state reset.
//
// Pure model (node-testable): isChunkLoadError + shouldAutoReload take their
// inputs explicitly. The impure orchestration (sessionStorage, SW update,
// location.reload) lives in the two exported browser helpers at the bottom.

const CHUNK_ERROR_PATTERNS = [
  // Vite's __vitePreload helper: a route chunk's CSS dependency 404'd.
  'unable to preload css',
  // Chromium: `import()` of a missing/stale chunk.
  'failed to fetch dynamically imported module',
  // Safari: same failure, different words.
  'importing a module script failed',
  // Firefox: same failure, different words again.
  'error loading dynamically imported module',
  // Generic bundler spellings — cheap to keep, harmless when absent.
  'chunkloaderror',
  'loading chunk',
  'loading css chunk',
]

/** True when an error message belongs to the stale-chunk-after-deploy class. */
export function isChunkLoadError(message: string | null | undefined): boolean {
  if (!message) return false
  const lower = message.toLowerCase()
  return CHUNK_ERROR_PATTERNS.some((p) => lower.includes(p))
}

export const CHUNK_RELOAD_KEY = 'atlas.chunkReloadOnce'

/**
 * Two auto-reloads within this window = the reload did not cure (offline,
 * broken deploy) — stop cycling and leave the reader on the error card, where
 * TRY AGAIN still reloads manually. A LATER deploy in the same session (stamp
 * older than the window) is allowed to auto-recover again.
 */
export const CHUNK_RELOAD_WINDOW_MS = 60_000

type StampStore = Pick<Storage, 'getItem' | 'setItem'>

/**
 * Cycle guard. Returns true — and stamps the attempt — when no auto-reload
 * happened inside the window. A storage that throws (private mode with
 * sessionStorage disabled) returns false: without a working guard an
 * auto-reload could loop forever, so recovery stays manual there.
 */
export function shouldAutoReload(store: StampStore, now: number): boolean {
  try {
    const raw = store.getItem(CHUNK_RELOAD_KEY)
    const last = raw == null ? Number.NaN : Number(raw)
    if (Number.isFinite(last) && now - last < CHUNK_RELOAD_WINDOW_MS) return false
    store.setItem(CHUNK_RELOAD_KEY, String(now))
    return true
  } catch {
    return false
  }
}

/**
 * The reload itself, always stamped. Before reloading, best-effort ask the
 * registered service worker(s) to update so the reload lands on the FRESH
 * precache/index instead of the same stale one (vite-plugin-pwa runs
 * registerType 'autoUpdate' → the updated worker skips waiting and claims
 * immediately). Never waits more than ~1.5s on a slow SW fetch — the reload
 * happens regardless.
 */
export function forceReloadForChunkError(): void {
  try {
    sessionStorage.setItem(CHUNK_RELOAD_KEY, String(Date.now()))
  } catch {
    /* guard unavailable — still reload; this path is user/deploy initiated */
  }
  const reload = () => window.location.reload()
  try {
    const sw = navigator.serviceWorker
    if (sw?.getRegistrations) {
      const updated = sw
        .getRegistrations()
        .then((regs) => Promise.all(regs.map((r) => r.update().catch(() => {}))))
        .catch(() => {})
      Promise.race([updated, new Promise((res) => setTimeout(res, 1500))]).then(reload, reload)
      return
    }
  } catch {
    /* fall through to plain reload */
  }
  reload()
}

/**
 * Auto-recovery entry point for error boundaries: reloads (guarded) when the
 * error is the stale-chunk class. Returns true when a reload was initiated —
 * the caller can keep its error card as the fallback for the guarded case.
 */
export function maybeAutoReloadForChunkError(message: string | null | undefined): boolean {
  if (!isChunkLoadError(message)) return false
  let store: StampStore
  try {
    store = sessionStorage
  } catch {
    return false
  }
  if (!shouldAutoReload(store, Date.now())) return false
  forceReloadForChunkError()
  return true
}

let preloadListenerInstalled = false

/**
 * Global safety net for Vite's own signal: dynamic-import preload failures
 * dispatch `vite:preloadError` on window BEFORE the error is rethrown to the
 * importer. A guarded reload here recovers even paths that never reach a
 * boundary; when the guard blocks, the event proceeds uncancelled and the
 * nearest PaneErrorBoundary shows the card (whose TRY AGAIN reloads).
 * Idempotent — safe to call from any module that participates in recovery.
 */
export function installChunkPreloadRecovery(): void {
  if (preloadListenerInstalled || typeof window === 'undefined') return
  preloadListenerInstalled = true
  window.addEventListener('vite:preloadError', (event) => {
    const payload = (event as Event & { payload?: unknown }).payload
    const message = payload instanceof Error ? payload.message : String(payload ?? 'Unable to preload')
    // Force the class: this event IS the chunk-failure signal even when the
    // payload message is browser-specific.
    if (maybeAutoReloadForChunkError(isChunkLoadError(message) ? message : 'Unable to preload CSS')) {
      event.preventDefault()
    }
  })
}
