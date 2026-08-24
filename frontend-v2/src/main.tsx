import { Component, StrictMode, Suspense, lazy, useEffect, useState, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { installWarmCache, bumpWarmCacheGeneration } from './lib/fetchWarmCache'
import { refreshDelightFeed } from './lib/delight'
import { installTooltips } from './lib/tooltips'

// Global [data-tip] controller: a single body-level fixed node that flips +
// clamps inside the viewport, so tips never slide under the header or crop off
// the screen edges. Delegation-based, so it covers every pane at once.
installTooltips()

// #239 slice 1: route switches remount the whole tree (Brief↔App) and refire
// every fetch — the warm cache paints the first request per URL instantly
// from the last known response and revalidates in the background.
installWarmCache()

// Loading-delight feed: refresh the localStorage fact cache off the critical
// path — the NEXT load reads it synchronously. Idle-time, best-effort.
if (typeof window !== 'undefined') {
  const idle = (window as Window & { requestIdleCallback?: (cb: () => void) => void }).requestIdleCallback
  if (idle) idle(() => refreshDelightFeed())
  else setTimeout(refreshDelightFeed, 4000)
}

function WarmCacheRouteReset() {
  const location = useLocation()
  useEffect(() => { bumpWarmCacheGeneration() }, [location.pathname])
  return null
}

// Suspense fallback for the lazy panes: full-viewport LoadingMoment (the same
// honest loading surface the Brief/universe already use — zero new bundle cost,
// it ships in the entry chunk via BriefNewspaper).
function PaneChunkLoading() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <LoadingMoment />
    </div>
  )
}

// #239 slice 2 — keep-alive shell. Route switches used to UNMOUNT the whole
// console/Brief tree (all state + the EE map died on every Brief↔App hop).
// With MapLibre deprecated (2026-07-04) the display:none crash class is gone:
// EE is a plain canvas that already handles display:none→block resizes. Each
// pane mounts on first visit and then stays alive hidden; deep-link params
// keep working because App/Brief are now URL-reactive with pathname guards.
function AppBriefKeepAlive() {
  const { pathname } = useLocation()
  const isApp = pathname === '/app'
  const isBrief = pathname === '/brief'
  const [appOn, setAppOn] = useState(isApp)
  const [briefOn, setBriefOn] = useState(isBrief)
  useEffect(() => { if (isApp) setAppOn(true) }, [isApp])
  useEffect(() => { if (isBrief) setBriefOn(true) }, [isBrief])
  return (
    <>
      {/* C5: each pane owns its own blast radius. Without these, a throw inside
          the console — likeliest exactly when a rate-limited backend is handing
          panels shapes they did not expect — propagated to RootErrorBoundary,
          which wraps <MobileTabBar/> too: the three tabs vanished with the
          surface that failed and a reload was the only control left. The bar is
          rendered at the root, outside <Routes>, specifically so it outlives
          whatever a pane does; boundarying the panes is what makes that true.
          `resetKey` is the visible route, so leaving for another tab and coming
          back is itself the retry. */}
      {(appOn || isApp) && (
        <div style={isApp ? { display: 'contents' } : { display: 'none' }}>
          <PaneErrorBoundary paneName="The console" resetKey={pathname}>
            {/* Suspense sits INSIDE the boundary so a failed chunk fetch (dead
                network mid-session) lands on the pane's own error card, and the
                route-keyed reset makes leaving+returning the retry. */}
            <Suspense fallback={<PaneChunkLoading />}>
              <App />
            </Suspense>
          </PaneErrorBoundary>
        </div>
      )}
      {(briefOn || isBrief) && (
        <div style={isBrief ? { display: 'contents' } : { display: 'none' }}>
          <PaneErrorBoundary paneName="The Brief" resetKey={pathname}>
            <BriefNewspaper />
          </PaneErrorBoundary>
        </div>
      )}
    </>
  )
}
import '@fontsource-variable/geist/index.css'
import '@fontsource-variable/geist-mono/index.css'
import './index.css'
import './styles/variables.css'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider } from './contexts/AuthContext'
import { EclipseProvider } from './contexts/EclipseModeContext'
import { EclipseTakeover } from './components/EclipseTakeover'
import { EclipseChrome } from './components/EclipseChrome'
import './components/eclipse.css'
import { StoryLensProvider } from './contexts/StoryLensContext'
import './components/storyLens.css'
import { MobileNavProvider } from './contexts/MobileNavContext'
import { MobileTabBar } from './components/MobileTabBar.tsx'
import { PaneErrorBoundary } from './components/PaneErrorBoundary.tsx'
import { LoadingMoment } from './components/LoadingMoment.tsx'
import { Landing } from './pages/Landing.tsx'
import { BriefNewspaper } from './pages/BriefNewspaper.tsx'

