import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { ConsoleTab } from '../lib/mobileNav'

interface MobileNavValue {
  consoleTab: ConsoleTab
  setConsoleTab: (t: ConsoleTab) => void
}

const Ctx = createContext<MobileNavValue>({ consoleTab: 'lens', setConsoleTab: () => {} })

export function MobileNavProvider({ children }: { children: ReactNode }) {
  const [consoleTab, setConsoleTab] = useState<ConsoleTab>('lens')
  const value = useMemo(() => ({ consoleTab, setConsoleTab }), [consoleTab])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useMobileNav() {
  return useContext(Ctx)
}
