import { describe, it, expect } from 'vitest'
import { fieldCoverageReadout } from './fieldCoverage'

// Cold-user probe 2026-08-12 §4/§7: the console header printed
// "175 countries · 100,587 signals" while the console dock and the Brief
// printed "218 · 109,632" on the same view. Traced: /api/v2/nodes is a MAP
// endpoint that silently drops every country it cannot plot and then totals
// only what survived, so a cartographic constraint was leaking into a
// statistical readout. The backend now discloses both numbers; this helper
// makes the header print the real base and name what the map could not draw.
describe('fieldCoverageReadout', () => {
  const coverage = {
    basis: 'hourly_rollup',
    label: 'hourly rollup',
    note: 'Counted over the hourly country rollup. 43 country code(s) carrying 9,045 signals have no map coordinates and are not drawn; the counted totals include them.',
    counted_countries: 218,
    counted_signals: 109632,
    mapped_countries: 175,
    mapped_signals: 100587,
    unmapped_countries: 43,
    unmapped_signals: 9045,
  }

  it('prints the counted base, not the plotted subset', () => {
    const r = fieldCoverageReadout(coverage, [{ signalCount: 1 }, { signalCount: 2 }])
    expect(r.countries).toBe(218)
    expect(r.signals).toBe(109632)
    expect(r.label).toBe('218 countries · 109,632 signals')
  })

  it('discloses the unmapped remainder in the tip so the map gap is legible', () => {
    const r = fieldCoverageReadout(coverage, [])
    expect(r.tip).toMatch(/43/)
    expect(r.tip).toMatch(/not drawn|no map coordinates/i)
  })

  it('says nothing about drawing when every counted country is mappable', () => {
    const clean = {
      ...coverage,
      mapped_countries: 218,
      mapped_signals: 109632,
      unmapped_countries: 0,
      unmapped_signals: 0,
    }
    const r = fieldCoverageReadout(clean, [])
    expect(r.countries).toBe(218)
    expect(r.tip).not.toMatch(/not drawn/i)
  })

  it('falls back to counting the rendered nodes when coverage is absent', () => {
    // Older payloads (and any degraded response) carry no coverage object.
    // Falling back is honest; inventing a total is not.
    const r = fieldCoverageReadout(null, [{ signalCount: 10 }, { signalCount: 5 }])
    expect(r.countries).toBe(2)
    expect(r.signals).toBe(15)
    expect(r.tip).toMatch(/drawn|render/i)
  })

  it('tolerates nodes with missing signal counts without producing NaN', () => {
    const r = fieldCoverageReadout(null, [{ signalCount: undefined }, { signalCount: 7 }])
    expect(r.signals).toBe(7)
    expect(Number.isNaN(r.signals)).toBe(false)
  })

  it('ignores a coverage object whose counted totals are missing', () => {
    const partial = { basis: 'hourly_rollup', label: 'hourly rollup', note: 'x' }
    const r = fieldCoverageReadout(partial as never, [{ signalCount: 3 }])
    expect(r.countries).toBe(1)
    expect(r.signals).toBe(3)
  })

  it('never lets the plotted subset exceed the counted base in the printed line', () => {
    const r = fieldCoverageReadout(coverage, [])
    expect(r.countries).toBeGreaterThanOrEqual(coverage.mapped_countries)
  })
})
