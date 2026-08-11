import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { ConsoleTab } from '../lib/mobileNav'
import { FIELD_SCOPE, popScope, pushScope, resetScope, trailsEqual, type LensScope } from '../lib/lensScope'

interface MobileNavValue {
  consoleTab: ConsoleTab
  setConsoleTab: (t: ConsoleTab) => void
  /** Where the Lens has been. Last entry = what it is showing now. */
  trail: LensScope[]
  /**
   * Record the scope the console is now showing. Called from ONE place — the
   * console's derivation effect — never from the doors that open things, so
   * the trail can never claim a scope the panel is not rendering.
   */
  focusLens: (s: LensScope) => void
  /**
   * Shorten the trail by one. ONLY valid paired with the console's own
   * `popPanel` in the same handler — alone it does not move the console, so
   * the head would sit wrong until the next scope change (it would NOT be
   * re-pushed immediately: the push effect is dep-gated on the derived scope,
   * which a bare pop does not change).
   *
   * Paired, it is what keeps a back-tap from DEEPENING the trail: peeling a
   * thread can reveal a country the trail never visited, and appending that
   * on top of the thread just closed leaves a breadcrumb pointing back at it
   * — one tap from a loop.
   */
  rewindLens: () => void
  /**
   * Empty the trail back to the field. ONLY valid paired with a console change
   * in the same handler — and only for a LATERAL PIVOT, a door that re-scopes
   * by clearing what the console was showing rather than opening something on
   * top of it. Today that is exactly one door: the Lens's `where it lives`
   * country row, which closes the thread it was measured from.
   *
   * Why the trail cannot just append there: the breadcrumb names
   * `trail[length - 2]` and Back peels ONE console dimension, so the two agree
   * only while the entries behind the head are still standing. After a pivot
   * they are not. See `resetScope` in lib/lensScope.ts for the measured case.
   */
  resetLens: () => void
}

// No default value on purpose: a silent no-op setter would let a consumer
// mounted outside the provider look like it works while every tap did nothing.
const Ctx = createContext<MobileNavValue | null>(null)

/**
 * Lives above <Routes>, so the trail survives the Brief<->console hop the same
 * way the keep-alive shell keeps the console's own focus state (#239 slice 2).
 * Both survive, and they cannot drift, because the trail is derived from that
 * state rather than kept alongside it.
 */
export function MobileNavProvider({ children }: { children: ReactNode }) {
  const [consoleTab, setConsoleTab] = useState<ConsoleTab>('lens')
  const [trail, setTrail] = useState<LensScope[]>([FIELD_SCOPE])

  const focusLens = useCallback((s: LensScope) => {
    // Identity guard: the caller re-derives its scope on every render, so a
    // value-equal push must return the SAME array or the context value churns
    // and every consumer re-renders for nothing.
    setTrail((prev) => {
      const next = pushScope(prev, s)
      return trailsEqual(prev, next) ? prev : next
    })
  }, [])

  const rewindLens = useCallback(() => {
    setTrail((prev) => {
      const next = popScope(prev)
      return trailsEqual(prev, next) ? prev : next
    })
  }, [])

  const resetLens = useCallback(() => {
    setTrail((prev) => resetScope(prev))
  }, [])

  const value = useMemo(
    () => ({ consoleTab, setConsoleTab, trail, focusLens, rewindLens, resetLens }),
    [consoleTab, trail, focusLens, rewindLens, resetLens],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useMobileNav(): MobileNavValue {
  const value = useContext(Ctx)
  if (!value) throw new Error('useMobileNav must be used inside <MobileNavProvider> (see main.tsx)')
  return value
}
