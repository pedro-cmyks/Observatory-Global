import { describe, expect, it } from 'vitest'
import { getPublicAttentionTopUrl } from './publicAttention'

describe('public attention helpers', () => {
  it('uses a seven-day wiki window so daily ingestion gaps do not look like endless loading', () => {
    expect(getPublicAttentionTopUrl(10)).toBe('/api/v2/wiki/top?days=7&limit=10')
  })
})
