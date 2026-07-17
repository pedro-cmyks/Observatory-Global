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
function isFigureClaim(prose: string, token: string, start: number, end: number): boolean {
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

  // 1) Confirmation words — only a problem when nothing backs them.
  if (!ctx.corroborationBacked) {
    for (const m of prose.matchAll(CONFIRMATION_RE)) {
      const original = m[0]
      const start = m.index ?? 0
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
    if (!isFigureClaim(prose, token, start, end)) continue
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
