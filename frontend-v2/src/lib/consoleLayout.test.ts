import { describe, it, expect } from 'vitest'
import {
  GRID_COLS,
  GRID_ROWS,
  LAYOUT_STORAGE_KEY,
  PANEL_IDS,
  bucketForWidth,
  clearSavedLayouts,
  defaultLayoutFor,
  isValidLayout,
  layoutFillsWidth,
  layoutForBucket,
  loadSavedLayouts,
  rowHeightFor,
  saveLayout,
} from './consoleLayout'
import type { LayoutBucket } from './consoleLayout'

function fakeStorage(initial: Record<string, string> = {}) {
  const store = new Map(Object.entries(initial))
  return {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => { store.set(k, v) },
    removeItem: (k: string) => { store.delete(k) },
    dump: () => Object.fromEntries(store),
  }
}

describe('bucketForWidth', () => {
  it('buckets laptop / desktop / big at 1600 and 2400 boundaries', () => {
    expect(bucketForWidth(1280)).toBe('laptop')
    expect(bucketForWidth(1599)).toBe('laptop')
    expect(bucketForWidth(1600)).toBe('desktop')
    expect(bucketForWidth(2399)).toBe('desktop')
    expect(bucketForWidth(2400)).toBe('big')
    expect(bucketForWidth(3840)).toBe('big')
  })
})

describe('defaultLayoutFor', () => {
  const buckets: LayoutBucket[] = ['laptop', 'desktop', 'big']

  it('covers exactly the four panel ids in every bucket', () => {
    for (const b of buckets) {
      const ids = defaultLayoutFor(b).map(l => l.i).sort()
      expect(ids).toEqual([...PANEL_IDS].sort())
    }
  })

  it('fits inside the grid: x+w <= cols and y+h <= rows', () => {
    for (const b of buckets) {
      for (const item of defaultLayoutFor(b)) {
        expect(item.x + item.w).toBeLessThanOrEqual(GRID_COLS)
        expect(item.y + item.h).toBeLessThanOrEqual(GRID_ROWS)
      }
    }
  })

  it('big preset is four full-height columns with no overlap', () => {
    const big = defaultLayoutFor('big')
    for (const item of big) {
      expect(item.y).toBe(0)
      expect(item.h).toBe(GRID_ROWS)
    }
    // non-overlap on x-ranges
    const sorted = [...big].sort((a, b) => a.x - b.x)
    for (let i = 1; i < sorted.length; i++) {
      expect(sorted[i].x).toBeGreaterThanOrEqual(sorted[i - 1].x + sorted[i - 1].w)
    }
  })

  it('every item carries sane minimums', () => {
    for (const b of buckets) {
      for (const item of defaultLayoutFor(b)) {
        expect(item.minW).toBeGreaterThanOrEqual(3)
        expect(item.minH).toBeGreaterThanOrEqual(4)
      }
    }
  })
})

describe('isValidLayout', () => {
  it('accepts a preset', () => {
    expect(isValidLayout(defaultLayoutFor('laptop'))).toBe(true)
  })
  it('rejects non-arrays, wrong ids, missing items, bad numbers', () => {
    expect(isValidLayout(null)).toBe(false)
    expect(isValidLayout({})).toBe(false)
    expect(isValidLayout([])).toBe(false)
    const missing = defaultLayoutFor('laptop').slice(0, 3)
    expect(isValidLayout(missing)).toBe(false)
    const renamed = defaultLayoutFor('laptop').map(l => ({ ...l, i: l.i === 'dock' ? 'dockk' : l.i }))
    expect(isValidLayout(renamed)).toBe(false)
    const nan = defaultLayoutFor('laptop').map(l => ({ ...l, w: Number.NaN }))
    expect(isValidLayout(nan)).toBe(false)
  })
})

describe('persistence', () => {
  it('save → load roundtrip per bucket', () => {
    const s = fakeStorage()
    const layout = defaultLayoutFor('desktop').map(l => ({ ...l, x: l.x }))
    saveLayout('desktop', layout, s)
    const loaded = loadSavedLayouts(s)
    expect(loaded.desktop).toEqual(layout)
    expect(loaded.laptop).toBeUndefined()
  })

  it('corrupt JSON → empty object', () => {
    const s = fakeStorage({ [LAYOUT_STORAGE_KEY]: '{not json' })
    expect(loadSavedLayouts(s)).toEqual({})
  })

  it('clearSavedLayouts removes the key', () => {
    const s = fakeStorage({ [LAYOUT_STORAGE_KEY]: '{}' })
    clearSavedLayouts(s)
    expect(s.dump()).toEqual({})
  })
})

describe('layoutFillsWidth', () => {
  it('is true for every preset (they span the full grid width)', () => {
    for (const b of ['laptop', 'desktop', 'big'] as LayoutBucket[]) {
      expect(layoutFillsWidth(defaultLayoutFor(b))).toBe(true)
    }
  })
  it('is false when the rightmost edge stops short of the last column', () => {
    const narrow = defaultLayoutFor('big').map(l => ({ ...l, w: Math.min(l.w, 4), x: 0 }))
    expect(layoutFillsWidth(narrow)).toBe(false)
  })
})

describe('layoutForBucket', () => {
  it('prefers a valid saved layout', () => {
    const custom = defaultLayoutFor('laptop').map(l => (l.i === 'radar' ? { ...l, w: 12 } : l))
    const out = layoutForBucket('laptop', { laptop: custom })
    expect(out.find(l => l.i === 'radar')?.w).toBe(12)
  })
  it('falls back to preset when saved is missing or invalid', () => {
    expect(layoutForBucket('big', {})).toEqual(defaultLayoutFor('big'))
    const broken = [{ i: 'radar', x: 0, y: 0, w: 4, h: 4 }]
    expect(layoutForBucket('big', { big: broken })).toEqual(defaultLayoutFor('big'))
  })
  it('discards a stale saved layout that leaves a dead strip on the right', () => {
    // Valid ids/shape but rightmost edge = 20 < 24 cols → migrate to preset.
    const narrow = defaultLayoutFor('big').map(l => ({ ...l, w: 5, x: { radar: 0, stream: 5, threads: 10, dock: 15 }[l.i] ?? 0 }))
    expect(isValidLayout(narrow)).toBe(true)
    expect(layoutFillsWidth(narrow)).toBe(false)
    expect(layoutForBucket('big', { big: narrow })).toEqual(defaultLayoutFor('big'))
  })
})

describe('rowHeightFor', () => {
  it('computes viewport-fit row height', () => {
    // h=852, marginY=6, paddingY=6: (852 - 12 - 23*6) / 24 = 29.25 → 29
    expect(rowHeightFor(852, 6, 6)).toBe(29)
  })
  it('never returns below the 16px floor', () => {
    expect(rowHeightFor(100, 6, 6)).toBe(16)
  })
})
