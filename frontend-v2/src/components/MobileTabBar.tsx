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
  const { consoleTab, setConsoleTab } = useMobileNav()

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

  return (
    <>
      {/* Lens<->Live swaps the whole visible surface with no route change, so
          there is nothing for a screen reader to announce on its own. Name the
          surface here rather than stealing focus — the reading cursor stays
          where the user put it. (Task 7: once <LensPanel/> owns a real
          heading, moving focus to it becomes the better option.) */}
      <div className="mobile-tabbar-announce" role="status" aria-live="polite">
        {activeLabel}
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
