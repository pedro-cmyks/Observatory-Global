import { describe, it, expect } from 'vitest'
import {
  cleanSubjectValue,
  composeEditionStandfirst,
  formatDateRange,
  standfirstChrome,
  type StandfirstReadiness,
} from './briefStandfirst'

const ready = (values: string[]) => ({ status: 'ready', values, reason_codes: [] })
const partial = (values: string[], reasons: string[] = ['x_incomplete']) => ({
  status: 'partial', values, reason_codes: reasons,
})
const missing = () => ({ status: 'missing', values: [], reason_codes: ['not_measured'] })

function proseOf(sf: ReturnType<typeof composeEditionStandfirst>): string {
  return sf.parts.map(p => (p.kind === 'text' ? p.text : p.name)).join('')
}

describe('composeEditionStandfirst — all Ready', () => {
  const payload: StandfirstReadiness = {
    what: ready(['Cargo Ship Sinks Off India', 'Drone Attacks Kill Women', 'Japan Earthquake Injuries']),
    who: ready(['Canada (place)', 'Donald Trump', 'India (place)']),
    where: ready(['CA', 'IN']),
    when: ready(['2026-08-23', '2026-08-24']),
    how: ready(['abc15.com', 'arabic.rt.com']),
    why: partial(['x: velocity=+1'], ['causal_explanation_not_measured']),
  }

  it('weaves every ready field into one readable paragraph', () => {
    const sf = composeEditionStandfirst(payload, 'en')
    expect(sf.hasProse).toBe(true)
    expect(proseOf(sf)).toBe(
      'Today’s lead: Cargo Ship Sinks Off India. Atlas measured coverage in CA · IN. '
      + 'Coverage window: Aug 23–24. Lead outlets: abc15.com and arabic.rt.com. '
      + 'At the center: Canada, Donald Trump and India. '
      + '2 more stories met today’s measured bar.',
    )
  })

  it('declares the always-partial WHY in the below-bar line, never in prose', () => {
    const sf = composeEditionStandfirst(payload, 'en')
    expect(sf.belowBar).toEqual(['why'])
    expect(sf.belowBarLine).toBe('Below the full bar today: WHY.')
    expect(proseOf(sf)).not.toContain('velocity')
  })

  it('marks a HOW outlet classified STATE by sourceTiers', () => {
    const sf = composeEditionStandfirst(payload, 'en')
    const outlets = sf.parts.filter(p => p.kind === 'outlet')
    expect(outlets).toEqual([
      { kind: 'outlet', name: 'abc15.com', state: false },
      { kind: 'outlet', name: 'arabic.rt.com', state: true },
    ])
  })

  it('cleans the "(place)" annotation from the render only', () => {
    const sf = composeEditionStandfirst(payload, 'en')
    expect(proseOf(sf)).toContain('Canada, Donald Trump and India')
    expect(proseOf(sf)).not.toContain('(place)')
    // the datum was never mutated
    expect(payload.who?.values).toContain('Canada (place)')
  })

  it('speaks Spanish when asked', () => {
    const sf = composeEditionStandfirst(payload, 'es')
    expect(proseOf(sf)).toBe(
      'La nota del día: Cargo Ship Sinks Off India. Atlas midió la cobertura en CA · IN. '
      + 'Ventana de cobertura: 23–24 ago. Medios principales: abc15.com y arabic.rt.com. '
      + 'Al centro: Canada, Donald Trump y India. '
      + '2 historias más pasaron la barra medida de hoy.',
    )
    expect(sf.belowBarLine).toBe('Hoy bajo la barra completa: WHY.')
  })
})

describe('composeEditionStandfirst — mixed Ready/Partial (the live 2026-08-24 shape)', () => {
  const payload: StandfirstReadiness = {
    what: ready(['Cargo Ship Sinks Off India', 'Drone Attacks Kill Women']),
    when: ready(['2026-08-23', '2026-08-24']),
    how: ready(['abc15.com', 'arabic.rt.com', 'arabnews.com']),
    who: partial(['Canada (place)', 'Donald Trump'], ['actor_attribution_incomplete_for_story_nodes']),
    where: partial(['CA', 'IN'], ['subject_geography_incomplete_for_story_nodes']),
    why: partial([], ['causal_explanation_not_measured']),
  }

  it('weaves ONLY the ready fields; partial values never reach the prose', () => {
    const sf = composeEditionStandfirst(payload, 'en')
    const prose = proseOf(sf)
    expect(prose).toBe(
      'Today’s lead: Cargo Ship Sinks Off India. Coverage window: Aug 23–24. '
      + 'Lead outlets: abc15.com, arabic.rt.com and 1 more outlet. '
      + '1 more story met today’s measured bar.',
    )
    // partial WHO / WHERE values are absent from the woven text
    expect(prose).not.toContain('Donald Trump')
    expect(prose).not.toContain('CA · IN')
  })

  it('names every partial field once, in the honest closing line', () => {
    const sf = composeEditionStandfirst(payload, 'en')
    expect(sf.belowBar).toEqual(['who', 'where', 'why'])
    expect(sf.belowBarLine).toBe('Below the full bar today: WHO, WHERE, WHY.')
  })
})

