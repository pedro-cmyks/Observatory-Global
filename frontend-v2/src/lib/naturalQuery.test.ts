import { describe, it, expect } from 'vitest'
import { looksLikeNaturalQuestion, askAtlasLabel } from './naturalQuery'

describe('looksLikeNaturalQuestion', () => {
  it('catches the witness query (colegio ciego, usuario-perdido)', () => {
    expect(looksLikeNaturalQuestion('what is happening in israel')).toBe(true)
  })

  it('catches a Spanish question', () => {
    expect(looksLikeNaturalQuestion('qué está pasando en Israel')).toBe(true)
    expect(looksLikeNaturalQuestion('que esta pasando en israel')).toBe(true)
    expect(looksLikeNaturalQuestion('por qué subió el dólar')).toBe(true)
  })

  it('catches a short question by its question word', () => {
    expect(looksLikeNaturalQuestion('why gaza')).toBe(true)
    expect(looksLikeNaturalQuestion('cómo va Ucrania')).toBe(true)
  })

  it('catches anything ending in a question mark', () => {
    expect(looksLikeNaturalQuestion('israel?')).toBe(true)
  })

  it('catches a long phrase even without a question word', () => {
    expect(looksLikeNaturalQuestion('colombia earthquake casualties august')).toBe(true)
  })

  it('leaves analyst vocabulary alone — those queries have their own doors', () => {
    expect(looksLikeNaturalQuestion('israel')).toBe(false)
    expect(looksLikeNaturalQuestion('gaza conflict')).toBe(false)
    expect(looksLikeNaturalQuestion('oil')).toBe(false)
    expect(looksLikeNaturalQuestion('')).toBe(false)
    expect(looksLikeNaturalQuestion('   ')).toBe(false)
  })

  it('does not fire on a three-word country phrase with no question word', () => {
    expect(looksLikeNaturalQuestion('united arab emirates')).toBe(false)
  })
})

describe('askAtlasLabel', () => {
  it('quotes the query the reader actually typed, not a stripped token', () => {
    expect(askAtlasLabel('what is happening in israel')).toBe('Ask Atlas: “what is happening in israel”')
  })

  it('trims and clamps a runaway query so the row never blows the dropdown', () => {
    const long = 'a'.repeat(90)
    const label = askAtlasLabel(`  ${long}  `)
    expect(label.length).toBeLessThan(90)
    expect(label.endsWith('…”')).toBe(true)
  })
})
