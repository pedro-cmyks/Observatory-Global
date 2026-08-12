// Prose-vs-tables validator (council Phase 3, Lane B).
//
// Marcos' blocker: generated prose lies more than tables. The dossier synthesis
// (and Editor's-Analysis / auto-title) is ONE LLM pass; it can assert a figure
// no receipt carries, or say a story is "confirmed" while corroboration was
// never measured. This module validates generated prose against the MEASURED
// set the dossier already holds — the claim-table figures, measured sentiment /
// coverage counts, and the corroboration verdict — and annotates every span:
//
//   ok                    → backed (or not a claim); rendered verbatim.
//   unbacked-figure       → a numeric claim no measured value backs; the
//                           renderer keeps the text but attaches a caveat chip.
//   unbacked-confirmation → "confirmed"/"verified"/"corroborated"/"established"
//                           with NO corroboration verdict behind it. Marcos'
//                           hard rule: never assert corroboration we didn't
//                           measure → the word is downgraded to
//                           "reported (uncorroborated)" with a data-tip.
//
// PURE — no fetch, no localStorage, no DOM. Mirrors reconcileSentimentProse's
// number-in-context approach (keyword-gated, so ordinary integers/years/citation
// markers never false-fire). The renderer decides how to present the segments.
import type { CorroborationData } from './dossierCorroboration'

export type ProseAnnotationKind = 'ok' | 'unbacked-figure' | 'unbacked-confirmation'

export interface ProseAnnotatedSegment {
  /** Rendered text. For unbacked-confirmation this is the SOFTENED replacement
   *  ("reported (uncorroborated)"); for everything else it is the original text. */
  text: string
  kind: ProseAnnotationKind
  /** The original prose text, present on the two flagged kinds. */
  original?: string
  /** Human explanation for the data-tip / caveat chip. */
  note?: string
}

/** The measured evidence the prose is checked against. */
export interface MeasuredContext {
  /** Every measured numeric value available at render time — claim-table
   *  figures, measured sentiment, coverage/corroboration counts. A prose figure
   *  passes when it matches any of these within tolerance. */
  figures: number[]
  /** True when at least one corroboration verdict actually backs the
   *  investigation (a pin measured `established`). Gates the confirmation words. */
  corroborationBacked: boolean
}

/** The assertion words that claim corroboration we may not have measured. */
const CONFIRMATION_RE = /\b(confirmed|verified|corroborated|established)\b/gi

/** Quantity keywords that turn a nearby number into a figure CLAIM (so bare
 *  integers, durations, and years are not validated as counts). */
const QUANTITY_KEYWORD_RE =
  /\b(dead|kill(?:ed|s)?|death|deaths|casualt\w*|toll|wounded|injur\w*|displaced|fatalit\w*|victim\w*|source\w*|outlet\w*|article\w*|independent|sentiment|tone|mood|percent)\b/i

/** How far (chars) a quantity keyword may sit from a number for it to count as
 *  a figure claim. */
const FIGURE_KEYWORD_WINDOW = 40

/** Numeric token: thousands-separated form tried first, then plain. Optional
 *  ASCII/Unicode sign. */
