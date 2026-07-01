// PWA install-prompt gate + platform detection (spec
// docs/specs/2026-07-01-pwa-install-prompt.md). Pure logic, node-testable:
// the component injects the browser facts, these functions decide.
import { describe, it, expect } from 'vitest'

import {
  DISMISS_WINDOW_MS,
  detectPlatform,
  shouldShowInstallPrompt,
  type InstallEnv,
} from './installPrompt'

const NOW = 1_751_000_000_000 // fixed epoch ms for deterministic window math

// A base env where the prompt WOULD show (iOS, fresh). Each test overrides
// exactly the one fact under test.
function env(over: Partial<InstallEnv> = {}): InstallEnv {
  return {
    isStandalone: false,
    isMobile: true,
    isInAppWebview: false,
    isIOS: true,
    hasInstallEvent: false,
    installed: false,
    dismissedAt: null,
    permanentlyDismissed: false,
    ...over,
  }
}

const UA = {
  iphoneSafari:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
  ipadSafari:
    'Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
  androidChrome:
    'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36',
  facebook:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 [FBAN/FBIOS;FBAV/470.0.0]',
  instagram:
    'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Mobile Safari/537.36 Instagram 320.0.0.0 Android',
  androidWebview:
    'Mozilla/5.0 (Linux; Android 14; Pixel 8; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0.0.0 Mobile Safari/537.36',
  desktopChrome:
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
}

describe('detectPlatform', () => {
  it('flags iPhone Safari as iOS, not a webview', () => {
    const p = detectPlatform(UA.iphoneSafari)
    expect(p.isIOS).toBe(true)
    expect(p.isInAppWebview).toBe(false)
  })

  it('flags iPad as iOS', () => {
    expect(detectPlatform(UA.ipadSafari).isIOS).toBe(true)
  })

  it('Android Chrome is not iOS and not a webview', () => {
    const p = detectPlatform(UA.androidChrome)
    expect(p.isIOS).toBe(false)
    expect(p.isInAppWebview).toBe(false)
  })

  it('detects the Facebook in-app browser', () => {
    expect(detectPlatform(UA.facebook).isInAppWebview).toBe(true)
  })

  it('detects the Instagram in-app browser', () => {
    expect(detectPlatform(UA.instagram).isInAppWebview).toBe(true)
  })

  it('detects a raw Android WebView (; wv)', () => {
    expect(detectPlatform(UA.androidWebview).isInAppWebview).toBe(true)
  })

  it('desktop Chrome is neither iOS nor webview', () => {
    const p = detectPlatform(UA.desktopChrome)
    expect(p.isIOS).toBe(false)
    expect(p.isInAppWebview).toBe(false)
  })
})

describe('shouldShowInstallPrompt', () => {
  it('shows for a fresh iOS visitor (no event needed)', () => {
    expect(shouldShowInstallPrompt(env(), NOW)).toBe(true)
  })

  it('shows for Android once beforeinstallprompt is captured', () => {
    expect(
      shouldShowInstallPrompt(env({ isIOS: false, hasInstallEvent: true }), NOW),
    ).toBe(true)
  })

  it('waits (hidden) on Android before the event fires', () => {
    expect(
      shouldShowInstallPrompt(env({ isIOS: false, hasInstallEvent: false }), NOW),
    ).toBe(false)
  })

  it('never shows when already installed / standalone', () => {
    expect(shouldShowInstallPrompt(env({ isStandalone: true }), NOW)).toBe(false)
    expect(shouldShowInstallPrompt(env({ installed: true }), NOW)).toBe(false)
  })

  it('never shows on desktop', () => {
    expect(shouldShowInstallPrompt(env({ isMobile: false }), NOW)).toBe(false)
  })

  it('never shows inside an in-app webview', () => {
    expect(shouldShowInstallPrompt(env({ isInAppWebview: true }), NOW)).toBe(false)
  })

  it('stays hidden while a dismissal is still within the 30-day window', () => {
    const yesterday = NOW - 24 * 60 * 60 * 1000
    expect(shouldShowInstallPrompt(env({ dismissedAt: yesterday }), NOW)).toBe(false)
  })

  it('shows again once the 30-day dismissal window has elapsed', () => {
    const longAgo = NOW - (DISMISS_WINDOW_MS + 1)
    expect(shouldShowInstallPrompt(env({ dismissedAt: longAgo }), NOW)).toBe(true)
  })

  it('never shows again after a permanent dismissal (iOS ✕), even years later', () => {
    const longAgo = NOW - (DISMISS_WINDOW_MS * 100)
    expect(
      shouldShowInstallPrompt(env({ permanentlyDismissed: true, dismissedAt: longAgo }), NOW),
    ).toBe(false)
  })
})
