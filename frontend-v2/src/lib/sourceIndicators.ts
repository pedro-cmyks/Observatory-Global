// Source-indicator legibility (fix round 2026-08-12, cold-user probe pair e).
//
// The panel printed "Source Diversity 99" directly above "Source Quality 30"
// with nothing but the two composites. The reader has no way to tell whether
// the scores contradict each other — and they do not. Measured on prod for
// East Timor: diversity 99 comes from 48 distinct outlets over 53 signals with
// the top outlet at 11%; quality 30 comes from 0 allowlisted / 48 unknown
// outlets. Many voices, none of them on our recognized-publisher list. That is
// one coherent story, invisible while only "99" and "30" are on screen.
//
// The indicators endpoint already returns every input — the frontend just
// dropped them. This module turns those inputs into the inline note and the
// data-tip, and makes the one judgement call the score display gets wrong.
//
// Everything is optional: an older payload must degrade to less text, never to
// a crash or an invented number.

export interface DiversityPayload {
  score?: number | null
  unique_count?: number | null
  total_signals?: number | null
  /** Top outlets as [domain, count] tuples, as the endpoint serves them. */
  top_domains?: Array<[string, number]> | null
  breakdown?: { unique_score?: number | null; entropy_score?: number | null } | null
}

export interface QualityPayload {
  score?: number | null
  allowlisted_count?: number | null
  denylisted_count?: number | null
  unknown_count?: number | null
}

export interface IndicatorNote {
  /** Short line rendered next to the score, or null when we know nothing. */
  inline: string | null
  /** data-tip explaining what the composite is made of. */
  tip: string
}

export interface QualityNote extends IndicatorNote {
  /**
   * True when the low score is driven purely by outlets we do not recognize —
   * a gap in OUR allowlist, not a measured judgement on the country's press.
   */
  unclassified: boolean
  /** Verdict word to print instead of the score band, or null to keep the band. */
  verdict: 'unclassified' | null
}

function count(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : null
}

/**
 * The diversity score is an outlet-count component plus an evenness
 * (entropy) component. Both are computed over the FULL window population —
 * not the ten receipts the panel lists underneath, which is exactly the
 * mismatch that made a cold reader distrust the number ("7 of the 10 stories
 * are from one domain, how is diversity 99?").
 */
export function describeDiversity(payload: DiversityPayload): IndicatorNote {
  const outlets = count(payload.unique_count)
  const total = count(payload.total_signals)
  const top = Array.isArray(payload.top_domains) ? payload.top_domains[0] : undefined

  const tipParts: string[] = [
    'Combines two things: how many distinct outlets carried this country, and how evenly the signals are spread across them (a field where one outlet dominates scores lower than one where many share it).',
  ]
  if (outlets !== null && total !== null) {
    tipParts.push(`Measured over ${outlets.toLocaleString()} outlets across all ${total.toLocaleString()} signals in this window.`)
  }
  if (top && typeof top[1] === 'number' && total !== null && total > 0) {
    tipParts.push(`Busiest outlet: ${top[0]} with ${top[1].toLocaleString()} of them.`)
  }
  tipParts.push('That full-window population is not the same as the sample of receipts listed below, where one outlet can look dominant by chance.')
  const tip = tipParts.join(' ')

  if (outlets === null) return { inline: null, tip }

  const outletWord = outlets === 1 ? 'outlet' : 'outlets'
  const segments = [`${outlets.toLocaleString()} ${outletWord}`]

  // Guard the divide: total_signals of 0 must print no share at all rather
  // than NaN% or Infinity%.
  if (top && typeof top[1] === 'number' && total !== null && total > 0) {
    const pct = Math.round((top[1] / total) * 100)
    segments.push(`top ${top[0]} ${pct}%`)
  }

  return { inline: segments.join(' · '), tip }
}

/**
 * The quality score starts at a floor and rises only for outlets on a known
 * publisher allowlist. A regional press corps we have never catalogued
 * therefore scores low WITHOUT any evidence about its quality — so calling
 * that "Poor" (in danger red) is a verdict we have not earned. When nothing
 * is allowlisted AND nothing is denylisted, the honest word is "unclassified".
 */
export function describeQuality(payload: QualityPayload): QualityNote {
  const allow = count(payload.allowlisted_count)
  const deny = count(payload.denylisted_count)
  const unknown = count(payload.unknown_count)

  const known = allow ?? 0
  const total = (allow ?? 0) + (deny ?? 0) + (unknown ?? 0)
  const anyField = allow !== null || deny !== null || unknown !== null

  // Unclassified only when we truly hold no opinion: nothing recognized as
  // reputable, nothing flagged as bad, and outlets present to judge.
  const unclassified = anyField && known === 0 && (deny ?? 0) === 0 && (unknown ?? 0) > 0

  const base =
    'Starts at a floor and rises only for outlets on a known-publisher allowlist.'

  let tip: string
  if (unclassified) {
    tip =
      `${base} None of the ${(unknown ?? 0).toLocaleString()} outlets covering this country are on that list, so the score stays near the floor. ` +
      'That is a gap in our allowlist, not a claim that this press is low quality — we have no evidence either way, which is why the verdict reads "unclassified".'
  } else if ((deny ?? 0) > 0) {
    tip =
      `${base} ${(deny as number).toLocaleString()} outlet${(deny as number) === 1 ? ' is' : 's are'} on the denylist of known low-credibility publishers, which pulls the score down — that part IS a measured judgement. ` +
      `${known.toLocaleString()} are recognized as reputable; outlets we have never catalogued neither raise nor condemn it.`
  } else {
    tip =
      `${base} ${known.toLocaleString()} of ${total.toLocaleString()} outlets here are recognized. ` +
      'Outlets missing from the list are unknown to us, not judged — a low score can simply mean we have not catalogued this country\'s press.'
  }

  const inline = anyField && total > 0
    ? `${known.toLocaleString()} of ${total.toLocaleString()} outlet${total === 1 ? '' : 's'} recognized`
    : null

  return { inline, tip, unclassified, verdict: unclassified ? 'unclassified' : null }
}
