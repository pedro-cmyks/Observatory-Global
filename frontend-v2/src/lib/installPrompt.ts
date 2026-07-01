// PWA install-prompt gate + platform detection.
// Spec: docs/specs/2026-07-01-pwa-install-prompt.md
//
// Atlas already ships as an installable PWA (vite-plugin-pwa, display:standalone,
// full icon set). This module decides WHEN to surface the "install the app" toast
// and on WHICH platform path — Android gets a real 1-tap install via
// `beforeinstallprompt`; iOS can only be shown a Share → Add-to-Home hint (Apple
// blocks programmatic install). All browser facts are injected so the decision is
// pure and node-testable.

/** How long a dismissal suppresses the prompt (30 days). */
export const DISMISS_WINDOW_MS = 30 * 24 * 60 * 60 * 1000

/** localStorage key holding the last dismissal timestamp (ms epoch). Mirrors the
 *  `atlas_*_v1` walkthrough-key convention. */
export const INSTALL_PROMPT_KEY = 'atlas_install_prompt_v1'

/** The browser facts the gate needs — all injected, none read here. */
export interface InstallEnv {
  /** Running as an installed app (display-mode: standalone / iOS navigator.standalone). */
  isStandalone: boolean
  /** Mobile read surface (viewport ≤ MOBILE_MAX). */
  isMobile: boolean
  /** Inside an in-app webview (FB/IG/…) that cannot Add-to-Home. */
  isInAppWebview: boolean
  /** iOS Safari — the hint path (no programmatic install). */
  isIOS: boolean
  /** A `beforeinstallprompt` event has been captured (Android/Chromium). */
  hasInstallEvent: boolean
  /** `appinstalled` fired this session. */
  installed: boolean
  /** Last dismissal timestamp (ms epoch), or null if never dismissed. */
  dismissedAt: number | null
  /** Dismissed for good — the iOS ✕ path, where we can never re-detect an
   *  install from a Safari tab, so a dismissal is honored permanently. */
  permanentlyDismissed: boolean
}

export interface Platform {
  isIOS: boolean
  isAndroidChromium: boolean
  isInAppWebview: boolean
}

const IOS_RE = /iphone|ipad|ipod/i
const ANDROID_RE = /android/i
const CHROMIUM_RE = /chrome|crios|chromium/i
// FB/IG/Line/TikTok/Twitter in-app tokens + the raw Android WebView marker `; wv)`.
const IN_APP_RE = /FBAN|FBAV|FB_IAB|Instagram|Line\/|Twitter|TikTok|; wv\)/i

/** Classify the browser from its user-agent string. Pure. */
export function detectPlatform(userAgent: string): Platform {
  const ua = userAgent || ''
  const isInAppWebview = IN_APP_RE.test(ua)
  const isIOS = IOS_RE.test(ua)
  const isAndroidChromium = ANDROID_RE.test(ua) && CHROMIUM_RE.test(ua)
  return { isIOS, isAndroidChromium, isInAppWebview }
}

/** Decide whether the install toast should be visible right now. Pure. */
export function shouldShowInstallPrompt(env: InstallEnv, now: number): boolean {
  if (env.installed || env.isStandalone) return false
  if (env.permanentlyDismissed) return false
  if (!env.isMobile) return false
  if (env.isInAppWebview) return false
  if (env.dismissedAt != null && now - env.dismissedAt < DISMISS_WINDOW_MS) return false
  // iOS shows the hint with no event; every other platform needs a captured
  // beforeinstallprompt (which also proves the app is actually installable).
  return env.isIOS || env.hasInstallEvent
}
