// Fix round 2026-07-17 item 3 — never render two different numbers for the
// same metric on one page.
//
// The Brief's "Editor's analysis" prose is generated (and can be stale or
// cached); the instrument strip is measured live. The P1-4 chip anchored the
// prose to the measurement, but the stale figure STILL co-rendered ("-0.1"
// three lines under the -0.53 strip). This helper detects numeric sentiment
// claims inside the prose and, when a claim disagrees with the measured value
// beyond `tolerance`, replaces the figure inline with the measured one. The
// replacement is marked so the renderer can attach a small "corrected against
// the measured strip" data-tip — the correction is visible, never silent.
//
// ROUND 2 scope-fix (2026-07-17): only GLOBAL claims are reconciled against
// the global measurement. The first cut replaced ANY ±1 number near a
// sentiment keyword — which rewrote five legitimate PER-COUNTRY figures
// (-0.09 US, +0.08 CN, …) into the global value, producing prose where both
// polarities carried the same number. A figure now corrects only when:
//   - NO country name sits adjacent to it (within ADJACENT_WINDOW), and
//   - the surrounding window either carries global wording
//     (overall/global/average/window…) or contains no country name at all.
// Numbers attributed to a country are per-country claims and pass through
// untouched.

import { formatSentimentPm1 } from './sentimentScale'
import { COUNTRY_NAMES } from './countryNames'

export interface ProseSegment {
  text: string
  /** Present when this segment is a corrected figure; carries the original. */
  corrected?: { original: string }
}

/** How far (chars) a sentiment keyword may sit from a number for the number to
 * count as a sentiment CLAIM. Keeps "magnitude 5.9" out of scope. */
const KEYWORD_WINDOW = 48

/** A country name within this many chars of the number makes the number a
 * PER-COUNTRY figure — never corrected, even if global wording is also near
 * (the global wording may belong to the neighboring sentence). */
const ADJACENT_WINDOW = 24

const KEYWORD_RE = /sentiment|tone|mood/i

/** Wording that marks a claim as GLOBAL (about the whole window/world). */
const GLOBAL_RE = /(?:overall|global\w*|averag\w*|aggregate|worldwide|window|across the board)/gi

/** Numeric token: optional ASCII/Unicode minus, decimal. NOT preceded/followed
 * by % or more digits (percentages and counts are not sentiment claims). */
const NUMBER_RE = /(?:[-−+]?\d+(?:\.\d+)?)/g

// ── Country-mention detector (round-2) ──────────────────────────────────────
// Names come from the display map (countryNames); a few prose-common aliases
// are added. Bare 2-letter UPPERCASE ISO codes ("in US", "in CN") also count —
// matched case-sensitively so ordinary words never fire.
const COUNTRY_ALIASES = ['U.S.A.', 'U.S.', 'USA', 'U.K.', 'Britain', 'America']

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

const COUNTRY_NAME_RE = new RegExp(
  `(?<![A-Za-z])(?:${Array.from(new Set([...Object.values(COUNTRY_NAMES), ...COUNTRY_ALIASES]))
    .sort((a, b) => b.length - a.length)
    .map(escapeRe)
    .join('|')})(?![A-Za-z])`,
  'gi',
)

const ISO_CODE_RE = /(?<![A-Za-z])[A-Z]{2}(?![A-Za-z])/g
const ISO_CODES = new Set(Object.keys(COUNTRY_NAMES))

/** Smallest char gap between the number (at [ns,ne) inside `ctx`) and any
 * regex match in `ctx`; null when nothing matches. 0 = overlapping/adjacent. */
function nearestGap(
  ctx: string,
  ns: number,
  ne: number,
  re: RegExp,
  accept?: (m: string) => boolean,
): number | null {
  let best: number | null = null
  for (const m of ctx.matchAll(re)) {
    if (accept && !accept(m[0])) continue
    const s = m.index ?? 0
    const e = s + m[0].length
    const gap = e <= ns ? ns - e : s >= ne ? s - ne : 0
    if (best === null || gap < best) best = gap
  }
  return best
}

/** Nearest country mention (name or bare uppercase ISO code) to the number. */
function nearestCountryGap(ctx: string, ns: number, ne: number): number | null {
  const byName = nearestGap(ctx, ns, ne, COUNTRY_NAME_RE)
  const byCode = nearestGap(ctx, ns, ne, ISO_CODE_RE, (m) => ISO_CODES.has(m))
  if (byName === null) return byCode
  if (byCode === null) return byName
  return Math.min(byName, byCode)
}

export function reconcileSentimentProse(
  prose: string,
  measured: number,
  tolerance = 0.05,
): ProseSegment[] {
  if (!prose || !Number.isFinite(measured)) return [{ text: prose }]

  const out: ProseSegment[] = []
  let cursor = 0
  const measuredText = formatSentimentPm1(measured)

  for (const m of prose.matchAll(NUMBER_RE)) {
    const token = m[0]
    const start = m.index ?? 0
    const end = start + token.length
    // % values and figures glued to other digits are not sentiment claims.
    if (prose[end] === '%') continue
    // A sentiment/tone/mood keyword must sit near the number.
    const ctxStart = Math.max(0, start - KEYWORD_WINDOW)
    const ctx = prose.slice(ctxStart, Math.min(prose.length, end + KEYWORD_WINDOW))
    if (!KEYWORD_RE.test(ctx)) continue
    const value = Number(token.replace('−', '-'))
    if (!Number.isFinite(value)) continue
    // Sentiment claims live on the ±1 scale; larger magnitudes (counts, %,
    // magnitudes) are out of scope.
    if (Math.abs(value) > 1) continue
    if (Math.abs(value - measured) <= tolerance) continue

    // Round-2 scope: is this claim GLOBAL? Per-country figures pass through.
    const ns = start - ctxStart
    const ne = end - ctxStart
    const countryGap = nearestCountryGap(ctx, ns, ne)
    if (countryGap !== null) {
      // A country RIGHT NEXT to the figure = a per-country claim, always.
      if (countryGap <= ADJACENT_WINDOW) continue
      // A country in the wider window: only global wording overrides it.
      const globalGap = nearestGap(ctx, ns, ne, GLOBAL_RE)
      if (globalGap === null) continue
    }

    if (start > cursor) out.push({ text: prose.slice(cursor, start) })
    out.push({ text: measuredText, corrected: { original: token } })
    cursor = end
  }

  if (cursor < prose.length) out.push({ text: prose.slice(cursor) })
  if (out.length === 0) return [{ text: prose }]
  return out
}

/** Plain-text join (tests + any non-JSX consumer). */
export function joinSegments(segs: ProseSegment[]): string {
  return segs.map(s => s.text).join('')
}
