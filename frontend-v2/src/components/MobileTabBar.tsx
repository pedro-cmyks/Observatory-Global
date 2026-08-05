import { useLocation, useNavigate } from 'react-router-dom'
import { useIsMobile } from '../hooks/useIsMobile'
import { useMobileNav } from '../contexts/MobileNavContext'
import {
  MOBILE_TABS,
  routeForTab,
  tabForRoute,
  consoleTabFor,
  showsMobileTabBar,
  type MobileTab,
} from '../lib/mobileNav'
import { scopeTitle } from '../lib/lensScope'
import './MobileTabBar.css'

/**
 * Rendered ONCE at the root, outside <Routes>, so both keep-alive panes
 * (/app and /brief) carry the same bar. Switching to Brief is a route change
 * the keep-alive shell answers instantly — no remount, no refetch.
 */
export function MobileTabBar() {
  const isMobile = useIsMobile()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { consoleTab, setConsoleTab, trail } = useMobileNav()

  const onTap = (tab: MobileTab) => {
    // null = Brief, which selects no console surface: the console keeps
    // whatever the user last chose, so returning lands where they left.
    const next = consoleTabFor(tab)
    if (next) setConsoleTab(next)
    const route = routeForTab(tab)
    if (route !== pathname) navigate(route)
  }

  if (!isMobile) return null
  if (!showsMobileTabBar(pathname)) return null

  const active = tabForRoute(pathname, consoleTab)
  const activeLabel = MOBILE_TABS.find((t) => t.id === active)?.label ?? ''
  // The Lens is the one tab whose name does not tell you what is on it, so it
  // announces its scope too. The trail's head is derived from the console's
  // focus state, so this can never name something the surface is not showing.
  const announced = active === 'lens' && trail.length > 0
    ? `${activeLabel} · ${scopeTitle(trail[trail.length - 1])}`
    : activeLabel

  return (
    <>
      {/* Lens<->Live swaps the whole visible surface with no route change, so
          there is nothing for a screen reader to announce on its own. Name the
          surface here rather than stealing focus — the reading cursor stays
          where the user put it.
          Task 7 weighed moving focus to the Lens heading instead and kept the
          announcement: the Lens surface also swaps when the SCOPE changes (a
          Brief deep-link, a thread opened from another panel), and a focus
          move on those would yank the cursor with no gesture behind it.
          Distinguishing "tap" from "scope change" needs the bar to tell the
          Lens a tap happened — plumbing bought for one case. So the Lens got
          a real <h2> heading to navigate BY, and this region carries what the
          focus move was going to deliver: the scope's name. */}
      <div className="mobile-tabbar-announce" role="status" aria-live="polite">
        {announced}
      </div>
      <nav className="mobile-tabbar" aria-label="Atlas sections" data-tour="mobile-tabs">
        {MOBILE_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={active === t.id ? 'active' : ''}
            /* Brief is a real route, so it is the current PAGE. Lens and Live
               change content in place, so they are merely current — 'page'
               there would tell a screen reader a navigation happened. */
            aria-current={active === t.id ? (t.id === 'brief' ? 'page' : 'true') : undefined}
            onClick={() => onTap(t.id)}
          >
            <span className="mobile-tab-glyph">{t.glyph}</span>
            {t.label}
          </button>
        ))}
      </nav>
    </>
  )
}
