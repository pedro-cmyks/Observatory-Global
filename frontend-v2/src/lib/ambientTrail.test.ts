import { beforeEach, describe, it, expect, vi } from 'vitest'
const backing = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (k: string) => backing.get(k) ?? null,
  setItem: (k: string, v: string) => void backing.set(k, String(v)),
  removeItem: (k: string) => void backing.delete(k),
  clear: () => backing.clear(),
})
beforeEach(() => backing.clear())
import { recordTrailStep, readTrail, TRAIL_CAP } from './ambientTrail'

describe('ambientTrail', () => {
  it('records steps newest-first and dedupes the immediate repeat', () => {
    recordTrailStep({ surface: 'thread', kind: 'theme', value: 'a', label: 'A' })
    recordTrailStep({ surface: 'thread', kind: 'theme', value: 'a', label: 'A' })
    recordTrailStep({ surface: 'country', kind: 'country', value: 'US', label: 'US' })
    expect(readTrail().map(s => s.value)).toEqual(['US', 'a'])
  })
  it('caps the ring buffer', () => {
    for (let i = 0; i < TRAIL_CAP + 10; i++) recordTrailStep({ surface: 's', kind: 'theme', value: `v${i}`, label: `${i}` })
    expect(readTrail().length).toBe(TRAIL_CAP)
  })
})
