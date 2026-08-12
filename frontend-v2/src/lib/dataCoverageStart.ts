// The "FROM <date>" archive chip.
//
// Cold-user probe 2026-08-12 §4: the chip read `FROM 9 AUG 2026` on desktop and
// `FROM 5 AUG 2026` on mobile at the same moment. There is only ONE renderer --
// the divergence was entirely data-side, from two compounding causes:
//
//  1. STALENESS. The fetch had `[]` deps, and <App/> never unmounts (the
//     Brief↔console keep-alive shell hides panes with display:none), so the
//     value froze at whatever it was when the browser session first loaded.
//     The PWA (`display: standalone`) keeps a phone session alive for days
//     while desktop reloads constantly -- so the phone showed a days-old floor.
//     `oldest_signal` is a retention floor that advances daily, which is
//     exactly the shape of the observed 4-day gap. Fixed by revalidating when
//     the document becomes visible again.
//  2. TIMEZONE. `signals_v2.timestamp` can serialize without an offset, and ES
//     parses an offset-less date-time as LOCAL time. Two devices in different
//     zones then render the same payload ±1 day apart. Fixed by reading it as
//     UTC and formatting in UTC.

/** How long a fetched coverage floor stays trustworthy before revalidation. */
export const COVERAGE_START_MAX_AGE_MS = 30 * 60 * 1000

/**
 * Parse a server timestamp, treating an offset-less value as UTC.
 *
 * Postgres `TIMESTAMP WITHOUT TIME ZONE` reaches us as e.g.
 * "2026-08-05T10:10:14" with no zone. Left to the platform, that is read as
 * local time and the same payload renders on different calendar days in
 * different places -- a divergence with no measurement behind it.
 */
export function parseSignalTimestamp(raw: unknown): Date | null {
  if (typeof raw !== 'string' || !raw.trim()) return null
  const trimmed = raw.trim()
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(trimmed)
  const normalized = hasZone ? trimmed : `${trimmed.replace(' ', 'T')}Z`
  const dt = new Date(normalized)
  return Number.isNaN(dt.getTime()) ? null : dt
}

/**
 * Format the coverage floor for the chip, in UTC.
 *
 * UTC, not the device zone: the number this labels is a UTC retention floor, so
 * rendering it in local time would reintroduce the ±1-day device split.
 */
export function formatCoverageStart(date: Date | null): string | null {
  if (!date || Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

/** One-shot: raw server value -> printable chip text (or null). */
export function coverageStartLabel(raw: unknown): string | null {
  return formatCoverageStart(parseSignalTimestamp(raw))
}

/**
 * Should a cached coverage floor be refetched?
 *
 * A floor that advances daily must not be allowed to persist across a
 * multi-day PWA session.
 */
export function coverageStartIsStale(
  fetchedAtMs: number | null,
  nowMs: number,
  maxAgeMs: number = COVERAGE_START_MAX_AGE_MS,
): boolean {
  if (fetchedAtMs == null) return true
  return nowMs - fetchedAtMs >= maxAgeMs
}
