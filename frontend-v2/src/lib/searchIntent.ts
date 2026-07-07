// One query → one obvious primary action (2026-07-06, Pedro: the search
// dropdown had too many competing CTAs). Pure classifier so the SearchBar can
// LEAD with a single action and demote the rest — no silent filtering, the
// power tools just move behind a "more" affordance.

export type QueryIntent = 'empty' | 'country' | 'topic' | 'compound'

export interface QueryClassification {
  /** The dominant intent that decides the primary CTA. */
  intent: QueryIntent
  /** Query is research-shaped → the Workbench investigation is worth surfacing
   *  inline instead of hiding it behind "more". */
  isInvestigative: boolean
}

export interface QueryClassifyInput {
  /** Raw text the user typed. */
  raw: string
  /** Resolved country code, or null when the query names no country. */
  countryCode: string | null
  /** True when stripping the country name left no topic behind
   *  (e.g. "Venezuela" → country only; "conflicto Venezuela" → compound). */
  bareCountry: boolean
}

/** Heuristic: a query is "clearly investigative" when it reads like a research
 *  question — several words or a long phrase — not a bare noun. */
export function isInvestigativeQuery(raw: string): boolean {
  const trimmed = raw.trim()
  const words = trimmed.split(/\s+/).filter(Boolean)
  return words.length >= 4 || trimmed.length >= 28
}

export function classifyQuery(input: QueryClassifyInput): QueryClassification {
  const trimmed = input.raw.trim()
  const isInvestigative = isInvestigativeQuery(trimmed)

  if (trimmed.length < 2) {
    return { intent: 'empty', isInvestigative: false }
  }
  if (input.countryCode) {
    return { intent: input.bareCountry ? 'country' : 'compound', isInvestigative }
  }
  return { intent: 'topic', isInvestigative }
}
