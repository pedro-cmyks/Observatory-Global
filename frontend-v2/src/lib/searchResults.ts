export interface SearchVisibilityResult {
  themes: Array<{ total_signals: number }>
  persons: Array<{ total_signals: number }>
  countries: unknown[]
  concepts?: unknown[]
  region?: unknown | null
  public_attention?: unknown[]
  signal_matches?: unknown[]
}

export function hasVisibleSearchResults<T extends SearchVisibilityResult>(results: T | null): boolean {
  if (!results) return false
  return (
    results.themes.some(t => t.total_signals > 0) ||
    results.persons.some(p => p.total_signals > 0) ||
    results.countries.length > 0 ||
    (results.concepts?.length ?? 0) > 0 ||
    results.region != null ||
    (results.public_attention?.length ?? 0) > 0 ||
    (results.signal_matches?.length ?? 0) > 0
  )
}
