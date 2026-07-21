// L1 country edition — client contract + pure section composer + fetch.
//
// The country door is a full edition: three adaptive/honest sections composed
// from country-scoped threads + a country coverage-gaps band. Section splitting
// reuses the global edition's deterministic classifier (splitEditionThreads).
// Adaptive by construction: a section renders only when it has content; empty
// sections carry an honest reason and are never invented to fill.

import { splitEditionThreads, type EditionThreadLike } from './briefEdition'

export interface CountryGap {
  slug: string
  label: string
  raw_signals: number
  verified: number
  scored: number
}

export interface CountryEditionArticle {
  status?: string
  via?: string
  excerpt?: string | null
  outlet?: string | null
  fetched_at?: string | null
}

export interface CountryEditionEnrichment {
  contract?: string
  yield?: { ok: number; attempted: number; pending: number }
  pending_urls?: string[]
  articles?: Record<string, CountryEditionArticle>
  note?: string
}

export interface CountryEdition {
  contract: 'country-edition-v0'
  country: string
  country_name: string
  generated_at: string
  window_hours: number
  // Thread rows are TopThread-compatible (fetch_threads output). Kept loose
  // here; the page maps them via its existing TopThread renderers.
  threads: Array<Record<string, unknown>>
  coverage_gaps: CountryGap[]
  article_enrichment: CountryEditionEnrichment | null
}

export type CountrySectionKind =
  | 'country_today'
  | 'under_radar'
  | 'culture_sport_life'

export interface CountrySection<T> {
  kind: CountrySectionKind
  present: boolean
  threads: T[]
  gaps: CountryGap[]
  empty_reason: string | null
}

const EMPTY_REASONS: Record<CountrySectionKind, string> = {
  country_today: 'poca actividad en las últimas 24 h',
  under_radar: 'nada bajo el radar hoy',
  culture_sport_life: 'sin cultura, deporte ni vida en 24 h',
}

/**
 * Partition country threads + gaps into the three adaptive sections.
 * - country_today  = the "world" (serious/crisis-relevant) country threads
 * - under_radar    = country coverage-gaps (domestic signal, 0 gate-kept)
 * - culture_sport_life = culture/sport/life country threads
 * Splitting reuses splitEditionThreads (category-first, label fallback).
 */
export function composeCountrySections<T extends EditionThreadLike>(
  threads: readonly T[],
  gaps: readonly CountryGap[],
): [CountrySection<T>, CountrySection<T>, CountrySection<T>] {
  const { world, culture } = splitEditionThreads(threads)
  const gapList = Array.from(gaps)
  return [
    {
      kind: 'country_today',
      present: world.length > 0,
      threads: world,
      gaps: [],
      empty_reason: world.length > 0 ? null : EMPTY_REASONS.country_today,
    },
    {
      kind: 'under_radar',
      present: gapList.length > 0,
      threads: [],
      gaps: gapList,
      empty_reason: gapList.length > 0 ? null : EMPTY_REASONS.under_radar,
    },
    {
      kind: 'culture_sport_life',
      present: culture.length > 0,
      threads: culture,
      gaps: [],
      empty_reason: culture.length > 0 ? null : EMPTY_REASONS.culture_sport_life,
    },
  ]
}

/** Fetch the live country edition. Returns null on any failure (honest degrade). */
export async function fetchCountryEdition(
  cc: string,
  hours = 24,
): Promise<CountryEdition | null> {
  try {
    const resp = await fetch(`/api/v2/country-edition?cc=${cc}&hours=${hours}`)
    if (!resp.ok) return null
    const data = await resp.json()
    if (data?.contract !== 'country-edition-v0') return null
    return data as CountryEdition
  } catch {
    return null
  }
}
