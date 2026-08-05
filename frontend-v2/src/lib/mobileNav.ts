/**
 * The phone's three-tab model.
 *
 * Brief is the home (the glance). Lens is the one surface that re-scopes to
 * whatever you are looking at. Live is the raw stream. Map, Threads, Pulse and
 * Universe are not tabs any more — they are absorbed as sections of the Lens.
 *
 * The bar only NAVIGATES. It holds no data, which is what makes it safe to
 * render at the root across both keep-alive routes.
 */
export type MobileTab = 'brief' | 'lens' | 'live'
export type ConsoleTab = 'lens' | 'live'

export interface MobileTabDef {
  id: MobileTab
  label: string
  glyph: string
}

export const MOBILE_TABS: MobileTabDef[] = [
  { id: 'brief', label: 'Brief', glyph: '◈' },
  { id: 'lens', label: 'Lens', glyph: '◎' },
  { id: 'live', label: 'Live', glyph: '≋' },
]

export function routeForTab(tab: MobileTab): string {
  return tab === 'brief' ? '/brief' : '/app'
}

export function tabForRoute(pathname: string, rememberedConsoleTab: ConsoleTab): MobileTab {
  if (pathname === '/brief') return 'brief'
  if (pathname === '/app') return rememberedConsoleTab
  return 'lens'
}

export function consoleTabFor(tab: MobileTab): ConsoleTab {
  return tab === 'live' ? 'live' : 'lens'
}
