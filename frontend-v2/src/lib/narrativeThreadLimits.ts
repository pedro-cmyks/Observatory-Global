export const getNarrativeFetchLimit = (hasCountryFilter: boolean) => hasCountryFilter ? 24 : 20

export function getNarrativesForDisplay<T extends { top_countries: string[] }>(
  narratives: T[],
  country?: string,
): T[] {
  if (!country) return narratives
  return narratives.filter(narrative => narrative.top_countries.includes(country))
}
