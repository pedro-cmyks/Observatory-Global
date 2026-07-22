/**
 * The shared trackball: free 3D rotation + zoom/pan gestures for a normalized
 * point cloud. Extracted verbatim from UniverseView (2026-07-03 "roll
 * disponible 3D... para donde sea") so the universe, the story constellation
 * and the investigation cloud all share ONE working implementation.
 *
 * Orientation is an accumulated 3×3 matrix (arcball), never Euler angles: no
 * gimbal lock, no clamp, any orientation.
 *
 * Thermal discipline (2026-07-03 kernel-panic post-mortem — a 60fps re-render
 * of a large SVG is exactly the compositor load that tripped the WindowServer
 * watchdog): ambient spin ticks at ~10fps, stops while dragging or hovering,
 * while the tab is hidden, while the PANEL is CSS-hidden (display:none does not
 * set document.hidden), and rests after 90s of no interaction.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent, type RefObject, type WheelEvent } from 'react'
import { IDENTITY_ROT, mul3, rotX, rotY, rotZ, type Rot3 } from '../lib/universeLayout'

export interface TrackballView { k: number; tx: number; ty: number }

export interface UseTrackballOptions {
  /** The canvas element — used for cursor-relative zoom, tap coordinates and
      the CSS-hidden check. */
  containerRef: RefObject<HTMLDivElement | null>
  /** Drag intent when no modifier is held. */
  navMode?: 'rotate' | 'pan' | 'roll'
  minZoom?: number
  maxZoom?: number
  /** Multiplier per wheel notch. */
  wheelStep?: number
  /** Ambient yaw when idle. Off by default: only the universe spins by itself. */
  ambient?: boolean
  /** External pause (a hover card is open, another view covers this one). */
  paused?: boolean
  /** A press that never moved: canvas-local coordinates of the tap. */
  onTap?: (lx: number, ly: number) => void
}

export interface Trackball {
  rot: Rot3
  setRot: React.Dispatch<React.SetStateAction<Rot3>>
  view: TrackballView
  setView: React.Dispatch<React.SetStateAction<TrackballView>>
  reset: () => void
  /** True while a drag/pinch is in flight (callers pause their own animation). */
  isDragging: () => boolean
  handlers: {
    onWheel: (e: WheelEvent<HTMLDivElement>) => void
    onPointerDown: (e: PointerEvent<HTMLDivElement>) => void
    onPointerMove: (e: PointerEvent<HTMLDivElement>) => void
    onPointerUp: (e: PointerEvent<HTMLDivElement>) => void
    onPointerLeave: (e: PointerEvent<HTMLDivElement>) => void
    onContextMenu: (e: { preventDefault: () => void }) => void
    onDragStart: (e: { preventDefault: () => void }) => void
  }
}

const DEFAULT_VIEW: TrackballView = { k: 1, tx: 0, ty: 0 }
/** Ambient yaw ≈ one turn per 105s. */
const AMBIENT_RATE = 0.06
const AMBIENT_TICK_MS = 100
const REST_AFTER_MS = 90_000
const TAP_SLOP_PX = 5

