// Anonymous time-to-value telemetry (master-consolidation T5.1 / founder review).
//
// Fire-and-forget: never blocks, never throws, no PII. `session_id` is a random
// client id in localStorage. This is the "instrument before you guess" lever —
// measure whether a session reaches a VALUE MOMENT (thread opened, evidence
// seen, dossier generated) and how long it takes.

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

export function track(event: string, props?: Record<string, unknown>): void {
  try {
    fetch('/api/v2/telemetry', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ events: [{ event, session_id: sessionId(), props }] }),
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
