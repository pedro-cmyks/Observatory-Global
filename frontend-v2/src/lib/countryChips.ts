// Country chips on threads reflect the countries appearing in a story's
// COVERAGE ROWS (signals_v2.country_code — a mix of story subject and
// reporting location), NOT verified outlet origin and NOT verified subject
// geography (#238).
//
// Council R2 N1: the old label "Covered from: X" asserted ORIGIN from
// subject-mixed data (an Iowa radio station wore "COVERED FROM: Iran").
// Origin assertions may only derive from source_origin_country — those render
// as per-receipt origin chips via lib/sourceProvenance. This thread-level chip
// row therefore uses origin-neutral language.

export const COVERAGE_CHIP_LABEL = 'In coverage'

export function coverageChipTip(country: string): string {
  return `${country} appears in this story's coverage (as subject or reporting location) — not a verified outlet origin, and not necessarily the story's subject.`
}
