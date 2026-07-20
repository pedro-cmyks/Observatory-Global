// Source provenance chips that ENTAIL outlet origin (council R2 N1).
//
// The lie this module kills: tier + country chips rendered side by side read as
// one assertion — "LOCAL IR" — while the country was actually the story's
// SUBJECT country (signals_v2.country_code) and the tier came from a name
// classifier. A Mexican outlet (globalmedia.mx) covering Iran wore "LOCAL IR";
// an Iowa radio station wore "COVERED FROM: Iran".
//
// The contract, by construction:
//   * An origin assertion ("covered from X" / a flagged country next to the
//     outlet) derives ONLY from `signals_v2.source_origin_country` — the
//     outlet's own home country recorded at ingestion. The subject country is
//     not an input to this module, so it can never leak into an origin chip.
//   * When origin is unknown: NO origin chip (absence over guess).
//   * Tier chips: wire/state/major are name-classified and origin-independent —
//     they render regardless. LOCAL specifically asserts locality, which is
//     meaningless without a known origin — a local-classified outlet with no
//     recorded origin renders as UNKNOWN with an honest why.

import { classifyOutlet, coarseTierLabel, TIER_TIP, type CoarseTier } from './sourceTiers'
import { resolveCountryName } from './countryNames'

/** Placeholder codes that mean "we do not actually know" — never an origin. */
const NON_COUNTRY_CODES = new Set(['XX', 'ZZ', 'UN'])

/** True when `code` is a plausible ISO2 origin country we can assert. */
export function isKnownOriginCountry(code: string | null | undefined): boolean {
  const cc = (code ?? '').trim().toUpperCase()
  return /^[A-Z]{2}$/.test(cc) && !NON_COUNTRY_CODES.has(cc)
}

export interface OriginChip {
  /** Normalized ISO2 of the OUTLET's origin (source_origin_country). */
  countryCode: string
  /** Human country name for display. */
  countryName: string
  tip: string
}

/** The only legal producer of a "covered from" / origin assertion.
 *  Returns null when the origin is unknown — the chip simply does not render. */
export function resolveOriginChip(originCountry: string | null | undefined): OriginChip | null {
  if (!isKnownOriginCountry(originCountry)) return null
  const cc = (originCountry as string).trim().toUpperCase()
  const name = resolveCountryName(cc, cc)
  return {
    countryCode: cc,
    countryName: name,
    tip: `Outlet based in ${name} — the outlet's recorded origin, not the story's subject.`,
  }
}

export interface ProvenanceTierChip {
  tier: CoarseTier
  label: string
  tip: string
}

/** Tier chip with the origin-entailment rule applied: LOCAL only renders when
 *  the outlet's origin country is actually known; wire/state/major/unknown are
 *  origin-independent name classifications. */
export function resolveTierChip(
  source: string | null | undefined,
  originCountry: string | null | undefined,
): ProvenanceTierChip {
  const { tier } = classifyOutlet(source)
  if (tier !== 'local') {
    return { tier, label: coarseTierLabel(tier), tip: TIER_TIP[tier] }
  }
  const origin = resolveOriginChip(originCountry)
  if (!origin) {
    return {
      tier: 'unknown',
      label: coarseTierLabel('unknown'),
      tip: 'Registered outlet, but its origin country is not on record — locality cannot be asserted, so it is shown as UNKNOWN (absence over guess).',
    }
  }
  return {
    tier: 'local',
    label: coarseTierLabel('local'),
    tip: `Local/regional outlet based in ${origin.countryName} (recorded outlet origin).`,
  }
}
