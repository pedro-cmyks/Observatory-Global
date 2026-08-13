// L4 markets — typed client for the DESCRIPTIVE product surface.
//
// Consumes GET /api/v2/markets (contract markets-descriptive-v0, see
// backend/app/routers/markets.py and docs/research/markets-l4/
// 2026-07-21-markets-relational-axis-design.md §7/§8). This is a DORMANT/
// DESCRIPTIVE skeleton: it serves level + trend only — NEVER a correlation,
// lead-lag, "news moved this", or a trade signal. The discovered-relation tier
// stays a reserved-but-dark slot (`relation_status: pending-validation-226`)
// until the #226 event study clears at ~150 trading days (~Oct 2026).
//
// Honest states are first-class here: `failed` (the fetch itself died — network,
// 404 before deploy, timeout) is DISTINCT from a 200 `{degraded:true}` response
// and from an instrument whose price is still pending. An error-state is never
// an empty-state (design §7).

import { useEffect, useState } from 'react'
import { tradingWindowPhrase } from './statPhrases'

export type MarketRole = 'currency' | 'index' | 'champion' | 'export-commodity'

export interface MarketInstrument {
  symbol: string
  label: string
  asset_class: string
  role: MarketRole | null
  last_close: number | null
  last_close_at: string | null
  spark_30d: number[] | null
  change_pct: number | null
  price_pending: boolean
}

export interface MarketCountry {
  country_code: string
  has_own_instruments: boolean
  instruments: MarketInstrument[]
}

export interface MarketsData {
  contract: string
  tier: string
  /** 'pending-validation-226' (dark relation slot) | 'measured' (never, until #226 clears). */
  relation_status: string
  honesty: string
  as_of: string | null
  world: MarketInstrument[]
  country: MarketCountry | null
  degraded: boolean
  reason?: string
}

export const MARKETS_CONTRACT = 'markets-descriptive-v0'
export const RELATION_PENDING = 'pending-validation-226'

/** The reserved-but-dark relation slot copy — a greyed absence, never a number. */
export const RELATION_PENDING_TEXT =
  'relation analysis — pending validation (#226, re-run ~Oct 2026)'

/** Persistent no-trade-signal microcopy (design §7/§8). */
export const NOT_ADVICE_TEXT = 'descriptive context — not investment advice'

export function marketsUrl(country?: string | null): string {
  const cc = country ? country.toUpperCase() : null
  return cc ? `/api/v2/markets?country=${encodeURIComponent(cc)}` : '/api/v2/markets'
}

/**
 * Best-effort fetch of the descriptive markets contract. Resolves `null` on ANY
 * failure or on a route that is not deployed yet (dev may 429 / 404) — absence is
 * honest. A 200 `{degraded:true}` response resolves as data (the caller reads
 * `.degraded`), because a degraded receipt is meaningfully different from a dead
 * fetch.
 */
export async function fetchMarkets(
  country?: string | null,
  signal?: AbortSignal,
): Promise<MarketsData | null> {
  try {
    const r = await fetch(marketsUrl(country), { signal })
    if (!r.ok) return null
    const d = await r.json()
    if (!d || typeof d !== 'object' || !Array.isArray((d as MarketsData).world)) return null
    return d as MarketsData
  } catch {
    return null
  }
}

export interface UseMarketsState {
  data: MarketsData | null
  loading: boolean
  /** The fetch itself failed (network / not-deployed / timeout). Distinct from a
   *  200 degraded payload (`data.degraded`) — error-state ≠ empty-state. */
  failed: boolean
}

/**
 * Live descriptive-markets hook, copying the best-effort fetch idiom used across
 * Atlas (AbortController + timeout + silent-degrade). Re-fetches when the scoped
 * country changes.
 */
export function useMarkets(country?: string | null): UseMarketsState {
  const cc = country ? country.toUpperCase() : null
  const [data, setData] = useState<MarketsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let alive = true
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), 12000)
    setLoading(true)
    setFailed(false)
    fetchMarkets(cc, ctrl.signal)
      .then(d => {
        if (!alive) return
        if (d) setData(d)
        else setFailed(true)
      })
      .finally(() => {
        if (!alive) return
        clearTimeout(timer)
        setLoading(false)
      })
    return () => {
      alive = false
      clearTimeout(timer)
      ctrl.abort()
    }
  }, [cc])

  return { data, loading, failed }
}

// ---- pure formatting helpers (unit-aware, descriptive only) ----

export type MarketDirection = 'up' | 'down' | 'flat'

