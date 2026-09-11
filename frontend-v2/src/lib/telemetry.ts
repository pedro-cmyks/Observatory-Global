// Anonymous time-to-value telemetry (master-consolidation T5.1 / founder review).
//
// Fire-and-forget: never blocks, never throws, no PII. `session_id` is a random
// client id in localStorage. This is the "instrument before you guess" lever —
// measure whether a session reaches a VALUE MOMENT (thread opened, evidence
// seen, dossier generated) and how long it takes.

import { acquisitionProps, currentAcquisition } from './acquisition'

const SID_KEY = 'atlas.sid.v1'

function sessionId(): string {
  try {
    let s = localStorage.getItem(SID_KEY)
    if (!s) {
      s = Math.random().toString(36).slice(2, 12) + Date.now().toString(36)
      localStorage.setItem(SID_KEY, s)
    }
    return s
  } catch {
    return 'anon'
  }
}

// accounts-v1: pseudonymous identity. When a user signs in, every event
// carries their Supabase user id in props (an opaque uuid — no email/PII).
// This is the funnel/retention apparatus the monetization gate requires.
let telemetryUserId: string | null = null
export function setTelemetryUser(id: string | null): void { telemetryUserId = id }

export function track(event: string, props?: Record<string, unknown>): void {
  try {
    // Campaign attribution (spec §2.2): every event carries where this client
    // first came from and what brought it today — UTM tags we authored plus
    // the referrer host. Empty touches add no keys.
    const acq = acquisitionProps(currentAcquisition())
    const merged: Record<string, unknown> | undefined =
      Object.keys(acq).length > 0 || telemetryUserId
        ? { ...acq, ...props, ...(telemetryUserId ? { user_id: telemetryUserId } : {}) }
        : props
    fetch('/api/v2/telemetry', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ events: [{ event, session_id: sessionId(), props: merged }] }),
      keepalive: true,
    }).catch(() => { /* best-effort */ })
  } catch {
    /* never break the UI */
  }
}

const fired = new Set<string>()

/** Fire at most once per page-session — for "first value" moments where the
 *  conversion, not the count, is what matters. */
export function trackOnce(event: string, props?: Record<string, unknown>): void {
  if (fired.has(event)) return
  fired.add(event)
  track(event, props)
}
