/**
 * The mobile search sheet's result model — not its fetching.
 *
 * Task 9 of the mobile-native IA plan. The plan's first draft of this task
 * ("search carries the constellation") is CANCELLED by Task 8's measurement:
 * the sibling lane this would have reused is 30/50 top-5 rows an unrelated
 * story presented as kin, over a field that is 61.25% blob, and the client
 * cannot tell a fused anchor from a clean one — the same reason `connected`
 * in the Lens (lensSections.ts) withholds it. This module renders search
 * RESULTS, never search NEIGHBOURS.
 *
 * Follows the discipline lensSections.ts established for the Lens:
 * - a `state` of 'ok' | 'empty' | 'degraded' | 'loading', never a bare list.
 * - an empty result renders its REASON, never a blank sheet — and "nothing
 *   matched" (a measured absence) is a DIFFERENT sentence than "the search
 *   could not be reached" (a failed lookup). Conflating them is the exact
 *   defect this codebase already shipped once on the desktop SearchBar (a
 *   degraded lane rendering "No results for …") and paid to fix
 *   (searchResults.ts, `searchEmptyVariant`) — reused here rather than
 *   re-derived, so the two search surfaces cannot answer the same question
 *   differently.
 * - a row carries what it IS (`kind`), so the sheet can label its segments
 *   without re-deriving the kind from field presence.
 *
 * WHY THIS DOES NOT OWN THE FETCH. The sheet's own submit handler calls
 * `fetch()` and turns the outcome into a `SearchPhase` — a plain, JSON-able
 * value this module can build a `SearchSheetSection` from without a network,
 * a DOM, or a mock. That is the whole point of keeping it here: every branch
 * below is a vitest `it()`, not a browser click.
 */

import {
  degradedSearchSegments, describeDegradedSegments, hasVisibleSearchResults,
  type DegradableSearchResult, type SearchVisibilityResult,
} from './searchResults'
import { decodeEntities } from './decodeEntities'

/** What a row IS. Lets the sheet label its segments and lets the tap handler
 *  route to the right door without re-deriving the kind from which fields
 *  happen to be set. */
export type SearchRowKind = 'thread' | 'country' | 'person' | 'signal'

export interface SearchRow {
  kind: SearchRowKind
  /** Stable React key, and what a tap acts on: a theme/thread id, a country
   *  code, a person's name, or a signal's numeric id (stringified). */
  id: string
  label: string
  /** Raw counts — this module makes no locale-formatting decisions, the same
   *  restraint lensSections' CountryRow keeps (a raw `count`, not a string). */
  totalSignals?: number
  category?: string | null
  isUmbrella?: boolean
  /** Live-thread label match quality — SearchBar's "partial match" chip. */
  match?: 'all' | 'partial'
  /** Set on 'country' rows (the code itself) and on 'signal' rows that carry
   *  a country (so a signal with no thread can still open a country door). */
  countryCode?: string | null
  /** Set on 'signal' rows: which outlet reported it. */
  source?: string
  /** Set on 'signal' rows that resolved to a thread — the tap handler prefers
   *  this door over the country one, mirroring SearchBar's own
   *  handleSignalMatchClick (theme first, country only as a fallback). */
  themeId?: string
}

export type SearchSheetState = 'ok' | 'empty' | 'degraded' | 'loading'

export interface SearchSheetSection {
  state: SearchSheetState
  /** Present on every state but 'ok' — what to render instead of rows. */
  reason?: string
  rows: SearchRow[]
  /**
   * Set only when state is 'ok' AND a sibling lane still failed: the rows
   * are real, but not the whole truth. Mirrors `Section.withheld` in
   * lensSections.ts — an honest note that rides ALONGSIDE real results
   * instead of replacing them, because rows that did arrive are not less
   * true for a neighbour lane timing out.
   */
  partialFailure?: string
}

/** What the sheet's submit handler measured, in a form this module can build
 *  a section from without touching `fetch` itself. */
export type SearchPhase =
  | { kind: 'idle' }
  | { kind: 'too_short' }
  | { kind: 'loading' }
  | { kind: 'network_error' }
  | { kind: 'http_error'; status: number }
  | { kind: 'ok'; json: unknown }

