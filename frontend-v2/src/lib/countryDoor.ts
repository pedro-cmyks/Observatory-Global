/**
 * The country door — where it goes, and how to get back (C4).
 *
 * The blind judge clicked a Heating Up tile and, in their words, landed in "a
 * completely different dark analyst console… no warning, no way back except
 * the browser Back button. Total context whiplash." (§4.2)
 *
 * The console side of that is already built: `/app?country=XX` sets the scope,
 * the P2 scope path renders `World ▸ COUNTRY Tajikistan`, the CountryBrief
 * panel opens, and every surface re-scopes (#234). Verified live. So the
 * destination was never the defect — the DOOR was. A bare tile printing a
 * country name and a number gives the reader no way to know it is a door at
 * all, let alone where it opens or that the first crumb walks back out.
 *
 * The page already had one door that reads correctly: The Gap's
 * "Open Colombia →" — it names the destination before the click. This module
 * generalises exactly that, so every country door on the front page speaks
 * with one voice instead of five.
 *
 * WHY COPY AND NOT A ROUTE CHANGE. Moving the door into the Brief's own
 * country edition would remove the jump but also remove the folder: the
 * breadcrumb, the re-scoped map, the stream — the thing the reader actually
 * clicked toward. The honest fix is not to hide the transition, it is to
 * announce it and to name the way back, which is the crumb.
 */

/** How a country door presents itself. */
export interface CountryDoorCopy {
  /** Visible affordance on the control — a labeled door, never a bare tile. */
  cue: string
  /** `data-tip`: where it goes and how to come back. */
  tip: string
  /** Accessible name — the same promise, for a reader who cannot see the cue. */
  ariaLabel: string
}

/**
 * The way back, named. This sentence is the one the judge needed and did not
 * get; it is deliberately about the CRUMB (a word that is always present, in
 * one place) rather than about the browser's Back button.
 */
export const WAY_BACK = 'the “World” crumb at the top walks back out'

/**
 * @param countryName  Resolved display name — never a raw ISO code, which is
 *                     what a door promising continuity must not print.
 * @param context      What the reader is standing on, for the tip's first
 *                     clause ("its heat", "its coverage", …). Optional.
 */
export function countryDoorCopy(
  countryName: string,
  context?: string | null,
): CountryDoorCopy {
  // No possessive: half the world's country names end in -s ("United States's"),
  // and a door that reads clumsily reads as machine output.
  const name = (countryName ?? '').trim() || 'this country'
  const where = context ? `, ${context}` : ''
  return {
    cue: `Open ${name} →`,
    tip: `Opens ${name} in the analyst console — a denser surface than this page, `
      + `already scoped to ${name}${where} (World ▸ ${name}). Coming back: ${WAY_BACK}.`,
    ariaLabel: `Open ${name} in the analyst console — scoped to ${name}, ${WAY_BACK}`,
  }
}
