import { describe, expect, it } from 'vitest'
import { selectVisibleKeyPersons } from './countryBriefPeople'

describe('selectVisibleKeyPersons', () => {
  it('keeps named people with counts and limits the CountryBrief people strip', () => {
    const people = selectVisibleKeyPersons([
      { name: 'america latin', count: 50 },
      { name: 'Gustavo Petro', count: 42 },
      { name: '  ', count: 99 },
      { name: 'Maria Corina Machado', count: 31 },
      { name: 'El Pais', count: 20 },
      { name: 'Claudia Sheinbaum', count: 18 },
      { name: 'Luiz Inacio Lula', count: 16 },
      { name: 'Gabriel Boric', count: 14 },
      { name: 'Javier Milei', count: 12 },
      { name: 'Nicolas Maduro', count: 10 },
    ])

    expect(people).toEqual([
      { name: 'Gustavo Petro', count: 42 },
      { name: 'Maria Corina Machado', count: 31 },
      { name: 'Claudia Sheinbaum', count: 18 },
      { name: 'Luiz Inacio Lula', count: 16 },
      { name: 'Gabriel Boric', count: 14 },
      { name: 'Javier Milei', count: 12 },
      { name: 'Nicolas Maduro', count: 10 },
    ])
  })
})
