import { describe, it, expect } from 'vitest'
import { createScrollLock, type ScrollLockTarget } from './scrollLock'

const target = (overflow = ''): ScrollLockTarget => ({ style: { overflow } })

describe('createScrollLock', () => {
  it('locks on the first acquire and restores the ORIGINAL value on the last release', () => {
    const t = target('')
    const lock = createScrollLock(t)
    const release = lock.acquire()
    expect(t.style.overflow).toBe('hidden')
    release()
    expect(t.style.overflow).toBe('')
  })

  it('preserves a non-empty original value rather than clearing it', () => {
    const t = target('scroll')
    const lock = createScrollLock(t)
    const release = lock.acquire()
    expect(t.style.overflow).toBe('hidden')
    release()
    expect(t.style.overflow).toBe('scroll')
  })

  // THE MEASURED BUG, half one. Two owners of one global style that each
  // save/restore independently only survive STRICT nesting. Released out of
  // order, the outer owner restores the inner owner's 'hidden' and the page
  // never scrolls again — reload the only exit.
  it('survives out-of-order release: inner released first', () => {
    const t = target('')
    const lock = createScrollLock(t)
    const a = lock.acquire()
    const b = lock.acquire()
    b()
    expect(t.style.overflow).toBe('hidden') // still one holder
    a()
    expect(t.style.overflow).toBe('')
  })

  it('survives out-of-order release: outer released first', () => {
    const t = target('')
    const lock = createScrollLock(t)
    const a = lock.acquire()
    const b = lock.acquire()
    a()
    expect(t.style.overflow).toBe('hidden')
    b()
    expect(t.style.overflow).toBe('')
  })

  it('treats a second release from the same holder as a no-op', () => {
    const t = target('')
    const lock = createScrollLock(t)
    const a = lock.acquire()
    const b = lock.acquire()
    a()
    a()
    a()
    expect(t.style.overflow).toBe('hidden') // b still holds it
    b()
    expect(t.style.overflow).toBe('')
  })

  // THE MEASURED BUG, half two. The keep-alive shell HIDES the console
  // (display:none) instead of unmounting it, so a held lock outlives the
  // surface that took it — measured live on prod: body.style.overflow stayed
  // 'hidden' on /brief with scrollHeight 13544 and scrollY pinned at 0.
  it('releases the page while suspended even though the holder is still mounted', () => {
    const t = target('')
    const lock = createScrollLock(t)
    lock.acquire()
    expect(t.style.overflow).toBe('hidden')
    lock.setSuspended(true)
    expect(t.style.overflow).toBe('')
    expect(lock.holders).toBe(1) // the holder never let go; the page is free anyway
  })

  it('re-applies on resume while a holder is still standing', () => {
    const t = target('')
    const lock = createScrollLock(t)
    lock.acquire()
    lock.setSuspended(true)
    lock.setSuspended(false)
    expect(t.style.overflow).toBe('hidden')
  })

  it('does not re-apply on resume once every holder has let go', () => {
    const t = target('')
    const lock = createScrollLock(t)
    const release = lock.acquire()
    lock.setSuspended(true)
    release()
    lock.setSuspended(false)
    expect(t.style.overflow).toBe('')
    expect(lock.holders).toBe(0)
  })

  it('acquiring while suspended does not lock the page', () => {
    const t = target('')
    const lock = createScrollLock(t)
    lock.setSuspended(true)
    lock.acquire()
    expect(t.style.overflow).toBe('')
    lock.setSuspended(false)
    expect(t.style.overflow).toBe('hidden')
  })

  it('never reports locked with zero holders, however the calls interleave', () => {
    const t = target('')
    const lock = createScrollLock(t)
    const a = lock.acquire()
    lock.setSuspended(true)
    const b = lock.acquire()
    a()
    lock.setSuspended(false)
    b()
    lock.setSuspended(true)
    lock.setSuspended(false)
    expect(lock.holders).toBe(0)
    expect(lock.locked).toBe(false)
    expect(t.style.overflow).toBe('')
  })

  it('is idempotent under repeated suspend calls of the same value', () => {
    const t = target('auto')
    const lock = createScrollLock(t)
    lock.acquire()
    lock.setSuspended(true)
    lock.setSuspended(true)
    lock.setSuspended(false)
    lock.setSuspended(false)
    expect(t.style.overflow).toBe('hidden')
  })
})
