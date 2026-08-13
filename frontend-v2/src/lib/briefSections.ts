/**
 * The Brief's two measured sections, client side (T3.3 — renders T3.2's
 * `brief-rising-v1` / `brief-gap-v1`).
 *
 * The backend computes both with template prose over measured fields and serves
 * the SAME payload to the live briefing and to the sealed package, so this
 * module deliberately does NO arithmetic on the measurement: it maps shapes,
 * chooses honest copy for the states that carry no finding, and hands the rest
 * to the renderer verbatim. Any number the reader sees was measured upstream.
 *
 * The states are the point. A section with nothing in it has to say WHICH of
 * two very different things happened — "we measured and found nothing" versus
 * "we could not measure" — because collapsing them is how a page starts
 * claiming an absence it never established (the 2026-07-22 silent-risk kill).
 * Every field here is optional: a payload from an older seal, or from a backend
 * mid-deploy, degrades to the honest state instead of throwing.
 */

export interface SectionReceipt {
  signal_id?: number | string | null
  headline?: string | null
  source?: string | null
  url?: string | null
  lang?: string | null
  origin_country?: string | null
  timestamp?: string | null
}

/** The Brief's receipt row contract (a subset of ThreadEvidence). */
export interface SectionEvidence {
  id?: number | string
  headline: string
  source?: string
  url?: string
  source_lang?: string | null
  source_origin_country?: string | null
  timestamp?: string | null
}

export interface RisingItem {
  thread_id: string
  label: string
  category?: string | null
  /** Label Court verdict — `failed`/`partial` are marked, never hidden. */
  label_status?: string | null
  surprise?: number
  velocity?: number
  volume?: number
  trend?: string | null
  /** The measured why-now, already templated backend-side. */
  why_now?: string
  /**
   * X4 (2026-08-13) — the same why-now, split so the renderer can set the two
   * halves differently instead of re-parsing a sentence client-side.
   *
   * `why_now_plain` is the lay reading ("Rising much faster than its own normal
   * pace, and still speeding up"); `why_now_measured` is the statistics that
   * back it. Both come from `brief_sections.py`, and `why_now` is exactly their
   * join, so a payload from an older seal that carries only `why_now` still
   * renders the whole sentence.
   */
  why_now_plain?: string | null
  why_now_measured?: string | null
  receipts?: SectionReceipt[] | null
  receipt_status?: string | null
  /** Which membership regime answered for the receipts (v1-compat / unified). */
  receipt_basis?: string | null
  measured_at?: string | null
}

export interface RisingSection {
  contract?: string
  bar?: Record<string, unknown> | null
  items?: RisingItem[] | null
  candidates?: number
  /** Cleared the bar, then could not be printed — reason → count. */
  excluded_after_bar?: Record<string, number> | null
  status?: string
  reason?: string | null
  measured_at?: string | null
}

export interface GapMeasured {
  volume?: number
  baseline?: number
  baseline_days?: number
  multiplier?: number
  self_voice_ratio?: number | null
  self_voice_status?: string
  known_origin_n?: number
  domestic_n?: number
  unattributed_n?: number
  reprint_concentration?: Record<string, unknown> | null
}

export interface GapSection {
  contract?: string
  bar?: Record<string, unknown> | null
  confidence?: string
  confidence_note?: string | null
  day?: string
  day_complete?: boolean
  candidates_scored?: number
  candidates_cleared?: number
  status?: string
  reason?: string | null
  country?: { code: string; name: string } | null
  measured?: GapMeasured | null
  prose?: string | null
  /** Load-bearing honesty — rendered verbatim, never paraphrased or trimmed. */
  caveat?: string | null
  receipts?: SectionReceipt[] | null
  measured_at?: string | null
}

export const RISING_KICKER = 'Measured acceleration'
export const RISING_TITLE = 'What Is Rising'
export const gapKicker = 'The coverage nobody wrote'
export const GAP_TITLE = 'The Gap'

/** Reason codes the two lanes serve, in the reader's words. */
const RISING_REASONS: Record<string, string> = {
  movement_unavailable:
    'The movement lane did not answer for this window, so today\'s acceleration is unmeasured — '
    + 'not a claim that nothing is rising.',
  no_story_cleared_the_bar: 'No story cleared the acceleration bar in this window.',
}

const GAP_REASONS: Record<string, string> = {
  no_country_cleared_the_bar: 'No country cleared the divergence bar today — no blindspot is claimed.',
  anomaly_lane_unavailable:
    'The anomaly lane did not answer, so today\'s blindspot is unmeasured — not a claim that '
    + 'there is none.',
  voice_lane_unavailable:
    'The voice lane did not answer. A volume spike alone is not a blindspot, so nothing is '
    + 'served rather than a finding we cannot support.',
}

