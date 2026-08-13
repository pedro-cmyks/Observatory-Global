/**
 * Markets strip freshness (W5, re-judge §3 / §5: "LAST CLOSE AUG 11" on Aug 13).
 *
 * DIAGNOSIS (measured 2026-08-13, prod `/api/v2/markets` + the M1 cron):
 * the accumulation cron is ALIVE — `com.atlas.markets-accumulate` is loaded,
 * last exit 0, ran the night before and pushed all 212 symbols. The data is as
 * fresh as Yahoo gives it. Two things made it read as rot:
 *
 *   1. The strip printed a bare date and no AGE, so a reader on a Thursday
 *      could not tell "the market simply has not closed since" from "our
 *      pipeline died three days ago". Both look like an old date.
 *   2. The basket is MIXED — WTI and the dollar index last closed Aug 11 while
 *      gold, copper, the S&P and the VIX closed Aug 12 — and the endpoint's
 *      `as_of` is a `max()` over them. One stamp was standing in for six
 *      instruments that do not share it.
 *
 * So the fix is not a data fix, it is a truth-telling fix: state the age, name
 * the oldest member when the basket disagrees with itself, and reserve the
 * loud "stale" only for a lag no weekend can explain.
 *
 * Pure: the clock is injected. All date maths is done in UTC on the `YYYY-MM-DD`
 * close dates so a viewer's timezone can never shift a close by a day.
 */

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/**
 * A weekend puts three days between Friday's close and Monday morning; a
 * Monday holiday puts four. Five is the first age no market calendar explains,
 * so it is the first age we are entitled to call stale.
 */
const STALE_AFTER_DAYS = 5

export interface FreshnessInstrument {
  symbol?: string
  last_close_at?: string | null
}

export interface MarketFreshnessInput {
  instruments: readonly FreshnessInstrument[]
  /** The endpoint's own `as_of` — used only as a fallback, never over the rows. */
  asOf?: string | null
  now: Date
}

export interface MarketFreshness {
  /** Newest close in the basket, `YYYY-MM-DD`, or null when nothing is stamped. */
  newest: string | null
  /** Oldest close in the basket, `YYYY-MM-DD`, or null. */
  oldest: string | null
  /** True when the basket does not share a single close date. */
  mixed: boolean
  /** Whole days between the newest close and now; null when unmeasured. */
  ageDays: number | null
  tone: 'fresh' | 'lagging' | 'stale' | 'unknown'
  /** Convenience for the loud case — the one that must be prominent. */
  stale: boolean
  /** "Aug 12" — the newest close, formatted without timezone drift. */
  stamp: string | null
  /** "closed today" / "1 day ago" / "6 days ago — stale" / honest unknown. */
  ageNote: string
  /** Names the oldest member when the basket disagrees; null when it agrees. */
  mixedNote: string | null
}

/** `YYYY-MM-DD` → UTC-midnight epoch ms, or null when unparseable. */
function dayMs(iso: string | null | undefined): number | null {
  if (!iso || typeof iso !== 'string') return null
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso.trim())
  if (!m) return null
  const t = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  return Number.isFinite(t) ? t : null
}

/** `YYYY-MM-DD` → "Aug 12", built from the string so no timezone can shift it. */
function formatDay(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (!m) return iso
  const month = MONTHS[Number(m[2]) - 1]
  return month ? `${month} ${Number(m[3])}` : iso
}

export function marketFreshness({ instruments, asOf, now }: MarketFreshnessInput): MarketFreshness {
  const dated = instruments
    .map(i => i.last_close_at)
    .filter((d): d is string => dayMs(d) !== null)

  // The endpoint's as_of is a fallback ONLY. The instrument rows are the
  // evidence; a stamp that outruns every row it summarises is exactly the
  // flattening this function exists to stop.
  if (dated.length === 0) {
    const fb = dayMs(asOf) !== null ? (asOf as string) : null
    if (fb) dated.push(fb)
  }

  if (dated.length === 0) {
    return {
      newest: null, oldest: null, mixed: false, ageDays: null,
      tone: 'unknown', stale: false, stamp: null,
      ageNote: 'last close not stamped — freshness unknown',
      mixedNote: null,
    }
  }

  const sorted = [...dated].sort((a, b) => (dayMs(a)! - dayMs(b)!))
  const oldest = sorted[0]
  const newest = sorted[sorted.length - 1]
  const mixed = oldest !== newest

  const nowDay = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())
  // Clamp at 0: a close stamped ahead of our clock is a data oddity, never a
  // negative age printed at the reader.
  const ageDays = Math.max(0, Math.round((nowDay - dayMs(newest)!) / 86_400_000))

  const tone: MarketFreshness['tone'] =
    ageDays <= 1 ? 'fresh' : ageDays < STALE_AFTER_DAYS ? 'lagging' : 'stale'

  const elapsed = ageDays === 0
    ? 'closed today'
    : `${ageDays} day${ageDays === 1 ? '' : 's'} ago`
  const ageNote = tone === 'stale'
    ? `${elapsed} — stale, longer than a market weekend explains`
    : elapsed

  return {
    newest, oldest, mixed, ageDays, tone,
    stale: tone === 'stale',
    stamp: formatDay(newest),
    ageNote,
    // Terse on the divider (which is already carrying the overlay caveat); the
    // full sentence lives in the tooltip the caller builds from this.
    mixedNote: mixed ? `oldest ${formatDay(oldest)}` : null,
  }
}
