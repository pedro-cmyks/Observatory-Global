// LinkedIn story-share caption (the weekly "one story" ritual — the per-STORY
// sibling of briefEdition.buildShareCaption, which covers the whole edition).
//
// Honesty rules, by construction:
//   * Absent field = absent line. Nothing here defaults, rounds up, or invents
//     a number the payload did not serve.
//   * A signal count only prints WITH the window it was really counted over
//     (the N19 lesson: stamping an assumed window over a number counted across
//     another one is the bug). No window → no count.
//   * The source count is a receipt-sample measurement, and says so.
//   * A state-media receipt is marked STATE MEDIA (resolveTierChip — the same
//     classifier the receipt rows render; council R3 P0: state media is never
//     presented as neutral).
//
// Pure: no window/DOM. The deep link arrives pre-built by the caller.

import { resolveTierChip } from './sourceProvenance'

export interface StoryShareReceipt {
  headline: string
  outlet?: string | null
  /** Source language code as served (e.g. "es") — printed only when present. */
  lang?: string | null
}

export interface StoryShareInput {
  /** The story's resolved label. */
  label: string
  /** Verified/served signal count — omit (null/undefined) when unmeasured. */
  signals?: number | null
  /** The window `signals` was really counted over, e.g. "last 24 hours" or
   *  "latest clustering pass (Aug 22), 7d window". Required for the count to
   *  print at all. */
  signalsWindow?: string | null
  /** Countries with measured coverage — omit when not served. */
  countries?: number | null
  /** Distinct outlets — omit when not served. */
  sources?: number | null
  /** 'receipt_sample' = counted among the resolved receipts, never the story's
   *  full outlet total (ThemeData.sourceCountBasis). */
  sourcesBasis?: 'receipt_sample' | null
  /** Up to 3 render; extras are dropped, receipts without a headline too. */
  receipts?: StoryShareReceipt[]
  /** Pre-built absolute link (window.location.origin + /app?theme=<id>). */
  deepLink: string
}

const MAX_RECEIPTS = 3

function statsLine({ signals, signalsWindow, countries, sources, sourcesBasis }: StoryShareInput): string | null {
  const parts: string[] = []
  if (signals != null && signalsWindow) {
    parts.push(`${signals.toLocaleString('en-US')} signals (${signalsWindow})`)
  }
  if (countries != null) {
    parts.push(`${countries.toLocaleString('en-US')} ${countries === 1 ? 'country' : 'countries'}`)
  }
  if (sources != null) {
    const basis = sourcesBasis === 'receipt_sample' ? ' (distinct outlets in the sampled receipts)' : ''
    parts.push(`${sources.toLocaleString('en-US')} sources${basis}`)
  }
  return parts.length > 0 ? `Measured coverage: ${parts.join(' · ')}.` : null
}

function receiptLine(r: StoryShareReceipt): string {
  let line = `• “${r.headline}”`
  if (r.outlet) line += ` — ${r.outlet}`
  if (r.lang) line += ` (${r.lang})`
  // Tier from the outlet name alone (ThemeDetail's receipt rows serve no
  // origin/ingest flag) — only the STATE verdict is strong enough to print.
  if (r.outlet && resolveTierChip(r.outlet, undefined).tier === 'state') {
    line += ' — STATE MEDIA'
  }
  return line
}

/** The LinkedIn caption for one story: label, measured vitals, receipts, link. */
export function buildStoryShareCaption(input: StoryShareInput): string {
  const blocks: string[] = [`${input.label} — measurement, not opinion.`]

  const stats = statsLine(input)
  if (stats) blocks.push(stats)

  const receipts = (input.receipts ?? []).filter(r => !!r.headline).slice(0, MAX_RECEIPTS)
  if (receipts.length > 0) {
    blocks.push(['Receipts — sampled coverage:', ...receipts.map(receiptLine)].join('\n'))
  }

  blocks.push(`Open the measured story on Atlas → ${input.deepLink}`)
  return blocks.join('\n\n')
}
