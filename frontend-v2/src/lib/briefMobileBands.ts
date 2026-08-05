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
  /**
   * Pre-formatted seal age with no "sealed " prefix — e.g. "just now",
   * "2 hours ago", "3 days ago". Derive it from lib/staleBanner.ts's own
   * `age` field (its "sealed " prefix stripped), never recompute the elapsed
   * time here: an earlier version did `Math.floor(ms / 3600000)` and printed
   * "sealed 0h ago" for a 20-minute-old seal and "sealed 87h ago" for a
   * 3-day-old one, while the expanded box — reading staleBanner.age directly
   * — said "sealed just now" / "sealed 3 days ago" for the SAME fact. One
   * phrasing, one source: this module formats a sentence, it does not
   * compute a duration.
   */
  sealedAge: string | null
  fullTextOk: number | null
  fullTextTotal: number | null
}

export function freshnessSummary(f: FreshnessFacts): string {
  const parts: string[] = []
  parts.push(f.sealedAge === null ? 'seal time unknown' : `sealed ${f.sealedAge}`)
  if (f.fullTextOk !== null && f.fullTextTotal !== null) {
    parts.push(`full text ${f.fullTextOk}/${f.fullTextTotal}`)
  }
  return parts.join(' · ')
}
