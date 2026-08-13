/**
 * The lead's VOICES, woven into prose (T3.3, spec §3b.1).
 *
 * The absorbed voice-bar design (`2026-08-12-brief-voice-bar-design.md`) lives
 * here as TEXT rather than as a chart: "48 outlets in 9 languages are carrying
 * this; Syria's own press: 2". That is the Brief's whole thesis in one line —
 * it is the diary of the COVERAGE, so the standfirst says who is telling the
 * story and who is not, not just what happened.
 *
 * THREE RULES, ALL STRUCTURAL:
 *
 * 1. **No clause is ever fabricated.** Every clause is emitted only when its
 *    fields are present; a missing field removes its clause, it never becomes a
 *    zero, a guess, or an em-dash. A payload with nothing countable returns
 *    `null` and the standfirst simply does not render.
 * 2. **The two lineages are named, never blended.** The outlet total is the
 *    story's own measured `source_count`; languages / origins / state flags are
 *    counted from the RECEIPTS the payload carries, which are a slice. So the
 *    receipt-derived counts are printed as floors ("at least N languages") and
 *    `basis` states where each number came from. Mixing a measured total with a
 *    sampled count silently is exactly the class of error the source-count
 *    honesty pass (lib/briefSourceCount.ts) was written to stop.
 * 3. **Own-press is OWNERSHIP, not language.** The 2026-06-22 WAVE-4 correction
 *    stands: BBC Persian covering Iran is British eyes in Persian. The clause
 *    counts `source_origin_country` against the story's SUBJECT countries, and
 *    its denominator is only the receipts whose origin is actually known —
 *    unattributed receipts are neither domestic nor foreign, so they are
 *    excluded from both sides and the sentence says so.
 *
 * The disputed clause is carried, never authored: V2's tension guard attributes
 * the divergence backend-side (both quotes, both outlets, "possible — verify
 * quotes"). This module only re-states it with its outlets attached; the full
 * quotes keep rendering in the coverage-check block below the lead.
 */

import { INGEST_POPULATION } from './ingestBasis'

export interface VoiceReceipt {
  source?: string | null
  /** BCP-47-ish 2-letter code. `xx` is GDELT's UNKNOWN, never a language. */
  source_lang?: string | null
  /** OUTLET home country — the only legal basis for an own-press claim (N1). */
  source_origin_country?: string | null
  /** Authoritative ingest flag; only `true` counts (null = unknown, not false). */
  is_state_media?: boolean | null
}

/** The cross-read tension as the package serves it (already attributed). */
export interface VoiceTension {
  note?: string | null
  a?: { outlet?: string | null } | null
  b?: { outlet?: string | null } | null
}

export interface VoicesInput {
  /** The story's MEASURED outlet count (`source_count`), when it is measured. */
  outlets?: number | null
  /** The receipts the payload carries with this story. */
  receipts?: readonly VoiceReceipt[] | null
  /** ISO codes the story is ABOUT (subject geography, never coverage volume). */
  subjectCountries?: readonly string[] | null
  /** Display names, positionally aligned with `subjectCountries`. */
  subjectCountryNames?: readonly string[] | null
  /** A cross-read tension finding, if the package carries one. */
  tension?: VoiceTension | null
}

export type VoiceClauseKind = 'coverage' | 'ownVoice' | 'stateMedia' | 'disputed'

export interface VoiceClause {
  kind: VoiceClauseKind
  text: string
}

export interface VoicesProse {
  clauses: VoiceClause[]
  /** The clauses as one readable sentence. */
  sentence: string
  /** Where the numbers come from — an honesty rail, always rendered. */
  basis: string
}

/** GDELT's placeholder for "language not identified". */
const UNKNOWN_LANG = 'xx'

function clean(value?: string | null): string {
  return (value ?? '').trim()
}

function distinctLanguages(receipts: readonly VoiceReceipt[]): number {
  const langs = new Set<string>()
  for (const receipt of receipts) {
    const lang = clean(receipt.source_lang).toLowerCase()
    if (!lang || lang === UNKNOWN_LANG) continue
    langs.add(lang)
  }
  return langs.size
}

/** "Iran and United States" / "Iran, Syria and Lebanon". */
function joinNames(names: string[]): string {
  if (names.length <= 1) return names[0] ?? ''
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
}

/** "Syria's" but "United States'" — a name already ending in s takes the bare
 *  apostrophe (found in the browser on the live US-Iran lead). */
function possessive(name: string): string {
  return /s$/i.test(name) ? `${name}'` : `${name}'s`
}

function subjectNames(input: VoicesInput): string[] {
  const codes = (input.subjectCountries ?? []).map(code => clean(code).toUpperCase()).filter(Boolean)
  const names = input.subjectCountryNames ?? []
  return codes.map((code, i) => clean(names[i]) || code)
}

