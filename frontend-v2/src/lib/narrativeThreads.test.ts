import { describe, expect, it } from 'vitest'
import { getNarrativeDisplayLimit, getNarrativeFetchLimit } from './narrativeThreadLimits'

describe('NarrativeThreads limits', () => {
  it('fetches enough global narratives to fill the available panel space', () => {
    expect(getNarrativeFetchLimit(false)).toBeGreaterThanOrEqual(20)
  })

  it('keeps country-filtered narratives from collapsing back to five rows', () => {
    expect(getNarrativeDisplayLimit(true)).toBeGreaterThanOrEqual(20)
  })
})
