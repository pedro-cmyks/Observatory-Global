import { describe, it, expect } from 'vitest'
import { changeWindowLabel, changeWindowTip, formatChangePct } from './markets'

// Cold-user probe 2026-08-12: the Brief summary card printed `WTI ▲ +20.10%`
// with no window, and it read as a one-day move. The window lives only in the
// drill chart. Same discipline as council N19 (countQualifier): a number never
// renders without the window it belongs to — and the window is the MEASURED
// one (the served series length), never a hardcoded default.
describe('changeWindowLabel', () => {
  it('labels the full 30-close series', () => {
    expect(changeWindowLabel({ spark_30d: new Array(30).fill(1) })).toBe('30 sessions')
  })

  it('labels a SHORT series by what was actually served, never "30"', () => {
    // A newly tracked instrument has fewer closes; hardcoding 30 would be the
    // exact N19 sin (printing a window the number does not belong to).
    expect(changeWindowLabel({ spark_30d: new Array(12).fill(1) })).toBe('12 sessions')
  })

  it('says "2 sessions" (plural) and "1 session" only where a delta could exist', () => {
    expect(changeWindowLabel({ spark_30d: [1, 2] })).toBe('2 sessions')
  })

  it('returns null when there is no delta to label', () => {
    expect(changeWindowLabel({ spark_30d: [1] })).toBeNull()
    expect(changeWindowLabel({ spark_30d: [] })).toBeNull()
    expect(changeWindowLabel({ spark_30d: null })).toBeNull()
    expect(changeWindowLabel({})).toBeNull()
  })

  it('counts only finite closes — a null/NaN hole never inflates the window', () => {
    expect(changeWindowLabel({
      spark_30d: [1, NaN as unknown as number, 3, null as unknown as number, 5],
    })).toBe('3 sessions')
  })

  it('is stated in SESSIONS, not days — the series is trading closes', () => {
    // push_atlas_db.latest_snapshots takes the trailing N rows of
    // market_price_daily (trading days), so 30 closes span ~6 calendar weeks.
    // "30d" would read as calendar days and be wrong by ~2x.
    const label = changeWindowLabel({ spark_30d: new Array(30).fill(1) })
    expect(label).not.toMatch(/\bd\b|day/)
    expect(label).toMatch(/session/)
  })
})

describe('changeWindowTip', () => {
  it('states first-vs-last over the measured window and refuses the daily reading', () => {
    const tip = changeWindowTip({ spark_30d: new Array(30).fill(1) })
    expect(tip).toMatch(/30 sessions/)
    expect(tip).toMatch(/not.*(today|one-day|single)/i)
  })

  it('has no tip when there is no window to state', () => {
    expect(changeWindowTip({ spark_30d: [1] })).toBeNull()
  })
})

describe('formatChangePct (unchanged contract)', () => {
  it('keeps the signed two-decimal form the tile prints', () => {
    expect(formatChangePct(20.1)).toBe('+20.10%')
    expect(formatChangePct(-7.11)).toBe('-7.11%')
    expect(formatChangePct(null)).toBeNull()
  })
})

// X4 (2026-08-13) — blind college C5. The LABEL keeps "sessions" (W5 pinned
// that: a bare "30 days" reads as calendar days and is wrong by ~2x), so the
// tip is where the word gets learnable. Additive — the tip loses nothing.
describe('changeWindowTip — the trade word, glossed (X4)', () => {
  it('says what a session is, without giving up the measured window', () => {
    const tip = changeWindowTip({ spark_30d: new Array(21).fill(1) })
    expect(tip).toMatch(/21 sessions/)
    expect(tip).toMatch(/21 trading days/)
    expect(tip).toMatch(/not a claim that news moved it/i)
  })

  it('is singular where singular is correct', () => {
    expect(changeWindowTip({ spark_30d: [1, 2] })).toMatch(/2 trading days/)
  })
})
