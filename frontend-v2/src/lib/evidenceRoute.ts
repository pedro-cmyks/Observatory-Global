// #173 — Evidence Route breadcrumb: the honest funnel from a Country down to the
// raw Evidence Signals, every step carrying its REAL count from the CountryBrief
// payload. Pure builder: given the counts CountryBrief already fetched -> the
// ordered breadcrumb steps. A missing count renders "—" (see EvidenceRoute.tsx),
// never a fabricated number; the "% foreign" detail is omitted when unknown.
//
// Anti-goal: this is a coverage/volume trail. It never implies public-attention
// is corroboration — public attention is not a step in the route.

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
      label: 'Narrative Threads',
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