// Bundle split (2026-08-18, brief-input-blocking §residuo): the console (App —
// maps, panels, d3) used to be a STATIC import here, so /brief on a phone
// parsed+evaluated ~1.2MB of console code it would never mount (the keep-alive
// only mounts it on the first /app visit). React.lazy moves that entire subtree
// into its own chunk, fetched+evaluated on the first /app navigation instead of
// blocking the Brief masthead. Keep-alive semantics are untouched: the lazy
// component resolves once, mounts once, and then lives hidden forever — the
// Suspense fallback only ever shows during the one-time chunk load. Docs gets
// the same treatment (named export → default shim). Landing/Brief stay static:
// they ARE the entry surfaces ('/' and the PWA start_url).
const App = lazy(() => import('./App.tsx'))
const Docs = lazy(() => import('./pages/Docs.tsx').then((m) => ({ default: m.Docs })))
// Account lane (2026-08-24): the campaign registration door + the two pages
// Supabase emails land on. Ordinary <Routes> entries — they mount/unmount
// normally and never touch the App/Brief keep-alive shell. Lazy like Docs so
// the entry chunk stays lean; supabase-js already ships in the entry via
// AuthProvider, so the email-link token in the URL is consumed at root
// regardless of which chunk is still loading.
const Register = lazy(() => import('./pages/Register.tsx').then((m) => ({ default: m.Register })))
const AuthCallback = lazy(() => import('./pages/AuthCallback.tsx').then((m) => ({ default: m.AuthCallback })))
const AuthReset = lazy(() => import('./pages/AuthReset.tsx').then((m) => ({ default: m.AuthReset })))
import { InstallPrompt } from './components/InstallPrompt.tsx'

class RootErrorBoundary extends Component<{ children: ReactNode }, { crashed: boolean; message: string }> {
  state = { crashed: false, message: '' }
  static getDerivedStateFromError(error: Error) { return { crashed: true, message: error.message } }
  componentDidCatch(error: Error) { console.error('[RootErrorBoundary]', error) }
  render() {
    if (this.state.crashed) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#0a0f1a', color: '#94a3b8', fontFamily: 'system-ui, sans-serif', gap: 12 }}>
          <div style={{ fontSize: 32 }}>⚠</div>
          <div style={{ fontSize: 14, color: '#e2e8f0' }}>Something went wrong</div>
          {this.state.message && (
            <div style={{ fontSize: 11, color: '#f87171', maxWidth: 400, textAlign: 'center', wordBreak: 'break-all', padding: '0 16px' }}>{this.state.message}</div>
          )}
          <button onClick={() => { this.setState({ crashed: false, message: '' }); window.location.reload() }} style={{ marginTop: 8, padding: '6px 16px', background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#94a3b8', cursor: 'pointer', fontSize: 12 }}>Reload</button>
        </div>
      )
    }
    return this.props.children
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RootErrorBoundary>
      <ThemeProvider>
        <BrowserRouter>
          {/* accounts-v1: session + sync-engine lifecycle for every pane.
              Sits OUTSIDE Routes (and outside the keep-alive shell) so a
              route switch never tears down the auth session. */}
          <AuthProvider>
            <EclipseProvider>
              <StoryLensProvider>
                {/* #236 Task 6: which console surface the phone is showing —
                    shared state, because the tab bar lives at the root and the
                    console reads it. Outside <Routes>, like the panes it
                    drives, so a Brief↔console hop never resets it. */}
                <MobileNavProvider>
                  <WarmCacheRouteReset />
                  {/* App+Brief live OUTSIDE <Routes> so route switches hide, never
                      unmount them (#239 slice 2). Their Route entries render null —
                      they only claim the paths so '*' doesn't send them to Landing. */}
                  <AppBriefKeepAlive />
                  <Routes>
                    <Route path="/" element={<Landing />} />
                    <Route path="/app" element={null} />
                    <Route path="/brief" element={null} />
                    <Route path="/docs" element={<Suspense fallback={<PaneChunkLoading />}><Docs /></Suspense>} />
                    <Route path="/docs/*" element={<Suspense fallback={<PaneChunkLoading />}><Docs /></Suspense>} />
                    <Route path="/register" element={<Suspense fallback={<PaneChunkLoading />}><Register /></Suspense>} />
                    <Route path="/auth/callback" element={<Suspense fallback={<PaneChunkLoading />}><AuthCallback /></Suspense>} />
                    <Route path="/auth/reset" element={<Suspense fallback={<PaneChunkLoading />}><AuthReset /></Suspense>} />
                    <Route path="*" element={<Landing />} />
                  </Routes>
                  {/* The phone's Brief ◈ · Lens ◎ · Live ≋ bar. One instance for
                      both keep-alive routes — it navigates and nothing else, so
                      it carries no state across the hop. */}
                  <MobileTabBar />
                  <InstallPrompt />
                  <EclipseTakeover />
                  <EclipseChrome />
                </MobileNavProvider>
              </StoryLensProvider>
            </EclipseProvider>
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </RootErrorBoundary>
  </StrictMode>,
)
