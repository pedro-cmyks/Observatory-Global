import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { ConsoleTab } from '../lib/mobileNav'

interface MobileNavValue {
  consoleTab: ConsoleTab
  setConsoleTab: (t: ConsoleTab) => void
}

// No default value on purpose: a silent no-op setter would let a consumer
// mounted outside the provider look like it works while every tap did nothing.
const Ctx = createContext<MobileNavValue | null>(null)

export function MobileNavProvider({ children }: { children: ReactNode }) {
  const [consoleTab, setConsoleTab] = useState<ConsoleTab>('lens')
  const value = useMemo(() => ({ consoleTab, setConsoleTab }), [consoleTab])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useMobileNav(): MobileNavValue {
  const value = useContext(Ctx)
  if (!value) throw new Error('useMobileNav must be used inside <MobileNavProvider> (see main.tsx)')
  return value
}
