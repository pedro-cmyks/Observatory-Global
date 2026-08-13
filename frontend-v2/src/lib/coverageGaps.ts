// Coverage gaps = the "Under the Radar" substrate. A category that got real
// signal in the window but had ZERO rows clear the quality gate — "attention
// without verified coverage". Served by GET /api/v2/attention/coverage-gaps,
// global or scoped to one country. Same definition the Brief renders.

export interface GapReceipt {
  headline: string
  source: string | null
  url: string | null
  gate_score: number
  /** How the engine assigned this row to the category — the honest basis the
   *  card renders instead of the raw score (W5 "precision theatre"). Absent on
   *  older payloads, which fall back to naming the tier. */
  method?: 'lexicon' | 'embedding' | null
}

export interface CoverageGap {
  slug: string
  label: string
  raw_signals: number
  verified: number
  scored: number
  status: 'gate_pending' | 'none_verified'
  extended_receipts?: GapReceipt[]
}

export interface CoverageGapsData {
  contract: string
  scope: 'global' | 'country'
  country: string | null
  hours: number
  /** Machine-readable state. NEVER infer this from `notes` prose or gaps.length.
   *  ok = gaps returned · empty = query ran clean, genuinely none ·
   *  degraded = query did not run or failed. */
  status: 'ok' | 'empty' | 'degraded'
  /** Raw-signal floor the scope used (20 global / 8 country by default), so the
   *  UI can state the threshold instead of implying one. */
  floor: number | null
  gaps: CoverageGap[]
  notes: string[]
}

export const COVERAGE_GAPS_CONTRACT = 'coverage-gaps-v0'

export function coverageGapsUrl(country?: string | null, hours = 24): string {
  const params = new URLSearchParams()
  if (country) params.set('country', country)
  params.set('hours', String(hours))
  return `/api/v2/attention/coverage-gaps?${params.toString()}`
}

/** Contract-validated parse. Returns null for anything we do not recognise —
 *  the caller renders an honest empty state rather than guessing. */
export function parseCoverageGaps(payload: unknown): CoverageGapsData | null {
  if (!payload || typeof payload !== 'object') return null
  const p = payload as Record<string, unknown>
  if (p.contract !== COVERAGE_GAPS_CONTRACT) return null
  const gaps = Array.isArray(p.gaps) ? (p.gaps as CoverageGap[]) : []
  // Unknown/missing status degrades CONSERVATIVELY: without the server saying
  // "empty" we must not render an honest-empty claim we cannot back.
  const status: CoverageGapsData['status'] =
    p.status === 'ok' || p.status === 'empty' || p.status === 'degraded'
      ? p.status
      : (gaps.length > 0 ? 'ok' : 'degraded')
  return {
    contract: COVERAGE_GAPS_CONTRACT,
    scope: p.scope === 'country' ? 'country' : 'global',
    country: typeof p.country === 'string' ? p.country : null,
    hours: typeof p.hours === 'number' ? p.hours : 24,
    status,
    floor: typeof p.floor === 'number' ? p.floor : null,
    gaps,
    notes: Array.isArray(p.notes) ? (p.notes as string[]) : [],
  }
}

/** Shared denominator for the gap bars — at least 1 so we never divide by zero. */
export function maxGapRaw(gaps: CoverageGap[]): number {
  return Math.max(1, ...gaps.map(g => g.raw_signals))
}