export function useTrackball({
  containerRef,
  navMode = 'rotate',
  minZoom = 0.6,
  maxZoom = 8,
  wheelStep = 1.12,
  ambient = false,
  paused = false,
  onTap,
}: UseTrackballOptions): Trackball {
  const [rot, setRot] = useState<Rot3>(IDENTITY_ROT)
  const [view, setView] = useState<TrackballView>(DEFAULT_VIEW)

  const draggingRef = useRef(false)
  const lastInteractionRef = useRef(performance.now())
  const dragRef = useRef<{
    lastX: number; lastY: number; downX: number; downY: number
    moved: boolean; mode: 'orbit' | 'roll' | 'pan'
  } | null>(null)
  const pointersRef = useRef<Map<number, { x: number; y: number }>>(new Map())
  const pinchRef = useRef<{ dist: number; cx: number; cy: number; tx: number; ty: number; k: number; angle: number } | null>(null)
  const viewRef = useRef(view)
  viewRef.current = view
  const pausedRef = useRef(paused)
  pausedRef.current = paused
  const onTapRef = useRef(onTap)
  onTapRef.current = onTap

  const clampZoom = useCallback(
    (k: number) => Math.min(maxZoom, Math.max(minZoom, k)),
    [maxZoom, minZoom],
  )

  const localPoint = useCallback((clientX: number, clientY: number) => {
    const rect = containerRef.current?.getBoundingClientRect()
    return { lx: clientX - (rect?.left ?? 0), ly: clientY - (rect?.top ?? 0) }
  }, [containerRef])

  const reset = useCallback(() => {
    setRot(IDENTITY_ROT)
    setView(DEFAULT_VIEW)
    lastInteractionRef.current = performance.now()
  }, [])

  useEffect(() => {
    if (!ambient) return
    let raf = 0
    let last = performance.now()
    let acc = 0
    const tick = (now: number) => {
      acc += now - last
      last = now
      if (acc >= AMBIENT_TICK_MS) {
        const resting = now - lastInteractionRef.current > REST_AFTER_MS
        // display:none does NOT set document.hidden — without this check the
        // SVG kept re-rendering behind a hidden mobile panel (battery burn).
        const panelHidden = containerRef.current !== null
          && containerRef.current.offsetParent === null
        if (!pausedRef.current && !draggingRef.current && !document.hidden && !resting && !panelHidden) {
          setRot(r => mul3(rotY((acc / 1000) * AMBIENT_RATE), r))
        }
        acc = 0
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [ambient, containerRef])

  const handlers = useMemo(() => ({
    onWheel: (e: WheelEvent<HTMLDivElement>) => {
      e.preventDefault()
      lastInteractionRef.current = performance.now()
      const factor = e.deltaY < 0 ? wheelStep : 1 / wheelStep
      const { lx, ly } = localPoint(e.clientX, e.clientY)
      setView(v => {
        const k = clampZoom(v.k * factor)
        return { k, tx: lx - (lx - v.tx) * (k / v.k), ty: ly - (ly - v.ty) * (k / v.k) }
      })
    },

    onPointerDown: (e: PointerEvent<HTMLDivElement>) => {
      e.preventDefault()
      try { (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId) } catch { /* synthetic/inactive pointer */ }
      draggingRef.current = true
      lastInteractionRef.current = performance.now()
      pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
      if (pointersRef.current.size === 2) {
        const pts = [...pointersRef.current.values()]
        pinchRef.current = {
          dist: Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y),
          cx: (pts[0].x + pts[1].x) / 2,
          cy: (pts[0].y + pts[1].y) / 2,
          angle: Math.atan2(pts[1].y - pts[0].y, pts[1].x - pts[0].x),
          tx: viewRef.current.tx, ty: viewRef.current.ty, k: viewRef.current.k,
        }
        dragRef.current = null
      } else {
        const mode: 'orbit' | 'roll' | 'pan' =
          (navMode === 'pan' || e.shiftKey || e.button === 2 || e.button === 1) ? 'pan'
          : (navMode === 'roll' || e.altKey || e.ctrlKey || e.metaKey) ? 'roll'
          : 'orbit'
        dragRef.current = {
          lastX: e.clientX, lastY: e.clientY,
          downX: e.clientX, downY: e.clientY, moved: false, mode,
        }
      }
    },

    onPointerMove: (e: PointerEvent<HTMLDivElement>) => {
      if (pointersRef.current.has(e.pointerId)) {
        pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
      }
      if (pinchRef.current && pointersRef.current.size === 2) {
        const pts = [...pointersRef.current.values()]
        const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y)
        const cx = (pts[0].x + pts[1].x) / 2
        const cy = (pts[0].y + pts[1].y) / 2
        const angle = Math.atan2(pts[1].y - pts[0].y, pts[1].x - pts[0].x)
        const p = pinchRef.current
        setView({
          k: clampZoom(p.k * (dist / Math.max(1, p.dist))),
          tx: p.tx + (cx - p.cx),
          ty: p.ty + (cy - p.cy),
        })
        const dRoll = angle - p.angle
        if (Math.abs(dRoll) > 1e-4) setRot(r => mul3(rotZ(dRoll), r))
        pinchRef.current = { ...p, angle }
        lastInteractionRef.current = performance.now()
        return
      }
      const d = dragRef.current
      if (!d) return
      lastInteractionRef.current = performance.now()
      const dx = e.clientX - d.lastX
      const dy = e.clientY - d.lastY
      d.lastX = e.clientX; d.lastY = e.clientY
      if (Math.hypot(e.clientX - d.downX, e.clientY - d.downY) > TAP_SLOP_PX) d.moved = true
      if (d.mode === 'pan') {
        setView(v => ({ ...v, tx: v.tx + dx, ty: v.ty + dy }))
      } else if (d.mode === 'roll') {
        setRot(r => mul3(rotZ(dx * 0.01), r))
      } else {
        // free trackball orbit: screen-space incremental rotation, premultiplied
        // → no fixed up-vector, roll emerges from combined drags
        setRot(r => mul3(mul3(rotX(-dy * 0.006), rotY(dx * 0.006)), r))
      }
    },

    onPointerUp: (e: PointerEvent<HTMLDivElement>) => {
      const d = dragRef.current
      if (d && !d.moved && pointersRef.current.size === 1) {
        const { lx, ly } = localPoint(e.clientX, e.clientY)
        onTapRef.current?.(lx, ly)
      }
      pointersRef.current.delete(e.pointerId)
      if (pointersRef.current.size < 2) pinchRef.current = null
      if (pointersRef.current.size === 0) { dragRef.current = null; draggingRef.current = false }
    },

    onPointerLeave: (e: PointerEvent<HTMLDivElement>) => {
      pointersRef.current.delete(e.pointerId)
      if (pointersRef.current.size === 0) {
        pinchRef.current = null; dragRef.current = null; draggingRef.current = false
      }
    },

    onContextMenu: (e: { preventDefault: () => void }) => e.preventDefault(),
    onDragStart: (e: { preventDefault: () => void }) => e.preventDefault(),
  }), [clampZoom, localPoint, navMode, wheelStep])

  return {
    rot, setRot, view, setView, reset,
    isDragging: () => draggingRef.current,
    handlers,
  }
}
