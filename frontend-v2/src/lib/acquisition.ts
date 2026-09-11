// Acquisition attribution — WHERE a session came from (campaign spec §2.2).
//
// The LinkedIn ritual only becomes a measured loop when the sessions it sends
// are distinguishable from everyone else's. Two halves, both honest by
// construction:
//   * The campaign LINK carries standard UTM tags (buildCampaignDeepLink in
//     storyShare.ts) — the reader's URL says "linkedin / sow-2026-W37".
//   * On arrival the app records FIRST TOUCH once per client (localStorage,
//     same lifetime as the telemetry session id) and the CURRENT visit's
//     touch, and every telemetry event carries both. Absent tags = absent
//     fields; a bare referrer host is recorded as-is (no guessing a channel
//     from a host we do not know).
//
// Pure parsing + a tiny storage adapter. No PII: UTMs are campaign labels we
// authored; the referrer is reduced to its host.

export interface Touch {
  source?: string
  medium?: string
  campaign?: string
  content?: string
  /** The app's own `entry=` param (brief/eclipse/landing/linkedin…). */
  entry?: string
  /** document.referrer reduced to its host — the only fragment kept. */
  ref?: string
}

export interface Acquisition {
  /** First touch ever recorded for this client — attribution of record. */
  first: Touch
  /** This visit's touch — what brought the reader back today. */
  current: Touch
  /** True when this visit's touch became the first touch (a new client). */
  isNew: boolean
}

const ACQ_KEY = 'atlas.acq.v1'
const MAX_LEN = 80

function clip(v: string | null | undefined): string | undefined {
  const t = (v ?? '').trim()
  return t ? t.slice(0, MAX_LEN) : undefined
}

function refHost(referrer: string | null | undefined): string | undefined {
  if (!referrer) return undefined
  try {
    return new URL(referrer).host || undefined
  } catch {
    return undefined
  }
}

/** Parse one visit's touch from the location search + referrer. Own-origin
 *  referrers (in-app navigation) are dropped so a Brief → console hop never
 *  looks like an external arrival. */
export function parseTouch(search: string, referrer?: string | null, ownHost?: string | null): Touch {
  const p = new URLSearchParams(search)
  const t: Touch = {}
  const source = clip(p.get('utm_source'))
  const medium = clip(p.get('utm_medium'))
  const campaign = clip(p.get('utm_campaign'))
  const content = clip(p.get('utm_content'))
  const entry = clip(p.get('entry'))
  if (source) t.source = source
  if (medium) t.medium = medium
  if (campaign) t.campaign = campaign
  if (content) t.content = content
  if (entry) t.entry = entry
  const host = refHost(referrer)
  if (host && host !== (ownHost ?? '')) t.ref = host
  return t
}

export function isEmptyTouch(t: Touch): boolean {
  return Object.keys(t).length === 0
}

interface Stored {
  first: Touch
  /** ISO timestamp of the first touch — lets a report age cohorts. */
  first_at: string
}

/** Record this visit's touch; return the client's acquisition. Storage
 *  failures (private mode, blocked storage) degrade to "current only". */
export function captureAcquisition(
  search: string,
  referrer?: string | null,
  ownHost?: string | null,
  now: () => string = () => new Date().toISOString(),
): Acquisition {
  const current = parseTouch(search, referrer, ownHost)
  let stored: Stored | null = null
  try {
    const raw = localStorage.getItem(ACQ_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<Stored>
      if (parsed && typeof parsed === 'object' && parsed.first && typeof parsed.first === 'object') {
        stored = { first: parsed.first as Touch, first_at: String(parsed.first_at ?? '') }
      }
    }
  } catch { /* storage unreadable — treat as new */ }

  if (stored) {
    return { first: stored.first, current, isNew: false }
  }
  // First touch of record: even an untagged direct visit is recorded (as an
  // empty touch) so a later tagged visit cannot rewrite history.
  const fresh: Stored = { first: current, first_at: now() }
  try { localStorage.setItem(ACQ_KEY, JSON.stringify(fresh)) } catch { /* best-effort */ }
  return { first: current, current, isNew: true }
}

/** Flatten for telemetry props — only non-empty touches produce keys. */
export function acquisitionProps(acq: Acquisition | null | undefined): Record<string, unknown> {
  if (!acq) return {}
  const out: Record<string, unknown> = {}
  if (!isEmptyTouch(acq.first)) out.acq_first = acq.first
  if (!isEmptyTouch(acq.current)) out.acq = acq.current
  return out
}

let memo: Acquisition | null = null

/** The module-level acquisition for this page load — computed once from the
 *  live window, memoized; `null` outside a browser. */
export function currentAcquisition(): Acquisition | null {
  if (memo) return memo
  if (typeof window === 'undefined') return null
  try {
    memo = captureAcquisition(window.location.search, document.referrer, window.location.host)
  } catch {
    memo = null
  }
  return memo
}

export function __resetAcquisitionMemo(): void { memo = null }
