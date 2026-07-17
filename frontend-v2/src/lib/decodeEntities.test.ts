import { describe, it, expect } from 'vitest'
import { decodeEntities } from './decodeEntities'
import { decodeEntities as reExported } from './attentionEclipse'

// Shared HTML-entity decoder (council P0-3): headlines/labels arrive
// entity-encoded ("&#x936;…" hex soup) on ≥5 surfaces. One decoder, promoted
// to its own module; the old attentionEclipse path re-exports it.
describe('decodeEntities', () => {
  it('decodes hex numeric entities (the Cyrillic/Devanagari hex-soup class)', () => {
    expect(decodeEntities('&#x41F;&#x440;&#x438;&#x432;&#x435;&#x442;')).toBe('Привет')
  })

  it('decodes decimal numeric entities', () => {
    expect(decodeEntities('Caf&#233; con leche')).toBe('Café con leche')
  })

  it('decodes common named entities', () => {
    expect(decodeEntities('Bonnie &amp; Clyde &quot;wanted&quot;')).toBe('Bonnie & Clyde "wanted"')
  })

  it('drops a trailing incomplete entity left by mid-entity truncation', () => {
    expect(decodeEntities('…लगा&#')).toBe('…लगा')
  })

  it('returns plain strings unchanged (no & → no work)', () => {
    expect(decodeEntities('Plain headline about trade')).toBe('Plain headline about trade')
  })

  it('is re-exported from the legacy attentionEclipse path', () => {
    expect(reExported).toBe(decodeEntities)
  })
})
