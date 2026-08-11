import { decodeEntities } from './decodeEntities'

export const getNarrativeFetchLimit = (hasCountryFilter: boolean) => hasCountryFilter ? 24 : 20

/**
 * Threads are ambient — the live day. The list stopped being re-windowed by the
 * VIEW selector (2026-07-15); looking back is the map scrubber's job.
 */
export const THREAD_POOL_HOURS = 24

/**
 * The one definition of "the pool of threads on screen right now".
 *
 * It is shared rather than re-typed because the #234 sibling relation
 * (lib/threadRelation) weights an entity by how many threads in THE POOL carry
 * it — so a caller that fetched a different pool would honestly compute a
 * different receipt for the same pair of threads, and two surfaces on the same
 * phone would then disagree about why two stories are neighbours.
 */
export function threadPoolQuery(countryCode?: string | null, hours: number = THREAD_POOL_HOURS): string {
  const params = new URLSearchParams({
    hours: String(hours),
    limit: String(getNarrativeFetchLimit(!!countryCode)),
  })
  if (countryCode) params.set('country_code', countryCode)
  return `/api/v2/threads?${params.toString()}`
}

/** A pool row, reduced to what a second reader of this pool needs. */
export interface PoolThread {
  thread_id: string
  label: string
  top_countries: string[]
  top_entities: string[]
}

/**
 * Read a `/api/v2/threads` body into pool rows, or `null` when the body is not
 * a pool at all.
 *
 * `null` rather than `[]` on a malformed body, for the reason this codebase has
 * already paid for once: an unreadable answer rendered as an empty one is the
 * timeout-as-absence defect, and it makes a broken lane look like a measured
 * zero. The endpoint itself raises on failure (it has no 200-with-error
 * branch), so the only way here is a body that is not what it claims.
 */
export function readThreadPool(json: unknown): PoolThread[] | null {
  const raw = (json as { threads?: unknown } | null | undefined)?.threads
  if (!Array.isArray(raw)) return null
  return (raw as Array<Record<string, unknown>>)
    .filter(t => typeof t?.thread_id === 'string' && t.thread_id.length > 0)
    .map(t => ({
      thread_id: t.thread_id as string,
      // Labels arrive entity-encoded often enough that decoding is part of
      // reading them, not part of rendering them.
      label: decodeEntities(String(t.label || t.thread_id)),
      top_countries: Array.isArray(t.top_countries) ? (t.top_countries as string[]) : [],
      top_entities: Array.isArray(t.top_entities) ? (t.top_entities as string[]) : [],
    }))
}

export interface CountryThreadEmptyState {
  title: string
  body: string
  actionLabel: string
}

export function getNarrativesForDisplay<T extends { top_countries: string[] }>(
  narratives: T[],
  country?: string,
): T[] {
  if (!country) return narratives
  return narratives
}

export function buildCountryThreadEmptyState(countryCode: string, countryName = countryCode): CountryThreadEmptyState {
  const label = countryName || countryCode
  return {
    title: `No living Narrative Threads detected for ${label} in this window`,
    body: `Atlas asked for country-scoped threads. This usually means ${label} has signals, but no coherent thread cleared the current quality gate for the selected time range.`,
    actionLabel: 'Show global threads',
  }
}
