import { describe, it, expect } from 'vitest'
import { anomalyMultiplierBasis, volumeZBasis } from './volumeBasis'

// Cold-user probe, pair (c): the country panel printed "12× above 7-day
// baseline" and "(z: 71.2)" side by side. They are TWO DIFFERENT QUANTITIES
// from TWO endpoints — a ratio over a fixed 24h window against an 8-day daily
// average, and a z-score over the panel's window against a 7-day raw baseline —
// and neither said so. Council doctrine: a labeled divergence invites
// reconciliation, a mislabel forecloses it.
describe('anomalyMultiplierBasis', () => {
  it('names the REAL baseline length served by the endpoint, never a hardcoded 7', () => {
    // The SQL window is 8 days; the copy said "7-day baseline" for months.
    const b = anomalyMultiplierBasis({ multiplier: 12.4, baselineDays: 8, daysObserved: 8 })
    expect(b.text).toBe('12× vs 8-day baseline')
    expect(b.tip).toMatch(/8-day|8 day/)
    expect(b.tip).not.toMatch(/7-day/)
  })

  it('falls back to "recent baseline" when the endpoint does not serve the length', () => {
    // Absence stays absence: inventing "7-day" is the bug being fixed.
    const b = anomalyMultiplierBasis({ multiplier: 12.4 })
    expect(b.text).toBe('12× vs recent baseline')
    expect(b.tip).toMatch(/recent baseline/i)
    expect(b.tip).not.toMatch(/\d+-day baseline/)
  })

  it('tip states it is a RATIO on a fixed 24h window, distinct from the z-score', () => {
    const b = anomalyMultiplierBasis({ multiplier: 12.4, baselineDays: 8 })
    expect(b.tip).toMatch(/ratio/i)
    expect(b.tip).toMatch(/24[- ]?h/i)
    expect(b.tip).toMatch(/divided by|÷/)
    // The reconciliation half: it must name the other number on the screen.
    expect(b.tip).toMatch(/z-score/i)
    expect(b.tip).toMatch(/different/i)
  })

  it('reports how many days were actually observed when the baseline is short', () => {
    const b = anomalyMultiplierBasis({ multiplier: 12.4, baselineDays: 8, daysObserved: 3 })
    expect(b.tip).toMatch(/3 of 8 days|only 3 days/i)
  })

  it('keeps a decimal below 10× — rounding 1.4 to "1×" would erase the anomaly', () => {
    expect(anomalyMultiplierBasis({ multiplier: 1.4, baselineDays: 8 }).text)
      .toBe('1.4× vs 8-day baseline')
    expect(anomalyMultiplierBasis({ multiplier: 9.94, baselineDays: 8 }).text)
      .toBe('9.9× vs 8-day baseline')
  })

  it('a legitimate 0 multiplier renders, it does not vanish', () => {
    const b = anomalyMultiplierBasis({ multiplier: 0, baselineDays: 8 })
    expect(b.text).toBe('0.0× vs 8-day baseline')
  })

  it('missing multiplier degrades to null — never a fabricated number', () => {
    expect(anomalyMultiplierBasis({ multiplier: null }).text).toBeNull()
    expect(anomalyMultiplierBasis({ multiplier: undefined }).text).toBeNull()
    expect(anomalyMultiplierBasis({ multiplier: Number.NaN }).text).toBeNull()
  })
})

describe('volumeZBasis', () => {
  it('prints the precise z when the baseline is sound, and names its own basis', () => {
    const b = volumeZBasis({ zScore: 3.2, windowLabel: '24h', baselineDays: 7, daysObserved: 7 })
    expect(b.text).toBe('z: 3.2')
    expect(b.precise).toBe(true)
    expect(b.tip).toMatch(/24h/)
    expect(b.tip).toMatch(/7[- ]day/)
    // Must state it is NOT the same measure as the × badge.
    expect(b.tip).toMatch(/not the same|different (measure|statistic)/i)
    expect(b.tip).toMatch(/multiplier|×/i)
  })

  it('THIN BASELINE: degrades to a direction, never a precise 71.2', () => {
    // East-Timor class: a 2-day baseline on a handful of signals makes sigma
    // meaningless, so "z: 71.2" is a fabricated precision.
    const b = volumeZBasis({ zScore: 71.2, thinBaseline: true, daysObserved: 2, windowLabel: '24h' })
    expect(b.text).toBe('z: high (thin baseline)')
    expect(b.precise).toBe(false)
    expect(b.text).not.toMatch(/71/)
    expect(b.tip).toMatch(/2 days?/)
    expect(b.tip).toMatch(/not meaningful|unreliable|cannot be trusted/i)
  })

  it('THIN BASELINE below typical reads low, and an unremarkable one reads n/a', () => {
    expect(volumeZBasis({ zScore: -4, thinBaseline: true, daysObserved: 2 }).text)
      .toBe('z: low (thin baseline)')
    expect(volumeZBasis({ zScore: 0.4, thinBaseline: true, daysObserved: 2 }).text)
      .toBe('z: n/a (thin baseline)')
  })

  it('a legitimate z of 0 renders — the `||` bug made it vanish', () => {
    const b = volumeZBasis({ zScore: 0, windowLabel: '24h', baselineDays: 7 })
    expect(b.text).toBe('z: 0.0')
    expect(b.precise).toBe(true)
  })

  it('missing z-score degrades to null, thin baseline or not', () => {
    expect(volumeZBasis({ zScore: null }).text).toBeNull()
    expect(volumeZBasis({ zScore: undefined }).text).toBeNull()
    expect(volumeZBasis({ zScore: null, thinBaseline: true, daysObserved: 2 }).text).toBeNull()
  })

  it('missing baseline metadata still explains the basis in words it can stand behind', () => {
    const b = volumeZBasis({ zScore: 3.2 })
    expect(b.text).toBe('z: 3.2')
    expect(b.tip).toMatch(/baseline/i)
    // Its OWN basis is described without inventing numbers. (The tip may still
    // state the multiplier badge's fixed 24h window — that one is genuinely
    // hard-coded server-side, and naming it is the whole point of the contrast.)
    expect(b.tip).toMatch(/the current window/i)
    expect(b.tip).not.toMatch(/\d+-day baseline/)
    expect(b.tip).not.toMatch(/\d+ of \d+ days/)
  })
})
