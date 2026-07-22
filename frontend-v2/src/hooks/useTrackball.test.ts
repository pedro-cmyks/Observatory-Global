/**
 * The shared trackball's decision math.
 *
 * The hook itself is gesture plumbing, but three 3D surfaces (universe, story
 * constellation, investigation cloud) now depend on these three decisions
 * behaving identically: which gesture a press starts, whether a press was a
 * click or a drag, and how zoom anchors under the cursor. They were verified by
 * eye during the extraction; these tests pin them for the next refactor.
 */
import { describe, expect, it } from 'vitest'
import { TAP_SLOP_PX, dragMode, isTap, zoomAt } from './useTrackball'

describe('dragMode', () => {
  it('defaults to the surface nav mode when no modifier is held', () => {
    expect(dragMode('rotate', {})).toBe('orbit')
    expect(dragMode('pan', {})).toBe('pan')
    expect(dragMode('roll', {})).toBe('roll')
  })

  it('pans on shift, right button and middle button', () => {
    expect(dragMode('rotate', { shiftKey: true })).toBe('pan')
    expect(dragMode('rotate', { button: 2 })).toBe('pan')
    expect(dragMode('rotate', { button: 1 })).toBe('pan')
  })

  it('rolls on alt / ctrl / meta', () => {
    expect(dragMode('rotate', { altKey: true })).toBe('roll')
    expect(dragMode('rotate', { ctrlKey: true })).toBe('roll')
    expect(dragMode('rotate', { metaKey: true })).toBe('roll')
  })

  it('gives pan precedence over roll when both are asked for', () => {
    expect(dragMode('rotate', { shiftKey: true, altKey: true })).toBe('pan')
    expect(dragMode('roll', { shiftKey: true })).toBe('pan')
  })

  it('treats the primary button as no modifier', () => {
    expect(dragMode('rotate', { button: 0 })).toBe('orbit')
  })
})

describe('isTap', () => {
  it('accepts a press that never travelled past the slop', () => {
    expect(isTap(100, 100, 100, 100)).toBe(true)
    expect(isTap(100, 100, 100 + TAP_SLOP_PX, 100)).toBe(true)
    expect(isTap(100, 100, 103, 104)).toBe(true)   // exactly 5px diagonally
  })

  it('rejects a press that became a drag', () => {
    expect(isTap(100, 100, 106, 100)).toBe(false)
    expect(isTap(100, 100, 104, 104)).toBe(false)  // ~5.66px
  })
})

describe('zoomAt', () => {
  const view = { k: 1, tx: 0, ty: 0 }

  it('keeps whatever sits under the cursor fixed', () => {
    const lx = 120, ly = 80
    const next = zoomAt(view, 2, lx, ly, 0.6, 8)
    // the world point under the cursor before and after must be the same
    const before = { x: (lx - view.tx) / view.k, y: (ly - view.ty) / view.k }
    const after = { x: (lx - next.tx) / next.k, y: (ly - next.ty) / next.k }
    expect(after.x).toBeCloseTo(before.x, 9)
    expect(after.y).toBeCloseTo(before.y, 9)
  })

  it('clamps both ends', () => {
    expect(zoomAt(view, 100, 0, 0, 0.6, 8).k).toBe(8)
    expect(zoomAt(view, 0.001, 0, 0, 0.6, 8).k).toBe(0.6)
  })

  it('does not move the view when already clamped', () => {
    const maxed = { k: 8, tx: 30, ty: -10 }
    expect(zoomAt(maxed, 2, 50, 50, 0.6, 8)).toEqual(maxed)
  })
})
