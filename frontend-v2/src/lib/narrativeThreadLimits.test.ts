import { describe, it, expect } from 'vitest'
import { threadPoolQuery, getNarrativeFetchLimit, readThreadPool } from './narrativeThreadLimits'

/**
 * The pool query has two callers that MUST agree — the console's thread list
 * and the phone's Lens `connected` section. The #234 relation weights entities
 * by how many threads in the pool carry them, so two callers measuring
 * different pools would show different receipts for the same pair of threads.
 * Same string, same pool, same receipts.
 */
describe('threadPoolQuery', () => {
  it('asks for the global 24h pool at the unscoped limit', () => {
    expect(threadPoolQuery()).toBe(`/api/v2/threads?hours=24&limit=${getNarrativeFetchLimit(false)}`)
  })

  it('scopes to a country at the country limit', () => {
    expect(threadPoolQuery('CO')).toBe(
      `/api/v2/threads?hours=24&limit=${getNarrativeFetchLimit(true)}&country_code=CO`,
    )
  })

  it('treats an empty or null country as unscoped', () => {
    expect(threadPoolQuery(null)).toBe(threadPoolQuery())
    expect(threadPoolQuery('')).toBe(threadPoolQuery())
  })

  it('encodes the country code it is given', () => {
    expect(threadPoolQuery('a b')).toContain('country_code=a+b')
  })
})

describe('readThreadPool', () => {
  it('reads the fields the relation measures on', () => {
    const rows = readThreadPool({
      threads: [{ thread_id: 'dt-1', label: 'Kyiv strikes', top_countries: ['UA'], top_entities: ['Zelensky'] }],
    })
    expect(rows).toEqual([
      { thread_id: 'dt-1', label: 'Kyiv strikes', top_countries: ['UA'], top_entities: ['Zelensky'] },
    ])
  })

  it('decodes an entity-encoded label — the Cyrillic hex soup reaches this surface too', () => {
    const rows = readThreadPool({ threads: [{ thread_id: 'dt-1', label: 'Caf&amp;eacute;' }] })
    expect(rows![0].label).toBe('Caf&eacute;')
  })

  it('falls back to the id rather than showing a nameless row', () => {
    expect(readThreadPool({ threads: [{ thread_id: 'dt-1' }] })![0].label).toBe('dt-1')
  })

  it('drops a row with no id — nothing can be opened or matched by it', () => {
    expect(readThreadPool({ threads: [{ label: 'orphan' }, { thread_id: 'dt-1' }] })).toHaveLength(1)
  })

  it('accepts an empty pool as a real, measured empty', () => {
    expect(readThreadPool({ threads: [] })).toEqual([])
  })

  it('returns null for a body that is not a pool, so a caller can say degraded', () => {
    // Not `[]`: an unreadable answer is a failure, and reporting it as an empty
    // pool is the timeout-as-absence defect wearing a different hat.
    expect(readThreadPool(null)).toBeNull()
    expect(readThreadPool({})).toBeNull()
    expect(readThreadPool({ threads: 'nope' })).toBeNull()
  })
})
