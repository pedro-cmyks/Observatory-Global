// Console panel grid model (#233 revival).
// Pure helpers for the resizable/movable L2 cockpit grid: width buckets,
// per-bucket default presets, localStorage persistence, viewport-fit row
// height. The React wiring lives in App.tsx; everything here is testable
// without a DOM.
import type { LayoutItem } from 'react-grid-layout'

export type LayoutBucket = 'laptop' | 'desktop' | 'big'

export const GRID_COLS = 24
export const GRID_ROWS = 24
// v3 (2026-07-16): the default arrangement changed to Ocean-v2 (Pedro's pick)
// — bump the key once so stale 3-column saved layouts reset to the new preset.
export const LAYOUT_STORAGE_KEY = 'atlas.console-layout.v3'
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
  // Ocean arrangement, v2 (Pedro 2026-07-16, arranged live by hand): the MAP
  // is the hero — wide, top-left — with the SIGNAL STREAM reading directly
  // under it; NARRATIVE THREADS take the full-height right column; the Intel
  // Dock is a full-width strip below. Presets are starting points —
  // drag/resize/persist/reset all still apply; reset returns HERE.
  laptop: [
    item('radar', 0, 0, 14, 12),
    item('stream', 0, 12, 14, 6),
    item('threads', 14, 0, 10, 18),
    item('dock', 0, 18, 24, 6),
  ],
  desktop: [
    item('radar', 0, 0, 15, 12),
    item('stream', 0, 12, 15, 6),
    item('threads', 15, 0, 9, 18),
    item('dock', 0, 18, 24, 6),
  ],
  // Big monitors: four full-height columns — the dock earns a column instead
  // of a mostly-empty strip (matches the reference console at 4K).
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

// A layout "fills the grid width" when its rightmost panel edge reaches the
// last column. Stale saved layouts from an older preset (or a bucket that
// used fewer columns) can leave a dead strip on the right — those get
// discarded in favour of the current preset rather than persisting the gap.
export function layoutFillsWidth(layout: readonly LayoutItem[]): boolean {
  let maxRight = 0
  for (const l of layout) maxRight = Math.max(maxRight, l.x + l.w)
  return maxRight >= GRID_COLS
}

export function layoutForBucket(
  bucket: LayoutBucket,
  saved: Partial<Record<LayoutBucket, LayoutItem[]>>,
): LayoutItem[] {
  const candidate = saved[bucket]
  if (isValidLayout(candidate) && layoutFillsWidth(candidate)) return candidate
  return defaultLayoutFor(bucket)
}

// --- Resize snap ------------------------------------------------------------
// When a panel resize ends, its right/bottom edges "clip" to the alignment
// lines the rest of the grid already draws: any neighboring panel edge or the
// container edge within `threshold` grid units. A small dead gap (<= threshold)
// against the next obstacle gets absorbed — the panel expands to fill it.
// Pure: only the resized item ever changes; neighbors are never moved or
// shrunk; minW/minH and the grid bounds are respected; never creates overlap.

export interface SnapOptions {
  threshold?: number
}

interface Rect {
  x: number
  y: number
  w: number
  h: number
}

function rectsOverlap(a: Rect, b: Rect): boolean {
  return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h
}

// Pick the best snap target for one edge (right or bottom). Candidates are
// neighbor edges + the container edge; nearest wins, ties prefer expansion
// (fill over shrink). A candidate that would push the item below its minimum,
// past the container, or into another panel is skipped. When nothing within
// threshold qualifies, the current edge stays — which also makes the snap
// idempotent (a snapped edge sits at delta 0 of its own candidate line).
function snapEdge(
  currentEdge: number,
  fixedStart: number,
  minSize: number,
  containerEnd: number,
  candidates: readonly number[],
  fits: (edge: number) => boolean,
  threshold: number,
): number {
  let best = currentEdge
  let bestDelta = Number.POSITIVE_INFINITY
  for (const c of candidates) {
    if (c - fixedStart < minSize) continue
    if (c > containerEnd) continue
    const delta = Math.abs(c - currentEdge)
    if (delta > threshold) continue
    if (!fits(c)) continue
    if (delta < bestDelta || (delta === bestDelta && c > best)) {
      best = c
      bestDelta = delta
    }
  }
  return best
}

