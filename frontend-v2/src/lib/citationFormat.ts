// X5 · copy citation (colegio ciego 2026-08-13, persona ESTUDIANTE).
//
// The finding, verbatim: "the Ukraine page was genuinely a one-stop source
// list" … "One change that would most help: a **copy citation / export source
// list** button that gives outlet + headline + date + URL per story. The
// receipts are all there; making them exportable would turn this into a
// bibliography machine."
//
// So this module MEASURES NOTHING. Every field it prints is already on the
// receipt row the reader is looking at; the only new thing is the shape. Two
// rules, both inherited from the receipt chips themselves:
//
//  1. ABSENCE OVER GUESS. An unknown outlet, date, language or url is OMITTED
//     from the line — never "n.d.", never "Unknown outlet". A citation that
//     invents a field is worse than a short one.
//  2. THE LANGUAGE NAMED IS THE ORIGINAL'S. `sourceLang` is the language the
//     piece was PUBLISHED in, not the language the reader read it in — the
//     translated-local-press product (council C2) is exactly what a student
//     needs to cite honestly.

import { decodeEntities } from './decodeEntities'

export interface CitableReceipt {
  headline: string
  source?: string | null
  url?: string | null
  /** ISO 639-1 (or BCP-47) of the ORIGINAL text — signals_v2.source_lang. */
  sourceLang?: string | null
  /** ISO day or full timestamp; only the day reaches the citation. */
  publishedDate?: string | null
}

/** Shared with dossierConnections' coverage-lens vocabulary; kept local so the
 *  formatter has no dependency on the connections lane. */
const LANG_NAMES: Record<string, string> = {
  en: 'English', ro: 'Romanian', es: 'Spanish', fr: 'French', de: 'German',
  ru: 'Russian', ar: 'Arabic', zh: 'Chinese', tr: 'Turkish', pt: 'Portuguese',
  it: 'Italian', fa: 'Persian', hi: 'Hindi', ja: 'Japanese', ko: 'Korean',
  uk: 'Ukrainian', pl: 'Polish', nl: 'Dutch', sv: 'Swedish', he: 'Hebrew',
  id: 'Indonesian', bn: 'Bengali', ur: 'Urdu', el: 'Greek', hu: 'Hungarian',
  cs: 'Czech', sr: 'Serbian', bg: 'Bulgarian', fi: 'Finnish', da: 'Danish',
  no: 'Norwegian', vi: 'Vietnamese', th: 'Thai', sw: 'Swahili', ka: 'Georgian',
}

/** Markers the ingest lanes use for "language not determined" — these must
 *  read as absence, never as a language called "XX". */
const UNKNOWN_LANGS = new Set(['xx', 'und', 'unknown', 'zxx'])

export function citationLanguageLabel(raw: string | null | undefined): string | null {
  const base = (raw ?? '').trim().toLowerCase().split(/[-_]/)[0]
  if (!base || UNKNOWN_LANGS.has(base)) return null
  return LANG_NAMES[base] ?? base.toUpperCase()
}

export function citationDay(raw: string | null | undefined): string | null {
  const s = (raw ?? '').trim()
  if (!s) return null
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/)
  return m ? `${m[1]}-${m[2]}-${m[3]}` : null
}

/** One receipt → one pasteable line. Entities decoded and whitespace collapsed
 *  so a headline that renders across two lines still cites as one. */
function oneLine(s: string): string {
  return decodeEntities(s ?? '').replace(/\s+/g, ' ').trim()
}

/**
 * `Outlet — “Headline” (Original language), YYYY-MM-DD. https://url`
 *
 * Every segment is dropped when its field is absent; the punctuation closes up
 * around the gap rather than leaving a placeholder behind.
 */
export function formatCitation(r: CitableReceipt): string {
  const headline = oneLine(r.headline)
  const outlet = oneLine(r.source ?? '')
  const url = (r.url ?? '').trim()
  const lang = citationLanguageLabel(r.sourceLang)
  const day = citationDay(r.publishedDate)

  // Nothing identifies this row → no citation at all (the caller hides the
  // affordance rather than copying an empty string).
  if (!headline && !outlet && !url) return ''

  const title = headline ? `“${headline}”${lang ? ` (${lang})` : ''}` : ''
  // Outlet and title join with an em dash; with no title the outlet carries
  // the line on its own.
  let line = outlet && title ? `${outlet} — ${title}` : (title || outlet)
  if (day) line += `, ${day}`
  if (url) line += `. ${url}`
  return line
}

export interface SourceListOptions {
  /** The story / country / investigation these receipts belong to. */
  title?: string | null
  /** ISO day the reader copied the list (caller-supplied so the formatter
   *  stays pure and testable). */
  retrievedAt?: string | null
}

/** Identity of a receipt for de-duplication: the url when it has one (the true
 *  identity of a source line — same rule as {@link citationId}), else outlet +
 *  headline, so syndicated repeats are cited once. */
function receiptKey(r: CitableReceipt): string {
  const url = (r.url ?? '').trim()
  if (url) return `u:${url}`
  return `h:${oneLine(r.source ?? '').toLowerCase()}|${oneLine(r.headline).toLowerCase()}`
}

/**
 * The whole visible receipt set as a numbered source list — the "export source
 * list" half of the student's ask. Deduped, numbered, headed by what it is.
 * Empty when nothing is citable (caller renders no button).
 */
export function formatSourceList(
  rows: CitableReceipt[],
  opts: SourceListOptions = {},
): string {
  const seen = new Set<string>()
  const lines: string[] = []
  for (const r of rows) {
    const line = formatCitation(r)
    if (!line) continue
    const key = receiptKey(r)
    if (seen.has(key)) continue
    seen.add(key)
    lines.push(line)
  }
  if (lines.length === 0) return ''

  const title = (opts.title ?? '').trim()
  const day = citationDay(opts.retrievedAt)
  const header = [
    title ? `Sources — ${title}` : 'Sources',
    `${lines.length} receipt${lines.length === 1 ? '' : 's'}`,
    ...(day ? [`retrieved ${day}`] : []),
  ].join(' · ')

  return `${header}\n\n${lines.map((l, i) => `${i + 1}. ${l}`).join('\n')}`
}
