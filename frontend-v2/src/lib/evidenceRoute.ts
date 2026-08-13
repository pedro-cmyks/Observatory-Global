// #173 — Evidence Route breadcrumb: the honest funnel from a Country down to the
// raw Evidence Signals, every step carrying its REAL count from the CountryBrief
// payload. Pure builder: given the counts CountryBrief already fetched -> the
// ordered breadcrumb steps. A missing count renders "—" (see EvidenceRoute.tsx),
// never a fabricated number; the "% foreign" detail is omitted when unknown.
//
// Anti-goal: this is a coverage/volume trail. It never implies public-attention
// is corroboration — public attention is not a step in the route.

import { MENTIONED_IT, PASSED_VERIFICATION } from './statPhrases'

export interface EvidenceRouteInput {
  countryName: string
  /** Distinct outlets covering the country (top_sources.length). */
  outletCount?: number | null
  /** Share of coverage from foreign-origin outlets, 0-100. Omitted when unknown. */
  foreignSourcePct?: number | null
  /** Atlas topics present in the coverage (top_themes.length). */
  atlasTopicCount?: number | null
  /** Narrative threads that stand behind the gate (verified thread count). */
  narrativeThreadCount?: number | null
  /** Raw evidence signals in the window (signal_count). */
  evidenceSignalCount?: number | null
}

export interface EvidenceRouteStep {
  /** Stable key for React + tests. */
  key: string
  /** Human label, e.g. "Source Mix". */
  label: string
  /** Real count, or null when the payload didn't carry it -> renders "—". */
  count: number | null
  /** Secondary honest detail, e.g. "18% foreign", or null when absent. */
  detail: string | null
  /** Id of the CountryBrief section this chip scrolls to. */
  targetId: string
}

/** Coerce to a finite non-negative integer, else null (honest absence). */
function asCount(value: number | null | undefined): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0
    ? Math.round(value)
    : null
}

// ── #173 cross-context routes (2026-08-03) ──────────────────────────────────
// The same honest-funnel contract for the other three drilldown contexts the
// issue names: topic (ThemeDetail), person (EntityPanel), signal
// (SignalDetailPanel). Same rules: real counts only, null -> "—", public
// attention is never a route step, attention/discussion never reads as
// corroboration.

export interface TopicEvidenceRouteInput {
  topicLabel: string
  /** Raw signals assigned to the thread (rawTotal). */
  rawAssignedCount?: number | null
  /** Signals the relevance gate verified (total). */
  verifiedCount?: number | null
  /** Countries in the coverage breakdown. */
  countryCount?: number | null
  /** Distinct outlets (topSources.length). */
  outletCount?: number | null
  /** Evidence rows fetched with headline + outlet in this view (signals.length). */
  sourcedEvidenceCount?: number | null
}

/**
 * ThemeDetail: Thread -> Raw assigned -> Gate-verified -> Countries -> Source Mix -> Evidence.
 *
 * X4 (2026-08-13): "Raw assigned / Gate-verified" is a verbatim witness from
 * the blind college's C5 — four of eight personas could not read the funnel.
 * The engine's own terms stay as labels (the analyst navigates by them) and
 * the plain reading rides in `detail`, which this breadcrumb already renders
 * beside the count.
 */
export function buildTopicEvidenceRoute(input: TopicEvidenceRouteInput): EvidenceRouteStep[] {
  return [
    { key: 'topic', label: input.topicLabel, count: null, detail: null, targetId: 'td-header' },
    { key: 'raw', label: 'Raw assigned', count: asCount(input.rawAssignedCount), detail: MENTIONED_IT, targetId: 'td-header' },
    { key: 'verified', label: 'Gate-verified', count: asCount(input.verifiedCount), detail: PASSED_VERIFICATION, targetId: 'td-signals' },
    { key: 'countries', label: 'Countries', count: asCount(input.countryCount), detail: null, targetId: 'td-coverage' },
    { key: 'sources', label: 'Source Mix', count: asCount(input.outletCount), detail: null, targetId: 'td-sources' },
    { key: 'signals', label: 'Evidence Signals', count: asCount(input.sourcedEvidenceCount), detail: null, targetId: 'td-signals' },
  ]
}

export interface PersonEvidenceRouteInput {
  personName: string
  /** Signals mentioning the entity in the window (summary.total_signals). */
  signalCount?: number | null
  /** Countries covering the entity (summary.total_countries). */
  countryCount?: number | null
  /** Threads the person participates in — omit (undefined) when the context
   *  never measures it (theme-entity focus), null when measured-but-absent. */
  threadCount?: number | null
  /** Typed key subjects surfaced alongside the entity. */
  keySubjectCount?: number | null
}

