// Temporal signature chip resolver — pure copy contract (Lane C).
// Freezes: continuous/NULL/unknown -> NO chip (absence over guess; the
// default state is not a badge), and the plain-language copy for
// new / recurrent / resurrected including the meta-driven qualifiers.
import { describe, expect, it } from 'vitest'
import { resolveTemporalChip } from './temporalSignatureChip'

describe('resolveTemporalChip', () => {
  it('renders nothing for continuous — the default is not a badge', () => {
    expect(resolveTemporalChip('continuous', { eras: 1 })).toBeNull()
  })

  it('renders nothing when unclassified (below member floor / not yet run)', () => {
    expect(resolveTemporalChip(null)).toBeNull()
    expect(resolveTemporalChip(undefined)).toBeNull()
  })

  it('renders nothing for unknown future values', () => {
    expect(resolveTemporalChip('mystery-signature')).toBeNull()
  })

  it('NEW carries the no-prior-coverage claim', () => {
    const chip = resolveTemporalChip('new', { eras: 1, first_seen_week: '2026-07-13' })
    expect(chip?.label).toBe('NEW')
    expect(chip?.tip).toContain('No prior coverage matched')
    expect(chip?.tip).toContain('since May')
  })

  it('RECURRENT names the active-era ordinal', () => {
    const chip = resolveTemporalChip('recurrent', { eras: 3, returned_week: '2026-07-06' })
    expect(chip?.label).toBe('RECURRENT')
    expect(chip?.tip).toContain('3rd active era')
    expect(chip?.tip).toContain('returned Jul 6')
  })

  it('RECURRENT degrades gracefully without meta', () => {
    const chip = resolveTemporalChip('recurrent')
    expect(chip?.label).toBe('RECURRENT')
    expect(chip?.tip).toContain('more than once')
    expect(chip?.tip).not.toContain('undefined')
  })

  it('RESURRECTED states the quiet gap and return week', () => {
    const chip = resolveTemporalChip('resurrected', { gap_weeks: 3, returned_week: '2026-07-12' })
    expect(chip?.label).toBe('RESURRECTED')
    expect(chip?.tip).toContain('Quiet 3 weeks')
    expect(chip?.tip).toContain('returned Jul 12')
  })

  it('RESURRECTED singular week reads naturally', () => {
    const chip = resolveTemporalChip('resurrected', { gap_weeks: 1 })
    expect(chip?.tip).toContain('Quiet 1 week ')
  })

  it('RESURRECTED degrades gracefully without meta', () => {
    const chip = resolveTemporalChip('resurrected', null)
    expect(chip?.label).toBe('RESURRECTED')
    expect(chip?.tip).toContain('dormant')
    expect(chip?.tip).not.toContain('undefined')
  })

  it('ordinal edges: 1st / 2nd / 11th / 21st', () => {
    expect(resolveTemporalChip('recurrent', { eras: 11 })?.tip).toContain('11th active era')
    expect(resolveTemporalChip('recurrent', { eras: 21 })?.tip).toContain('21st active era')
    expect(resolveTemporalChip('recurrent', { eras: 2 })?.tip).toContain('2nd active era')
  })
})
