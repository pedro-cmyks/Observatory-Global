import { useLocation, useNavigate } from 'react-router-dom'
import { useIsMobile } from '../hooks/useIsMobile'
import { useMobileNav } from '../contexts/MobileNavContext'
import { MOBILE_TABS, routeForTab, tabForRoute, consoleTabFor } from '../lib/mobileNav'
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

  if (!isMobile) return null
  if (pathname !== '/app' && pathname !== '/brief') return null

  const active = tabForRoute(pathname, consoleTab)

  return (
    <nav className="mobile-tabbar" aria-label="Atlas sections" data-tour="mobile-tabs">
      {MOBILE_TABS.map((t) => (
        <button
          key={t.id}
          type="button"
          className={active === t.id ? 'active' : ''}
          aria-current={active === t.id ? 'page' : undefined}
          onClick={() => {
            if (t.id !== 'brief') setConsoleTab(consoleTabFor(t.id))
            const route = routeForTab(t.id)
            if (route !== pathname) navigate(route)
          }}
        >
          <span className="mobile-tab-glyph">{t.glyph}</span>
          {t.label}
        </button>
      ))}
    </nav>
  )
}