/** Direction from the trailing net change. A |change| below 0.005% reads flat —
 *  it must NEVER be forced to up/down (no false signal). */
export function changeDirection(change_pct: number | null | undefined): MarketDirection {
  if (change_pct == null || !isFinite(change_pct) || Math.abs(change_pct) < 0.005) return 'flat'
  return change_pct > 0 ? 'up' : 'down'
}

export function formatChangePct(change_pct: number | null | undefined): string | null {
  if (change_pct == null || !isFinite(change_pct)) return null
  const sign = change_pct > 0 ? '+' : ''
  return `${sign}${change_pct.toFixed(2)}%`
}

/**
 * The window a `change_pct` belongs to, MEASURED from the served series.
 *
 * Cold-user probe 2026-08-12: the Brief card printed `WTI ▲ +20.10%` and it
 * read as a one-day move; the window (`· 30d`) appeared only after drilling
 * into the full chart. Council N19's discipline applies verbatim — a number
 * never renders without its window, and the window is the one the number
 * actually belongs to, never a hardcoded default.
 *
 * Stated in SESSIONS, not days: `markets/push_atlas_db.latest_snapshots` takes
 * the trailing N ROWS of `market_price_daily` (trading days), so 30 closes span
 * roughly six calendar weeks. Printing "30d" would swap a right label for a
 * wrong one. A short/patchy series labels itself honestly ("12 sessions").
 *
 * Returns null when fewer than two finite closes exist — there is no delta to
 * label, and the tile prints no percentage either.
 */
export function changeWindowLabel(
  inst: Pick<MarketInstrument, 'spark_30d'> | { spark_30d?: number[] | null },
): string | null {
  const clean = (inst.spark_30d ?? []).filter(v => typeof v === 'number' && isFinite(v))
  if (clean.length < 2) return null
  return `${clean.length} session${clean.length === 1 ? '' : 's'}`
}

/** Tip for the window chip: what the delta spans, and what it is NOT. */
export function changeWindowTip(
  inst: Pick<MarketInstrument, 'spark_30d'> | { spark_30d?: number[] | null },
): string | null {
  const label = changeWindowLabel(inst)
  if (!label) return null
  // X4 (2026-08-13, blind college C5): "sessions" is trade vocabulary. The
  // LABEL keeps it — W5 pinned that deliberately, because a bare "30 days"
  // reads as calendar days and is wrong by ~2x — so the word is glossed here,
  // where the tile's window is already explained. Nothing is given up: the tip
  // still carries the measured window and the two refusals.
  const plainWindow = tradingWindowPhrase(
    (inst.spark_30d ?? []).filter(v => typeof v === 'number' && isFinite(v)).length,
  )
  const gloss = plainWindow ? ` — that is ${plainWindow} the market was open` : ''
  return `Net change across the last ${label} of daily closes, first vs last${gloss}. NOT today's move, and not a claim that news moved it.`
}

/** A neutral triangle glyph for direction — redundant with color + the signed %,
 *  so color is never the sole channel (CVD safety, design §7). */
export function directionGlyph(dir: MarketDirection): string {
  return dir === 'up' ? '▲' : dir === 'down' ? '▼' : '·'
}

/** Format a last-close level with unit-appropriate precision. FX pairs carry more
 *  decimals; large index levels carry thousands separators. Returns an em-dash when
 *  the price is pending (never a fabricated 0.00). */
export function formatLevel(value: number | null | undefined): string {
  if (value == null || !isFinite(value)) return '—'
  const abs = Math.abs(value)
  if (abs >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 0 })
  if (abs >= 100) return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (abs >= 1) return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return value.toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 })
}

/** A short, inline unit tag stating what the number IS (design §7: unit stated
 *  inline). Descriptive labels only — no forward meaning. */
export function unitTag(inst: Pick<MarketInstrument, 'asset_class' | 'role'>): string {
  const ac = (inst.asset_class || '').toLowerCase()
  if (inst.role === 'currency' || ac === 'fx' || ac === 'currency') return 'FX'
  if (inst.role === 'index' || ac === 'index' || ac === 'etf') return 'INDEX'
  if (ac === 'commodity' || inst.role === 'export-commodity') return 'COMMODITY'
  if (inst.role === 'champion' || ac === 'equity' || ac === 'stock') return 'EQUITY'
  if (ac === 'volatility' || ac === 'vol') return 'VOL'
  return (inst.asset_class || '').toUpperCase() || 'MKT'
}
