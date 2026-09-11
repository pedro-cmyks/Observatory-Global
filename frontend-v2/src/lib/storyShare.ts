// LinkedIn story-share caption (the weekly "one story" ritual — the per-STORY
// sibling of briefEdition.buildShareCaption, which covers the whole edition).
//
// v2 (2026-08-24, campaign spec §2.1): Pedro judged v1 "cero tratamiento
// editorial, solo una foto de datos crudos". The caption may now open with a
// MINI-EDITORIAL lede — but only one the backend quote-gated sentence by
// sentence against the CURATED receipts (story_editorial.py: verbatim-quote
// substring gate + number guard + state-media attribution guard). Absent lede
// = the v1 "measured, not editorialized" template, unchanged.
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
//   * A translated receipt says what it was translated FROM — a Spanish
//     headline rendered in English without the mark would claim an English
//     source that does not exist.
//   * The measured finding (computeShareFinding) is MATH over served fields —
//     no LLM anywhere near it — and every clause names its basis (receipt
//     sample vs full-window country tone).
//
// LinkedIn split (marketing 2026-08-24, accepted by Pedro): LinkedIn shows
// posts with a link in the body to fewer people. The caption therefore
// carries NO link; the deep link ships separately via buildStoryFirstComment,
// posted as the post's first comment.
//
// Pure: no window/DOM. The deep link arrives pre-built by the caller.

import { resolveTierChip } from './sourceProvenance'
import { resolveCountryName } from './countryNames'

export interface StoryShareReceipt {
  headline: string
  outlet?: string | null
  /** Source language code as served (e.g. "es") — printed only when present. */
  lang?: string | null
  /** English translation applied in the kit (server /translate cache). When
   *  present it becomes the display text and the line is marked
   *  "(translated from <lang>)" — never passed off as the original. */
  translated?: string | null
  translatedFrom?: string | null
}

export interface StoryShareInput {
  /** The story's resolved label. */
  label: string
  /** Quote-gated editorial lede from /api/v2/story/{id}/share-editorial —
   *  ONLY ever pass a lede that endpoint served (its gate is the license to
   *  print prose here). Absent → the v1 measured-template opening. */
  lede?: string | null
  /** Measured hook finding (computeShareFinding) — math over served fields. */
  finding?: string | null
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
  /** Pre-built absolute link (window.location.origin + /app?theme=<id>).
   *  NOT printed in the caption — feed it to buildStoryFirstComment. */
  deepLink: string
  /** The author's own closing question to readers (campaign §2.2: a human
   *  CTA beats a templated one — LinkedIn 2026 downranks generic copy). Typed
   *  in the kit, never generated. Blank = no closing line. */
  question?: string | null
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
  const translated = (r.translated ?? '').trim()
  let line = `• “${translated || r.headline}”`
  if (r.outlet) line += ` — ${r.outlet}`
  if (translated && r.translatedFrom) line += ` (translated from ${r.translatedFrom})`
  else if (translated) line += ' (translated)'
  else if (r.lang) line += ` (${r.lang})`
  // Tier from the outlet name alone (ThemeDetail's receipt rows serve no
  // origin/ingest flag) — only the STATE verdict is strong enough to print.
  if (r.outlet && resolveTierChip(r.outlet, undefined).tier === 'state') {
    line += ' — STATE MEDIA'
  }
  return line
}

/** The LinkedIn caption for one story, HOOK-FIRST for the feed (campaign
 *  §2.2: ~140 mobile chars show before "see more", so the first line must
 *  carry the measured claim, not the label):
 *    lede (quote-gated) or the label tagline → Measured: <finding> → vitals →
 *    curated receipts → "Story on Atlas: <label>" → the author's question.
 *  No link — the link goes in the first comment (buildStoryFirstComment). */
export function buildStoryShareCaption(input: StoryShareInput): string {
  const lede = (input.lede ?? '').trim()
  const finding = (input.finding ?? '').trim()
  const blocks: string[] = []
  if (lede) {
    // The lede IS editorial treatment — the tagline would be false over it.
    // Its license: every sentence was quote-gated server-side against the
    // receipts printed below, so the receipts header names that relation.
    blocks.push(lede)
    if (finding) blocks.push(`Measured: ${finding}`)
  } else if (finding) {
    // No lede: the measured finding is the strongest honest hook we have.
    blocks.push(`Measured: ${finding}`)
  } else {
    blocks.push(`${input.label} — measurement, not opinion.`)
  }

  const stats = statsLine(input)
  if (stats) blocks.push(stats)

  const receipts = (input.receipts ?? []).filter(r => !!r.headline).slice(0, MAX_RECEIPTS)
  if (receipts.length > 0) {
    const header = lede
      ? 'Receipts — the lede above is synthesized only from these, quote-checked:'
      : 'Receipts — sampled coverage:'
    blocks.push([header, ...receipts.map(receiptLine)].join('\n'))
  }

  // The label closes when it did not open — the story stays nameable.
  if (lede || finding) blocks.push(`Story on Atlas: ${input.label} — measurement, not opinion.`)

  const question = (input.question ?? '').trim()
  if (question) blocks.push(question)

  return blocks.join('\n\n')
}

