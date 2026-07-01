import { useCallback, useEffect, useRef, useState } from 'react'
import './InstallPrompt.css'
import {
  INSTALL_PROMPT_KEY,
  detectPlatform,
  shouldShowInstallPrompt,
  type InstallEnv,
} from '../lib/installPrompt'
import { isMobileWidth } from '../hooks/useIsMobile'
import { track, trackOnce } from '../lib/telemetry'

/** iOS Safari share glyph — a small inline SVG so the hint is unambiguous. */
function ShareGlyph() {
  return (
    <svg className="install-toast__share" viewBox="0 0 24 24" width={13} height={13} aria-hidden focusable="false">
      <path d="M12 3v11" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M8 7l4-4 4 4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M6 11h-1v9h14v-9h-1" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

// Market-grade PWA install promotion (spec 2026-07-01-pwa-install-prompt.md).
// A non-invasive slide-in toast that reads "download the app": Android gets a
// real 1-tap install via `beforeinstallprompt`; iOS gets the Share → Add-to-Home
// hint (Apple blocks programmatic install). Shows only after the visitor has
// engaged (~15s or a scroll), never nags (30-day dismissal), never blocks the page.

/** The `beforeinstallprompt` event — not in the standard DOM lib types. */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

type Mode = 'android' | 'ios' | 'success'

const ENGAGE_MS = 15_000
const SCROLL_TRIGGER_PX = 400

function isSpanish(): boolean {
  try {
    return (navigator.language || 'en').toLowerCase().startsWith('es')
  } catch {
    return false
  }
}

// Android stores a timestamp (30-day snooze). iOS stores the sentinel 'never':
// once an iOS user dismisses, we can never re-detect the install from a Safari
// tab (no API, partitioned storage), so honor the dismissal for good.
function readDismissState(): { dismissedAt: number | null; permanentlyDismissed: boolean } {
  try {
    const v = localStorage.getItem(INSTALL_PROMPT_KEY)
    if (!v) return { dismissedAt: null, permanentlyDismissed: false }
    if (v === 'never') return { dismissedAt: null, permanentlyDismissed: true }
    return { dismissedAt: Number(v), permanentlyDismissed: false }
  } catch {
    return { dismissedAt: null, permanentlyDismissed: false } // private mode → fail open
  }
}

function isStandalone(): boolean {
  try {
    const mq = window.matchMedia?.('(display-mode: standalone)').matches
    // iOS Safari exposes standalone on navigator, not via display-mode.
    const iosStandalone = (navigator as unknown as { standalone?: boolean }).standalone === true
    return Boolean(mq) || iosStandalone
  } catch {
    return false
  }
}

const COPY = {
  es: {
    androidTitle: 'Instala la app de Atlas',
    androidSub: 'Gratis, sin tienda.',
    install: 'Instalar',
    iosTitle: 'Añade Atlas a tu inicio',
    iosTap: 'Toca',
    iosRest: 'y “Añadir a pantalla de inicio”.',
    success: 'Atlas instalado ✓',
    close: 'Cerrar',
  },
  en: {
    androidTitle: 'Install the Atlas app',
    androidSub: 'Free — no app store.',
    install: 'Install',
    iosTitle: 'Add Atlas to your home screen',
    iosTap: 'Tap',
    iosRest: 'then “Add to Home Screen”.',
    success: 'Atlas installed ✓',
    close: 'Close',
  },
}

export function InstallPrompt() {
  const [visible, setVisible] = useState(false)
  const [mode, setMode] = useState<Mode>('android')
  const deferredRef = useRef<BeforeInstallPromptEvent | null>(null)
  // Engagement + captured-event + installed are refs (read at eval time) plus a
  // tick to re-run the reveal effect when any of them changes.
  const armedRef = useRef(false)
  const hasEventRef = useRef(false)
  const installedRef = useRef(false)
  const [tick, setTick] = useState(0)
  const bump = useCallback(() => setTick(t => t + 1), [])

  // Reveal evaluation — runs whenever engagement / event / install state changes.
  useEffect(() => {
    if (visible || !armedRef.current || installedRef.current) return
    let mobile = false
    try {
      mobile = isMobileWidth(window.innerWidth)
    } catch {
      mobile = false
    }
    const platform = detectPlatform(typeof navigator !== 'undefined' ? navigator.userAgent : '')
    const dismissState = readDismissState()
    const env: InstallEnv = {
      isStandalone: isStandalone(),
      isMobile: mobile,
      isInAppWebview: platform.isInAppWebview,
      isIOS: platform.isIOS,
      hasInstallEvent: hasEventRef.current,
      installed: installedRef.current,
      dismissedAt: dismissState.dismissedAt,
      permanentlyDismissed: dismissState.permanentlyDismissed,
    }
    if (!shouldShowInstallPrompt(env, Date.now())) return
    const plat = env.isIOS ? 'ios' : 'android'
    setMode(plat)
    setVisible(true)
    trackOnce('install_prompt_shown', { platform: plat })
    if (env.isIOS) trackOnce('install_prompt_ios_hint_shown')
  }, [tick, visible])

  // Wire browser events + the engagement trigger once.
  useEffect(() => {
    const onBeforeInstall = (e: Event) => {
      e.preventDefault() // suppress Chrome's mini-infobar; we drive our own UI
      deferredRef.current = e as BeforeInstallPromptEvent
      hasEventRef.current = true
      bump()
    }
    const onInstalled = () => {
      installedRef.current = true
      deferredRef.current = null
      track('app_installed')
      setMode('success')
      setVisible(true)
      window.setTimeout(() => setVisible(false), 4000)
    }
    const arm = () => {
      if (armedRef.current) return
      armedRef.current = true
      bump()
    }
    const onScroll = () => {
      if (window.scrollY > SCROLL_TRIGGER_PX) arm()
    }

    window.addEventListener('beforeinstallprompt', onBeforeInstall)
    window.addEventListener('appinstalled', onInstalled)
    window.addEventListener('scroll', onScroll, { passive: true })
    const timer = window.setTimeout(arm, ENGAGE_MS)

    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstall)
      window.removeEventListener('appinstalled', onInstalled)
      window.removeEventListener('scroll', onScroll)
      window.clearTimeout(timer)
    }
  }, [bump])

  const dismiss = useCallback(() => {
    // iOS ✕ is permanent ('never'); Android ✕ snoozes 30 days (timestamp).
    const permanent = mode === 'ios'
    try {
      localStorage.setItem(INSTALL_PROMPT_KEY, permanent ? 'never' : String(Date.now()))
    } catch {
      /* private mode — best effort */
    }
    track('install_prompt_dismissed', { platform: mode, permanent })
    setVisible(false)
  }, [mode])

  const install = useCallback(async () => {
    const ev = deferredRef.current
    if (!ev) return
    try {
      await ev.prompt()
      const choice = await ev.userChoice
      track('install_prompt_accepted', { outcome: choice.outcome })
    } catch {
      /* user gesture race — ignore */
    }
    deferredRef.current = null
    setVisible(false) // `appinstalled` will confirm with the success toast
  }, [])

  if (!visible) return null

  const t = isSpanish() ? COPY.es : COPY.en

  if (mode === 'success') {
    return (
      <div className="install-toast install-toast--success" role="status">
        <span className="install-toast__icon" aria-hidden>✓</span>
        <span className="install-toast__title">{t.success}</span>
      </div>
    )
  }

  return (
    <div className="install-toast" role="dialog" aria-label={mode === 'ios' ? t.iosTitle : t.androidTitle}>
      <img className="install-toast__app-icon" src="/icon-192.png" alt="" width={36} height={36} />
      <div className="install-toast__body">
        <div className="install-toast__title">{mode === 'ios' ? t.iosTitle : t.androidTitle}</div>
        <div className="install-toast__sub">
          {mode === 'ios' ? (
            <span className="install-toast__ios-hint">
              {t.iosTap} <ShareGlyph /> {t.iosRest}
            </span>
          ) : (
            t.androidSub
          )}
        </div>
      </div>
      {mode === 'android' ? (
        <button className="install-toast__cta" onClick={install}>
          {t.install} <span aria-hidden>↓</span>
        </button>
      ) : (
        <span className="install-toast__ios-arrow" aria-hidden>⤓</span>
      )}
      <button className="install-toast__close" onClick={dismiss} aria-label={t.close}>×</button>
    </div>
  )
}