// ---- raw response shapes --------------------------------------------------
// Mirrors what SearchBar.tsx destructures at runtime against the SAME
// `/api/v2/search/unified` endpoint — the only verified ground truth
// reachable without touching backend/.

interface RawLiveThread {
  id?: string
  label?: string
  category?: string | null
  total_signals?: number
  is_umbrella?: boolean
  match?: 'all' | 'partial'
}
interface RawTheme {
  theme?: string
  /** Deliberately unused for display — see the labelForTheme note below. */
  label?: string
  category?: string | null
  total_signals?: number
}
interface RawCountry { code?: string; name?: string }
interface RawPerson { person?: string; total_signals?: number }
interface RawSignalMatch {
  id?: number
  country?: string | null
  source?: string
  headline?: string | null
  themes?: string[]
}
interface RawSearchResponse {
  live_threads?: RawLiveThread[]
  themes?: RawTheme[]
  countries?: RawCountry[]
  persons?: RawPerson[]
  signal_matches?: RawSignalMatch[]
}

/** How many rows of ONE kind the sheet renders before it stops — a phone
 *  screen, not a dropdown. Same number LensPanel's `where it lives` caps at
 *  (WHERE_IT_LIVES_CAP), kept independent rather than imported: the two caps
 *  bound unrelated lists and happening to agree is not a reason to couple
 *  them. */
export const SEARCH_ROW_CAP = 12

export interface ParseRowsOptions {
  /** Legacy `themes[]` rows carry a `theme` CODE — SearchBar translates it
   *  through `getThemeLabel`, never the field's own `.label` (which can be a
   *  stale or absent value; the code is the one the client's own taxonomy
   *  map is kept in sync with). Injected rather than imported so this module
   *  stays dependency-free and testable with a stub; the real caller passes
   *  the real `getThemeLabel`. Defaults to identity — an untranslated code is
   *  ugly, never wrong. */
  labelForTheme?: (code: string) => string
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === 'object'
}

/** Turn a raw `/api/v2/search/unified` body into rows, tagged and ordered.
 *
 * Order — thread, country, person, signal — leads with the discovery unit
 * the product foregrounds everywhere else (Live Threads lead the desktop
 * dropdown too) and ends with raw media signals, the least composed result.
 * Not required to match SearchBar's on-screen section order exactly: that
 * order also interleaves region/public-attention/CTAs this sheet does not
 * render, so copying it byte-for-byte would imply a parity this module does
 * not claim.
 */
export function parseSearchRows(json: unknown, opts: ParseRowsOptions = {}): SearchRow[] {
  if (!isPlainObject(json)) return []
  const r = json as RawSearchResponse
  const labelForTheme = opts.labelForTheme ?? ((code: string) => code)

  const threads: SearchRow[] = []
  for (const t of r.live_threads ?? []) {
    if (!t?.id) continue
    threads.push({
      kind: 'thread', id: t.id, label: decodeEntities(t.label ?? t.id),
      totalSignals: t.total_signals ?? 0, category: t.category ?? null,
      isUmbrella: !!t.is_umbrella, match: t.match,
    })
  }
  // Legacy `themes[]`: the server does not pre-filter these the way it does
  // live_threads, so a zero-signal entry is not a real result — same floor
  // SearchBar applies (`results.themes.filter(t => t.total_signals > 0)`).
  for (const t of r.themes ?? []) {
    if (!t?.theme || !((t.total_signals ?? 0) > 0)) continue
    threads.push({
      kind: 'thread', id: t.theme, label: labelForTheme(t.theme),
      totalSignals: t.total_signals, category: t.category ?? null,
    })
  }

  const countries: SearchRow[] = []
  for (const c of r.countries ?? []) {
    if (!c?.code) continue
    countries.push({ kind: 'country', id: c.code, label: c.name ?? c.code, countryCode: c.code })
  }

  const persons: SearchRow[] = []
  for (const p of r.persons ?? []) {
    if (!p?.person || !((p.total_signals ?? 0) > 0)) continue
    persons.push({ kind: 'person', id: p.person, label: p.person, totalSignals: p.total_signals })
  }

  const signals: SearchRow[] = []
  for (const s of r.signal_matches ?? []) {
    if (s?.id == null) continue
    const themeId = s.themes?.[0]
    const countryCode = s.country ?? null
    // A signal with neither a thread nor a country has no door this sheet can
    // open (SearchBar's handleSignalMatchClick tries theme then country and
    // otherwise does nothing) — dropped here rather than rendered inert, so
    // the tap handler never has to guess whether a row that LOOKS tappable
    // actually goes anywhere (the class of defect this plan kept finding).
    if (!themeId && !countryCode) continue
    signals.push({
      kind: 'signal', id: String(s.id),
      label: s.headline ? decodeEntities(s.headline) : `Signal from ${s.source ?? 'an unnamed source'}`,
      countryCode, source: s.source, themeId,
    })
  }

  return [
    ...threads.slice(0, SEARCH_ROW_CAP),
    ...countries.slice(0, SEARCH_ROW_CAP),
    ...persons.slice(0, SEARCH_ROW_CAP),
    ...signals.slice(0, SEARCH_ROW_CAP),
  ]
}

