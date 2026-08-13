/**
 * What the stream's header is ALLOWED to say about itself (C9 — the N23 class,
 * in the stream).
 *
 * The blind panel (2026-08-13) ended BOTH mobile sessions in the same place:
 * the Live tab printing "● LIVE" and "0 sig/min · No signals found" at the same
 * time. Doomscroller: *"Looks dead."* — and he extended it, explicitly, to the
 * credibility of the data itself. The reader is right to. Three different
 * things were wearing one word:
 *
 *   1. the lane never answered (network throw, 503 db_busy, 429)   → UNKNOWN
 *   2. the lane has not answered YET (first paint)                 → UNKNOWN
 *   3. the lane answered, and the answer was zero                  → MEASURED
 *
 * "LIVE" over an empty list collapses all three into the most confident of the
 * four possible readings, which is the same sin `briefLanes.ts` was built to
 * kill on the front page: *an absence of measurement rendered as a measurement
 * of absence*, in the honesty voice. Here it is worse in one respect — the word
 * LIVE is a claim about the PRESENT TENSE of the pipeline, so a dead lane
 * borrows the credibility of a working one.
 *
 * So the lane state is carried, never inferred from emptiness. `SignalStream`
 * already knew it (`feedError` is set on `!res.ok` and on a throw, and cleared
 * only by a real 200) — this module makes the knowledge reach the chrome, and
 * makes the forbidden pairing UNREPRESENTABLE rather than merely reviewed:
 * `claimsLive` is true in exactly one branch, and that branch requires rows.
 *
 * Pure. Every state is a function of (lane, counts, clock) with no fetch of its
 * own, which is what lets the table be a test rather than a screenshot.
 */

/** Which of the three things happened. Reported by the fetch path, never guessed. */
export type StreamLaneState =
  /** No response yet this scope — first paint, or a scope change mid-flight. */
  | 'pending'
  /** Fetch threw, timed out, or came back non-2xx. Every count is unknown. */
  | 'unanswered'
  /** A real 200. A zero here is a MEASURED zero. */
  | 'served'

export interface StreamLivenessInput {
  lane: StreamLaneState
  /** Rows the reader can actually see, after tab + relevance filtering. */
  visibleCount: number
  /** Rows the lane put in the pool, before those client-side view filters. */
  fetchedCount: number
  /** Newest signal timestamp observed this session (ms epoch), or null if none. */
  lastSignalAt: number | null
  now: number
  /** Pointer resting on the list — the deliberate, reader-owned pause. */
  hovered: boolean
  /**
   * Measured throughput. The API serves this loosely typed (it emits the
   * literal `'--'` when a rate is not computable from the window), so anything
   * that is not a finite number is treated as "no rate" rather than printed.
   */
  velocityPerMinute: number | string | null | undefined
  /** True when a server-side `topic=` scope (Eclipse / Story Lens) is applied. */
  scoped?: boolean
}

export type StreamTone = 'live' | 'quiet' | 'filtered' | 'paused' | 'unanswered' | 'pending'

export interface StreamLiveness {
  tone: StreamTone
  /**
   * The single gate on the word LIVE. True in ONE branch of `streamLiveness`,
   * and that branch cannot be reached with `visibleCount === 0`.
   */
  claimsLive: boolean
  /** The header sentence. */
  statusText: string
  /** Suffix for `.stream-live-dot` — the colour must not outrun the words. */
  dotModifier: '' | 'paused' | 'feed-error' | 'quiet' | 'pending'
  /** Whether a `N sig/min` rate is meaningful here. */
  showVelocity: boolean
  /** The empty-list sentence; null while rows are rendering. */
  emptyCopy: string | null
  /** The second line under it — which of the three things this is. */
  emptyNote: string | null
}

/**
 * Same rounding the stream rows use (`formatRelativeAge` in SignalStream), so
 * "last signal 14m ago" in the header and "14m" on a row mean the same thing.
 */
