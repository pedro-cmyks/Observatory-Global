export interface SearchVisibilityResult {
  themes: Array<{ total_signals: number }>
  persons: Array<{ total_signals: number }>
  countries: unknown[]
  concepts?: unknown[]
  region?: unknown | null
  live_threads?: unknown[]
  public_attention?: unknown[]
  signal_matches?: unknown[]
}

export function hasVisibleSearchResults<T extends SearchVisibilityResult>(results: T | null): boolean {
  if (!results) return false
  return (
    results.themes.some(t => t.total_signals > 0) ||
    results.persons.some(p => p.total_signals > 0) ||
    results.countries.length > 0 ||
    results.region != null ||
    (results.live_threads?.length ?? 0) > 0 ||
    (results.public_attention?.length ?? 0) > 0 ||
    (results.signal_matches?.length ?? 0) > 0
  )
}

/** Sentinel segment for a request that failed before the backend could answer
 *  (network error, non-OK response) — the whole lookup failed, not one lane. */
export const SEARCH_LOOKUP_FAILED = 'lookup_failed'

export interface DegradableSearchResult {
  degraded?: boolean
  degraded_segments?: string[]
}

/** Failed lanes of a search response. The backend appends a segment ONLY from
 *  the except block around its timed-out query, so `degraded: true` always
 *  means "a lookup FAILED" — never "the lookup ran and found nothing". */
export function degradedSearchSegments(results: DegradableSearchResult | null): string[] {
  if (!results?.degraded) return []
  const segments = results.degraded_segments ?? []
  return segments.length > 0 ? segments : [SEARCH_LOOKUP_FAILED]
}

const SEGMENT_LABELS: Record<string, string> = {
  live_threads: 'live stories',
  public_attention: 'public attention',
  signal_matches: 'media signals',
  themes: 'themes',
  persons: 'people',
  db_matches: 'signal lookups',
  [SEARCH_LOOKUP_FAILED]: 'the search request',
}

export function describeDegradedSegments(segments: string[]): string {
  return segments.map(s => SEGMENT_LABELS[s] ?? s.replace(/_/g, ' ')).join(', ')
}

export type SearchEmptyVariant = 'none' | 'measured_absence' | 'failed_lookup'

/** Which empty state (if any) the dropdown may claim. 'measured_absence'
 *  ("No results for …") is reachable only for a response that ran clean —
 *  a degraded or still-loading lookup must never be rendered as absence. */
export function searchEmptyVariant(
  results: (SearchVisibilityResult & DegradableSearchResult) | null,
  loading: boolean,
): SearchEmptyVariant {
  if (loading || !results) return 'none'
  if (hasVisibleSearchResults(results)) return 'none'
  return degradedSearchSegments(results).length > 0 ? 'failed_lookup' : 'measured_absence'
}
