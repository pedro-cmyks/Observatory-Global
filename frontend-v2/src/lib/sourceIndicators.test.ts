import { describe, it, expect } from 'vitest'
import { describeDiversity, describeQuality } from './sourceIndicators'

// Cold-user probe, pair (e): "Source Diversity 98" sat next to "Source Quality
// 30" with no inputs shown, so the reader could not tell whether the two
// composites contradicted each other. Measured on prod (East Timor): diversity
// 99 from 48 outlets over 53 signals (top outlet 11%), quality 30 from 0
// allowlisted / 48 unknown. They ARE consistent — many outlets, none
// recognized — but only the inputs make that legible.
describe('describeDiversity', () => {
  it('prints outlet count and the top outlet share of the FULL window population', () => {
    const d = describeDiversity({ score: 99, unique_count: 48, total_signals: 53, top_domains: [['tribunnews.com', 6], ['antaranews.com', 4]] })
    expect(d.inline).toBe('48 outlets · top tribunnews.com 11%')
    expect(d.tip).toMatch(/48/)
    expect(d.tip).toMatch(/53/)
  })

  it('tip names both components and says the base is the window, not the receipts on screen', () => {
    const d = describeDiversity({ score: 99, unique_count: 48, total_signals: 53, top_domains: [['tribunnews.com', 6]] })
    expect(d.tip).toMatch(/even|spread|concentrat/i)
    expect(d.tip).toMatch(/how many .*outlets|outlet count|number of outlets/i)
    // The probe's "7 of 10 from one domain" came from the 10-item receipt list —
    // a different population. The tip must say so.
    expect(d.tip).toMatch(/receipt|listed below|shown below|sample/i)
  })

  it('zero signals never divides by zero — the share is simply omitted', () => {
    const d = describeDiversity({ score: 0, unique_count: 0, total_signals: 0, top_domains: [] })
    expect(d.inline).toBe('0 outlets')
    expect(d.inline).not.toMatch(/NaN|Infinity|%/)
    expect(d.tip).toBeTruthy()
  })

  it('missing top_domains degrades to the outlet count alone', () => {
    expect(describeDiversity({ score: 80, unique_count: 12, total_signals: 40 }).inline).toBe('12 outlets')
    expect(describeDiversity({ score: 80, unique_count: 12, total_signals: 40, top_domains: [] }).inline).toBe('12 outlets')
  })

  it('a fully absent payload degrades to no inline note at all', () => {
    expect(describeDiversity({}).inline).toBeNull()
    expect(describeDiversity({ score: 50 }).inline).toBeNull()
  })

  it('a single outlet carrying everything reads as 100%', () => {
    const d = describeDiversity({ score: 10, unique_count: 1, total_signals: 20, top_domains: [['rt.com', 20]] })
    expect(d.inline).toBe('1 outlet · top rt.com 100%')
  })
})

describe('describeQuality', () => {
  it('prints recognized-of-total so the score is auditable', () => {
    const q = describeQuality({ score: 30, allowlisted_count: 0, denylisted_count: 0, unknown_count: 48 })
    expect(q.inline).toBe('0 of 48 outlets recognized')
  })

  it('ALL-UNKNOWN is unclassified, not "Poor" — an allowlist gap is not a verdict', () => {
    // The honesty fix: a low score driven purely by outlets we do not recognize
    // is a coverage gap in OUR allowlist, never a measured judgement on a
    // country's press corps.
    const q = describeQuality({ score: 30, allowlisted_count: 0, denylisted_count: 0, unknown_count: 48 })
    expect(q.unclassified).toBe(true)
    expect(q.verdict).toBe('unclassified')
    expect(q.tip).toMatch(/do not recognize|not recognized|unrecognized|allowlist/i)
    expect(q.tip).toMatch(/not a (claim|judgement|judgment)|does not mean/i)
    expect(q.tip).not.toMatch(/poor/i)
  })

  it('any allowlisted outlet makes the score earned again', () => {
    const q = describeQuality({ score: 62, allowlisted_count: 12, denylisted_count: 0, unknown_count: 30 })
    expect(q.unclassified).toBe(false)
    expect(q.verdict).toBeNull()
    expect(q.inline).toBe('12 of 42 outlets recognized')
  })

  it('a denylisted outlet is a MEASURED judgement — never unclassified', () => {
    const q = describeQuality({ score: 20, allowlisted_count: 0, denylisted_count: 3, unknown_count: 40 })
    expect(q.unclassified).toBe(false)
    expect(q.inline).toBe('0 of 43 outlets recognized')
    expect(q.tip).toMatch(/3/)
    expect(q.tip).toMatch(/deny|flagged|known-?bad|low-?credibility/i)
  })

  it('no outlets at all: no inline note, no unearned verdict', () => {
    const q = describeQuality({ score: 30, allowlisted_count: 0, denylisted_count: 0, unknown_count: 0 })
    expect(q.inline).toBeNull()
    expect(q.unclassified).toBe(false)
  })

  it('a fully absent payload degrades without throwing', () => {
    const q = describeQuality({})
    expect(q.inline).toBeNull()
    expect(q.unclassified).toBe(false)
    expect(q.tip).toBeTruthy()
  })
})
