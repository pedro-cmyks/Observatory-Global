/**
 * The base every coverage/voice SHAPE claim is actually measured over.
 *
 * X1, 2026-08-13 — the systemic class from the veracity scorecard
 * (`docs/research/gold/2026-08-13-veracidad-scorecard.md`: claim 3 REFUTADO,
 * claims 8 and 9 DIVERGEN).
 *
 * Atlas told a blind panel that Colombia had "0% own voices" on its own 7.4
 * earthquake while El Tiempo, Noticias Caracol and El Colombiano were leading
 * with it, and that the US press had not picked up the Hormuz tanker arc while
 * CNN ran live coverage. Neither number was wrong about what it measured. Both
 * were wrong about what the screen said they measured: **the shape of Atlas's
 * ingest, rendered as the shape of the world.**
 *
 * This is the July silent-risk finding arriving in production UI — 5/5
 * "uncovered" candidates were covered by outlets Atlas does not ingest. Press
 * silence is not verifiable from this corpus, so absence in Atlas is a fact
 * about Atlas's feed set and never about the world's press.
 *
 * Every surface making a claim of this class imports its wording from here, and
 * the payloads that serve one carry `basis` (backend mirror:
 * `app/services/ingest_basis.py`, test-pinned on both sides). Copy and data are
 * then the same string by construction and cannot drift.
 */

/**
 * ~220 hand-verified RSS feeds across 126 countries and 31 languages, plus the
 * GDELT firehose. Deliberately approximate — an exact count goes stale on the
 * next feed wave, and a stale precise number is worse than an honest round one.
 */
export const INGEST_POPULATION = '~220 curated feeds plus the GDELT firehose'

/**
 * The leading clause, written to sit in FRONT of a measured sentence so the
 * qualification arrives before the claim rather than as a footnote after it.
 */
export const IN_INGEST = 'In what Atlas ingests'

/** The short in-copy qualifier, for labels too tight for a full clause. */
export const OF_WHAT_ATLAS_INGESTS = 'of what Atlas ingests'

/** The fuller version — what every tooltip on a shape claim must carry. */
export const INGEST_NOTE =
  'Atlas ingests ~220 curated feeds across 126 countries plus the GDELT firehose. '
  + 'A zero here means none of THOSE outlets carried it — not that nobody did.'

/** The closing clause for a ZERO: the misreading, refused in the copy itself. */
export function absenceCaveat(countryName: string): string {
  return `That is a gap in Atlas's own feed set — ${INGEST_POPULATION} — `
    + `not proof that ${countryName}'s press stayed silent.`
}

/** The closing clause for a non-zero SHARE — a share, not a silence claim. */
export function shareCaveat(): string {
  return `Those shares are of Atlas's own feed set — ${INGEST_POPULATION} — `
    + 'not of everything published.'
}

/**
 * Append the base to an existing tooltip.
 *
 * Existing tips explain the METHOD (ownership vs language, which denominator);
 * none of them named the POPULATION, which is the half that misled the panel.
 * This keeps the method text and adds the base, so no tooltip loses meaning.
 */
export function withBasisTip(tip?: string | null): string {
  const base = (tip ?? '').trim()
  return base ? `${base} ${INGEST_NOTE}` : INGEST_NOTE
}
