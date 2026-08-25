import { describe, it, expect } from 'vitest'
import {
  buildTodaysNumber,
  hoursUntilNextSeal,
  todaysNumberMixFrom,
  type TodaysNumberMix,
} from './briefTodaysNumber'

const mix = (over: Partial<TodaysNumberMix>): TodaysNumberMix => ({
  wire: 0, state: 0, major: 0, local: 0, unknown: 0, totalReceipts: 48,
  ...over,
})

describe('buildTodaysNumber — R1 (state matched major)', () => {
  it('fires when the served integers are equal and both present', () => {
    const hero = buildTodaysNumber({ mix: mix({ state: 14, major: 14, wire: 40, local: 20, unknown: 12 }) })
    expect(hero).not.toBeNull()
    expect(hero!.rule).toBe('R1')
    expect(hero!.headline).toBe('14% = 14%')
    expect(hero!.body).toBe(
      "State outlets wrote 14 percent of today's 48 receipts. "
      + 'Major news outlets also wrote 14 percent. '
      + 'Today, state media matched the major press.',
    )
    expect(hero!.voicesNote).toBeNull()
  })

  it('does NOT fire on a vacuous 0% = 0% (documented guard)', () => {
    const hero = buildTodaysNumber({ mix: mix({ state: 0, major: 0, wire: 60, local: 20, unknown: 20 }) })
    expect(hero?.rule).not.toBe('R1')
  })
})

describe('buildTodaysNumber — R2 (state above major)', () => {
  it('fires when state > major', () => {
    const hero = buildTodaysNumber({ mix: mix({ state: 31, major: 22, wire: 30, local: 10, unknown: 7 }) })
    expect(hero!.rule).toBe('R2')
    expect(hero!.headline).toBe('31% to 22%')
    expect(hero!.body).toBe(
      "State outlets wrote more of today's receipts than major outlets: 31% to 22%. "
      + 'Base: 48 receipts.',
    )
  })

  it('beats major = 0 too — 5% to 0% is a real comparison', () => {
    const hero = buildTodaysNumber({ mix: mix({ state: 5, major: 0, wire: 60, local: 20, unknown: 15 }) })
    expect(hero!.rule).toBe('R2')
    expect(hero!.headline).toBe('5% to 0%')
  })
})

describe('buildTodaysNumber — R3 (local beats the rest together)', () => {
  it('fires when local > wire+state+major, and carries the voices note', () => {
    const hero = buildTodaysNumber({ mix: mix({ local: 46, wire: 20, state: 8, major: 10, unknown: 16 }) })
    expect(hero!.rule).toBe('R3')
    expect(hero!.headline).toBe('46% to 38%')
    expect(hero!.body).toBe(
      'Local outlets wrote more receipts than wire, state and major outlets together: 46% to 38%. '
      + 'Base: 48 receipts.',
    )
    expect(hero!.voicesNote).toBe(
      'Local outlets wrote more receipts than wire, state and major outlets together: 46% to 38%.',
    )
  })
})

describe('buildTodaysNumber — R4 (the unknown share)', () => {
  it('fires at unknown >= 30', () => {
    const hero = buildTodaysNumber({ mix: mix({ unknown: 30, wire: 40, major: 30 }) })
    expect(hero!.rule).toBe('R4')
    expect(hero!.headline).toBe('30%')
    expect(hero!.body).toBe(
      "We cannot identify 30 percent of today's 48 voices. "
      + 'We tell you when we do not know.',
    )
  })

  it('stays silent at 29', () => {
    const hero = buildTodaysNumber({ mix: mix({ unknown: 29, wire: 41, major: 30 }) })
    expect(hero?.rule ?? null).not.toBe('R4')
  })
})

describe('buildTodaysNumber — R5 (lead fallback)', () => {
  it('fires only from a served lead when no mix rule matched', () => {
    const hero = buildTodaysNumber({
      mix: mix({ wire: 50, major: 40, state: 0, local: 5, unknown: 5 }),
      lead: { outlets: 51, label: 'Cargo Ship Sinks Off India' },
    })
    expect(hero!.rule).toBe('R5')
    expect(hero!.headline).toBe('51 outlets')
    expect(hero!.body).toBe('51 outlets covered one story today: "Cargo Ship Sinks Off India".')
  })

  it('fires with NO mix at all (mix null, lead served)', () => {
    const hero = buildTodaysNumber({ mix: null, lead: { outlets: 1, label: 'One Story' } })
    expect(hero!.rule).toBe('R5')
    expect(hero!.headline).toBe('1 outlet')
    expect(hero!.body).toBe('1 outlet covered one story today: "One Story".')
  })

  it('refuses a lead without a measured outlet count or without a label', () => {
    expect(buildTodaysNumber({ lead: { outlets: null, label: 'X' } })).toBeNull()
    expect(buildTodaysNumber({ lead: { outlets: 12, label: '' } })).toBeNull()
  })
})

