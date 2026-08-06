import { describe, it, expect } from 'vitest'
import { buildThreadRelation, distinctiveCap } from './threadRelation'

/** Minimal pool row — the four fields the relation actually reads. */
const t = (thread_id: string, top_countries: string[] = [], top_entities: string[] = []) =>
  ({ thread_id, label: thread_id, top_countries, top_entities })

const NAMES: Record<string, string> = { US: 'United States', RU: 'Russia', UA: 'Ukraine', CO: 'Colombia' }
const resolveCountryName = (c: string) => NAMES[c] ?? c

const build = (pool: ReturnType<typeof t>[], anchorId: string | null) =>
  buildThreadRelation(pool, anchorId, { resolveCountryName })

describe('distinctiveCap', () => {
  it('is a quarter of the pool, capped at 3', () => {
    expect(distinctiveCap(20)).toBe(3)
    expect(distinctiveCap(12)).toBe(3)
  })

  it('never drops below 2, so a small pool still admits a shared entity', () => {
    expect(distinctiveCap(4)).toBe(2)
    expect(distinctiveCap(0)).toBe(2)
  })
})

describe('buildThreadRelation — the anchor', () => {
  it('is inert with no anchor id', () => {
    const rel = build([t('a', ['US']), t('b', ['US'])], null)
    expect(rel.anchor).toBeNull()
    expect(rel.active).toBe(false)
    expect(rel.related).toEqual([])
  })

  it('is inert when the anchor is not in the pool — nothing was measured against', () => {
    const rel = build([t('a', ['US']), t('b', ['US'])], 'not-in-pool')
    expect(rel.anchor).toBeNull()
    expect(rel.active).toBe(false)
    expect(rel.isRelated(t('a', ['US']))).toBe(false)
  })

  it('never carries a receipt for itself, and never appears in its own neighbourhood', () => {
    const rel = build([t('a', ['US']), t('b', ['US'])], 'a')
    expect(rel.isRelated(rel.anchor!)).toBe(true)
    expect(rel.reason(rel.anchor!)).toBeNull()
    expect(rel.related.map(r => r.thread.thread_id)).toEqual(['b'])
  })
})

describe('buildThreadRelation — shared primary geography', () => {
  it('relates on a country in the anchor top-2 and names it', () => {
    const rel = build([t('a', ['RU', 'UA']), t('b', ['UA', 'PL'])], 'a')
    expect(rel.active).toBe(true)
    expect(rel.reason(rel.related[0].thread)).toBe('Ukraine')
    expect(rel.related[0].receipt).toBe('Ukraine')
  })

  it('ignores a country outside the anchor top-2 — the dominant country is too broad', () => {
    const rel = build([t('a', ['RU', 'UA', 'US']), t('b', ['US'])], 'a')
    expect(rel.countries).toEqual(new Set(['RU', 'UA']))
    expect(rel.active).toBe(false)
    expect(rel.related).toEqual([])
  })
})

describe('buildThreadRelation — rarity-weighted entities', () => {
  it('relates on an entity few threads carry', () => {
    const pool = [
      t('a', [], ['Zelensky', 'Donald Trump']),
      t('b', [], ['Zelensky']),
      t('c', [], ['Donald Trump']),
      t('d', [], ['Donald Trump']),
      t('e', [], ['Donald Trump']),
    ]
    const rel = build(pool, 'a')
    expect(rel.related.map(r => r.thread.thread_id)).toEqual(['b'])
    expect(rel.related[0].receipt).toBe('Zelensky')
  })

  it('drops an entity carried by more threads than the cap — the measured "donald trump" case', () => {
    // DF("donald trump") = 5 over a 5-row pool; cap is 2. A common actor is
    // noise: without this the anchor would link every unrelated thread.
    const pool = [
      t('a', [], ['Donald Trump']),
      t('b', [], ['Donald Trump']),
      t('c', [], ['Donald Trump']),
      t('d', [], ['Donald Trump']),
      t('e', [], ['Donald Trump']),
    ]
    const rel = build(pool, 'a')
    expect(rel.entities.size).toBe(0)
    expect(rel.active).toBe(false)
  })

  it('matches entities across case and surrounding whitespace', () => {
    const rel = build([t('a', [], ['  Zelensky ']), t('b', [], ['ZELENSKY'])], 'a')
    expect(rel.related.map(r => r.thread.thread_id)).toEqual(['b'])
  })

  it('reports the sibling row\'s own spelling as the receipt, not the anchor\'s', () => {
    // The receipt has to be checkable against the row the reader is looking
    // at, so it is that row's string — not the anchor's, and not the
    // normalized form the match ran on.
    const rel = build([t('a', [], ['zelensky']), t('b', [], ['Zelensky'])], 'a')
    expect(rel.related[0].receipt).toBe('Zelensky')
  })

  it('does not relate two entities merely because one contains the other', () => {
    const rel = build([t('a', [], ['Zelensky']), t('b', [], ['Volodymyr Zelensky'])], 'a')
    expect(rel.related).toEqual([])
  })

  it('counts a repeated entity within one row once', () => {
    // Three rows carrying it, one of them twice: DF is 3, above a cap of 2, so
    // a per-mention count would have differed only by making it look rarer.
    const pool = [
      t('a', [], ['Zelensky']),
      t('b', [], ['Zelensky', 'zelensky']),
      t('c', [], ['Zelensky']),
      t('d', [], ['Someone Else']),
    ]
    expect(build(pool, 'a').entities.size).toBe(0)
  })
})

describe('buildThreadRelation — receipts and ordering', () => {
  it('prefers the shared entity over the shared country — the more specific basis', () => {
    const rel = build([t('a', ['UA'], ['Zelensky']), t('b', ['UA'], ['Zelensky'])], 'a')
    expect(rel.related[0].receipt).toBe('Zelensky')
  })

  it('keeps the pool order of the rows it surfaces', () => {
    const pool = [t('x', ['UA']), t('a', ['UA']), t('y', ['UA']), t('z', ['CO'])]
    const rel = build(pool, 'a')
    expect(rel.related.map(r => r.thread.thread_id)).toEqual(['x', 'y'])
  })

  it('falls back to the raw code when the resolver does not name a country', () => {
    const rel = buildThreadRelation([t('a', ['ZZ']), t('b', ['ZZ'])], 'a')
    expect(rel.related[0].receipt).toBe('ZZ')
  })

  it('is inactive when the anchor has no basis at all', () => {
    const rel = build([t('a'), t('b', ['US'], ['Donald Trump'])], 'a')
    expect(rel.active).toBe(false)
  })

  it('is inactive when the anchor has a basis but nothing else shares it', () => {
    const rel = build([t('a', ['CO']), t('b', ['US'])], 'a')
    expect(rel.countries.size).toBe(1)
    expect(rel.active).toBe(false)
    expect(rel.related).toEqual([])
  })

  it('tolerates rows with missing entity and country arrays', () => {
    const pool = [{ thread_id: 'a', top_countries: ['UA'], top_entities: [] }, { thread_id: 'b' }] as never[]
    const rel = buildThreadRelation(pool, 'a')
    expect(rel.active).toBe(false)
  })
})