export function snapResizedItem(
  layout: readonly LayoutItem[],
  itemId: string,
  opts: SnapOptions = {},
): LayoutItem[] {
  const threshold = opts.threshold ?? 1
  const out = layout.map(l => ({ ...l }))
  const item = out.find(l => l.i === itemId)
  if (!item) return out
  const others = out.filter(l => l.i !== itemId)

  const noOverlap = (rect: Rect) => others.every(o => !rectsOverlap(rect, o))

  // Right edge: neighbor left/right edges + the container's last column.
  const xCandidates: number[] = [GRID_COLS]
  for (const o of others) xCandidates.push(o.x, o.x + o.w)
  const newRight = snapEdge(
    item.x + item.w,
    item.x,
    item.minW ?? 1,
    GRID_COLS,
    xCandidates,
    edge => noOverlap({ x: item.x, y: item.y, w: edge - item.x, h: item.h }),
    threshold,
  )
  const newW = newRight - item.x

  // Bottom edge: neighbor top/bottom edges + the container's last row. Uses
  // the already-snapped width so the combined rect stays overlap-free.
  const yCandidates: number[] = [GRID_ROWS]
  for (const o of others) yCandidates.push(o.y, o.y + o.h)
  const newBottom = snapEdge(
    item.y + item.h,
    item.y,
    item.minH ?? 1,
    GRID_ROWS,
    yCandidates,
    edge => noOverlap({ x: item.x, y: item.y, w: newW, h: edge - item.y }),
    threshold,
  )

  item.w = newW
  item.h = newBottom - item.y
  return out
}

// Row height so GRID_ROWS rows + margins + padding exactly fill the available
// pixel height (no-scroll cockpit at the default presets).
export function rowHeightFor(availableHeightPx: number, marginY: number, paddingY: number): number {
  const usable = availableHeightPx - 2 * paddingY - (GRID_ROWS - 1) * marginY
  return Math.max(ROW_HEIGHT_FLOOR, Math.floor(usable / GRID_ROWS))
}

// --- Shell measurement ------------------------------------------------------
// The grid is NOT self-sizing: its pixel math is driven by a measured width and
// a measured available height. Both come from one observation of the shell, so
// they are resolved together and either accepted or rejected together.
//
// THE FREEZE (fixed 2026-08-12): the Brief↔console keep-alive shell (#239
// slice 2) keeps the console MOUNTED under `display:none` while the reader is
// on another route. A window resize fired in that state measured a 0-wide,
// top:0 box — the grid clamped to its 320px minimum and stayed there, because
// nothing re-measured when the console was shown again. Four panels then
// rendered as small boxes in the left ~310px of a wide viewport, and only a
// full reload recovered. A hidden box is an ABSENT measurement, not a small
// one: reject it and keep the last good metrics.

export const MIN_SHELL_WIDTH = 320
export const MIN_SHELL_HEIGHT = 320

export interface ShellMetrics {
  width: number
  height: number
}

export interface ShellBox {
  /** clientWidth — excludes the vertical scrollbar, so the grid never provokes a horizontal one. */
  clientWidth: number
  /** getBoundingClientRect().top — how far below the command bar + disclaimer strip the shell starts. */
  top: number
}

export function isMeasurableShell(box: ShellBox): boolean {
  return Number.isFinite(box.clientWidth) && box.clientWidth > 0 && Number.isFinite(box.top)
}

// Returns the metrics to apply. Returns `previous` BY REFERENCE when the
// observation is unusable (hidden/detached pane) or identical — callers can
// pass the result straight to setState without churning a render.
export function shellMetricsFrom(
  box: ShellBox,
  viewportHeight: number,
  previous: ShellMetrics,
): ShellMetrics {
  if (!isMeasurableShell(box) || !Number.isFinite(viewportHeight)) return previous
  const width = Math.max(MIN_SHELL_WIDTH, Math.round(box.clientWidth))
  const height = Math.max(MIN_SHELL_HEIGHT, Math.round(viewportHeight - box.top))
  if (width === previous.width && height === previous.height) return previous
  return { width, height }
}