describe('composeEditionStandfirst — all Partial', () => {
  it('produces the minimal honest paragraph: no prose, one declaration line', () => {
    const sf = composeEditionStandfirst({
      who: partial(['A']), what: partial(['B']), when: partial(['2026-08-24']),
      where: partial(['CA']), how: partial(['x.com']), why: partial([]),
    }, 'en')
    expect(sf.hasProse).toBe(false)
    expect(sf.parts).toEqual([])
    expect(sf.belowBar).toEqual(['who', 'what', 'when', 'where', 'how', 'why'])
    expect(sf.belowBarLine).toBe('Below the full bar today: WHO, WHAT, WHEN, WHERE, HOW, WHY.')
  })
})

describe('composeEditionStandfirst — absent fields and degraded payloads', () => {
  it('an absent field is an absent sentence (missing ≠ partial: not declared either)', () => {
    const sf = composeEditionStandfirst({
      what: ready(['Solo Story']),
      who: missing(),
      // when / where / how / why entirely absent from the payload
    }, 'en')
    expect(proseOf(sf)).toBe('Today’s lead: Solo Story.')
    expect(sf.belowBar).toEqual([])
    expect(sf.belowBarLine).toBeNull()
  })

  it('weaves coverage facts even when WHAT itself is not ready', () => {
    const sf = composeEditionStandfirst({
      what: partial(['X']),
      how: ready(['reuters.com']),
    }, 'en')
    expect(proseOf(sf)).toBe('Today’s coverage. Lead outlets: reuters.com.')
    expect(sf.belowBar).toEqual(['what'])
  })

  it('a null / undefined payload renders nothing and never throws', () => {
    for (const payload of [null, undefined]) {
      const sf = composeEditionStandfirst(payload as StandfirstReadiness, 'en')
      expect(sf.hasProse).toBe(false)
      expect(sf.parts).toEqual([])
      expect(sf.belowBarLine).toBeNull()
    }
  })

  it('a ready field with garbage values yields no invented prose', () => {
    const sf = composeEditionStandfirst({
      when: ready(['not-a-date', '2026-13-99']),
    }, 'en')
    expect(sf.hasProse).toBe(false)
  })
})

describe('formatDateRange', () => {
  it('same-month range collapses to one month token', () => {
    expect(formatDateRange(['2026-08-23', '2026-08-24'], 'en')).toBe('Aug 23–24')
    expect(formatDateRange(['2026-08-23', '2026-08-24'], 'es')).toBe('23–24 ago')
  })
  it('single day prints once', () => {
    expect(formatDateRange(['2026-08-24'], 'en')).toBe('Aug 24')
  })
  it('cross-month range keeps both months', () => {
    expect(formatDateRange(['2026-07-30', '2026-08-02'], 'en')).toBe('Jul 30 – Aug 2')
    expect(formatDateRange(['2026-07-30', '2026-08-02'], 'es')).toBe('30 jul – 2 ago')
  })
  it('cross-year range states the years', () => {
    expect(formatDateRange(['2025-12-31', '2026-01-01'], 'en')).toBe('Dec 31, 2025 – Jan 1, 2026')
  })
  it('invalid inputs yield null, never an invented date', () => {
    expect(formatDateRange(['garbage', ''], 'en')).toBeNull()
    expect(formatDateRange([], 'en')).toBeNull()
  })
})

describe('cleanSubjectValue', () => {
  it('strips the typed-subject annotation suffix', () => {
    expect(cleanSubjectValue('Canada (place)')).toBe('Canada')
    expect(cleanSubjectValue('Jane Doe (person)')).toBe('Jane Doe')
  })
  it('leaves everything else untouched', () => {
    expect(cleanSubjectValue('Doctors Without Borders (MSF)')).toBe('Doctors Without Borders (MSF)')
    expect(cleanSubjectValue('Donald Trump')).toBe('Donald Trump')
  })
})

describe('standfirstChrome', () => {
  it('serves both languages with a STATE tip from sourceTiers', () => {
    expect(standfirstChrome('en').seeQuestions).toBe('See the six measured questions')
    expect(standfirstChrome('es').seeQuestions).toBe('Ver las seis preguntas medidas')
    expect(standfirstChrome('en').stateTip.length).toBeGreaterThan(0)
  })
})