function coverageClause(outlets: number | null, languages: number): VoiceClause | null {
  const hasOutlets = outlets !== null
  const hasLanguages = languages >= 2
  if (hasOutlets && hasLanguages) {
    return {
      kind: 'coverage',
      text: `${outlets!.toLocaleString()} outlets are carrying this, in at least ${languages} languages`,
    }
  }
  if (hasOutlets) {
    return { kind: 'coverage', text: `${outlets!.toLocaleString()} outlets are carrying this` }
  }
  if (hasLanguages) {
    return {
      kind: 'coverage',
      text: `The receipts carried here span at least ${languages} languages`,
    }
  }
  return null
}

function ownVoiceClause(input: VoicesInput, receipts: readonly VoiceReceipt[]): VoiceClause | null {
  const names = subjectNames(input)
  const codes = (input.subjectCountries ?? []).map(code => clean(code).toUpperCase()).filter(Boolean)
  if (names.length === 0 || codes.length === 0) return null

  const known = receipts.filter(r => clean(r.source_origin_country).length > 0)
  // Unmeasurable, not zero: with no attributed origin there is no denominator
  // and therefore no claim to make about anybody's own press.
  if (known.length === 0) return null

  const subject = new Set(codes)
  const domestic = known.filter(r => subject.has(clean(r.source_origin_country).toUpperCase())).length
  const denominator = `${known.length} receipt${known.length === 1 ? '' : 's'} whose outlet home country is known`
  const owner = names.length === 1
    ? `${possessive(names[0])} own press`
    : `the press of ${joinNames(names)}`

  if (domestic === 0) {
    // X1 (2026-08-13): this clause, read straight, told a blind panel that
    // Colombia's press said nothing about Colombia's own 7.4 earthquake while
    // El Tiempo, Caracol and El Colombiano were leading with it. The zero was
    // real — of Atlas's receipts. So the refusal rides IN the clause: a reader
    // must not have to reach the basis rail to learn what the zero is about.
    return {
      kind: 'ownVoice',
      text: `none of the ${denominator} come from ${owner}`
        + ' — a gap in what Atlas ingests, not a silent press',
    }
  }
  // A share is not a silence claim, so it takes no refusal — only the basis
  // rail's denominator, which it already had.
  return { kind: 'ownVoice', text: `${owner}: ${domestic} of the ${denominator}` }
}

function stateMediaClause(receipts: readonly VoiceReceipt[]): VoiceClause | null {
  const n = receipts.filter(r => r.is_state_media === true).length
  if (n === 0) return null
  return {
    kind: 'stateMedia',
    text: n === 1
      ? '1 of the receipts is a state-controlled outlet'
      : `${n} of the receipts are state-controlled outlets`,
  }
}

function disputedClause(tension?: VoiceTension | null): VoiceClause | null {
  const note = clean(tension?.note)
  if (!note) return null
  const a = clean(tension?.a?.outlet)
  const b = clean(tension?.b?.outlet)
  // Attribution rides along when both sides are named; a half-attributed
  // divergence is still a real divergence, so it is stated without the names
  // rather than dropped.
  const attribution = a && b ? ` (${a} vs ${b})` : ''
  return { kind: 'disputed', text: `in dispute: ${note}${attribution}` }
}

function basisLine(receiptCount: number, hasOutletTotal: boolean): string {
  const counted = `Voices counted from the ${receiptCount} receipt${receiptCount === 1 ? '' : 's'} carried with this story`
  // The rail named the SAMPLE but never the POPULATION, so "48 outlets are
  // carrying this" still read as 48 of the world's outlets (X1). Both lineages
  // sit inside the same ingest, and the rail now says so — in the plural only
  // when there are in fact two lineages to cover.
  const over = `measured over what Atlas ingests (${INGEST_POPULATION}), not the whole press.`
  return hasOutletTotal
    ? `${counted}; the outlet total is the story's own measured source count. Both are ${over}`
    : `${counted}. That count is ${over}`
}

/**
 * Weave the measured voices into the lead's standfirst.
 *
 * Returns `null` when not one clause could be built — the honest state for a
 * story whose payload carries no receipts and no measured outlet count.
 */
export function weaveVoices(input: VoicesInput): VoicesProse | null {
  const receipts = input.receipts ?? []
  const outlets = typeof input.outlets === 'number'
    && Number.isFinite(input.outlets)
    && input.outlets > 0
    ? Math.round(input.outlets)
    : null

  const clauses = [
    coverageClause(outlets, distinctLanguages(receipts)),
    ownVoiceClause(input, receipts),
    stateMediaClause(receipts),
    disputedClause(input.tension),
  ].filter((clause): clause is VoiceClause => clause !== null)

  if (clauses.length === 0) return null

  return {
    clauses,
    sentence: `${clauses.map(c => c.text).join('; ')}.`,
    basis: basisLine(receipts.length, outlets !== null),
  }
}
