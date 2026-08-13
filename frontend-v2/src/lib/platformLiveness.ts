/**
 * What the command bar's pill is ALLOWED to say about the PLATFORM (the C9 /
 * N23 class, one level up from the stream).
 *
 * `streamLiveness.ts` made the stream's own header honest: LIVE requires rows,
 * by construction. But the pill above it said "LIVE DATA" unconditionally — a
 * hardcoded string asserting present-tense multi-lane ingest with no
 * measurement behind it. On mobile the two sat stacked: the pill claiming the
 * platform is live directly above a Live tab honestly reporting "stream did
 * not answer". The pill was borrowing credibility from a pipeline it had never
 * looked at.
 *
 * Same cure, same shape: the claim is a function of evidence the API already
 * serves. `/health` measures `rows_ingested_last_15m` and `ingest_lag_minutes`
 * from `signals_v2.created_at` (operational freshness, not provider
 * timestamps). Three honest states:
 *
 *   1. rows landed in the last 15 min            → LIVE DATA (measured)
 *   2. the pipeline answered but nothing recent  → DATA · Nm BEHIND (dated)
 *   3. health unreachable / measurement failed   → STATUS UNKNOWN (never
 *      assert live blind)
 *
 * `claimsLive` is true in exactly one branch, and that branch requires
 * measured rows — the streamLiveness discipline, applied to the platform.
 *
 * Pure. The fetch lives in App.tsx (one on mount + visibilitychange
 * revalidation gated by `livenessIsStale` — no polling storm); this module is
 * only the classifier, which is what lets the table be a test.
 */

/** Which of the three things happened. Reported by the fetch path, never guessed. */
export type HealthLaneState =
  /** No response yet — first paint. */
  | 'pending'
  /** Fetch threw, timed out, came back non-2xx, or the body was unparseable. */
  | 'unanswered'
  /** A real 200 with a readable body. */
  | 'served'

export interface HealthEvidence {
  /**
   * Minutes since the last inserted signal, or null. The backend measures
   * MAX(created_at) over a 2-hour window, so a MEASURED null means "older than
   * 2 h", not "unknown" — unless `measurementFailed` says otherwise.
   */
  ingestLagMinutes: number | null
  /** Signals inserted in the last 15 minutes. The evidence behind LIVE. */
  rowsIngestedLast15m: number
  /**
   * True when the payload is one of /health's fallback branches (pool busy /
   * error). Those return zeros as PLACEHOLDERS, not measurements — the
   * distinguishing mark in the contract is the `message` field, which the
   * happy path never carries.
   */
  measurementFailed: boolean
}

export type PlatformTone = 'checking' | 'live' | 'behind' | 'unknown'

export interface PlatformLiveness {
  tone: PlatformTone
  /** The single gate on the words LIVE DATA. True in ONE branch, and that branch requires measured rows. */
  claimsLive: boolean
  /** The pill text. */
  pillText: string
  /** Suffix for `.live-pill` / `.live-pill-dot` — the colour must not outrun the words. */
  dotModifier: '' | 'checking' | 'behind' | 'unknown'
  /** The data-tip: what was measured, or why nothing was. */
  tip: string
}

/**
 * How long a health answer stays trustworthy before the next foreground
 * return revalidates it. Short — the pill is a present-tense claim — but
 * revalidation only fires on visibilitychange, so there is no polling.
 */
export const LIVENESS_MAX_AGE_MS = 5 * 60 * 1000

/** Should the cached health answer be refetched? (Same shape as coverageStartIsStale.) */
export function livenessIsStale(
  fetchedAtMs: number | null,
  nowMs: number,
  maxAgeMs: number = LIVENESS_MAX_AGE_MS,
): boolean {
  if (fetchedAtMs == null) return true
  return nowMs - fetchedAtMs >= maxAgeMs
}

/**
 * Read the two ingest fields out of a /health body. Null means the body does
 * not honour the contract — the caller must treat that as `unanswered`, not
 * invent zeros.
 */
export function parseHealthPayload(json: unknown): HealthEvidence | null {
  if (typeof json !== 'object' || json === null) return null
  const body = json as Record<string, unknown>
  const rows = body['rows_ingested_last_15m']
  if (typeof rows !== 'number' || !Number.isFinite(rows)) return null
  const lagRaw = body['ingest_lag_minutes']
  const lag = typeof lagRaw === 'number' && Number.isFinite(lagRaw) ? lagRaw : null
  return {
    ingestLagMinutes: lag,
    rowsIngestedLast15m: rows,
    measurementFailed: typeof body['message'] === 'string',
  }
}

/** "38M" under an hour, "2H" above — pill-sized, never negative. */
export function formatLagBehind(lagMinutes: number): string {
  const mins = Math.max(0, Math.round(lagMinutes))
  if (mins < 60) return `${mins}M`
  return `${Math.floor(mins / 60)}H`
}

export function platformLiveness(lane: HealthLaneState, evidence: HealthEvidence | null): PlatformLiveness {
  // 1. Nothing has come back yet. Not an error — but not a LIVE claim either.
  if (lane === 'pending') {
    return {
      tone: 'checking',
      claimsLive: false,
      pillText: 'DATA · CHECKING',
      dotModifier: 'checking',
      tip: 'Checking ingest freshness against the platform health endpoint…',
    }
  }

  // 2. Health did not answer (or answered gibberish). Whether ingest is live
  //    is unknown, and the pill says so instead of asserting it.
  if (lane === 'unanswered' || evidence === null) {
    return {
      tone: 'unknown',
      claimsLive: false,
      pillText: 'STATUS UNKNOWN',
      dotModifier: 'unknown',
      tip: 'The health endpoint did not answer — whether ingest is live is unknown. This is a check that failed, not a platform that stopped.',
    }
  }

  // 3. Health answered with its fallback branch: the zeros in it are
  //    placeholders, not measurements. "BEHIND" here would fabricate a lag.
  if (evidence.measurementFailed) {
    return {
      tone: 'unknown',
      claimsLive: false,
      pillText: 'STATUS UNKNOWN',
      dotModifier: 'unknown',
      tip: 'The platform answered but could not measure ingest freshness (database busy). Whether data is live is unknown.',
    }
  }

  // 4. Measured rows inside the 15-minute window — the only place the words
  //    LIVE DATA exist, and they carry their evidence in the tip.
  if (evidence.rowsIngestedLast15m > 0) {
    return {
      tone: 'live',
      claimsLive: true,
      pillText: 'LIVE DATA',
      dotModifier: '',
      tip: `Live open signals from media, curated feeds, public attention, humanitarian sources, and NLP enrichment. Measured: ${evidence.rowsIngestedLast15m} signals ingested in the last 15 min.`,
    }
  }

  // 5. A measured zero with a dated lag. Real, and said plainly with the one
  //    number that makes it legible.
  if (evidence.ingestLagMinutes !== null) {
    const ago = formatLagBehind(evidence.ingestLagMinutes)
    return {
      tone: 'behind',
      claimsLive: false,
      pillText: `DATA · ${ago} BEHIND`,
      dotModifier: 'behind',
      tip: `No signals ingested in the last 15 min — the newest landed ${ago.toLowerCase()} ago. Ingest lanes may be between cycles or stalled; the data shown is real but not current.`,
    }
  }

  // 6. A measured null lag: the backend looked over its 2-hour window and
  //    found nothing to date. Older than the window — not unknown.
  return {
    tone: 'behind',
    claimsLive: false,
    pillText: 'DATA · >2H BEHIND',
    dotModifier: 'behind',
    tip: 'No signals ingested in the last 2 hours (the health measurement window). The data shown is real but not current.',
  }
}
