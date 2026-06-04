import { describe, expect, it } from 'vitest'
import { buildSourceIntegrityScopeLabel } from './sourceIntegrityScope'

describe('SourceIntegrity scope label', () => {
  it('names the active person when source metrics are scoped by FocusData', () => {
    expect(buildSourceIntegrityScopeLabel({ person: 'malhar jammu' })).toEqual({
      heading: 'malhar jammu',
      sublabel: 'Scoped to active person',
      scoped: true,
    })
  })

  it('labels global background when the center panel is focused but source data is not scoped', () => {
    expect(buildSourceIntegrityScopeLabel({ viewingLabel: 'Russia-Ukraine War Updates' })).toEqual({
      heading: 'Global background',
      sublabel: 'Viewing Russia-Ukraine War Updates',
      scoped: false,
    })
  })
})
