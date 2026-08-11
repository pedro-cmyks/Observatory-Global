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

/**
 * What the console is actually showing. The console has TWO tabs but THREE
 * surfaces, because the Lens changes shape with focus — and collapsing that
 * 2x2 (tab x focus) into a boolean is how Live silently became inert while a
 * thread was open: the pill moved, the screen did not.
 */
export type MobileSurface = 'live' | 'lens-focused' | 'lens-field'

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

/**
 * The console surface a bar tap selects — or `null` for Brief, which is a
 * route and selects no console surface at all. Returning null (rather than a
 * plausible-looking 'lens') is what keeps the caller honest: coming back from
 * the Brief lands on whichever surface the user last chose.
 */
export function consoleTabFor(tab: MobileTab): ConsoleTab | null {
  if (tab === 'brief') return null
  return tab
}

/** The bar belongs to the two keep-alive panes and nowhere else. */
export function showsMobileTabBar(pathname: string): boolean {
  return pathname === '/app' || pathname === '/brief'
}

/**
 * The console's surface. The TAB decides first and Live short-circuits, so
 * Live is always the stream; focus steers only the Lens. That ordering is the
 * invariant: tapping a tab must always change what is on screen.
 */
export function surfaceFor(tab: ConsoleTab, lensHasFocus: boolean): MobileSurface {
  if (tab === 'live') return 'live'
  return lensHasFocus ? 'lens-focused' : 'lens-field'
}

/**
 * Which of the console's two mounted panes is showing.
 *
 * The ranked field is the Lens's unfocused state and nothing else; the read
 * pane serves BOTH remaining surfaces — the opened thing under `lens-focused`,
 * the firehose under `live`. Exported rather than inlined because two callers
 * need it (the shell, to pause the pane it is hiding, and <LensPanel/>, to
 * toggle it) and a second copy of the rule is how the pane and its `paused`
 * flag would drift apart.
 */
export function fieldVisible(surface: MobileSurface): boolean {
  return surface === 'lens-field'
}