const REASON = {
  idle: 'Search Atlas — threads, countries, people, signals.',
  tooShort: 'Type at least 2 characters.',
  loading: 'Searching…',
  networkError: "Couldn't reach the search — check your connection and try again.",
  rateLimited: 'Too many searches in a short time — wait a moment and try again.',
  unreadable: 'The search response could not be read.',
  httpError: (status: number) => `The search request failed (status ${status}).`,
  none: (query: string) => `No results for "${query}".`,
  failedLookup: (segments: string[]) =>
    `Couldn't check ${describeDegradedSegments(segments)} — lookup failed, results may be incomplete.`,
}

/** Build the sheet's one section from a query and what the submit handler
 *  measured. `opts` threads the same theme-labeler `parseSearchRows` takes. */
export function buildSearchSection(
  query: string,
  phase: SearchPhase,
  opts: ParseRowsOptions = {},
): SearchSheetSection {
  switch (phase.kind) {
    case 'idle': return { state: 'empty', reason: REASON.idle, rows: [] }
    case 'too_short': return { state: 'empty', reason: REASON.tooShort, rows: [] }
    case 'loading': return { state: 'loading', reason: REASON.loading, rows: [] }
    case 'network_error': return { state: 'degraded', reason: REASON.networkError, rows: [] }
    case 'http_error':
      return phase.status === 429
        ? { state: 'degraded', reason: REASON.rateLimited, rows: [] }
        : { state: 'degraded', reason: REASON.httpError(phase.status), rows: [] }
    case 'ok':
      break
  }

  // phase.kind === 'ok' from here — a response arrived, but "arrived" does
  // not mean "shaped as expected" (a 200 with an empty body, or a JSON parse
  // failure the caller already reduced to `null`). Guarded the same way
  // lensSections' readNodesResponse guards `/api/v2/nodes`: a malformed body
  // degrades, it does not throw and it does not read as absence.
  if (!isPlainObject(phase.json)) {
    return { state: 'degraded', reason: REASON.unreadable, rows: [] }
  }

  const rows = parseSearchRows(phase.json, opts)
  const raw = phase.json as RawSearchResponse & DegradableSearchResult
  const segments = degradedSearchSegments(raw)
  // hasVisibleSearchResults assumes themes/persons/countries are ARRAYS (it
  // calls .some()/.length on them unguarded) — a defaulted view rather than a
  // raw cast, so a body missing one of those keys degrades instead of
  // throwing. rows.length is the belt-and-suspenders half: parseSearchRows
  // already applies the same total_signals floor this predicate does, so the
  // two cannot disagree about whether a live_thread with no signal count
  // counts as visible.
  const visible = rows.length > 0 || hasVisibleSearchResults<SearchVisibilityResult>({
    themes: (raw.themes ?? []).map((t) => ({ total_signals: t.total_signals ?? 0 })),
    persons: (raw.persons ?? []).map((p) => ({ total_signals: p.total_signals ?? 0 })),
    countries: raw.countries ?? [],
    live_threads: raw.live_threads ?? [],
    signal_matches: raw.signal_matches ?? [],
  })

  if (!visible) {
    return segments.length > 0
      ? { state: 'degraded', reason: REASON.failedLookup(segments), rows: [] }
      : { state: 'empty', reason: REASON.none(query), rows: [] }
  }

  return segments.length > 0
    ? { state: 'ok', rows, partialFailure: REASON.failedLookup(segments) }
    : { state: 'ok', rows }
}