/** EntityPanel: Person -> Signals -> Countries [-> Threads] -> Key Subjects. */
export function buildPersonEvidenceRoute(input: PersonEvidenceRouteInput): EvidenceRouteStep[] {
  const steps: EvidenceRouteStep[] = [
    { key: 'person', label: input.personName, count: null, detail: null, targetId: 'ep-header' },
    { key: 'signals', label: 'Mentioned in', count: asCount(input.signalCount), detail: 'signals', targetId: 'ep-coverage' },
    { key: 'countries', label: 'Countries', count: asCount(input.countryCount), detail: null, targetId: 'ep-countries' },
  ]
  if (input.threadCount !== undefined) {
    steps.push({ key: 'threads', label: 'Stories', count: asCount(input.threadCount), detail: null, targetId: 'ep-threads' })
  }
  steps.push({ key: 'subjects', label: 'Key Subjects', count: asCount(input.keySubjectCount), detail: null, targetId: 'ep-subjects' })
  return steps
}

export interface SignalEvidenceRouteInput {
  /** Stream lane from relevance scoring (#177) — the signal's source class. */
  lane?: string | null
  /** Living threads this signal connects to (member/semantic/keyword). */
  connectedThreadCount?: number | null
  /** Nearest embedding neighbours. */
  semanticNeighborCount?: number | null
  /** Raw GDELT taxonomy themes on the row. */
  gdeltThemeCount?: number | null
}

/** SignalDetailPanel: Signal -> Narrative Threads -> Semantic Neighbors -> GDELT taxonomy. */
export function buildSignalEvidenceRoute(input: SignalEvidenceRouteInput): EvidenceRouteStep[] {
  return [
    {
      key: 'signal',
      label: 'Signal',
      count: null,
      // The lane is the row's measured stream class (analyst/sports/…): the
      // one source-class fact the panel actually has for the raw row.
      detail: input.lane ? `${input.lane} lane` : null,
      targetId: 'sdp-headline',
    },
    { key: 'threads', label: 'Stories', count: asCount(input.connectedThreadCount), detail: null, targetId: 'sdp-threads' },
    { key: 'neighbors', label: 'Semantic Neighbors', count: asCount(input.semanticNeighborCount), detail: null, targetId: 'sdp-neighbors' },
    { key: 'taxonomy', label: 'GDELT Taxonomy', count: asCount(input.gdeltThemeCount), detail: 'raw themes', targetId: 'sdp-taxonomy' },
  ]
}

export interface SourceEvidenceRouteInput {
  domain: string
  /** Coarse tier label (classifyOutlet -> coarseTierLabel): WIRE/STATE/MAJOR/
   *  LOCAL/UNKNOWN — the head chip's source-class fact, the acceptance's
   *  "distinguish reporting / wire / state" requirement. */
  tierLabel?: string | null
  /** Signals from this outlet in the window (summary.total_signals). */
  signalCount?: number | null
  /** Countries this outlet covers (summary.total_countries). */
  countryCount?: number | null
  /** Distinct themes in the outlet's coverage (top_themes.length). */
  themeCount?: number | null
}

/** SourceProfile: Source (tier) -> Signals -> Countries -> Thematic Focus.
 *  The fifth acceptance context (#173) — why am I seeing this outlet's rows. */
export function buildSourceEvidenceRoute(input: SourceEvidenceRouteInput): EvidenceRouteStep[] {
  return [
    { key: 'source', label: input.domain, count: null, detail: input.tierLabel ?? null, targetId: 'sp-header' },
    { key: 'signals', label: 'Signals', count: asCount(input.signalCount), detail: null, targetId: 'sp-footprint' },
    { key: 'countries', label: 'Countries', count: asCount(input.countryCount), detail: null, targetId: 'sp-countries' },
    { key: 'themes', label: 'Thematic Focus', count: asCount(input.themeCount), detail: null, targetId: 'sp-themes' },
  ]
}

export function buildEvidenceRoute(input: EvidenceRouteInput): EvidenceRouteStep[] {
  const foreignPct = asCount(input.foreignSourcePct)

  return [
    {
      key: 'country',
      label: input.countryName,
      count: null,
      detail: null,
      targetId: 'cb-header',
    },
    {
      key: 'sources',
      label: 'Source Mix',
      count: asCount(input.outletCount),
      detail: foreignPct !== null ? `${foreignPct}% foreign` : null,
      targetId: 'cb-sources',
    },
    {
      key: 'topics',
      label: 'Atlas Topics',
      count: asCount(input.atlasTopicCount),
      detail: null,
      targetId: 'cb-threads',
    },
    {
      key: 'threads',
      label: 'Stories',
      count: asCount(input.narrativeThreadCount),
      detail: null,
      targetId: 'cb-threads',
    },
    {
      key: 'signals',
      label: 'Evidence Signals',
      count: asCount(input.evidenceSignalCount),
      detail: null,
      targetId: 'cb-signals',
    },
  ]
}