export function formatSignalAge(elapsedMs: number): string {
  const sec = Math.max(0, Math.floor(elapsedMs / 1000))
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m`
  return `${Math.floor(min / 60)}h`
}

/**
 * Newest `timestamp` in a RAW `/api/v2/signals` payload, or null if the payload
 * carries none this can date.
 *
 * Deliberately reads the raw rows, BEFORE the junk-headline and relevance
 * filters: when a window returns only unrenderable rows the reader sees an
 * empty list, but the lane still measured when the last one landed — and that
 * number is the difference between "quiet, last signal 14m ago" and a bare
 * emptiness that reads as abandonment. Unparseable rows are skipped rather than
 * coerced to 0, which would date the quiet to 1970.
 */
export function newestTimestamp(rows: unknown): number | null {
  if (!Array.isArray(rows)) return null
  let newest: number | null = null
  for (const row of rows) {
    const raw = (row as { timestamp?: unknown })?.timestamp
    if (typeof raw !== 'string' && typeof raw !== 'number') continue
    const ms = new Date(raw).getTime()
    if (!Number.isFinite(ms)) continue
    if (newest === null || ms > newest) newest = ms
  }
  return newest
}

/** The window the stream fetches. Kept here so the copy and the query agree. */
const WINDOW_LABEL = 'the last 24 h'

/** A rate exists only if it is a finite number — `'--'`, '', null all fail. */
function hasRate(v: number | string | null | undefined): boolean {
  if (v === null || v === undefined || v === '') return false
  return Number.isFinite(typeof v === 'number' ? v : Number(v))
}

export function streamLiveness(input: StreamLivenessInput): StreamLiveness {
  const { lane, visibleCount, fetchedCount, lastSignalAt, now, hovered, velocityPerMinute, scoped } = input
  const hasRows = visibleCount > 0

  // 1. The lane failed. Nothing below this line is knowable, including whether
  //    the world is quiet — so the chrome says so and the retry is named.
  //    Outranks the hover pause: a paused dead feed is still a dead feed.
  if (lane === 'unanswered') {
    return {
      tone: 'unanswered',
      claimsLive: false,
      statusText: 'stream did not answer · reconnecting',
      dotModifier: 'feed-error',
      showVelocity: false,
      emptyCopy: hasRows ? null : 'The signal stream did not answer — reconnecting…',
      emptyNote: hasRows
        ? null
        : `Whether anything landed in ${WINDOW_LABEL} is unknown — this is a lane that failed, not a quiet world.`,
    }
  }

  // 2. Nothing has come back yet. Also unknown, but it is not an error, and
  //    saying "reconnecting" on first paint would be its own small lie.
  if (lane === 'pending') {
    return {
      tone: 'pending',
      claimsLive: false,
      statusText: 'stream connecting…',
      dotModifier: 'pending',
      showVelocity: false,
      emptyCopy: hasRows ? null : 'Connecting to the signal stream…',
      emptyNote: hasRows ? null : 'The lane has not answered yet, so this window is not measured.',
    }
  }

  // 3. Served, with rows. The only place the word LIVE exists — and the reader's
  //    own hover pause is honoured first, because they caused it.
  if (hasRows) {
    if (hovered) {
      return {
        tone: 'paused',
        claimsLive: false,
        statusText: 'paused · last 15 min',
        dotModifier: 'paused',
        showVelocity: false,
        emptyCopy: null,
        emptyNote: null,
      }
    }
    return {
      tone: 'live',
      claimsLive: true,
      statusText: '● LIVE',
      dotModifier: '',
      // A measured 0 sig/min WITH rows on screen is honest: slow, not dead.
      showVelocity: hasRate(velocityPerMinute),
      emptyCopy: null,
      emptyNote: null,
    }
  }

  // 4. Served, no rows on screen. A rate chip here is the exact C9 pairing
  //    ("0 sig/min" next to an empty list), so it never renders.

  // 4a. The lane answered with signals; this VIEW filtered them all out. Saying
  //     "no signals" would be false about the world and unhelpful about the tab.
  if (fetchedCount > 0) {
    return {
      tone: 'filtered',
      claimsLive: false,
      statusText: 'quiet in this view',
      dotModifier: 'quiet',
      showVelocity: false,
      emptyCopy: `The stream answered with ${fetchedCount} signal${fetchedCount === 1 ? '' : 's'} in ${WINDOW_LABEL} — none of them are in this view.`,
      emptyNote: 'Switch to ALL to see the whole stream, including sport and entertainment lanes.',
    }
  }

  // 4b. A measured zero. This is a real editorial fact and it gets said plainly,
  //     with the one number that makes it legible: when the last one landed.
  if (lastSignalAt !== null) {
    const ago = formatSignalAge(now - lastSignalAt)
    return {
      tone: 'quiet',
      claimsLive: false,
      statusText: `quiet · last signal ${ago} ago`,
      dotModifier: 'quiet',
      showVelocity: false,
      emptyCopy: `Quiet right now — the last signal landed ${ago} ago.`,
      emptyNote: `The stream answered for ${WINDOW_LABEL}; nothing new has arrived since.`,
    }
  }

  // 4c. A measured zero with nothing to date it from. Refuse to invent one:
  //     saying "last signal 0m ago" would fabricate the very number that makes
  //     the sentence trustworthy.
  return {
    tone: 'quiet',
    claimsLive: false,
    statusText: `quiet · no signals in ${WINDOW_LABEL}`,
    dotModifier: 'quiet',
    showVelocity: false,
    emptyCopy: scoped
      ? `Quiet right now — the stream answered for this scope with no signals in ${WINDOW_LABEL}.`
      : `Quiet right now — the stream answered with no signals in ${WINDOW_LABEL}.`,
    emptyNote: 'The lane answered, so this is a measured zero — not a stream that failed.',
  }
}
