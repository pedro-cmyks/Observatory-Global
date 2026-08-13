import { describe, it, expect } from 'vitest'
import { marketFreshness, type FreshnessInstrument } from './marketsFreshness'

// The world basket exactly as prod served it on 2026-08-13 — the judge's case.
// Four instruments closed Aug 12, WTI and the dollar index closed Aug 11, and
// the strip flattened all six into one `max()` stamp with no age at all.
const MIXED: FreshnessInstrument[] = [
  { symbol: 'CL=F', last_close_at: '2026-08-11' },
  { symbol: 'GC=F', last_close_at: '2026-08-12' },
  { symbol: 'HG=F', last_close_at: '2026-08-12' },
  { symbol: '^GSPC', last_close_at: '2026-08-12' },
  { symbol: 'DX-Y.NYB', last_close_at: '2026-08-11' },
  { symbol: '^VIX', last_close_at: '2026-08-12' },
]

const at = (iso: string) => new Date(iso)

describe('marketFreshness — the strip states its own age', () => {
  it('measures age in whole days from the NEWEST close', () => {
    const f = marketFreshness({ instruments: MIXED, asOf: '2026-08-12', now: at('2026-08-13T13:00:00Z') })
    expect(f.newest).toBe('2026-08-12')
    expect(f.ageDays).toBe(1)
    expect(f.ageNote).toMatch(/1 day ago/)
  })

  it('says "today" / "yesterday" instead of a bare count where that reads better', () => {
    expect(marketFreshness({ instruments: MIXED, asOf: '2026-08-12', now: at('2026-08-12T20:00:00Z') }).ageNote)
      .toMatch(/today/i)
    expect(marketFreshness({ instruments: MIXED, asOf: '2026-08-12', now: at('2026-08-13T09:00:00Z') }).ageNote)
      .toMatch(/1 day ago/)
  })

  // The judge's exact complaint: Aug 11 shown on Aug 13, unexplained. That was
  // the basket BEFORE the Aug-12 closes landed — every member still on Aug 11.
  it("names the age for the judge's two-day case rather than leaving a bare date", () => {
    const judgeBasket = MIXED.map(i => ({ ...i, last_close_at: '2026-08-11' }))
    const f = marketFreshness({ instruments: judgeBasket, asOf: '2026-08-11', now: at('2026-08-13T13:00:00Z') })
    expect(f.ageDays).toBe(2)
    expect(f.ageNote).toContain('2 days ago')
    expect(f.stamp).toBe('Aug 11')
  })
})

describe('marketFreshness — tone separates market lag from a dead pipeline', () => {
  it('is fresh when the last close is today or yesterday', () => {
    expect(marketFreshness({ instruments: MIXED, asOf: '2026-08-12', now: at('2026-08-12T20:00:00Z') }).tone).toBe('fresh')
    expect(marketFreshness({ instruments: MIXED, asOf: '2026-08-12', now: at('2026-08-13T13:00:00Z') }).tone).toBe('fresh')
  })

  // A Monday morning legitimately shows Friday's close. Calling that "stale"
  // would cry wolf on correct market behaviour.
  it('is merely lagging across a weekend or a long weekend', () => {
    for (const days of [2, 3, 4]) {
      const now = new Date(Date.UTC(2026, 7, 12 + days, 13))
      const f = marketFreshness({ instruments: MIXED, asOf: '2026-08-12', now })
      expect(f.tone, `${days} days`).toBe('lagging')
      expect(f.stale, `${days} days`).toBe(false)
    }
  })

  // Beyond any weekend + holiday, the lag is ours, not the market's.
  it('is STALE past five days — longer than any weekend can explain', () => {
    const f = marketFreshness({ instruments: MIXED, asOf: '2026-08-12', now: at('2026-08-17T13:00:00Z') })
    expect(f.ageDays).toBe(5)
    expect(f.tone).toBe('stale')
    expect(f.stale).toBe(true)
    expect(f.ageNote).toMatch(/stale/i)
  })
})

describe('marketFreshness — a mixed basket is not flattened into one date', () => {
  it('reports the oldest member when the basket does not share one close', () => {
    const f = marketFreshness({ instruments: MIXED, asOf: '2026-08-12', now: at('2026-08-13T13:00:00Z') })
    expect(f.mixed).toBe(true)
    expect(f.oldest).toBe('2026-08-11')
    expect(f.mixedNote).toContain('Aug 11')
    expect(f.mixedNote).toMatch(/not all|some|oldest/i)
  })

  it('draws no mixed note when every instrument shares the same close', () => {
    const f = marketFreshness({
      instruments: [
        { symbol: 'A', last_close_at: '2026-08-12' },
        { symbol: 'B', last_close_at: '2026-08-12' },
      ],
      asOf: '2026-08-12',
      now: at('2026-08-13T13:00:00Z'),
    })
    expect(f.mixed).toBe(false)
    expect(f.mixedNote).toBeNull()
  })

  // The stamp must never claim a freshness no instrument actually has.
  it('derives the stamp from the instruments, not from a stale as_of', () => {
    const f = marketFreshness({ instruments: MIXED, asOf: null, now: at('2026-08-13T13:00:00Z') })
    expect(f.newest).toBe('2026-08-12')
    expect(f.stamp).toBe('Aug 12')
  })
})

describe('marketFreshness — degrades honestly rather than printing junk', () => {
  it('returns an unmeasured reading when nothing carries a close date', () => {
    const f = marketFreshness({ instruments: [], asOf: null, now: at('2026-08-13T13:00:00Z') })
    expect(f.tone).toBe('unknown')
    expect(f.stamp).toBeNull()
    expect(f.ageDays).toBeNull()
    expect(f.ageNote).toMatch(/unknown|not stamped/i)
  })

  it('ignores unparseable dates instead of producing NaN or Invalid Date', () => {
    const f = marketFreshness({
      instruments: [
        { symbol: 'A', last_close_at: 'not-a-date' },
        { symbol: 'B', last_close_at: '2026-08-12' },
      ],
      asOf: 'garbage',
      now: at('2026-08-13T13:00:00Z'),
    })
    expect(f.newest).toBe('2026-08-12')
    expect(f.stamp).toBe('Aug 12')
    expect(f.ageNote).not.toMatch(/NaN|Invalid/)
  })

  it('never reports a negative age when a close is stamped ahead of the clock', () => {
    const f = marketFreshness({
      instruments: [{ symbol: 'A', last_close_at: '2026-08-20' }],
      asOf: '2026-08-20',
      now: at('2026-08-13T13:00:00Z'),
    })
    expect(f.ageDays).toBe(0)
    expect(f.tone).toBe('fresh')
  })
})