/** What LO QUE SUBE says when it served no item. `null` when it served some. */
export function risingEmptyCopy(section: RisingSection | null | undefined): string | null {
  if (!section) return null
  if ((section.items ?? []).length > 0) return null
  const reason = section.reason ?? ''
  if (reason && RISING_REASONS[reason]) return RISING_REASONS[reason]
  if (reason) return `Not measured for this window (${reason}).`
  return RISING_REASONS.no_story_cleared_the_bar
}

/** What EL VACÍO says when it has no finding. `null` when it has one. */
export function gapEmptyCopy(section: GapSection | null | undefined): string | null {
  if (!section) return null
  if (section.status === 'ok' && section.country) return null
  const reason = section.reason ?? ''
  if (reason && GAP_REASONS[reason]) return GAP_REASONS[reason]
  if (reason) return `Not measured today (${reason}).`
  return GAP_REASONS.no_country_cleared_the_bar
}

/** Human words for an `excluded_after_bar` key; unknown codes de-snake honestly. */
function exclusionPhrase(reason: string, count: number): string {
  switch (reason) {
    case 'unlabelled':
      return `${count} with no label yet`
    case 'junk':
      return `${count} classified junk`
    case 'roundup':
      return `${count} service roundup${count === 1 ? '' : 's'}`
    case 'label_court_too_broad':
      return `${count} whose label the court ruled too broad`
    default:
      return `${count} ${reason.replaceAll('_', ' ')}`
  }
}

/**
 * The one-line note for stories that cleared the measured bar and were then
 * dropped as unprintable. Never silent — a story removed after clearing a bar
 * has to say why, next to the section it did not appear in.
 */
export function excludedAfterBarNote(
  excluded: Record<string, number> | null | undefined,
): string | null {
  const entries = Object.entries(excluded ?? {}).filter(([, n]) => typeof n === 'number' && n > 0)
  if (entries.length === 0) return null
  entries.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
  const total = entries.reduce((sum, [, n]) => sum + n, 0)
  const parts = entries.map(([reason, n]) => exclusionPhrase(reason, n))
  return `${total} ${total === 1 ? 'story' : 'stories'} cleared the bar but could not be printed: `
    + `${parts.join(', ')}.`
}

/** The confidence chip for EL VACÍO's own bar (`provisional` today). */
export function gapConfidenceChip(
  section: GapSection | null | undefined,
): { label: string; tip: string } | null {
  const confidence = (section?.confidence ?? '').trim()
  if (!confidence) return null
  const note = (section?.confidence_note ?? '').trim()
  return {
    label: `${confidence.toUpperCase()} BAR`,
    tip: note
      || 'This bar is provisional: it has not been validated against enough measured days yet.',
  }
}

export interface WhyNowParts {
  /** The lay reading, set in reader type. Null when the payload predates X4. */
  plain: string | null
  /** The statistics that back it, set as a stat line. */
  measured: string | null
}

/**
 * Split a rising item's why-now into the two halves the Brief renders.
 *
 * X4 (2026-08-13) — blind college C5. The number stays and gains a plain
 * companion, so the renderer needs both halves separately. The backend serves
 * them that way; this function exists for the payloads that do NOT — a sealed
 * edition frozen before X4 carries only the joined `why_now`, and the honest
 * thing to do with an old string is print it verbatim as the measured half
 * rather than guess where a plain clause might have been.
 */
export function whyNowParts(item: RisingItem | null | undefined): WhyNowParts {
  const plain = (item?.why_now_plain ?? '').trim()
  const measured = (item?.why_now_measured ?? '').trim()
  if (plain && measured) return { plain, measured }
  const joined = (item?.why_now ?? '').trim()
  if (measured) return { plain: plain || null, measured }
  return { plain: plain || null, measured: joined || null }
}

/** Map one served receipt onto the Brief's receipt row contract. */
export function sectionReceiptToEvidence(receipt: SectionReceipt): SectionEvidence {
  return {
    id: receipt.signal_id ?? undefined,
    headline: (receipt.headline ?? '').trim(),
    source: receipt.source ?? undefined,
    url: receipt.url ?? undefined,
    source_lang: receipt.lang ?? null,
    source_origin_country: receipt.origin_country ?? null,
    timestamp: receipt.timestamp ?? null,
  }
}

/** Every receipt that can actually be shown (a headline-less row shows nothing). */
export function sectionReceipts(
  receipts: SectionReceipt[] | null | undefined,
): SectionEvidence[] {
  return (receipts ?? [])
    .map(sectionReceiptToEvidence)
    .filter(receipt => receipt.headline.length > 0)
}
