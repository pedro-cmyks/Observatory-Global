/**
 * Which Brief bands start collapsed on a phone, and what their one-line
 * summary says.
 *
 * The mobile audit measured 1707px of chrome before the first headline. The fix
 * is NOT to delete the freshness box or the markets band — both are honesty
 * surfaces (one states how stale the edition is, the other states that it is a
 * live overlay outside the sealed edition). They collapse to a line that still
 * carries the honest fact, and expand on tap.
 */
export type BriefBand = 'freshness' | 'markets'

export function bandStartsCollapsed(band: BriefBand, isMobile: boolean): boolean {
  if (!isMobile) return false
  return band === 'freshness' || band === 'markets'
}

export interface FreshnessFacts {
  sealedHoursAgo: number | null
  fullTextOk: number | null
  fullTextTotal: number | null
}

export function freshnessSummary(f: FreshnessFacts): string {
  const parts: string[] = []
  parts.push(f.sealedHoursAgo === null ? 'seal time unknown' : `sealed ${f.sealedHoursAgo}h ago`)
  if (f.fullTextOk !== null && f.fullTextTotal !== null) {
    parts.push(`full text ${f.fullTextOk}/${f.fullTextTotal}`)
  }
  return parts.join(' · ')
}
