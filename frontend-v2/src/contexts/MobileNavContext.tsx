import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { ConsoleTab } from '../lib/mobileNav'
import { FIELD_SCOPE, pushScope, trailsEqual, type LensScope } from '../lib/lensScope'

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
  // There is deliberately NO `unfocusLens` here. Walking the trail back on its
  // own would be a silent no-op: the derivation re-pushes the scope the
  // console is still showing on the very next render. Back is the console's
  // own `popPanel` — the trail follows what that leaves behind.
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

  const value = useMemo(
    () => ({ consoleTab, setConsoleTab, trail, focusLens }),
    [consoleTab, trail, focusLens],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useMobileNav(): MobileNavValue {
  const value = useContext(Ctx)
  if (!value) throw new Error('useMobileNav must be used inside <MobileNavProvider> (see main.tsx)')
  return value
}
