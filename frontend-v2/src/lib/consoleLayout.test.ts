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
  shellMetricsFrom,
  MIN_SHELL_WIDTH,
  MIN_SHELL_HEIGHT,
  snapResizedItem,
} from './consoleLayout'
import type { LayoutBucket } from './consoleLayout'
import type { LayoutItem } from 'react-grid-layout'

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

describe('snapResizedItem', () => {
  const box = (i: string, x: number, y: number, w: number, h: number, extra: Partial<LayoutItem> = {}): LayoutItem =>
    ({ i, x, y, w, h, minW: 3, minH: 4, ...extra })

  it('snaps the right edge to a neighboring panel left edge within threshold (different row band)', () => {
    // radar right edge = 9; threads left edge = 10 (in a lower band, no adjacency)
    const layout = [
      box('radar', 0, 0, 9, 6),
      box('threads', 10, 6, 8, 6),
    ]
    const out = snapResizedItem(layout, 'radar', { threshold: 1 })
    expect(out.find(l => l.i === 'radar')?.w).toBe(10)
    // the neighbor is never moved or shrunk
    expect(out.find(l => l.i === 'threads')).toEqual(layout[1])
  })

  it('snaps the right edge to the container edge within threshold', () => {
    const layout = [
      box('radar', 14, 0, 9, 12), // right edge 23, container 24
      box('threads', 0, 0, 12, 12),
    ]
    const out = snapResizedItem(layout, 'radar', { threshold: 1 })
    expect(out.find(l => l.i === 'radar')?.w).toBe(10) // reaches col 24
  })

  it('snaps the bottom edge to the container bottom within threshold', () => {
    const layout = [
      box('radar', 0, 0, 10, GRID_ROWS - 1), // bottom edge 23, container 24
      box('threads', 12, 0, 12, 12),
    ]
    const out = snapResizedItem(layout, 'radar', { threshold: 1 })
    expect(out.find(l => l.i === 'radar')?.h).toBe(GRID_ROWS)
  })

  it('fills a small dead gap up to the next obstacle', () => {
    // one dead column between radar and threads (right edge 9, obstacle at 10)
    const layout = [
      box('radar', 0, 0, 9, 12),
      box('threads', 10, 0, 14, 12),
    ]
    const out = snapResizedItem(layout, 'radar', { threshold: 1 })
    expect(out.find(l => l.i === 'radar')?.w).toBe(10)
  })

  it('does not snap beyond the threshold', () => {
    // gap of 2 with threshold 1 → untouched
    const layout = [
      box('radar', 0, 0, 8, 12),
      box('threads', 10, 0, 14, 12),
    ]
    const out = snapResizedItem(layout, 'radar', { threshold: 1 })
    expect(out).toEqual(layout)
  })

  it('never creates an overlap: a candidate edge behind an obstacle is rejected', () => {
    // stream's left edge (10) is within threshold of radar's right edge (9),
    // but expanding radar to 10 would overlap threads (x 9..15, y 0..6).
    const layout = [
      box('radar', 0, 0, 9, 12),
      box('threads', 9, 0, 6, 6),
      box('stream', 10, 6, 5, 6),
    ]
    const out = snapResizedItem(layout, 'radar', { threshold: 1 })
    expect(out).toEqual(layout)
  })

  it('respects minW: never shrink-snaps below the minimum width', () => {
    // radar w=3=minW; a neighbor alignment line at x=2 (delta 1) may not shrink it to w=2
    const layout = [
      box('radar', 0, 0, 3, 12),
      box('threads', 2, 12, 10, 8),
    ]
    const out = snapResizedItem(layout, 'radar', { threshold: 1 })
    expect(out.find(l => l.i === 'radar')?.w).toBe(3)
  })

  it('is idempotent: snapping a snapped layout is a no-op', () => {
    const layout = [
      box('radar', 0, 0, 9, 11),
      box('threads', 10, 0, 14, GRID_ROWS),
      box('dock', 0, 12, 9, GRID_ROWS - 12),
    ]
    const once = snapResizedItem(layout, 'radar', { threshold: 1 })
    const twice = snapResizedItem(once, 'radar', { threshold: 1 })
    expect(twice).toEqual(once)
  })

  it('returns a copied layout unchanged when the item id is unknown', () => {
    const layout = [box('radar', 0, 0, 9, 12)]
    const out = snapResizedItem(layout, 'nope', { threshold: 1 })
    expect(out).toEqual(layout)
    expect(out).not.toBe(layout)
  })

  it('defaults threshold to 1 grid unit', () => {
    const layout = [
      box('radar', 14, 0, 9, 12),
      box('threads', 0, 0, 12, 12),
    ]
    const out = snapResizedItem(layout, 'radar')
    expect(out.find(l => l.i === 'radar')?.w).toBe(10)
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

describe('shellMetricsFrom (hidden-pane freeze guard)', () => {
  const prev = { width: 1440, height: 857 }

  it('measures width and viewport-fit height from a visible shell', () => {
    expect(shellMetricsFrom({ clientWidth: 2200, top: 43 }, 1200, prev))
      .toEqual({ width: 2200, height: 1157 })
  })

  // THE BUG: the Brief↔console keep-alive shell hides the console with
  // display:none, so a resize fired while the console is hidden measured a
  // 0-wide box, clamped the grid to its 320px minimum, and FROZE there —
  // nothing re-measured on re-show, so only a reload recovered.
  it('REJECTS a zero-width measurement (hidden pane) and keeps the last good one', () => {
    expect(shellMetricsFrom({ clientWidth: 0, top: 0 }, 1000, prev)).toBe(prev)
  })

  it('rejects negative / non-finite boxes too', () => {
    expect(shellMetricsFrom({ clientWidth: -5, top: 0 }, 1000, prev)).toBe(prev)
    expect(shellMetricsFrom({ clientWidth: NaN, top: 43 }, 1000, prev)).toBe(prev)
    expect(shellMetricsFrom({ clientWidth: 1440, top: NaN }, 1000, prev)).toBe(prev)
  })

  it('returns the SAME object when nothing changed (no re-render churn)', () => {
    const same = shellMetricsFrom({ clientWidth: 1440, top: 43 }, 900, prev)
    expect(same).toBe(prev)
  })

  it('floors width and height at their minimums for degenerate-but-real boxes', () => {
    const out = shellMetricsFrom({ clientWidth: 100, top: 500 }, 520, prev)
    expect(out).toEqual({ width: MIN_SHELL_WIDTH, height: MIN_SHELL_HEIGHT })
  })

  it('a hidden resize followed by a re-show recovers the true width', () => {
    // hidden resize 1440 -> 2500: measurement rejected, previous kept
    const whileHidden = shellMetricsFrom({ clientWidth: 0, top: 0 }, 1300, prev)
    expect(whileHidden).toEqual(prev)
    // re-show re-measures: the grid lands on the real viewport, no reload
    const onShow = shellMetricsFrom({ clientWidth: 2500, top: 43 }, 1300, whileHidden)
    expect(onShow).toEqual({ width: 2500, height: 1257 })
    expect(bucketForWidth(onShow.width)).toBe('big')
  })
})

describe('bucket re-resolution after a resize', () => {
  it('crossing a bucket edge serves that bucket layout, preset when none saved', () => {
    const saved = { laptop: defaultLayoutFor('laptop') }
    expect(bucketForWidth(1440)).toBe('laptop')
    expect(bucketForWidth(2500)).toBe('big')
    expect(layoutForBucket('big', saved)).toEqual(defaultLayoutFor('big'))
  })

  it('falls back to the preset when the persisted layout for the new bucket is invalid', () => {
    const saved = { big: [{ i: 'radar', x: 0, y: 0, w: 9 }] as unknown as LayoutItem[] }
    expect(isValidLayout(saved.big)).toBe(false)
    expect(layoutForBucket('big', saved)).toEqual(defaultLayoutFor('big'))
  })

  it('falls back to the preset when the persisted layout no longer fills the grid width', () => {
    // Shrink every panel that touches the right edge, so the layout leaves a
    // dead strip at columns 20-24 — the stale-preset shape layoutFillsWidth
    // exists to catch.
    const narrow = defaultLayoutFor('desktop').map(l =>
      l.i === 'threads' ? { ...l, w: 5 } : l.i === 'dock' ? { ...l, w: 10 } : l,
    )
    expect(isValidLayout(narrow)).toBe(true)
    expect(layoutFillsWidth(narrow)).toBe(false)
    expect(layoutForBucket('desktop', { desktop: narrow })).toEqual(defaultLayoutFor('desktop'))
  })
})
