// Console panel grid model (#233 revival).
// Pure helpers for the resizable/movable L2 cockpit grid: width buckets,
// per-bucket default presets, localStorage persistence, viewport-fit row
// height. The React wiring lives in App.tsx; everything here is testable
// without a DOM.
import type { LayoutItem } from 'react-grid-layout'

export type LayoutBucket = 'laptop' | 'desktop' | 'big'

export const GRID_COLS = 24
export const GRID_ROWS = 24
export const LAYOUT_STORAGE_KEY = 'atlas.console-layout.v2'
export const PANEL_IDS = ['radar', 'stream', 'threads', 'dock'] as const

const MIN_W = 3
const MIN_H = 4
const ROW_HEIGHT_FLOOR = 16

export function bucketForWidth(width: number): LayoutBucket {
  if (width >= 2400) return 'big'
  if (width >= 1600) return 'desktop'
  return 'laptop'
}

function item(i: string, x: number, y: number, w: number, h: number): LayoutItem {
  return { i, x, y, w, h, minW: MIN_W, minH: MIN_H }
}

const PRESETS: Record<LayoutBucket, LayoutItem[]> = {
  // Mirrors today's cockpit: map | stream | threads over a full-width dock.
  laptop: [
    item('radar', 0, 0, 9, 16),
    item('stream', 9, 0, 9, 16),
    item('threads', 18, 0, 6, 16),
    item('dock', 0, 16, 24, 8),
  ],
  desktop: [
    item('radar', 0, 0, 10, 16),
    item('stream', 10, 0, 8, 16),
    item('threads', 18, 0, 6, 16),
    item('dock', 0, 16, 24, 8),
  ],
  // Big monitors: four full-height columns — the dock earns a column instead
  // of a mostly-empty strip.
  big: [
    item('radar', 0, 0, 9, GRID_ROWS),
    item('stream', 9, 0, 6, GRID_ROWS),
    item('threads', 15, 0, 5, GRID_ROWS),
    item('dock', 20, 0, 4, GRID_ROWS),
  ],
}

export function defaultLayoutFor(bucket: LayoutBucket): LayoutItem[] {
  return PRESETS[bucket].map(l => ({ ...l }))
}

export function isValidLayout(l: unknown): l is LayoutItem[] {
  if (!Array.isArray(l) || l.length !== PANEL_IDS.length) return false
  const ids = new Set<string>()
  for (const entry of l) {
    if (typeof entry !== 'object' || entry === null) return false
    const e = entry as Record<string, unknown>
    if (typeof e.i !== 'string') return false
    for (const k of ['x', 'y', 'w', 'h'] as const) {
      if (typeof e[k] !== 'number' || Number.isNaN(e[k])) return false
    }
    ids.add(e.i)
  }
  return PANEL_IDS.every(id => ids.has(id))
}

type StorageReader = Pick<Storage, 'getItem'>
type StorageWriter = Pick<Storage, 'setItem' | 'getItem'>
type StorageRemover = Pick<Storage, 'removeItem'>

function defaultStorage(): Storage | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage
  } catch {
    return null
  }
}

export function loadSavedLayouts(
  storage: StorageReader | null = defaultStorage(),
): Partial<Record<LayoutBucket, LayoutItem[]>> {
  if (!storage) return {}
  try {
    const raw = storage.getItem(LAYOUT_STORAGE_KEY)
    if (!raw) return {}
    const parsed: unknown = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null) return {}
    const out: Partial<Record<LayoutBucket, LayoutItem[]>> = {}
    for (const bucket of ['laptop', 'desktop', 'big'] as const) {
      const candidate = (parsed as Record<string, unknown>)[bucket]
      if (isValidLayout(candidate)) out[bucket] = candidate
    }
    return out
  } catch {
    return {}
  }
}

export function saveLayout(
  bucket: LayoutBucket,
  layout: readonly LayoutItem[],
  storage: StorageWriter | null = defaultStorage(),
): void {
  if (!storage) return
  try {
    const all = loadSavedLayouts(storage)
    all[bucket] = [...layout]
    storage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(all))
  } catch {
    // Quota/serialization failures are non-fatal — layout just won't persist.
  }
}

export function clearSavedLayouts(storage: StorageRemover | null = defaultStorage()): void {
  if (!storage) return
  try {
    storage.removeItem(LAYOUT_STORAGE_KEY)
  } catch {
    // ignore
  }
}

export function layoutForBucket(
  bucket: LayoutBucket,
  saved: Partial<Record<LayoutBucket, LayoutItem[]>>,
): LayoutItem[] {
  const candidate = saved[bucket]
  return isValidLayout(candidate) ? candidate : defaultLayoutFor(bucket)
}

// Row height so GRID_ROWS rows + margins + padding exactly fill the available
// pixel height (no-scroll cockpit at the default presets).
export function rowHeightFor(availableHeightPx: number, marginY: number, paddingY: number): number {
  const usable = availableHeightPx - 2 * paddingY - (GRID_ROWS - 1) * marginY
  return Math.max(ROW_HEIGHT_FLOOR, Math.floor(usable / GRID_ROWS))
}
