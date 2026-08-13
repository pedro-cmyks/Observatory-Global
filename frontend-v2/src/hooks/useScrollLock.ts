import { useEffect } from 'react'
import { acquirePageScrollLock } from '../lib/scrollLock'

/**
 * Hold the page scroll lock while `active`.
 *
 * Every caller shares ONE ref-counted lock (lib/scrollLock), so panels that
 * overlap — a search sheet opened over an already-open story read — can let go
 * in any order without stranding the page at `overflow: hidden`. Releasing on
 * unmount is NOT sufficient on the phone: the keep-alive shell hides the
 * console instead of unmounting it, so the shell suspends the lock off the
 * visible route. See lib/scrollLock's header for the measured case.
 */
export function useScrollLock(active: boolean): void {
  useEffect(() => {
    if (!active) return
    return acquirePageScrollLock()
  }, [active])
}
