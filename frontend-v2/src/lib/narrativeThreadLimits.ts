export const getNarrativeFetchLimit = (hasCountryFilter: boolean) => hasCountryFilter ? 24 : 20

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
