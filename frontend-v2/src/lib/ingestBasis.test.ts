import { describe, it, expect } from 'vitest'
import {
  INGEST_POPULATION,
  IN_INGEST,
  INGEST_NOTE,
  absenceCaveat,
  shareCaveat,
  withBasisTip,
} from './ingestBasis'

/**
 * X1 (2026-08-13). The panel was shown "0% Colombian voices" and read it as a
 * fact about Colombia. These pin the wording that makes that reading
 * impossible, and pin it in LOCKSTEP with `app/services/ingest_basis.py` —
 * both sides assert the same strings, so a one-sided edit fails a suite.
 */
describe('the ingest base', () => {
  it('names feeds AND the firehose, so the base is not understated', () => {
    expect(INGEST_POPULATION.toLowerCase()).toContain('feeds')
    expect(INGEST_POPULATION.toLowerCase()).toContain('gdelt')
  })

  it('leads a sentence rather than trailing it', () => {
    // Backend lockstep: ingest_basis.IN_INGEST.
    expect(IN_INGEST).toBe('In what Atlas ingests')
    expect(IN_INGEST.endsWith('.')).toBe(false)
  })

  it('refuses the world reading in the tooltip, in words', () => {
    expect(INGEST_NOTE).toContain('not that nobody did')
    expect(INGEST_NOTE).toContain('Atlas')
  })

  it('refuses the silence reading for a zero, naming the country', () => {
    const line = absenceCaveat('Colombia')
    expect(line).toContain('Colombia')
    expect(line).toContain('not proof')
    expect(line).toContain('stayed silent')
  })

  it('refuses the world denominator for a share', () => {
    expect(shareCaveat()).toContain('not of everything published')
  })

  it('keeps an existing tooltip and adds the base to it', () => {
    // The method half of every tip (ownership vs language) is load-bearing and
    // must survive; only the missing POPULATION half is added.
    const tip = withBasisTip('Self-coverage is outlet OWNERSHIP, not language.')
    expect(tip).toContain('OWNERSHIP')
    expect(tip).toContain('not that nobody did')
  })

  it('degrades to the base alone when there was no tooltip', () => {
    expect(withBasisTip(undefined)).toBe(INGEST_NOTE)
    expect(withBasisTip('   ')).toBe(INGEST_NOTE)
  })
})