const NUMBER_RE = /[-−+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[-−+]?\d+(?:\.\d+)?/g

/** DATE SPANS (Frank 2026-08-12): the lede rendered "2026⚠-08⚠-10⚠" because
 *  NUMBER_RE splits an ISO date into 2026 / -08 / -10 and a quantity keyword
 *  ("outlets on 2026-08-10") sat inside the keyword window. A number that is
 *  PART OF A DATE is never a figure claim, so date spans are computed once per
 *  prose and any number intersecting one is skipped.
 *  Covered: YYYY-MM-DD · YYYY/MM/DD · DD-MM-YYYY · MM/DD/YYYY · long forms
 *  ("August 10, 2026", "10 August 2026", "Aug. 10"). The day in a long form is
 *  `\d{1,2}(?![\d,])` so "The March left 5,000 dead" keeps 5,000 a real count. */
const MONTH = '(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\\.?'
const DATE_RES: RegExp[] = [
  /\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b/g,
  /\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b/g,
  new RegExp(`\\b${MONTH}\\s+\\d{1,2}(?![\\d,])(?:st|nd|rd|th)?(?:,?\\s+\\d{4})?`, 'gi'),
  new RegExp(`\\b\\d{1,2}(?![\\d,])(?:st|nd|rd|th)?\\s+${MONTH}(?:,?\\s+\\d{4})?`, 'gi'),
]

function dateSpans(prose: string): Array<[number, number]> {
  const spans: Array<[number, number]> = []
  for (const re of DATE_RES) {
    re.lastIndex = 0
    for (const m of prose.matchAll(re)) {
      const start = m.index ?? 0
      spans.push([start, start + m[0].length])
    }
  }
  return spans
}

/** True when [start,end) touches a date span (the sign of "-08" sits INSIDE the
 *  ISO span, so intersection — not containment — is the test). */
function intersectsDate(spans: Array<[number, number]>, start: number, end: number): boolean {
  return spans.some(([s, e]) => start < e && end > s)
}

/** NEGATION SCOPE (Frank 2026-08-12): when the corroboration lane failed, the
 *  substitution spliced its phrase into negated clauses — "could not be verified
 *  or linked to the confirmed deal" rendered as "could not be reported
 *  (uncorroborated) or linked to the reported (uncorroborated) deal". That is
 *  both ungrammatical AND false: "could not be verified" is an honest statement
 *  of ABSENCE, exactly what the honesty rail wants — downgrading it asserts the
 *  opposite. A confirmation word already under a negation in its own clause is
 *  therefore left verbatim. Clause-scoped (not sentence-scoped) so a fresh
 *  assertion after a comma is still softened. */
const NEGATION_RE = /\b(?:not|never|no|nor|none|without|cannot|unable|lacks?|lacking|absent|yet)\b|n[’']t\b/i
const CLAUSE_BREAK_RE = /[.!?;:,()"“”—–]/
const NEGATION_WINDOW = 80

function isNegatedClaim(prose: string, start: number): boolean {
  const from = Math.max(0, start - NEGATION_WINDOW)
  let clause = prose.slice(from, start)
  const lastBreak = clause.split('').reduce(
    (acc, ch, i) => (CLAUSE_BREAK_RE.test(ch) ? i : acc), -1)
  if (lastBreak >= 0) clause = clause.slice(lastBreak + 1)
  return NEGATION_RE.test(clause)
}

interface Hit {
  start: number
  end: number
  kind: Exclude<ProseAnnotationKind, 'ok'>
  text: string
  original: string
  note: string
}

/** Whether the confirmation verdict actually backs the dossier: corroboration
 *  was run, the search lane answered, and at least one pin is `established`.
 *  Contested / unverified / not-applicable do NOT count — that is precisely the
 *  state where "confirmed" would be a lie. */
export function corroborationBackedFrom(c: CorroborationData | null | undefined): boolean {
  if (!c || !c.search_available) return false
  return c.pins.some(p => p.status === 'established')
}

/** Softened replacement for an unbacked confirmation word, preserving a
 *  sentence-leading capital. */
function softenConfirmation(original: string): string {
  const leadCap = /^[A-Z]/.test(original)
  return leadCap ? 'Reported (uncorroborated)' : 'reported (uncorroborated)'
}

/** True when a measured value backs `value` — exact for counts, small absolute
 *  slack for sentiment, ~1% relative slack for rounded large counts. */
function figureBacked(value: number, figures: number[]): boolean {
  const tol = Math.max(0.05, Math.abs(value) * 0.01)
  return figures.some(m => Number.isFinite(m) && Math.abs(m - value) <= tol)
}

function isCitationMarker(prose: string, start: number, end: number): boolean {
  return prose[start - 1] === '[' && prose[end] === ']'
}

/** Is the number at [start,end) a figure CLAIM (a count/percent/sentiment we
 *  should validate), rather than a year / duration / ordinal we should ignore? */
function isFigureClaim(
  prose: string, token: string, start: number, end: number, dates: Array<[number, number]>,
): boolean {
  if (intersectsDate(dates, start, end)) return false   // a date component, never a count
  if (token.includes(',')) return true          // thousands-separated → a count
  if (prose[end] === '%') return true           // a percentage
  const ctxStart = Math.max(0, start - FIGURE_KEYWORD_WINDOW)
  const ctxEnd = Math.min(prose.length, end + FIGURE_KEYWORD_WINDOW)
  return QUANTITY_KEYWORD_RE.test(prose.slice(ctxStart, ctxEnd))
}

/** Validate generated prose against the measured context. Returns ordered
 *  segments; only unbacked spans are non-`ok`. Consecutive backed text is
 *  merged into single `ok` segments. */
export function validateProse(prose: string, ctx: MeasuredContext): ProseAnnotatedSegment[] {
  if (!prose) return []

  const hits: Hit[] = []
  const dates = dateSpans(prose)

  // 1) Confirmation words — only a problem when nothing backs them AND the
  //    sentence actually ASSERTS corroboration. Under a negation the word is
  //    already honest ("could not be verified"), so it is left verbatim.
  if (!ctx.corroborationBacked) {
    for (const m of prose.matchAll(CONFIRMATION_RE)) {
      const original = m[0]
      const start = m.index ?? 0
      if (isNegatedClaim(prose, start)) continue
      hits.push({
        start,
        end: start + original.length,
        kind: 'unbacked-confirmation',
        text: softenConfirmation(original),
        original,
        note: 'No corroboration verdict backs this — downgraded from '
          + `"${original}" to reported (uncorroborated).`,
      })
    }
  }

  // 2) Numeric figure claims — flagged when no measured value backs them.
  for (const m of prose.matchAll(NUMBER_RE)) {
    const token = m[0]
    const start = m.index ?? 0
    const end = start + token.length
    if (isCitationMarker(prose, start, end)) continue
    if (!isFigureClaim(prose, token, start, end, dates)) continue
    const value = Number(token.replace(/,/g, '').replace('−', '-'))
    if (!Number.isFinite(value)) continue
    if (figureBacked(value, ctx.figures)) continue
    hits.push({
      start,
      end,
      kind: 'unbacked-figure',
      text: token,
      original: token,
      note: 'This figure is not backed by a measured value in the dossier — treat as reported, not established.',
    })
  }

  if (hits.length === 0) return [{ text: prose, kind: 'ok' }]

  // Order by position; drop any overlap (a confirmation word and a figure never
  // overlap in practice, but stay defensive — earliest hit wins).
  hits.sort((a, b) => a.start - b.start)
  const kept: Hit[] = []
  let lastEnd = -1
  for (const h of hits) {
    if (h.start < lastEnd) continue
    kept.push(h)
    lastEnd = h.end
  }

  const out: ProseAnnotatedSegment[] = []
  let cursor = 0
  for (const h of kept) {
    if (h.start > cursor) out.push({ text: prose.slice(cursor, h.start), kind: 'ok' })
    out.push({ text: h.text, kind: h.kind, original: h.original, note: h.note })
    cursor = h.end
  }
  if (cursor < prose.length) out.push({ text: prose.slice(cursor), kind: 'ok' })
  return out
}

/** Plain-text join (tests, markdown export, any non-JSX consumer). */
export function joinValidatedText(segs: ProseAnnotatedSegment[]): string {
  return segs.map(s => s.text).join('')
}

/** True when any span was flagged (drives a section-level caveat if wanted). */
export function hasUnbacked(segs: ProseAnnotatedSegment[]): boolean {
  return segs.some(s => s.kind !== 'ok')
}