/** The post's first comment — the only place the deep link appears (STE). */
export function buildStoryFirstComment(deepLink: string): string {
  return `Read the full measured story on Atlas (free): ${deepLink}`
}

// ─────────────────────────────────────────────────────────────────────────────
// Campaign link — the deep link the first comment carries, tagged so the
// arriving session is attributable (lib/acquisition.ts reads these). LinkedIn's
// lnkd.in wrapper and the iOS in-app browser often strip the referrer, so the
// URL itself must say where it came from.
// ─────────────────────────────────────────────────────────────────────────────

/** ISO-week campaign tag, e.g. "sow-2026-w37" (story of the week). Pure — the
 *  date is injected so the tag is testable and a post scheduled ahead can be
 *  tagged for its publication week. */
export function campaignTagForDate(d: Date): string {
  // ISO 8601 week number (weeks start Monday; week 1 holds the year's first Thursday).
  const t = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()))
  const day = t.getUTCDay() || 7
  t.setUTCDate(t.getUTCDate() + 4 - day)
  const yearStart = new Date(Date.UTC(t.getUTCFullYear(), 0, 1))
  const week = Math.ceil(((t.getTime() - yearStart.getTime()) / 86400000 + 1) / 7)
  return `sow-${t.getUTCFullYear()}-w${String(week).padStart(2, '0')}`
}

export interface CampaignLinkInput {
  origin: string
  /** The story's theme id (dynamic-topic-N). */
  theme: string
  /** utm_campaign — campaignTagForDate(now) by default. */
  campaign: string
  /** utm_source / utm_medium — organic LinkedIn unless told otherwise. */
  source?: string
  medium?: string
}

/** `/app?theme=…&entry=linkedin&utm_source=…` — every arrival from the post
 *  is measurable by construction; nothing else about the link changes. */
export function buildCampaignDeepLink(input: CampaignLinkInput): string {
  const p = new URLSearchParams()
  p.set('theme', input.theme)
  p.set('entry', input.source ?? 'linkedin')
  p.set('utm_source', input.source ?? 'linkedin')
  p.set('utm_medium', input.medium ?? 'organic')
  p.set('utm_campaign', input.campaign)
  p.set('utm_content', input.theme)
  return `${input.origin}/app?${p.toString()}`
}

// ─────────────────────────────────────────────────────────────────────────────
// Measured finding — the hook line. Math over fields the payload served;
// no LLM, no rounding up, every clause carries its basis.
// ─────────────────────────────────────────────────────────────────────────────

export interface ShareFindingInput {
  /** The FULL served receipt sample (data.signals), not the curated 3 —
   *  language/state counts are sample measurements and say so. */
  receipts: Array<{ outlet?: string | null; lang?: string | null }>
  /** ThemeData.countryBreakdown — per-country counts + avg tone over the
   *  story's real window. */
  countries?: Array<{ code: string; count: number; sentiment: number }> | null
}

/** Distinct languages worth calling out (2 is unremarkable). */
const FINDING_MIN_LANGS = 3
/** Per-country tone gap (±1 scale) below which a "split" would be noise. */
const FINDING_TONE_GAP = 0.5
/** Countries with fewer signals than this don't anchor a tone claim. */
const FINDING_TONE_MIN_COUNT = 3

/** Up to two measured clauses, priority languages → state share → tone split;
 *  null when nothing clears its floor — an absent hook over a manufactured one. */
export function computeShareFinding(input: ShareFindingInput): string | null {
  const clauses: string[] = []
  const n = input.receipts.length
  if (n > 0) {
    const langs = new Set(
      input.receipts.map(r => (r.lang ?? '').trim().toLowerCase()).filter(Boolean),
    )
    if (langs.size >= FINDING_MIN_LANGS) {
      clauses.push(`the sampled receipts span ${langs.size} languages`)
    }
    const nState = input.receipts.filter(
      r => r.outlet && resolveTierChip(r.outlet, undefined).tier === 'state',
    ).length
    if (nState > 0) {
      clauses.push(`${nState} of ${n} sampled receipts are from state-media outlets`)
    }
  }
  if (clauses.length < 2) {
    const eligible = (input.countries ?? []).filter(c => c.count >= FINDING_TONE_MIN_COUNT)
    if (eligible.length >= 2) {
      const sorted = [...eligible].sort((a, b) => a.sentiment - b.sentiment)
      const lo = sorted[0]
      const hi = sorted[sorted.length - 1]
      if (hi.sentiment - lo.sentiment >= FINDING_TONE_GAP) {
        clauses.push(
          `coverage tone splits by country — ${resolveCountryName(lo.code, lo.code)} ${lo.sentiment.toFixed(2)} vs ${resolveCountryName(hi.code, hi.code)} ${hi.sentiment.toFixed(2)} (avg tone, full window)`,
        )
      }
    }
  }
  if (clauses.length === 0) return null
  const text = clauses.slice(0, 2).join('; ')
  return text.charAt(0).toUpperCase() + text.slice(1) + '.'
}