describe('buildTodaysNumber — fixed priority', () => {
  it('R1 wins over R2/R3/R4/R5 when several could fire', () => {
    const hero = buildTodaysNumber({
      // state==major (R1), unknown>=30 (R4), lead served (R5) — R1 must win.
      mix: mix({ state: 10, major: 10, unknown: 40, wire: 20, local: 20 }),
      lead: { outlets: 9, label: 'X' },
    })
    expect(hero!.rule).toBe('R1')
  })

  it('R2 wins over R3/R4', () => {
    const hero = buildTodaysNumber({
      mix: mix({ state: 20, major: 5, local: 40, wire: 5, unknown: 30 }),
    })
    expect(hero!.rule).toBe('R2')
  })

  it('R3 wins over R4', () => {
    const hero = buildTodaysNumber({
      mix: mix({ local: 40, wire: 10, state: 0, major: 10, unknown: 40 }),
    })
    expect(hero!.rule).toBe('R3')
  })

  it('R4 wins over R5', () => {
    const hero = buildTodaysNumber({
      mix: mix({ unknown: 35, wire: 35, major: 30 }),
      lead: { outlets: 9, label: 'X' },
    })
    expect(hero!.rule).toBe('R4')
  })
})

describe('buildTodaysNumber — honest absence', () => {
  it('returns null with no data at all', () => {
    expect(buildTodaysNumber({})).toBeNull()
    expect(buildTodaysNumber({ mix: null, lead: null })).toBeNull()
  })

  it('returns null when the mix has a zero base and the lead is absent', () => {
    expect(buildTodaysNumber({ mix: mix({ totalReceipts: 0, state: 50, major: 10 }) })).toBeNull()
  })

  it('returns null when a percentage field is not a number', () => {
    const broken = { ...mix({}), state: Number.NaN }
    expect(buildTodaysNumber({ mix: broken })).toBeNull()
  })
})

describe('buildTodaysNumber — Spanish', () => {
  it('translates the R1 body with the same numbers', () => {
    const hero = buildTodaysNumber({ mix: mix({ state: 14, major: 14 }) }, 'es')
    expect(hero!.rule).toBe('R1')
    expect(hero!.body).toBe(
      'Los medios estatales escribieron el 14 por ciento de los 48 recibos de hoy. '
      + 'Los grandes medios también escribieron el 14 por ciento. '
      + 'Hoy, la prensa estatal igualó a la gran prensa.',
    )
  })

  it('translates R5 with singular/plural verbs', () => {
    const hero = buildTodaysNumber({ lead: { outlets: 2, label: 'X' } }, 'es')
    expect(hero!.body).toBe('2 medios cubrieron una historia hoy: "X".')
  })
})

describe('todaysNumberMixFrom — strip-identical adapter', () => {
  it('rounds exactly like the strip labels and treats absent patches as measured zero', () => {
    const m = todaysNumberMixFrom(
      [{ tier: 'wire', count: 20 }, { tier: 'state', count: 7 }, { tier: 'unknown', count: 21 }],
      48,
    )
    expect(m).toEqual({ wire: 42, state: 15, major: 0, local: 0, unknown: 44, totalReceipts: 48 })
  })

  it('refuses a zero or invalid base', () => {
    expect(todaysNumberMixFrom([], 0)).toBeNull()
    expect(todaysNumberMixFrom([], Number.NaN)).toBeNull()
  })
})

describe('hoursUntilNextSeal', () => {
  const now = new Date('2026-08-25T12:00:00Z')

  it('rounds exactly like the seal band (staleBanner round-to-hour)', () => {
    // 14 h 30 m → 15 (round half up), 15 h 20 m → 15 (never ceil to 16 while
    // the band beside it says "in 15 h").
    expect(hoursUntilNextSeal('2026-08-26T02:30:00Z', now)).toBe(15)
    expect(hoursUntilNextSeal('2026-08-26T03:20:00Z', now)).toBe(15)
  })

  it('floors at 1 hour for a near seal (never "in 0 hours")', () => {
    expect(hoursUntilNextSeal('2026-08-25T12:20:00Z', now)).toBe(1)
  })

  it('is null when absent, unparseable, or already past', () => {
    expect(hoursUntilNextSeal(null, now)).toBeNull()
    expect(hoursUntilNextSeal('not a date', now)).toBeNull()
    expect(hoursUntilNextSeal('2026-08-25T11:00:00Z', now)).toBeNull()
  })
})
