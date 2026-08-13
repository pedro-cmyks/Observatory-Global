import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
// MapLibre DEPRECATED 2026-07-04 (Pedro): the legacy mercator map lived behind
// a settings toggle, cost 1MB on every /app load, and carried the
// display:none crash class that blocked the keep-alive shell (#239 slice 2).
// EqualEarthMap has full parity (flows/aircraft/vessels/terminator/markers).
import './App.css'
// R3 Ocean surface language — emerald-scoped overrides ONLY ([data-theme^=
// 'emerald']); must load AFTER App.css and the panel CSS so ties resolve to
// the skin. Intel-noir/retro never match its selectors.
import './styles/oceanConsole.css'
import { useCrisis } from './contexts/CrisisContext'
import { SearchBar } from './components/SearchBar'
import { Briefing } from './components/Briefing'
import { ThemeDetail } from './components/ThemeDetail'
import { CountryBrief } from './components/CountryBrief'
import { EqualEarthMap } from './components/EqualEarthMap'
import { computeCountryHeatStates } from './lib/countryHeatStates'
import { useEclipseMode } from './contexts/EclipseModeContext'
import { buildEclipseSets, countryLens } from './lib/eclipseSets'
import { FocusProvider, useFocus } from './contexts/FocusContext'
import { FocusDataProvider, useFocusData, type NodeData } from './contexts/FocusDataContext'

import { MapTooltip, type TooltipData } from './components/MapTooltip'
import { ConflictEventPanel, type ConflictEventFocus } from './components/ConflictEventPanel'
import { track, trackOnce } from './lib/telemetry'
import { CrisisProvider } from './contexts/CrisisContext'
import { SettingsPanel } from './components/SettingsPanel'
import { CountryThemePanel } from './components/CountryThemePanel'
import { EntityPanel } from './components/EntityPanel'
import { PublicAttentionPanel } from './components/PublicAttentionPanel'
import { PersonCompare } from './components/PersonCompare'
import { ThemeCompare } from './components/ThemeCompare'
import { SourceProfile } from './components/SourceProfile'
import { WorkspaceProvider, useWorkspace } from './contexts/WorkspaceContext'
import { StoryLensBanner } from './components/StoryLensBanner'
import { useStoryLens } from './contexts/StoryLensContext'
import { STORY_LENS_AUTO, isLensAnchor } from './lib/storyLens'
import { FocusIndicator } from './components/FocusIndicator'
import { FrameStrip } from './components/FrameStrip'
import { FrameSheet } from './components/FrameSheet'
import { SearchSheet } from './components/SearchSheet'
import { maxReplayDays, farEdgeKind, positionForDaysBack, snapDaysBack, isoDayForDaysBack, REPLAY_ENDPOINT_CAP_DAYS } from './lib/scrubberScale'
import { Globe, ClipboardList, HelpCircle, BookmarkPlus, MoreHorizontal, Settings, Sun, Moon } from './lib/icons'
import { useTheme } from './contexts/ThemeContext'
import { CHOKEPOINTS, haversineKm, getChokepointVesselCounts, getCountryChokepoints, type Chokepoint } from './lib/chokepoints'
import { resolveCountryName } from './lib/countryNames'
import { conflictCountryCode } from './lib/conflictEvents'
import type { PublicAttentionOrigin } from './lib/publicAttention'
import { prefetchBriefing } from './lib/briefingPrefetch'
import { resolveThreadThemeTarget } from './lib/threadThemeTarget'
import { buildHistoricalCoverageCue } from './lib/historicalCoverageCue'
import ResearchPlanPanel from './components/ResearchPlanPanel'
import WorkbenchPanel from './components/WorkbenchPanel'
import { UniverseView } from './components/UniverseView'
import { resolveThreadLabel, resolveThreadTitle } from './lib/themeLabels'
import { createInvestigation, getActiveInvestigationId, getInvestigation, investigationQuery, addCitation } from './lib/workbench'
import { countryPin, receiptFrom } from './lib/capturePayloads'
import { buildBriefParams, parseConsoleDeepLink } from './lib/navParams'
// #233 grid revival: desktop panels live in a drag/resize grid. RGL positions
// children with CSS transforms — panels are NEVER unmounted by layout changes,
// which is what the keep-alive architecture requires.
import ReactGridLayout from 'react-grid-layout'
import type { Layout, LayoutItem } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import {
  GRID_COLS,
  bucketForWidth,
  clearSavedLayouts,
  layoutForBucket,
  loadSavedLayouts,
  rowHeightFor,
  saveLayout,
  snapResizedItem,
  type LayoutBucket,
} from './lib/consoleLayout'

// Terminal Panels
import { NarrativeThreads, type LivingThreadSelection } from './components/NarrativeThreads'
import { ThreadFocusPanel } from './components/ThreadFocusPanel'
import { SignalStream } from './components/SignalStream'
import { OnboardingCoachmark } from './components/OnboardingCoachmark'
import { CountryFocusWalkthrough, COUNTRY_WALKTHROUGH_KEY } from './components/CountryFocusWalkthrough'
import { DayEvidencePanel } from './components/DayEvidencePanel'
import { CorrelationMatrix } from './components/CorrelationMatrix'
import { AnomalyPanel } from './components/AnomalyPanel'
import { UnderRadarLens } from './components/UnderRadarLens'
import { MarketsPanel } from './components/MarketsPanel'
import { SourceIntegrityPanel } from './components/SourceIntegrityPanel'
import { PanelErrorBoundary } from './components/PanelErrorBoundary'
import { ChokepointPanel } from './components/ChokepointPanel'
import { AtlasLoader } from './components/AtlasLoader'
import { PanelHelpButton } from './components/PanelHelpDrawer'
import { Legend } from './components/Legend'
import { useUrlSync } from './hooks/useUrlSync'
import { useSavedWatches } from './hooks/useSavedWatches'
import { useIsMobile } from './hooks/useIsMobile'
import { useMobileNav } from './contexts/MobileNavContext'
import { surfaceFor, fieldVisible, type MobileSurface } from './lib/mobileNav'
import { consoleLensScope, consoleSlot } from './lib/lensScope'
import { LensPanel } from './components/LensPanel'







interface FeatureCollection {
  type: 'FeatureCollection'
  features: any[]
}

const emptyFeatureCollection = (): FeatureCollection => ({ type: 'FeatureCollection', features: [] })

// ── The scrubber is time (2026-07-15, supersedes the S4 VIEW selector) ──
// The command-bar time selector is GONE: looking back happens on the map
// scrubber (one log-scale bar, whole history inside). Former selector
// consumers each own a sensible fixed window now:
//   · ambient (nodes/flows/heat/threads/brief) — 24h, unchanged (S4 doctrine)
//   · investigative panels (theme/country/person/chokepoint/compare/source/
//     briefing/universe/conflict-event) — DAY_WINDOW_HOURS: the live day;
//     deeper look-back = the scrubber + deep-history, not a re-filter
//   · research plans (story panel + workbench) — RESEARCH_WINDOW_HOURS:
//     they already floored the lens at a week
const DAY_WINDOW_HOURS = 24
const RESEARCH_WINDOW_HOURS = 168

const DEG_TO_RAD = Math.PI / 180
// Gutter between grid panels (px) — also the container padding.
const GRID_GAP = 6

function getDayOfYear(date: Date): number {
  const start = new Date(date.getFullYear(), 0, 0)
  return Math.floor((date.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
}

function calculateTerminatorPolygon(date: Date = new Date(), lngOffsetDeg = 0): number[][] {
  const dayOfYear = getDayOfYear(date)
  const declination = -23.45 * Math.cos((360 / 365) * (dayOfYear + 10) * DEG_TO_RAD)
  const utcHours = date.getUTCHours() + date.getUTCMinutes() / 60
  const solarNoonLng = -((utcHours - 12) * 15)
  const terminatorLine: number[][] = []

  for (let lat = -90; lat <= 90; lat += 2) {
    const latRad = lat * DEG_TO_RAD
    const declRad = declination * DEG_TO_RAD
    const cosH = -Math.tan(latRad) * Math.tan(declRad)
    let lng: number

    if (cosH < -1) {
      lng = solarNoonLng + 180
    } else if (cosH > 1) {
      lng = solarNoonLng
    } else {
      const hourAngle = Math.acos(Math.max(-1, Math.min(1, cosH))) / DEG_TO_RAD
      lng = solarNoonLng + hourAngle
    }

    lng += lngOffsetDeg
    while (lng > 180) lng -= 360
    while (lng < -180) lng += 360
    terminatorLine.push([lng, lat])
  }

  const nightSide = solarNoonLng > 0 ? -180 : 180
  return [...terminatorLine, [nightSide, 90], [nightSide, -90], terminatorLine[0]]
}

function buildTerminatorData(visible: boolean): FeatureCollection {
  if (!visible) return emptyFeatureCollection()
  const now = new Date()
  return {
    type: 'FeatureCollection',
    features: [0, 3.5, 7, 10.5, 14].map((offset, index) => ({
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [calculateTerminatorPolygon(now, offset)],
      },
      properties: {
        opacity: [0.52, 0.28, 0.14, 0.07, 0.03][index],
      },
    })),
  }
}

interface CountryDetail {
  countryCode: string
  name?: string
  totalSignals: number
  sentiment: number
  themes: { name: string; count: number }[]
  sources: { name: string; count: number }[]
}

interface PublicAttentionSelection extends PublicAttentionOrigin {
  title: string
  views?: number
  country_count?: number
}

// removed sentimentColor
// removed generateNarrative et al.


const getNodePriority = (node: NodeData) => [
  node.heat ?? node.intensity ?? 0,
  node.signalCount ?? 0,
]

// Error boundary to prevent Deck.gl/WebGL crashes from black-screening the entire app
interface MapErrorBoundaryState { hasError: boolean }
class MapErrorBoundary extends React.Component<{ children: React.ReactNode }, MapErrorBoundaryState> {
  state: MapErrorBoundaryState = { hasError: false }
  static getDerivedStateFromError(): MapErrorBoundaryState { return { hasError: true } }
  componentDidCatch(error: Error) { console.error('[MapErrorBoundary]', error) }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: '100%', height: '100%',
          background: '#0a0a0a', color: '#ef4444', fontSize: '12px',
          fontFamily: 'monospace', flexDirection: 'column', gap: '8px'
        }}>
          <span>⚠ MAP RENDER ERROR</span>
          <button
            onClick={() => this.setState({ hasError: false })}
            style={{ padding: '4px 12px', background: '#1e293b', border: '1px solid #334155', color: '#94a3b8', borderRadius: '4px', cursor: 'pointer', fontSize: '11px' }}
          >
            Retry
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

// Static coordinate fallback for countries that may not appear in live signals
const COUNTRY_COORDS: Record<string, [number, number]> = {
  AF: [65, 33], AL: [20, 41], DZ: [3, 28], AO: [18, -12], AR: [-64, -34], AM: [45, 40], AU: [133, -27], AT: [14, 47],
  AZ: [47, 40], BH: [50, 26], BD: [90, 24], BY: [28, 53], BE: [4, 51], BO: [-65, -17], BA: [18, 44], BW: [24, -22],
  BR: [-51, -14], BG: [25, 43], KH: [105, 12], CM: [12, 6], CA: [-96, 60], CL: [-71, -30], CN: [105, 35],
  CO: [-74, 4], CD: [24, -3], CG: [15, -1], CR: [-84, 10], HR: [16, 45], CU: [-80, 22], CY: [33, 35], CZ: [16, 50],
  DK: [10, 56], DO: [-70, 19], EC: [-77, -2], EG: [30, 27], ET: [40, 8], FI: [27, 64], FR: [2, 46], GA: [12, -1],
  GE: [44, 42], DE: [10, 51], GH: [-1, 8], GR: [22, 39], GT: [-90, 15], HT: [-72, 19], HN: [-87, 15], HU: [19, 47],
  IN: [78, 21], ID: [118, -2], IR: [53, 32], IQ: [44, 33], IE: [-8, 53], IL: [35, 31], IT: [12, 42], JP: [138, 36],
  JO: [37, 31], KZ: [67, 48], KE: [38, -1], KW: [47, 29], LB: [36, 34], LY: [17, 27], LT: [24, 56], MA: [-7, 32],
  MX: [-102, 24], MD: [29, 47], MN: [105, 46], MZ: [35, -18], MM: [96, 17], NP: [84, 28], NL: [5, 52], NZ: [174, -41],
  NI: [-85, 13], NG: [8, 10], KP: [127, 40], NO: [10, 62], PK: [70, 30], PA: [-80, 9], PY: [-58, -23], PE: [-76, -10],
  PH: [122, 13], PL: [20, 52], PT: [-8, 39], QA: [51, 25], RO: [25, 46], RU: [100, 60], SA: [45, 24],
  SN: [-14, 14], RS: [21, 44], SG: [104, 1], SK: [19, 49], SI: [15, 46], SO: [46, 6], ZA: [25, -29], KR: [128, 36],
  SS: [30, 7], ES: [-4, 40], LK: [81, 7], SD: [30, 15], SE: [18, 62], CH: [8, 47], SY: [38, 35], TW: [121, 24],
  TZ: [35, -6], TH: [101, 15], TN: [9, 34], TR: [35, 39], UG: [32, 1], UA: [32, 49], AE: [54, 24],
  GB: [-2, 54], US: [-98, 39], UY: [-56, -33], VE: [-66, 8], VN: [108, 14], YE: [48, 15], ZM: [28, -14],
  ZW: [30, -20], XK: [21, 42], ME: [19, 42], PS: [35, 32], KV: [21, 42], RI: [118, -2],
  RB: [21, 44], SW: [18, 62], EI: [-8, 53],
}

function UtcClock() {
  const [time, setTime] = React.useState(() => new Date().toUTCString().slice(17, 25))
  React.useEffect(() => {
    const t = setInterval(() => setTime(new Date().toUTCString().slice(17, 25)), 1000)
    return () => clearInterval(t)
  }, [])
  return <span className="utc-clock">{time} UTC</span>
}

function AppContent() {
  const navigate = useNavigate()
  const location = useLocation()
  // Last search-string handled by the deep-link effect (keep-alive guard).
  const deepLinkProcessedRef = useRef<string | null>(null)
  // Last search-string handled by the `?lens=story` deep-link effect (Task
  // 10, spec-review issue 4): without this, an explicit banner ✕ (exit) can
  // be resurrected by the next focus-driven URL write — mergeFocusIntoParams
  // preserves `lens`/`theme` across those writes, so the effect would refire
  // with `!state.active` true and re-enter a lens the analyst just closed.
  const lensLinkProcessedRef = useRef<string | null>(null)

  // Sync filter state ↔ URL params for shareable links
  useUrlSync()

  // W1 (2026-07-05): one L3 store — the context adapts panel pins onto the
  // Workbench investigation; isOpen IS the workbench overlay state now.
  const { trackVisit, isOpen: workbenchOpen, setIsOpen: setWorkbenchOpen, items: workspaceItems, version: wbVersion, pinItem } = useWorkspace()
  // Story Lens (Task 10): the entry/exit wiring below is the only place this
  // console touches the lens directly — the banner and stream/threads panels
  // read the same context independently.
  const storyLens = useStoryLens()
  // Spec-review fix (issue 4 — deep-link resurrection): every exit ALSO
  // strips `lens=` from the URL. Without this, the next focus-driven URL
  // write (mergeFocusIntoParams preserves every param it doesn't own,
  // including `lens`) leaves `lens=story&theme=X` intact; the deep-link
  // effect then refires on that later change, reads `!state.active` as true
  // (the analyst just exited), and silently resurrects the lens. Confirmed
  // live via the banner's own ✕ (StoryLensBanner.tsx carries the same fix
  // for that direct path — this one covers every OTHER exit call site).
  const stripLensParam = useCallback(() => {
    const p = new URLSearchParams(location.search)
    if (!p.has('lens')) return
    p.delete('lens')
    navigate({ pathname: location.pathname, search: p.toString() }, { replace: true })
  }, [location.pathname, location.search, navigate])
  // Spec-review fix: handleThemeSelect is NOT the only thread-open door —
  // NarrativeThreads' onThreadSelect (the lens's OWN panel, wiring the
  // sibling walk), handleResearchOpenThread, the back-stack restores, and the
  // attention+theme deep link all set selectedTheme directly. ONE helper,
  // called at every door, so the lens can never desync from "what thread is
  // actually open" again. The same-anchor guard also kills the cold-load
  // double-fetch (a deep link enters first; the second caller for the same
  // id no-ops instead of re-fetching).
  // T11 gate fix (L4): optional `labelHint` — the SAME plumbing Item 8 built
  // so the theme chip never falls back to a generic skeleton on a named open
  // — reused here so the lens banner has a real title BEFORE the siblings
  // fetch resolves and STAYS with one if that fetch degrades (db_error /
  // network throw never populates `data.anchor`, so the banner previously
  // had nothing but the opaque anchorId to fall back to).
  const syncLensToThreadOpen = useCallback((id: string | null, labelHint?: string | null) => {
    if (!STORY_LENS_AUTO) return
    if (!id || !isLensAnchor(id)) {
      if (storyLens.state.active) { storyLens.exit(); stripLensParam() }
      return
    }
    if (!(storyLens.state.active && storyLens.state.anchorId === id)) storyLens.enter(id, labelHint)
  }, [storyLens, stripLensParam])

  // State
  const [selectedCountry, setSelectedCountry] = useState<CountryDetail | null>(null)
  const [selectedCountryCode, setSelectedCountryCode] = useState<string | null>(null)
  type SelectedTheme = {
    theme: string,
    originCountry?: string,
    originCountryName?: string,
    originAttention?: PublicAttentionOrigin,
    thread?: { thread_id: string, label: string },
    /** Item 8: the opener's human label (universe node / threads row) — used
     *  until the detail fetch fills `thread.label`; never a stored generic. */
    labelHint?: string,
  }
  const [selectedTheme, setSelectedTheme] = useState<SelectedTheme | null>(null)
  const [selectedThread, setSelectedThread] = useState<LivingThreadSelection | null>(null)
  const [themeBackStack, setThemeBackStack] = useState<SelectedTheme[]>([])
  const [selectedPublicAttention, setSelectedPublicAttention] = useState<PublicAttentionSelection | null>(null)
  const [selectedChokepoint, setSelectedChokepoint] = useState<Chokepoint | null>(null)
  // T3.3 P-FOCUS: a clicked conflict event becomes the subject (not its country).
  const [selectedConflictEvent, setSelectedConflictEvent] = useState<ConflictEventFocus | null>(null)
  const [rightPanelThemeCountry, setRightPanelThemeCountry] = useState<{ code: string, name: string } | null>(null)
  // One-level back navigation for the stream panel
  type PrevCtx =
    | { type: 'chokepoint'; cp: Chokepoint }
    | { type: 'theme'; theme: string; originCountry?: string; originCountryName?: string }
    | { type: 'country'; code: string; name: string }
  const [prevStreamCtx, setPrevStreamCtx] = useState<PrevCtx | null>(null)
  const [showBriefing, setShowBriefing] = useState(false)
  // Universe view (L11): the whole living story population as one field
  const [universeOpen, setUniverseOpen] = useState(false)
  const [researchQuery, setResearchQuery] = useState<string | null>(null)
  // Reopen fix: the research plan used to live only in this App state, so the
  // right panel went dead on every workbench reopen. The query is now PERSISTED
  // on the investigation (lib/workbench) — hydrate it when the overlay opens.
  useEffect(() => {
    if (!workbenchOpen || researchQuery) return
    const activeId = getActiveInvestigationId()
    const inv = activeId ? getInvestigation(activeId) : null
    if (inv) setResearchQuery(investigationQuery(inv))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workbenchOpen])
  // Search-submit story panel (2026-07-04, Pedro): a natural query's first
  // answer is the CROSS-THREAD STORY (research-plan anchors in the stream
  // slot), not a thread builder and not the Workbench.
  const [storyQuery, setStoryQuery] = useState<string | null>(null)
  const [wbRefresh, setWbRefresh] = useState(0)
  const [tourRunId, setTourRunId] = useState(0)
  // A4: one-time contextual walkthrough on the first country selection.
  const [countryWalkthrough, setCountryWalkthrough] = useState<string | null>(null)
  const countryWalkthroughDone = useRef<boolean>(
    (() => { try { return !!localStorage.getItem(COUNTRY_WALKTHROUGH_KEY) } catch { return true } })()
  )
  // #152 command-bar layout: overflow "···" menu (TOUR + Settings) and
  // controlled settings panel. (The compact time-range dropdown died with
  // the VIEW selector, 2026-07-15 — the scrubber is time.)
  const [moreMenuOpen, setMoreMenuOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  // Bottom dock active tab (#228 §3): anomaly | sources. The HEAT tab was
  // removed (#231) — heat is a map property (drives country color), not a
  // bottom list. The composite now colors the map directly.
  const [dockTab, setDockTab] = useState<'anomaly' | 'sources' | 'radar' | 'markets'>('anomaly')

  // X0 (L2 review 2026-07-05): the stream slot is L2's core state machine and
  // it was invisible to telemetry — panel_swap makes the middle of the
  // L0→L3 funnel readable.
  // Mobile IA (#236 Task 6): the phone has THREE tabs — Brief ◈ · Lens ◎ ·
  // Live ≋ — and the bar that switches them lives at the root (MobileTabBar),
  // because Brief is a route and the console is a surface. App only reads
  // which of its two console surfaces is showing. Desktop ignores this.
  const isMobile = useIsMobile()
  const { consoleTab, setConsoleTab, trail: lensTrail, focusLens, rewindLens, resetLens } = useMobileNav()
  // R3 emerald foundation: compact day/night flip in the command bar (full
  // theme selection, incl. Intel Noir, stays in Settings).
  const { theme: consoleTheme, toggleDayNight } = useTheme()

  useEffect(() => {
    if (!moreMenuOpen) return
    const onDown = (e: MouseEvent) => {
      const el = e.target as HTMLElement
      if (!el.closest('.cmd-more-wrap')) {
        setMoreMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [moreMenuOpen])
  const { watches, add: addWatch } = useSavedWatches()
  const [watchNamePrompt, setWatchNamePrompt] = useState<string | null>(null)
  // Reactive to the URL (not mount-only): under the #239 keep-alive shell App
  // stays mounted across Brief↔App switches, so a mount-only read went stale.
  // (useUrlSync now preserves `entry` across focus changes, so this stays
  // 'brief' for the whole reading session — 6.3a depends on it.)
  const entrySource = useMemo(() => new URLSearchParams(location.search).get('entry'), [location.search])
  const tourEntryContext = entrySource === 'brief'
    ? 'You came in from the Brief. Atlas will show the full console first, then you can keep exploring the country or narrative you selected.'
    : undefined
  useEffect(() => {
    if (entrySource === 'eclipse') {
      window.dispatchEvent(new Event('atlas:eclipse-refresh'))
    }
  }, [entrySource])
  // Story Lens (Task 10, Step 3): deep-link entry `?lens=story&theme=dynamic-
  // topic-N`. Ungated by STORY_LENS_AUTO — a deep link is an explicit request,
  // not the auto-enter-on-open behavior that kill switch controls. Guarded to
  // the console's own route the same way the theme/country deep-link effect
  // below is (App stays mounted under the keep-alive shell while on /brief;
  // its params must never drive this console's lens). isLensAnchor keeps an
  // atlas/emergent `?theme=` from opening a lens guaranteed to come back
  // empty; !state.active avoids re-firing on every focus-driven param rewrite
  // (mergeFocusIntoParams preserves `lens` across those writes, by design).
  useEffect(() => {
    if (location.pathname !== '/app') return
    if (lensLinkProcessedRef.current === location.search) return
    lensLinkProcessedRef.current = location.search
    const p = new URLSearchParams(location.search)
    const theme = p.get('theme')
    if (p.get('lens') === 'story' && theme && isLensAnchor(theme) && !storyLens.state.active) {
      storyLens.enter(theme)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search, location.pathname])
  // const [timeWindow, setTimeWindow] = useState(24) // Replaced by context
  const [tooltip] = useState<TooltipData | null>(null)

  // Comparison & Overlay states
  const [selectedSourceProfile, setSelectedSourceProfile] = useState<string | null>(null)
  const [comparePerson, setComparePerson] = useState<{ a: string, b: string } | null>(null)
  const [compareTheme, setCompareTheme] = useState<{ a: string, b: string } | null>(null)

  // Equal-area EE canvas is THE map (default since 2026-07-01, Pedro's
  // ADR-0005 P6 sign-off; MapLibre/mercator deprecated 2026-07-04).
  const [eeResetNonce, setEeResetNonce] = useState(0)

  // Focus hook for click-to-focus
  const { setFocus, focus, clearFocus, setCountry, setPerson, filter, setTheme, mapFlyCountry, setMapFlyCountry, isActive } = useFocus()

  // X0 (2026-07-05): the stream slot is L2's core state machine — panel_swap
  // makes the middle of the L0→L3 funnel readable (mirrors the render
  // priority chain of the stream panel).
  // Flywheel #4: mirror the NEW render ladder (thread/theme now outrank a
  // standing person — App.tsx streamPanel). Was person>thread>theme, which
  // mislabeled panel_swap as 'person' while a thread/theme panel rendered.
  const activeStreamPanel = storyQuery ? 'story'
    : selectedThread ? 'thread'
    : selectedTheme ? 'theme'
    : (focus.type === 'person' && focus.value) ? 'person'
    : (selectedCountry || selectedCountryCode) ? 'country'
    : selectedPublicAttention ? 'attention'
    : selectedChokepoint ? 'chokepoint'
    : 'stream'
  useEffect(() => {
    if (activeStreamPanel !== 'stream') track('panel_swap', { to: activeStreamPanel })
  }, [activeStreamPanel])


  // Layer visibility
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [showAircraft, setShowAircraft] = useState(false)
  const [aircraftData, setAircraftData] = useState([])
  const [aircraftError, setAircraftError] = useState(false)
  const [showVessels, setShowVessels] = useState(false)
  const [vesselData, setVesselData] = useState([])
  const [vesselConnected, setVesselConnected] = useState(false)
  const [disasterEvents, setDisasterEvents] = useState<Array<{
    id: string; source: string; type: string; title: string | null;
    country: string | null; latitude: number; longitude: number;
    magnitude: number | null; alert: string | null; time: string; url: string | null;
  }>>([])
  // #231: baseline-normalized composite heat (velocity/surprise/diversity/
  // voice) per country. The map fill must use THIS, not /nodes volume-rank
  // heat (which made the US permanently reddest). Keyed by ISO2.
  const [heatComposite, setHeatComposite] = useState<Map<string, number>>(new Map())
  // X2/S1 (time-as-dimension, 2026-07-05): globe time scrubber. Volume replay
  // from the pre-agg — HONESTLY labeled (composite heat has no history).
  const [replayData, setReplayData] = useState<Record<string, Record<string, number>> | null>(null)
  const [replayDay, setReplayDay] = useState<string | null>(null)
  // S3: country clicked WHILE scrubbed → that day's receipts (not the live view).
  const [dayEvidenceCountry, setDayEvidenceCountry] = useState<string | null>(null)
  useEffect(() => { if (!replayDay) setDayEvidenceCountry(null) }, [replayDay])

  const replayHeat = useMemo(() => {
    if (!replayDay || !replayData) return null
    const vals = Object.entries(replayData)
      .map(([cc, days]) => [cc, days[replayDay] ?? 0] as const)
      .filter(([, n]) => n > 0)
    const m = new Map<string, number>()
    if (!vals.length) return m
    const sorted = [...vals].sort((a, b) => a[1] - b[1])
    const n = Math.max(sorted.length - 1, 1)
    sorted.forEach(([code], i) => { m.set(code, Math.pow(i / n, 1.6)) })
    return m
  }, [replayDay, replayData])

  // Fetch Aircraft data
  useEffect(() => {
    if (!showAircraft) { setAircraftError(false); return }
    const fetchAircraft = async () => {
      try {
        const res = await fetch('/api/v2/aircraft')
        if (res.ok) {
          const data = await res.json()
          const aircraft = data.aircraft || []
          setAircraftData(aircraft)
          setAircraftError(aircraft.length === 0)
        } else {
          setAircraftError(true)
        }
      } catch (err) {
        console.error('Failed to fetch aircraft:', err)
        setAircraftData([])
        setAircraftError(true)
      }
    }
    fetchAircraft()
    const interval = setInterval(fetchAircraft, 60000)
    return () => clearInterval(interval)
  }, [showAircraft])

  // Fetch vessel positions (30s poll — backend streams from AISStream)
  useEffect(() => {
    if (!showVessels) { setVesselData([]); return }
    const fetchVessels = async () => {
      try {
        const res = await fetch('/api/v2/vessels')
        if (res.ok) {
          const data = await res.json()
          setVesselData(data.vessels || [])
          setVesselConnected(!!data.connected)
        }
      } catch (err) {
        console.error('Failed to fetch vessels:', err)
      }
    }
    fetchVessels()
    const interval = setInterval(fetchVessels, 30000)
    return () => clearInterval(interval)
  }, [showVessels])

  // Disaster events (USGS+GDACS, capture-doc L7) — the hazards CAMEO can't
  // represent, finally painted. Fixed 72h window (hazard relevance horizon,
  // independent of the news time-range); 15-min refresh matches ingest cadence.
  useEffect(() => {
    const fetchDisasters = async () => {
      try {
        const res = await fetch('/api/v2/disasters?hours=72')
        if (res.ok) {
          const data = await res.json()
          setDisasterEvents(data.events || [])
        }
      } catch (err) {
        console.error('Failed to fetch disasters:', err)
      }
    }
    fetchDisasters()
    const interval = setInterval(fetchDisasters, 15 * 60_000)
    return () => clearInterval(interval)
  }, [])

  // Auto-enable SHIPS when focused country has strategically relevant chokepoints
  useEffect(() => {
    if (!filter.country) return
    const relevant = getCountryChokepoints(filter.country)
    if (relevant.length > 0 && !showVessels) {
      setShowVessels(true)
    }
  }, [filter.country])

  // Active chokepoints: those associated with the currently focused country
  const activeChokepoints = useMemo(
    () => getCountryChokepoints(filter.country),
    [filter.country]
  )

  // Vessel counts per chokepoint, computed from live vessel positions
  const chokepointCounts = useMemo(
    () => getChokepointVesselCounts(vesselData),
    [vesselData]
  )

  // Aircraft filtered by context:
  // - No focus: cruise altitude only (>9000m) — shows global air corridors
  // - Country focused: all aircraft within 700km of that country's centroid
  const filteredAircraftData = useMemo(() => {
    if (!showAircraft || !aircraftData.length) return []
    if (!filter.country) {
      return aircraftData.filter((a: any) => (a.baro_altitude || 0) > 9000)
    }
    const coords = COUNTRY_COORDS[filter.country]
    if (!coords) return aircraftData.filter((a: any) => (a.baro_altitude || 0) > 9000)
    const [cLon, cLat] = coords
    return aircraftData.filter(
      (a: any) => haversineKm(cLat, cLon, a.latitude, a.longitude) < 700
    )
  }, [aircraftData, filter.country, showAircraft])

  // EE canvas renders synchronously — the whole MapLibre readiness dance
  // (onLoad gate, CDN-style watchdog, 0×0-container mount guard, mercator
  // teardown reset) died with the deprecation. Ready is a constant.
  const mapReady = true

  // T5.1: instrument the App console open (the denominator for time-to-value).
  useEffect(() => { track('app_open') }, [])

  // Settings toggles
  const [showTerminator, setShowTerminator] = useState(false)
  const [sizeBoost, setSizeBoost] = useState(false)
  const [showFlows, setShowFlows] = useState(false)

  // Click handlers
  function handleCountryClick(countryCode: string) {
    track('country_click')
    setStoryQuery(null) // story panel yields to an explicit country open
    setSelectedPublicAttention(null)
    setSelectedThread(null)
    // Country nav must take the stream slot: clear any open ThemeDetail so the
    // isCountry branch wins (else focus/chip update but the stream stays on the
    // old theme — the anomaly/map→country-while-theme-open bug). Flows that keep
    // a theme (ThemeDetail country card → right panel) don't go through here.
    setSelectedTheme(null)
    setThemeBackStack([])
    // T11 gate fix (M2): a country door is a full context switch AWAY from
    // the open story, not a peel of one compound-focus dimension — exit the
    // lens the same way popPanel's inline exit does when it closes the
    // thread/theme panel. This one call covers every door that routes
    // through handleCountryClick (Briefing's onCountrySelect,
    // NarrativeThreads' onCountrySelect, map/EntityPanel/conflict-panel
    // country clicks, etc.) — not syncLensToThreadOpen(null): its
    // !STORY_LENS_AUTO early-return must not apply to an explicit
    // navigation exit (see clearAll's comment above for the same reasoning).
    if (storyLens.state.active) { storyLens.exit(); stripLensParam() }
    setSelectedCountryCode(countryCode)
    setSelectedCountry({
      countryCode,
      name: resolveCountryName(countryCode),
      totalSignals: 0,
      sentiment: 0,
      themes: [],
      sources: [],
    })
    setShowFlows(true)
    // Single source of truth (A2): every country entry point also sets the
    // global focus so the stream, dock, legend and map re-scope together — and
    // the focus chip appears so the country can be deselected. The sync effect
    // guards on focus.value !== selectedCountryCode, so this can't loop.
    setCountry(countryCode)
    // A4: teach the select/deselect model once, on the first country click —
    // but never while the first-session tour is still on screen (don't stack).
    if (!countryWalkthroughDone.current && !document.querySelector('.onboarding-layer')) {
      countryWalkthroughDone.current = true
      setCountryWalkthrough(resolveCountryName(countryCode))
    }
  }

  // Exploration Flywheel (Task 3.7): the map's ◆ gestures. A country pins as a
  // WHERE-lane entity (pinItem → active investigation); an event marker pins as
  // an un-gated receipt (receiptFrom defaults gateStatus:'unknown' — never faked
  // to a tier), creating an investigation from the marker title if none is open.
  const handlePinMapCountry = useCallback((iso: string, name: string) => {
    pinItem(countryPin(iso, name))
  }, [pinItem])

  const handlePinMapMarker = useCallback((payload: { title: string; sourceLink: { url: string; label: string } | null; source?: string }) => {
    const cit = receiptFrom({ headline: payload.title, url: payload.sourceLink?.url, source: payload.source })
    let invId = getActiveInvestigationId()
    if (!invId || !getInvestigation(invId)) invId = createInvestigation(payload.title).id
    addCitation(invId, cit)
  }, [])

  // A1: one comprehensive deselect — the focus chip's ✕ and the map background
  // click both return to the whole, unfocused view. clearFocus() clears the
  // GlobalFilter (closing country/theme panels via their effects); the rest
  // resets local-only panel state.
  const clearAll = useCallback(() => {
    clearFocus()
    setSelectedTheme(null)
    setSelectedThread(null)
    setSelectedSourceProfile(null)
    setSelectedPublicAttention(null)
    setSelectedChokepoint(null)
    setRightPanelThemeCountry(null)
    setShowFlows(false)
    // Story Lens (Task 10, Step 2): the focus chip's ✕ is a full deselect —
    // the lens must not linger once everything else it was scoping has
    // cleared. Unconditional call is safe: exit() on an already-inactive
    // lens is a no-op state reset (StoryLensContext). stripLensParam (issue
    // 4) keeps this exit from being resurrected by the next URL write.
    // Inline exit, NOT syncLensToThreadOpen(null): the helper early-returns
    // on !STORY_LENS_AUTO, but deep-link entry is deliberately ungated — a
    // deep-linked lens must stay exitable with the flag off. (Same reasoning
    // at popPanel's and closeAll's inline exits below.)
    storyLens.exit()
    stripLensParam()
  }, [clearFocus, storyLens.exit, stripLensParam])

  // Workbench / research-plan handlers (Phase 2, #213). Anchors open the
  // existing surfaces: a thread anchor routes through the theme-detail
  // contract (same path NarrativeThreads uses), a country anchor through
  // CountryBrief.
  function handleResearchOpenThread(threadId: string, label: string) {
    const isDynamic = threadId.startsWith('dynamic-topic-')
    const slug = isDynamic ? threadId : threadId.split('--')[0]
    const countryCode = !isDynamic && threadId.includes('--')
      ? threadId.split('--')[1]?.split('-')[0]?.toUpperCase()
      : undefined
    setSelectedTheme({
      theme: slug,
      originCountry: countryCode,
      originCountryName: countryCode ? resolveCountryName(countryCode) : undefined,
      thread: { thread_id: threadId, label },
    })
    setSelectedThread(null)
    setSelectedCountry(null)
    setSelectedCountryCode(null)
    setSelectedPublicAttention(null)
    setSelectedChokepoint(null)
    setRightPanelThemeCountry(null)
    setThemeBackStack([])
    setWorkbenchOpen(false)
    // Story Lens (Task 10, spec-review fix): a research-plan anchor is a
    // thread-open door too.
    syncLensToThreadOpen(slug, label)
  }

  function handleResearchOpenCountry(countryCode: string) {
    handleCountryClick(countryCode)
    setMapFlyCountry(countryCode)
    setWorkbenchOpen(false)
  }

  // W1: panel pins (theme/country/person/source/attention) restore their L2
  // view from a query-string — the param router the retired force-graph used,
  // now serving WorkbenchPanel pin opens.
  function handleOpenParams(params: string) {
    const next = new URLSearchParams(params.replace(/^\?/, ''))
    const source = next.get('source')
    const theme = next.get('theme')
    const country = next.get('country')
    const person = next.get('person')
    const attention = next.get('attention')
    setWorkbenchOpen(false)

    if (attention) { handlePublicAttentionSelect({ title: attention }); return }
    if (source) { setSelectedSourceProfile(source); return }
    if (theme && country) {
      handleThemeSelect(theme, country, country, undefined)
      setMapFlyCountry(country)
      return
    }
    if (theme) { handleThemeSelect(theme); return }
    if (country) { handleCountryClick(country); setMapFlyCountry(country); return }
    if (person) { setFocus('person', person, person); setMapFlyCountry(null); return }
  }

  // Theme selection handlers
  const handleThemeSelect = (theme: string, countryCode?: string, countryName?: string, originAttention?: PublicAttentionOrigin, labelHint?: string) => {
    // Story Lens (spec-review issue 4, second finding): captured BEFORE
    // setSelectedTheme below — true when this call is a REDUNDANT re-fire for
    // the theme that's ALREADY open, not a genuine new/different open. The
    // Brief deep-link effect (guarded by deepLinkProcessedRef, pre-existing,
    // guards only on the raw search STRING) re-calls handleThemeSelect on ANY
    // unrelated URL change while `theme=` sits unchanged in the URL — e.g. a
    // country click right after the analyst dismissed the lens via the
    // banner's own ✕. syncLensToThreadOpen's same-anchor guard can't cover
    // this: after an exit state.active is false, so its no-op never fires.
    // Without this guard that redundant re-fire silently resurrects the lens.
    const isSameThemeReopen = selectedTheme?.theme === theme
    // T5.1: a thread open is a value moment (the analyst reached real narrative).
    track('thread_open')
    trackOnce('first_value_moment', { kind: 'thread' })
    setStoryQuery(null) // story panel yields to an explicit thread open
    setSelectedPublicAttention(null)
    setSelectedThread(null)
    // Custom query threads are synthetic — they must not pollute FocusContext
    // (which would fire focus-data fetches against a non-existent theme code).
    // Item 8: when the opener knows the real thread label (universe node,
    // threads row), it travels INTO the focus context — the chip must never
    // fall back to the generic "Narrative Thread" skeleton for a named open.
    if (!theme.startsWith('query-thread::')) setTheme(theme, null, labelHint ?? null)
    const nextTheme = { theme, originCountry: countryCode, originCountryName: countryName, originAttention, labelHint }
    setSelectedTheme(prev => {
      if (prev && prev.theme !== theme) {
        setThemeBackStack(stack => [prev, ...stack].slice(0, 5))
      }
      // Item 8: a re-open of the SAME theme without a label (URL-sync deep-link
      // re-fire) must not clobber the opener's label or the loaded thread meta.
      if (prev && prev.theme === theme) {
        return { ...nextTheme, labelHint: labelHint ?? prev.labelHint, thread: prev.thread }
      }
      return nextTheme
    })
    setRightPanelThemeCountry(null)

    // Story Lens (Task 10, spec D7): opening a story opens its measured
    // neighborhood. syncLensToThreadOpen handles the isLensAnchor gate,
    // enter/exit, and the same-anchor no-op. Skipped on a redundant re-fire
    // for the already-open theme (isSameThemeReopen, issue 4) — a genuinely
    // different theme, or this theme's very first open, still syncs normally.
    // labelHint (Item 8's own param) rides straight through — the same fix
    // for the theme chip's generic-skeleton fallback now covers the lens
    // banner's degraded-path fallback too (T11 gate L4).
    if (!isSameThemeReopen) syncLensToThreadOpen(theme, labelHint)
  }

  const handlePublicAttentionSelect = (item: PublicAttentionSelection) => {
    const title = item.title.replace(/_/g, ' ').trim()
    setSelectedPublicAttention({ ...item, title })
    setSelectedTheme(null)
    setSelectedThread(null)
    setRightPanelThemeCountry(null)
    setSelectedCountry(null)
    setSelectedCountryCode(null)
    setSelectedChokepoint(null)
    setSelectedSourceProfile(null)
    setShowFlows(false)
    setMapFlyCountry(null)
    clearFocus()
    if (filter.theme) setTheme(null)
  }

  // Reactive to the URL (not mount-only): under the #239 keep-alive shell the
  // console stays mounted across Brief↔App switches, so a Brief deep-link
  // (?theme=&country=) must re-trigger on search-param change. Guarded by a
  // last-processed ref so the same params never double-fire.
  useEffect(() => {
    // Only the console's own URL: under keep-alive App stays mounted while the
    // user is on /brief, and Brief's params must never drive the console.
    if (location.pathname !== '/app') return
    if (deepLinkProcessedRef.current === location.search) return
    deepLinkProcessedRef.current = location.search
    const dl = parseConsoleDeepLink(location.search)
    const attention = dl.attention
    const theme = dl.theme
    const country = dl.country || undefined
    // Carry-context (6.2b): a category/search deep-link with NO theme and NO
    // attention seeds the cross-thread STORY panel. Kept as its OWN branch —
    // handleThemeSelect nulls storyQuery internally, so the two must not merge.
    if (dl.q && !theme && !attention) {
      setStoryQuery(dl.q)
      return
    }
    // Brief → console deep-link without attention: open the theme detail on mount.
    // Atlas-topic slugs (e.g. "disease-outbreak") resolve to the gated theme view.
    // dl.label carries the Brief's real thread label forward (5th arg → labelHint).
    if (theme && !attention) {
      handleThemeSelect(theme, country, country ? resolveCountryName(country) : undefined, undefined, dl.label ?? undefined)
      if (country) setMapFlyCountry(country)
      return
    }
    if (!attention) {
      // Pure-country deep link (?country=VE): useUrlSync hydrates the focus,
      // but nothing flew the map — the click path flies, the link path didn't
      // (capture-doc A1, Pedro's browser check).
      if (country) setMapFlyCountry(country)
      return
    }
    const title = attention.replace(/_/g, ' ').trim()
    if (theme) {
      setSelectedPublicAttention(null)
      setSelectedTheme({
        theme,
        originCountry: country,
        originCountryName: country ? resolveCountryName(country) : undefined,
        originAttention: { title },
      })
      setRightPanelThemeCountry(null)
      // Story Lens (Task 10, spec-review fix): the attention+theme deep link
      // sets selectedTheme directly — it doesn't route through
      // handleThemeSelect, so it needs its own sync call.
      syncLensToThreadOpen(theme)
      return
    }
    handlePublicAttentionSelect({ title })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search, location.pathname])

  // Focus-aware data from provider - auto-refetches when focus changes
  const { nodes, flows, unfilteredFlows, acledConflicts, loading, isRefetching, refetch, meta: focusMeta } = useFocusData()

  // THE SCRUBBER IS TIME (2026-07-15): one log-scale bar carries the WHOLE
  // replayable history — right half ≈ the last 7-10 days at day granularity,
  // deep past compresses left, edge = the honest data bound (archive floor
  // May 3 until it recedes past the endpoint's 90-day cap).
  const scrubMaxDays = useMemo(() => maxReplayDays(), [])
  const replayRequestedRef = useRef(false)
  // Fetch the replay window ONCE at the full span; every scrub after that is
  // local (the payload already carries all days for all countries).
  const ensureReplayData = useCallback(() => {
    if (replayRequestedRef.current) return
    replayRequestedRef.current = true
    fetch(`/api/v2/map/replay?days=${scrubMaxDays}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.series) setReplayData(d.series) })
      .catch(() => { replayRequestedRef.current = false /* scrubber degrades to no-op; retry on next scrub */ })
  }, [scrubMaxDays])

  // Scrubber drag state. Whole days from NOW for the current scrub position
  // (0 = live); the continuous position lives in a ref so Shift-fine deltas
  // accumulate without re-render churn.
  const scrubDaysBack = replayDay
    ? Math.max(0, Math.floor((Date.now() - Date.parse(replayDay + 'T00:00:00Z')) / 86400000))
    : 0
  const scrubThumbPos = replayDay ? positionForDaysBack(scrubDaysBack, scrubMaxDays) : 1
  const scrubPosRef = useRef(1)
  const scrubDragRef = useRef<{ lastX: number } | null>(null)

  const applyScrubPosition = useCallback((p: number) => {
    const clamped = Math.min(1, Math.max(0, p))
    scrubPosRef.current = clamped
    const snapped = snapDaysBack(clamped, scrubMaxDays)
    // Snap to whole days everywhere except the live edge (0 = NOW).
    setReplayDay(snapped <= 0 ? null : isoDayForDaysBack(snapped))
  }, [scrubMaxDays])

  const onScrubPointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    trackOnce('scrubber_used', { surface: 'globe' })
    ensureReplayData()
    // Keyboard stepping (council wish 13): Safari/Firefox do NOT focus a
    // tabIndex div on click — without this, ArrowLeft/Right silently did
    // nothing after any pointer interaction with the track.
    e.currentTarget.focus()
    // Capture must never abort the scrub (it throws for exotic/synthetic
    // pointers) — without it the drag still works while the pointer stays
    // over the track.
    try { e.currentTarget.setPointerCapture(e.pointerId) } catch { /* uncaptured drag */ }
    const rect = e.currentTarget.getBoundingClientRect()
    scrubDragRef.current = { lastX: e.clientX }
    if (e.shiftKey) {
      // Shift = FINE from the start: grab the CURRENT position (no absolute
      // jump), then nudge with damped deltas.
      scrubPosRef.current = replayDay ? positionForDaysBack(
        Math.max(0, Math.floor((Date.now() - Date.parse(replayDay + 'T00:00:00Z')) / 86400000)),
        scrubMaxDays,
      ) : 1
    } else {
      applyScrubPosition((e.clientX - rect.left) / rect.width)
    }
  }, [ensureReplayData, applyScrubPosition, replayDay, scrubMaxDays])

  const onScrubPointerMove = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (!scrubDragRef.current) return
    const rect = e.currentTarget.getBoundingClientRect()
    if (e.shiftKey) {
      // FINE control (hold Shift): pointer deltas damped 4× — slower time
      // per pixel, for day-precise picking in the compressed deep past.
      // Fancier option (deliberately not built — Pedro: just the bar): scale
      // damping continuously by the pointer's VERTICAL distance from the
      // bar, so pulling away from the track smoothly increases granularity.
      const dx = e.clientX - scrubDragRef.current.lastX
      applyScrubPosition(scrubPosRef.current + (dx / Math.max(rect.width, 1)) * 0.25)
    } else {
      applyScrubPosition((e.clientX - rect.left) / rect.width)
    }
    scrubDragRef.current.lastX = e.clientX
  }, [applyScrubPosition])

  const onScrubPointerUp = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    scrubDragRef.current = null
    try { e.currentTarget.releasePointerCapture(e.pointerId) } catch { /* already released */ }
  }, [])

  const scrubStepDays = useCallback((delta: number) => {
    ensureReplayData()
    const current = replayDay
      ? Math.max(0, Math.floor((Date.now() - Date.parse(replayDay + 'T00:00:00Z')) / 86400000))
      : 0
    const next = Math.min(scrubMaxDays, Math.max(0, current + delta))
    scrubPosRef.current = positionForDaysBack(next, scrubMaxDays)
    setReplayDay(next <= 0 ? null : isoDayForDaysBack(next))
  }, [ensureReplayData, replayDay, scrubMaxDays])

  // #231: fetch the baseline-normalized heat composite for map color.
  // Falls back silently to volume if unavailable.
  // Fetch ALL countries (not a top-N) and min-max normalize the real value
  // band onto [0.1, 1.0] so the full blue→red gradient is used — the raw
  // composite clusters in a narrow band (~0.36–0.72), which mapped to a flat
  // orange and left most of the world dark (#231 follow-up, Pedro's review).
  useEffect(() => {
    let cancelled = false
    // Heat is ambient — the live 24h picture (matches country_heat_v2's
    // hardcoded 24h window). Selector retired 2026-07-15; this was already
    // pinned to 24h under S4.
    const h = DAY_WINDOW_HOURS
    fetch(`/api/v2/heat/countries?hours=${h}&limit=250`)
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (cancelled || !d?.items?.length) return
        const vals = d.items
          .filter((it: any) => it.country_code && typeof it.atlas_heat === 'number')
          .map((it: any) => [String(it.country_code).toUpperCase(), it.atlas_heat as number] as const)
        if (!vals.length) return
        // Rank-normalize + gamma instead of flat min-max→[0.1,1]. The old floor
        // was tuned when the endpoint served only the warm top-80; once ALL ~200
        // countries arrive (heat-fill 422 fixed 2026-07-01) min-max stretched the
        // COLD majority across the full ramp → rainbow world, nothing "hot".
        // Rank^1.6: bottom third ≈ transparent-faint, warm middle cyan/green,
        // top decile yellow→red — anomalies pop again (#231 semantics).
        const sorted = [...vals].sort((a, b) => a[1] - b[1])
        const n = Math.max(sorted.length - 1, 1)
        const m = new Map<string, number>()
        sorted.forEach(([code], i) => {
          m.set(code, Math.pow(i / n, 1.6))
        })
        setHeatComposite(m)
      })
      .catch(() => { /* map falls back to volume-intensity if composite unavailable */ })
    return () => { cancelled = true }
  }, [])

  // Initial map stays global. The hotspot reset button performs focused fly-to on demand.

  // Fly to top country when theme clicked in NarrativeThreads. EE consumes the
  // flyCountry prop transition; this just clears it after EE has latched.
  useEffect(() => {
    if (!mapFlyCountry) return
    setMapFlyCountry(null)
  }, [mapFlyCountry])

  // #234: focusing a person/thread centers the map on where its coverage
  // concentrates — the dominant country of the focus-scoped nodes. The trick
  // is to wait for the NEW nodes: on focus change `nodes` is briefly the
  // previous focus's data (refetch in flight), so flying immediately centres on
  // the wrong place and the ref-guard then suppresses the correction. Instead
  // we record the nodes reference at focus-change time and only fly once
  // `nodes` becomes a different array (the focus's own data has arrived).
  const flyTargetRef = useRef<{ key: string; nodesAtChange: unknown } | null>(null)
  useEffect(() => {
    const key = (focus.type === 'person' || focus.type === 'theme') && focus.value
      ? `${focus.type}:${focus.value}` : null
    flyTargetRef.current = key ? { key, nodesAtChange: nodes } : null
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus.type, focus.value])
  useEffect(() => {
    const target = flyTargetRef.current
    if (!target || !mapReady || nodes.length === 0) return
    if (nodes === target.nodesAtChange) return  // still the previous focus's nodes
    const dominant = nodes.reduce((m, n) => ((n.signalCount || 0) > (m.signalCount || 0) ? n : m), nodes[0])
    if (dominant?.id) { setMapFlyCountry(dominant.id); flyTargetRef.current = null }
  }, [nodes, mapReady, setMapFlyCountry])

  // Sync Global Focus to CountrySlide-over; EE flies via the flyCountry prop.
  // Flywheel: skip when a thread/theme panel is open — under compound focus a
  // thread opened while a country is focused keeps filter.country set, and
  // re-opening CountryBrief here would call handleCountryClick() which nulls
  // selectedTheme/selectedThread and snaps the just-opened thread closed.
  useEffect(() => {
    if (focus.type === 'country' && focus.value && focus.value !== selectedCountryCode
        && !selectedTheme && !selectedThread) {
      handleCountryClick(focus.value)
      setMapFlyCountry(focus.value)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus.type, focus.value, selectedCountryCode])

  // Open ThemeDetail when theme is focused via FocusContext (e.g. NarrativeThreads click)
  useEffect(() => {
    const filterCountry = filter.country || undefined
    // Flywheel: re-fire when the theme id changed OR — for a NON-thread theme
    // (opened via category/universe, not a thread-open) — when filter.country
    // changed under it, so a Country-chip ✕ correctly re-scopes the open theme
    // to global. A thread-open theme (selectedTheme.thread set) keeps its OWN
    // origin country and is NOT re-scoped (that origin came from the thread,
    // not the compound filter.country — the R2 protection).
    if (filter.theme && (!selectedTheme || selectedTheme.theme !== filter.theme
        || (!selectedTheme.thread && selectedTheme.originCountry !== filterCountry))) {
      const countryName = filter.country ? resolveCountryName(filter.country) : undefined
      // Item 8: carry the focus context's known label so a focus-driven open
      // keeps the opener's real thread name.
      setSelectedTheme({ theme: filter.theme, originCountry: filterCountry, originCountryName: countryName, labelHint: filter.themeLabel ?? undefined })
      setRightPanelThemeCountry(null)
    }
  }, [filter.theme, filter.country, selectedTheme])

  // Close CountryBrief when country focus is cleared externally (pill X button)
  useEffect(() => {
    if (!filter.country && selectedCountryCode) {
      setSelectedCountry(null)
      setSelectedCountryCode(null)
      setShowFlows(false)
      setRightPanelThemeCountry(null)
    }
  }, [filter.country])

  // #236 Task 7: the console's focus, read ONCE and handed to the ladder that
  // the stream slot (which panel to render), the Lens (what to name) and Back
  // (what to peel) all decide from. Declared above popPanel because that
  // callback depends on it.
  const consoleFocus = useMemo(() => ({
    storyQuery,
    threadId: selectedThread?.thread_id ?? null,
    threadLabel: selectedThread?.label ?? null,
    themeId: selectedTheme?.theme ?? null,
    // resolveThreadTitle, not resolveThreadLabel: for an opaque numeric id with
    // no label yet the latter returns the literal "Narrative Thread", which
    // reads as if the thread were nameless rather than still loading — and it
    // would be the breadcrumb's permanent text if the fetch never lands.
    // `loading` = we have no label from any opener yet; ThemeDetail's
    // onLabelResolved fills it in and pushScope swaps the trail entry.
    themeLabel: selectedTheme
      ? resolveThreadTitle(
          selectedTheme.theme,
          selectedTheme.thread?.label ?? selectedTheme.labelHint,
          !(selectedTheme.thread?.label ?? selectedTheme.labelHint),
        )
      : null,
    personName: focus.type === 'person' ? focus.value : null,
    countryCode: selectedCountryCode,
    countryName: selectedCountryCode ? resolveCountryName(selectedCountryCode, selectedCountry?.name) : null,
    attentionTitle: selectedPublicAttention?.title ?? null,
    chokepointId: selectedChokepoint?.id ?? null,
    chokepointName: selectedChokepoint?.name ?? null,
  }), [storyQuery, selectedThread, selectedTheme, focus.type, focus.value, selectedCountryCode, selectedCountry, selectedPublicAttention, selectedChokepoint])

  // Back navigation: pop the topmost open panel. Used by Escape (desktop), by
  // swipe-right-from-the-edge (mobile) and by the Lens breadcrumb.
  const popPanel = useCallback((): boolean => {
    // LAYERS ABOVE THE SLOT, peeled first because they are literally drawn on
    // top of it — a modal, the source profile, the theme's country drill-in.
    // They are deliberately NOT in consoleSlot: none of them is a Lens scope,
    // and peeling what sits underneath while one covers the screen would move
    // nothing the reader can see.
    if (showBriefing) { setShowBriefing(false); return true }
    if (selectedSourceProfile) { setSelectedSourceProfile(null); return true }
    if (rightPanelThemeCountry) { setRightPanelThemeCountry(null); return true }

    // THE SLOT ITSELF — ask the ladder, do not re-guess its order.
    //
    // This was a FOURTH hand-written copy of that ordering, and it disagreed
    // with the other three: it peeled thread/theme before story and attention
    // before person, where consoleSlot ranks story first and person above
    // attention. The disagreement was reachable, not theoretical —
    // FrameSheet's onOpenPin sets a person focus WITHOUT clearing an open
    // attention item (unlike handleThemeSelect and handleCountryClick, which
    // both null it), so the slot showed the person while Back cleared the
    // attention underneath it: the screen did not change and the tap did
    // nothing. Same shape for story-under-thread via SearchBar's onOpenStory.
    // Peel exactly the dimension that is SHOWING, and the three affordances
    // that share this function can no longer disagree with what is on screen.
    // Still one dimension per Back (never clearFocus, which would wipe the
    // whole compound frame at once).
    switch (consoleSlot(consoleFocus, false)) {
      case 'story': setStoryQuery(null); return true
      case 'person': setPerson(null); return true
      case 'attention': setSelectedPublicAttention(null); return true
      case 'thread':
      case 'theme':
        setSelectedTheme(null); setSelectedThread(null); setTheme(null)
        // Story Lens (Task 10, spec-review fix): Escape / mobile swipe-back
        // closing the thread panel must exit the lens the same way every other
        // close path does. stripLensParam (issue 4) prevents resurrection.
        // Inline exit, not syncLensToThreadOpen(null) — see clearAll's comment
        // above (the helper's !STORY_LENS_AUTO early-return must not apply here).
        if (storyLens.state.active) { storyLens.exit(); stripLensParam() }
        return true
      case 'country':
        setSelectedCountry(null)
        setSelectedCountryCode(null)
        setShowFlows(false)
        setCountry(null)
        return true
      case 'chokepoint': setSelectedChokepoint(null); return true
    }

    // Nothing is IN the slot, but a compound-focus COUNTRY CHIP can still be
    // standing: filter.country outlives the CountryBrief that set it, and the
    // ladder does not model it (the Lens never scopes to a chip alone). Kept
    // so Escape still clears a country focus set from the map without opening
    // a panel — the one peel the slot cannot see.
    if (selectedCountry || selectedCountryCode || filter.country) {
      setSelectedCountry(null)
      setSelectedCountryCode(null)
      setShowFlows(false)
      setCountry(null)
      return true
    }
    // 6.3a: nothing left to peel — on mobile, a Brief-entry analyst's swipe-back
    // exits to the Brief (same reading-first seam as closeAll), never a dead
    // gesture on a blank Stream tab. Desktop Escape stays a no-op (isMobile).
    if (isMobile && entrySource === 'brief') { navigate('/brief'); return true }
    return false
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showBriefing, selectedSourceProfile, rightPanelThemeCountry, consoleFocus, selectedCountry, selectedCountryCode, filter.country, isMobile, entrySource, navigate, storyLens.state.active, storyLens.exit, stripLensParam])

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') popPanel() }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [popPanel])

  // Swipe-right from the left edge = back (native mobile feel).
  useEffect(() => {
    let x0 = 0, y0 = 0, t0 = 0, tracking = false
    const onStart = (e: TouchEvent) => {
      const t = e.touches[0]
      tracking = t.clientX < 40 // only from near the left edge
      x0 = t.clientX; y0 = t.clientY; t0 = Date.now()
    }
    const onEnd = (e: TouchEvent) => {
      if (!tracking) return
      tracking = false
      const t = e.changedTouches[0]
      const dx = t.clientX - x0, dy = t.clientY - y0, dt = Date.now() - t0
      if (dx > 70 && Math.abs(dy) < 50 && dt < 600) popPanel()
    }
    window.addEventListener('touchstart', onStart, { passive: true })
    window.addEventListener('touchend', onEnd, { passive: true })
    return () => {
      window.removeEventListener('touchstart', onStart)
      window.removeEventListener('touchend', onEnd)
    }
  }, [popPanel])

  // #236 Task 6: a drill-in (thread, person, source, country, attention) is
  // exactly the thing the Lens exists to re-scope to, so opening one brings
  // the Lens forward — not Live, which is the unfocused firehose. The Lens
  // then renders the opened item (the focus argument to `surfaceFor` in the
  // shell below).
  useEffect(() => {
    if (!isMobile) return
    if (
      selectedTheme || focus.type === 'person' || selectedSourceProfile ||
      rightPanelThemeCountry || selectedCountry || selectedCountryCode ||
      selectedPublicAttention
    ) {
      setConsoleTab('lens')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMobile, selectedTheme, focus.type, selectedSourceProfile, rightPanelThemeCountry, selectedCountry, selectedCountryCode, selectedPublicAttention])

  const lensScope = useMemo(() => consoleLensScope(consoleFocus), [consoleFocus])

  useEffect(() => {
    // Phone only: on desktop the Lens does not render and the trail stays at
    // the field. A desktop->phone resize picks the scope up on the next tick.
    if (!isMobile) return
    focusLens(lensScope)
  }, [isMobile, lensScope, focusLens])


  // --- Session Trail Tracking ---
  useEffect(() => {
    if (selectedCountryCode) {
      trackVisit({ id: `country-${selectedCountryCode}`, type: 'country', title: selectedCountry?.name || selectedCountryCode, urlParams: `?country=${selectedCountryCode}` });
    }
  }, [selectedCountryCode, selectedCountry, trackVisit]);

  useEffect(() => {
    if (selectedTheme) {
      const params = new URLSearchParams()
      params.set('theme', selectedTheme.theme)
      if (selectedTheme.originCountry) params.set('country', selectedTheme.originCountry)
      if (selectedTheme.originAttention?.title) params.set('attention', selectedTheme.originAttention.title)
      trackVisit({
        id: `theme-${selectedTheme.theme}${selectedTheme.originAttention?.title ? `-attention-${selectedTheme.originAttention.title}` : ''}`,
        type: 'theme',
        title: selectedTheme.originAttention?.title
          ? `${selectedTheme.theme} from ${selectedTheme.originAttention.title}`
          : selectedTheme.theme,
        urlParams: `?${params.toString()}`,
        meta: selectedTheme.originAttention ? { originAttention: selectedTheme.originAttention.title } : undefined,
      });
    }
  }, [selectedTheme, trackVisit]);

  useEffect(() => {
    if (selectedSourceProfile) {
      trackVisit({ id: `source-${selectedSourceProfile}`, type: 'source', title: selectedSourceProfile, urlParams: `?source=${encodeURIComponent(selectedSourceProfile)}` });
    }
  }, [selectedSourceProfile, trackVisit]);

  useEffect(() => {
    if (focus.type === 'person' && focus.value) {
      trackVisit({ id: `person-${focus.value}`, type: 'person', title: focus.value, urlParams: `?person=${encodeURIComponent(focus.value)}` });
    }
  }, [focus.type, focus.value, trackVisit]);

  useEffect(() => {
    if (selectedPublicAttention) {
      trackVisit({ id: `public-attention-${selectedPublicAttention.title}`, type: 'public_attention', title: selectedPublicAttention.title, urlParams: `?attention=${encodeURIComponent(selectedPublicAttention.title)}` });
    }
  }, [selectedPublicAttention, trackVisit]);
  // ------------------------------

  // Auto-refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(refetch, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [refetch])

  // Zoom-adaptive flow limiting to reduce visual clutter
  const visibleFlows = useMemo(() => {
    // Determine the base set of flows:
    // On country focus, the FOCUSED fetch is now the authoritative source —
    // the backend computes pairs FOR that country (4fb25a11); the global
    // top-100 rarely contains small-country pairs, which is why focused
    // countries drew zero arcs (capture-doc A2). Unfiltered stays a fallback.
    // Flywheel #2: filter flows by the country ONLY when country is the
    // active map dimension (collapsed focus === country). Under a compound
    // "person over a warm country", selectedCountryCode is still set but the
    // map follows the person — showing that country's flow arcs would be the
    // same click-history incoherence the heat fix above removes.
    const flowCountry = focus.type === 'country' ? selectedCountryCode : null
    const baseFlows = flowCountry
      ? (flows.length ? flows : (unfilteredFlows || []))
      : flows;
    let filteredFlows = [...baseFlows];

    if (flowCountry) {
      filteredFlows = filteredFlows.filter(f =>
        f.sourceCountry === flowCountry ||
        f.targetCountry === flowCountry
      );
    }

    // EE is a fixed world-fit canvas (no zoom state) — the old MapLibre
    // zoom-scaled flow cap collapses to the world-view budget.
    const maxFlows = 25
    return filteredFlows
      .sort((a, b) => (b.strength || 0) - (a.strength || 0))
      .slice(0, maxFlows)
  }, [flows, unfilteredFlows, selectedCountryCode, focus.type])

  // Get crisis state for terminator auto-hide and anomalies
  const { enabled: crisisEnabled, anomalies } = useCrisis()

  // Merge anomaly data into nodes for coloring and pulse — capped at 100 by attention index,
  // not raw volume, so high-volume countries do not crowd out smaller baseline spikes.
  const enhancedNodes = useMemo(() => {
    const anomalyMap = new Map(anomalies.map((a: any) => [a.country_code, a]))
    return [...nodes].sort((a, b) => {
      const [aHeat, aSignals] = getNodePriority(a)
      const [bHeat, bSignals] = getNodePriority(b)
      if (bHeat !== aHeat) return bHeat - aHeat
      return bSignals - aSignals
    }).slice(0, 100).map(n => {
      const anomaly = anomalyMap.get(n.id)
      return {
        ...n,
        anomalyMultiplier: anomaly ? anomaly.multiplier : 1,
        isAnomaly: !!anomaly
      }
    })
  }, [nodes, anomalies])


  // Per-country heat + intensity — SINGLE SOURCE OF TRUTH for both the MapLibre
  // map (feature-states below) and the Equal Earth map (#212). See
  // lib/countryHeatStates. entityFocus mirrors the prior inline logic.
  const heatStates = useMemo(() => {
    // Flywheel #2: the map's node FETCH scopes by the collapsed `focus`
    // (person>country>theme). The heat COLORING must agree, or a compound
    // "person over a warm country" (selectedCountryCode still set) paints
    // country heat over person-fetched nodes — an incoherent map that depends
    // on click-history. So drive the country-heat branch off the collapsed
    // focus too: country heat only when focus.type==='country'; otherwise the
    // person/theme entityFocus wins (no longer gated on !selectedCountryCode).
    const entityFocus = isActive && !!focus.value
      && (focus.type === 'person' || focus.type === 'theme')
    return computeCountryHeatStates({
      enhancedNodes,
      // S1: a scrubbed day swaps the composite for that day's VOLUME ranks —
      // the strip label says so; never presented as historical heat.
      heatComposite: replayHeat ?? heatComposite,
      visibleFlows,
      selectedCountryCode: focus.type === 'country' ? selectedCountryCode : null,
      entityFocus,
    })
  }, [enhancedNodes, heatComposite, replayHeat, visibleFlows, selectedCountryCode, isActive, focus.type, focus.value])

  // Eclipse Lens: while engaged, MEMBERSHIP picks the hue (dominant footprint =
  // eclipse-red, shadow stories = shadow-cyan) and heat keeps driving opacity /
  // border glow. Off-lens this returns the SAME reference, so the map render is
  // byte-identical to before.
  const { mode: eclipseMode, data: eclipseData } = useEclipseMode()
  const eclipseHeatStates = useMemo(() => {
    if (eclipseMode !== 'ambient' || !eclipseData) return heatStates
    const sets = buildEclipseSets(eclipseData)
    const out = new Map(heatStates)
    for (const [cc, st] of out) {
      const lens = countryLens(cc, sets)
      if (lens) out.set(cc, { ...st, lens })
    }
    // Countries in the eclipse/shadow footprint with no heat still must read.
    for (const cc of sets.eclipseCountries) if (!out.has(cc)) out.set(cc, { heat: 0.15, intensity: 0.15, lens: 'eclipse' })
    for (const cc of sets.shadowCountries) if (!out.has(cc)) out.set(cc, { heat: 0.12, intensity: 0.12, lens: 'shadow' })
    return out
  }, [eclipseMode, eclipseData, heatStates])

  const nativeOverlayData = useMemo(() => {
    const activeChokepointSet = new Set(activeChokepoints)
    const flowsVisible = showFlows || !!selectedCountryCode || !!filter.theme
    return {
      flows: flowsVisible ? {
        type: 'FeatureCollection' as const,
        features: visibleFlows.map(flow => ({
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: [flow.source, flow.target] },
          properties: {
            strength: flow.strength || 0,
            sourceCountry: flow.sourceCountry,
            targetCountry: flow.targetCountry,
          },
        })),
      } : emptyFeatureCollection(),
      anomaly: {
        type: 'FeatureCollection' as const,
        features: enhancedNodes.filter((node: any) => node.isAnomaly).map((node: any) => {
          // #255 hover receipt: carry the anomaly's measured fields so the ring
          // can explain itself (multiplier/z/current vs baseline), not just ping.
          const a = anomalies.find((x: any) => x.country_code === node.id)
          return {
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [node.lon, node.lat] },
            properties: {
              signalCount: node.signalCount || 0,
              radius: Math.min(Math.max(6, Math.sqrt(node.signalCount || 1) * (sizeBoost ? 1.5 : 0.8)), 24),
              country_code: node.id,
              country_name: a?.country_name || node.label || node.id,
              multiplier: a?.multiplier ?? node.anomalyMultiplier ?? null,
              zscore: a?.zscore ?? null,
              current_count: a?.current_count ?? null,
              level: a?.level ?? null,
            },
          }
        }),
      },
      chokepoints: showVessels ? {
        type: 'FeatureCollection' as const,
        features: CHOKEPOINTS.map(cp => ({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [cp.lon, cp.lat] },
          properties: {
            ...cp,
            active: activeChokepointSet.has(cp.id),
            vesselCount: chokepointCounts[cp.id] || 0,
          },
        })),
      } : emptyFeatureCollection(),
      aircraft: showAircraft ? {
        type: 'FeatureCollection' as const,
        features: filteredAircraftData.map((aircraft: any) => ({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [aircraft.longitude, aircraft.latitude] },
          properties: {
            callsign: aircraft.callsign || 'Unknown',
            origin_country: aircraft.origin_country || '',
            alt: aircraft.baro_altitude || 0,
            true_track: aircraft.true_track,
          },
        })),
      } : emptyFeatureCollection(),
      vessels: showVessels ? {
        type: 'FeatureCollection' as const,
        features: vesselData.map((vessel: any) => ({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [vessel.longitude, vessel.latitude] },
          properties: {
            name: vessel.name || 'Unknown vessel',
            mmsi: vessel.mmsi || '',
            speed: vessel.speed || 0,
            heading: vessel.heading,
          },
        })),
      } : emptyFeatureCollection(),
      acled: {
        type: 'FeatureCollection' as const,
        features: (acledConflicts || [])
          .filter((event: any) => event.location?.longitude != null && event.location?.latitude != null)
          .map((event: any) => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [event.location.longitude, event.location.latitude] },
            properties: {
              type: event.type || '',
              fatalities: event.fatalities || 0,
              radius: Math.min(Math.max(4, Math.sqrt(event.fatalities || 1) * 3), 15) * (sizeBoost ? 1.25 : 1),
              // T3.3 P-FOCUS: carry the event identity so a click can center the
              // EVENT (not swallow it into its country). Flattened — MapLibre
              // feature props must be primitives.
              country: event.location?.country || '',
              place: event.location?.name || '',
              actor1: event.actors?.actor1 || '',
              actor2: event.actors?.actor2 || '',
              date: event.date || '',
              mentions: event.mentions || 0,
              lat: event.location?.latitude ?? null,
              lon: event.location?.longitude ?? null,
            },
          })),
      },
      disasters: {
        type: 'FeatureCollection' as const,
        features: disasterEvents
          .filter(ev => ev.longitude != null && ev.latitude != null)
          .map(ev => {
            const alert = (ev.alert || '').toLowerCase()
            const radius = ev.type === 'earthquake' && ev.magnitude
              ? Math.min(Math.max(4, (ev.magnitude - 3) * 2.2), 10)
              : alert === 'red' ? 8 : alert === 'orange' ? 6 : 4.5
            return {
              type: 'Feature',
              geometry: { type: 'Point', coordinates: [ev.longitude, ev.latitude] },
              properties: {
                dtype: ev.type, title: ev.title || '', alert: ev.alert || '',
                magnitude: ev.magnitude ?? null, url: ev.url || '',
                country: ev.country || '', radius,
                source: ev.source || '', time: ev.time || '',
                lat: ev.latitude, lon: ev.longitude,
              },
            }
          }),
      },
      terminator: buildTerminatorData(showTerminator && !crisisEnabled),
    }
  }, [
    activeChokepoints,
    acledConflicts,
    disasterEvents,
    chokepointCounts,
    enhancedNodes,
    filter.theme,
    filteredAircraftData,
    selectedCountryCode,
    showAircraft,
    showFlows,
    showTerminator,
    showVessels,
    sizeBoost,
    vesselData,
    visibleFlows,
    crisisEnabled,
    anomalies,
  ])

  // (MapLibre overlay-push + native layer-handler effects removed with the
  //  2026-07-04 deprecation — EE renders overlays from nativeOverlayData.)

  // Total signals for stats
  const totalSignals = nodes.reduce((sum, n) => sum + n.signalCount, 0)
  const historicalCoverageCue = buildHistoricalCoverageCue({
    source: focusMeta.source,
    coverage: focusMeta.coverage,
  })
  const openBrief = () => {
    // The Brief is the DAY's edition (fixed 24h since 2026-07-05) — the old
    // `range` param was already ignored there; dropped with the selector.
    // Carry-context (6.2): the active theme/label/query ride forward so the
    // Brief can honor what the analyst was reading. label only rides with a
    // theme (buildBriefParams enforces that); it asserts nothing on its own.
    const qs = buildBriefParams({
      country: selectedCountryCode,
      theme: selectedTheme?.theme,
      themeLabel: selectedTheme?.thread?.label ?? selectedTheme?.labelHint,
      storyQuery,
    })
    navigate(qs ? `/brief?${qs}` : '/brief')
  }

  // Data coverage start date
  const [dataStartDate, setDataStartDate] = useState<string | null>(null)
  useEffect(() => {
    fetch('/api/v2/stats')
      .then(r => r.json())
      .then(d => {
        if (d.database?.oldest_signal) {
          const dt = new Date(d.database.oldest_signal)
          setDataStartDate(dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }))
        }
      })
      .catch(() => { })
  }, [])

  // Prefetch briefing data so the modal opens instantly — the Brief and the
  // Briefing modal are both the DAY's edition (fixed 24h).
  const [prefetchedBriefing, setPrefetchedBriefing] = useState<any>(null)
  const [prefetchedInsight, setPrefetchedInsight] = useState<string | null>(null)
  const [prefetchedHours, setPrefetchedHours] = useState<number>(0)
  const [externalSearchQuery, setExternalSearchQuery] = useState<{ q: string; id: number } | undefined>(undefined)
  useEffect(() => {
    // The Brief is the DAY's edition (fixed 24h, 2026-07-05) — prefetch matches.
    prefetchBriefing(DAY_WINDOW_HOURS) // warm sessionStorage so /brief loads without spinner
    fetch(`/api/v2/briefing?hours=${DAY_WINDOW_HOURS}`).then(r => r.json()).then(d => { setPrefetchedBriefing(d); setPrefetchedHours(DAY_WINDOW_HOURS) }).catch(() => { })
    fetch(`/api/v2/briefing/insight?hours=${DAY_WINDOW_HOURS}`).then(r => r.json()).then(d => { if (d.insight) setPrefetchedInsight(d.insight) }).catch(() => { })
  }, [])

  // Show loader until nodes AND map are ready; hard cap at 10s
  const [appReady, setAppReady] = useState(false)
  useEffect(() => {
    if (!loading && nodes.length > 0 && mapReady) setAppReady(true)
  }, [loading, nodes.length, mapReady])
  useEffect(() => {
    const t = setTimeout(() => setAppReady(true), 10000)
    return () => clearTimeout(t)
  }, [])

  // ── #233 panel grid: bucketed presets + per-bucket persisted layout ──
  // Buckets (laptop/desktop/big) keep a 4K arrangement from ever being applied
  // to a laptop and vice versa; each bucket persists independently.
  const gridShellRef = useRef<HTMLDivElement | null>(null)
  const [savedGridLayouts, setSavedGridLayouts] = useState<Partial<Record<LayoutBucket, LayoutItem[]>>>(() => loadSavedLayouts())
  // The grid width drives BOTH the bucket and RGL's column pixel math, so it
  // must track the real container — not a fixed seed. (react-grid-layout's
  // useContainerWidth froze at its initialWidth here, leaving the cockpit
  // rendered at ~1280px inside a much wider viewport; measured off the shell
  // instead.) clientWidth excludes the vertical scrollbar so the grid never
  // provokes a horizontal one.
  const [gridWidth, setGridWidth] = useState(() => (typeof window === 'undefined' ? 1280 : Math.max(320, window.innerWidth)))
  const gridBucket = bucketForWidth(gridWidth)
  const gridLayout = useMemo(() => layoutForBucket(gridBucket, savedGridLayouts), [gridBucket, savedGridLayouts])
  // The shell sits below the command bar AND the in-flow disclaimer strip, so
  // its available height is measured, not assumed.
  const [gridShellH, setGridShellH] = useState(() => (typeof window === 'undefined' ? 800 : Math.max(320, window.innerHeight - 96)))
  useEffect(() => {
    if (isMobile) return
    const measure = () => {
      const el = gridShellRef.current
      if (!el) return
      setGridShellH(Math.max(320, window.innerHeight - el.getBoundingClientRect().top))
      setGridWidth(Math.max(320, el.clientWidth))
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [isMobile])
  const gridRowHeight = rowHeightFor(gridShellH, GRID_GAP, GRID_GAP)
  const handleGridLayoutChange = (layout: Layout) => {
    const next = layout.map(l => ({ ...l }))
    setSavedGridLayouts(prev => {
      const cur = prev[gridBucket]
      if (cur && JSON.stringify(cur) === JSON.stringify(next)) return prev
      saveLayout(gridBucket, next)
      return { ...prev, [gridBucket]: next }
    })
  }
  // Resize-end snap: the released panel clips to the alignment lines the grid
  // already draws (neighbor edges / container edge) and absorbs 1-unit dead
  // gaps — easy alignment instead of pixel nudging. Drag-stop is untouched.
  // RGL v2 fires onLayoutChange with the RAW layout synchronously right after
  // onResizeStop, so the snapped layout is applied one tick later to win the
  // write (the controlled `layout` prop then re-syncs the grid).
  const handleGridResizeStop = (layout: Layout, _oldItem: LayoutItem | null, newItem: LayoutItem | null) => {
    if (!newItem) return
    const snapped = snapResizedItem(layout, newItem.i)
    if (JSON.stringify(snapped) === JSON.stringify(layout)) return
    window.setTimeout(() => handleGridLayoutChange(snapped), 0)
  }
  const resetGridLayout = () => {
    clearSavedLayouts()
    setSavedGridLayouts({})
  }

  return (
    <div className={`app ${crisisEnabled ? 'crisis-mode' : ''}`}>
      <AtlasLoader visible={!appReady} />
      {/* Command Bar */}
      <header className="command-bar">
        <div className="command-bar-left">
          <h1 className="brand" onClick={() => navigate('/')} style={{ cursor: 'pointer' }} data-tip="Back to home"><Globe size={16} /> Atlas <span className="brand-tag">L2 · Analyst console</span></h1>
          <span className="live-pill" data-tip="Live open signals from media, curated feeds, public attention, humanitarian sources, and NLP enrichment. Source cadences vary.">
            <span className="live-pill-dot" />
            LIVE DATA
          </span>
          {dataStartDate && (
            <span className="data-since-pill" data-tip={`Signal archive starts ${dataStartDate}. Historical coverage grows over time.`}>
              FROM {dataStartDate.toUpperCase()}
            </span>
          )}
        </div>
        <div className="command-bar-center">
          <div data-tour="search" className="command-search-tour-target">
            <SearchBar
              onThemeSelect={handleThemeSelect}
              onCountrySelect={(code) => { handleCountryClick(code); setMapFlyCountry(code) }}
              onPublicAttentionSelect={handlePublicAttentionSelect}
              onOpenStory={(q) => {
                track('search_story_open', { q_len: q.length })
                setStoryQuery(q)
              }}
              onStartInvestigation={(q) => {
                createInvestigation(q)
                setResearchQuery(q)
                track('workbench_open', { via: 'start_investigation' })
                setWorkbenchOpen(true)
                setWbRefresh(t => t + 1)
              }}
              externalQuery={externalSearchQuery}
            />
          </div>
          {/* The VIEW time selector is GONE (2026-07-15): the scrubber is
              time — one log-scale bar on the map carries the whole history.
              The UNIVERSE shortcut is gone too: the GLOBE|UNIVERSE tab in
              the map panel is the single equal-billing home. */}
          <button
            className={`time-btn workbench-btn ${workbenchOpen ? 'active' : ''}`}
            data-tour="workspace-button"
            data-tip="Investigation Workbench: research plans, pins, and saved routes"
            onClick={() => setWorkbenchOpen(open => { if (!open) track('workbench_open'); return !open })}
          >
            WORKBENCH
            {workspaceItems.length > 0 && <span className="cmd-count">{workspaceItems.length}</span>}
          </button>
        </div>
        <div className="command-bar-right">
          <div className="stats">
            {loading ? '...' : (
              <span
                style={{ opacity: isRefetching ? 0.5 : 1, transition: 'opacity 0.2s' }}
                data-tip={`Countries and signals in the selected time window${filter.country || filter.theme ? ' (filtered view)' : ' (global)'}`}
              >
                {nodes.length} countries · {totalSignals.toLocaleString()} signals
              </span>
            )}
            {historicalCoverageCue && (
              <span className="historical-coverage-pill" data-tip={historicalCoverageCue.tip}>
                {historicalCoverageCue.label}
              </span>
            )}
          </div>
          <UtcClock />
          {isActive && (
            <button
              className="cmd-btn cmd-btn--watch"
              onClick={() => {
                const label = filter.person || filter.concept?.label || (filter.theme ? filter.theme.replace(/_/g, ' ').toLowerCase() : null) || filter.country || 'Watch'
                setWatchNamePrompt(label)
              }}
              data-tip="Save current filter as a named watch"
            >
              <BookmarkPlus size={13} /> <span className="cmd-btn-label">WATCH</span>
            </button>
          )}
          <button className="cmd-btn" data-tour="brief-button" onClick={openBrief} data-tip="Open the intelligence brief">
            <ClipboardList size={13} /> <span className="cmd-btn-label">BRIEF</span>
            {watches.length > 0 && <span className="cmd-count">{watches.length}</span>}
          </button>
          <button
            className="cmd-btn"
            onClick={toggleDayNight}
            aria-label={consoleTheme.scheme === 'dark' ? 'Switch to day theme' : 'Switch to night theme'}
            aria-pressed={consoleTheme.scheme === 'dark'}
            data-tip={consoleTheme.scheme === 'dark' ? 'Day theme' : 'Night theme'}
          >
            {consoleTheme.scheme === 'dark' ? <Sun size={13} /> : <Moon size={13} />}
          </button>
          {/* TOUR + Settings live in a "···" overflow menu (#152) so the bar
              keeps only primary actions visible. */}
          <div className="cmd-more-wrap">
            <button
              className="cmd-btn"
              onClick={() => setMoreMenuOpen(open => !open)}
              data-tip="More: guided tour, settings"
              aria-label="More options"
            >
              <MoreHorizontal size={13} />
            </button>
            {moreMenuOpen && (
              <div className="cmd-menu cmd-more-menu">
                <button
                  className="cmd-menu-item"
                  onClick={() => { setMoreMenuOpen(false); setTourRunId(id => id + 1) }}
                >
                  <HelpCircle size={13} /> Guided tour
                </button>
                <button
                  className="cmd-menu-item"
                  onClick={() => { setMoreMenuOpen(false); setSettingsOpen(true) }}
                >
                  <Settings size={13} /> Settings
                </button>
                {!isMobile && (
                  <button
                    className="cmd-menu-item"
                    onClick={() => { setMoreMenuOpen(false); resetGridLayout() }}
                    data-tip="Restore the default panel arrangement for this screen size"
                  >
                    <span style={{ fontSize: 13, lineHeight: 1 }}>⊞</span> Reset panel layout
                  </button>
                )}
              </div>
            )}
          </div>
          <SettingsPanel
            showTerminator={showTerminator}
            onToggleTerminator={setShowTerminator}
            sizeBoost={sizeBoost}
            onToggleSizeBoost={setSizeBoost}
            open={settingsOpen}
            onClose={() => setSettingsOpen(false)}
          />
        </div>
      </header>

      {/* A1: persistent focus chip — shows what's focused and gives one ✕ to
          return to the whole, unfocused view (the missing country deselect). */}
      {/* T11 gate fix (M2), reviewed and DELIBERATELY left unwired: this is
          the granular theme-chip ✕ (not a full country/context-switch door),
          and a prior review (T5/T10) ruled that keeping the lens active here
          is spec-compliant — it's the only door that reveals the STORY|ALL
          stream tabs, so closing the theme panel alone should not also kill
          the lens session the analyst may still want (e.g. to re-open a
          sibling from the STORY tab). Only handleCountryClick and the
          thread/theme-close paths in popPanel/clearAll/closeAll exit it. */}
      <FocusIndicator onClear={clearAll} onRemoveTheme={() => { setTheme(null); setSelectedTheme(null); setSelectedThread(null) }} />
      {/* Flywheel Task 2.4: the always-visible "investigation you're building" —
          pinned items auto-sorted into WHO/WHERE/WHAT lanes. Invisible until the
          first pin (prominence gradient). Clicking a pin re-opens it by type. */}
      {!isMobile && (
        <FrameStrip
          onOpenPin={(item) => {
            const p = new URLSearchParams(item.urlParams)
            if (item.type === 'theme' && p.get('theme')) handleThemeSelect(p.get('theme')!)
            else if (item.type === 'person') setFocus('person', decodeURIComponent(p.get('person') || item.title), item.title)
            else if (item.type === 'country' && p.get('country')) handleCountryClick(p.get('country')!)
          }}
          // ◎ callout: Scope opens+scopes the connected thread (compound focus);
          // ＋Report opens the Workbench to build from these pins.
          onScopeThread={(threadId, label) => handleThemeSelect(threadId, undefined, undefined, undefined, label)}
          onOpenReport={() => setWorkbenchOpen(true)}
        />
      )}

      <div className="coverage-disclaimer" data-tip="Atlas colors countries by deviation from each country's recent baseline. Raw volume increases evidence density, but it is not treated as real-world importance.">
        Coverage bias: map heat is baseline-normalized; raw volume is evidence density, not importance.
      </div>

      {(() => {
        /* #233 grid revival: panels are defined ONCE, then laid out either in
           the mobile tab shell (unchanged IA) or the desktop drag/resize grid.
           RGL positions children with transforms — panels never unmount on
           drag/resize/rearrange (display-toggle keep-alive preserved). */
        /* Panel 1: GLOBAL RADAR */
        const radarPanel = (
        <div className="terminal-panel radar" data-tour="globe">
          <div className="panel-header">
            <div className="panel-header-title-wrap">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <button
                  className={`dock-tab ${!universeOpen ? 'active' : ''}`}
                  onClick={() => setUniverseOpen(false)}
                  data-tip="Geographic projection — narrative activity by country"
                >
                  GLOBE
                </button>
                <button
                  className={`dock-tab ${universeOpen ? 'active' : ''}`}
                  onClick={() => setUniverseOpen(true)}
                  data-tip="Semantic projection — every living story as a body; categories as constellations; relations measured in full vector space"
                >
                  UNIVERSE
                </button>
                {!universeOpen && <PanelHelpButton panel="globe" />}
              </span>
              <span className="panel-subtitle">{universeOpen ? 'stories by meaning · alive in time' : 'narrative activity by country'}</span>
            </div>
            {!universeOpen && (
            <div className="panel-header-controls">
              <button
                className={`layer-btn ${showHeatmap ? 'active' : ''}`}
                onClick={() => { track('layer_toggle', { layer: 'heat', on: !showHeatmap }); setShowHeatmap(!showHeatmap) }}
                data-tip="Country heat layer — color = composite anomaly (velocity, surprise, source diversity, local voice) vs each country's own baseline, NOT raw volume. A small country spiking above its norm outranks a high-volume one. Border thickness = signal volume (evidence density)."
              >
                HEAT
              </button>
              <button
                className={`layer-btn ${showFlows ? 'active' : ''}`}
                onClick={() => { track('layer_toggle', { layer: 'flow', on: !showFlows }); setShowFlows(!showFlows) }}
                data-tip="Narrative flows — arcs connect countries sharing dominant media themes. Width = co-occurrence strength. Non-directional."
              >
                FLOW
              </button>
              <button
                className={`layer-btn ${showAircraft ? 'active' : ''} ${showAircraft && aircraftError ? 'layer-btn-error' : ''} ${!showAircraft && (filter.country || filter.theme) ? 'layer-btn-hint' : ''}`}
                onClick={() => { track('layer_toggle', { layer: 'plane', on: !showAircraft }); setShowAircraft(!showAircraft) }}
                data-tip={
                  showAircraft && aircraftError
                    ? 'No aircraft data available'
                    : !showAircraft && (filter.country || filter.theme)
                      ? 'Aircraft layer — not typically relevant to narrative analysis. Enable only for transport/geopolitical investigations.'
                      : 'Live ADS-B aircraft positions. White = cruise (> 10,000 ft), amber = mid, orange = low altitude.'
                }
              >
                PLANE {showAircraft && aircraftError && '⚠'}
              </button>
              <button
                className={`layer-btn ${showVessels ? 'active' : ''} ${activeChokepoints.length > 0 && !showVessels ? 'layer-btn-hint' : ''}`}
                onClick={() => { track('layer_toggle', { layer: 'ships', on: !showVessels }); setShowVessels(!showVessels) }}
                data-tip={
                  showVessels
                    ? `${vesselData.length} vessels at chokepoints${vesselConnected ? ' · live' : ' · connecting...'}`
                    : activeChokepoints.length > 0
                      ? `${activeChokepoints.length} relevant chokepoint(s) for this country`
                      : 'Show vessels near strategic chokepoints'
                }
              >
                SHIPS{showVessels && vesselData.length > 0 ? ` ${vesselData.length}` : ''}{showVessels && !vesselConnected ? ' ⏳' : ''}
              </button>
              <button
                className="layer-btn layer-btn--reset"
                onClick={() => {
                  // Reset EE's transform + clear focus; re-center on the
                  // HOTTEST region (the composite, not volume) — L8, Pedro:
                  // 'que empiece en lo más caliente'.
                  setSelectedCountry(null)
                  setSelectedCountryCode(null)
                  setShowFlows(false)
                  clearFocus()
                  setEeResetNonce(n => n + 1)
                  let hottest: string | null = null, hv = -1
                  heatComposite.forEach((v, code) => { if (v > hv) { hv = v; hottest = code } })
                  setMapFlyCountry(hottest)
                }}
                data-tip="Tilted or rotated: reset to flat north-up view. Already flat: fly to highest-attention region"
                aria-label="Reset map view or fly to highest-attention region"
              >
                ↺
              </button>
            </div>
            )}
          </div>
          <div className="panel-content">
            <MapErrorBoundary>
              {(  /* EE canvas — the one map; MapLibre deprecated 2026-07-04 */
                <EqualEarthMap
                  heatStates={eclipseHeatStates}
                  showHeatmap={showHeatmap}
                  selectedCountryCode={selectedCountryCode}
                  flyCountry={mapFlyCountry}
                  resetNonce={eeResetNonce}
                  overlay={nativeOverlayData}
                  onPinCountry={handlePinMapCountry}
                  onPinMarker={handlePinMapMarker}
                  onMarkerClick={(kind, p) => {
                    // Mirrors the MapLibre layer handlers (parity audit).
                    if (kind === 'chokepoint') {
                      const cp = CHOKEPOINTS.find(item => item.id === p?.id)
                      if (!cp) return
                      setSelectedChokepoint(prev => prev?.id === cp.id ? null : cp)
                      setMapFlyCountry(cp.primaryCountry)
                    } else if (kind === 'disaster') {
                      if (p.url) window.open(String(p.url), '_blank', 'noopener,noreferrer')
                    } else {
                      setSelectedConflictEvent({
                        type: String(p.type || ''), country: String(p.country || ''), place: String(p.place || ''),
                        actor1: String(p.actor1 || ''), actor2: String(p.actor2 || ''), date: String(p.date || ''),
                        fatalities: Number(p.fatalities) || 0, mentions: Number(p.mentions) || 0,
                        lat: p.lat != null && p.lat !== '' ? Number(p.lat) : null,
                        lon: p.lon != null && p.lon !== '' ? Number(p.lon) : null,
                      })
                      // #232 UX slice: the map also centers on the event's country
                      // (T3.3 keeps the EVENT as the subject; this only moves the
                      // camera — full country focus stays behind the panel's link).
                      const cc = conflictCountryCode({ location: { country: String(p.country || '') } })
                      if (cc) setMapFlyCountry(cc)
                    }
                  }}
                  onCountryClick={(gdelt, name) => {
                    // S3: while scrubbed, a country click asks about THAT DAY.
                    if (replayDay) { setDayEvidenceCountry(gdelt); return }
                    handleCountryClick(gdelt)
                    setFocus('country', gdelt, name || gdelt)
                    setMapFlyCountry(gdelt)
                  }}
                />
              )}
              <div className="globe-vignette" />
              {!universeOpen && replayDay && dayEvidenceCountry && (
                <DayEvidencePanel
                  day={replayDay}
                  country={dayEvidenceCountry}
                  onClose={() => setDayEvidenceCountry(null)}
                  onOpenLive={() => {
                    const cc = dayEvidenceCountry
                    setDayEvidenceCountry(null)
                    setReplayDay(null)
                    if (cc) { handleCountryClick(cc); setFocus('country', cc, cc); setMapFlyCountry(cc) }
                  }}
                />
              )}
              {!universeOpen && (
                /* THE SCRUBBER IS TIME (2026-07-15): one bar, the whole
                   replayable history inside. Log scale — the right half is
                   the last ~7-10 days at day granularity, the deep past
                   compresses toward the left edge (archive floor / 90d cap,
                   honestly labeled). Hold Shift while dragging for fine
                   control. Follow-up: the UNIVERSE scrubber still runs its
                   own linear 30d scale (topic tracks) — unify it onto
                   lib/scrubberScale when its history deepens. */
                <div className="globe-scrubber" data-tip={`The scrubber is time — the whole replayable history in one bar. Recent days are wide on the right; the deep past compresses left (log scale). Hold SHIFT while dragging for fine control. Country intensity replays that day's signal VOLUME (the composite heat has no history); scrubber reaches back ${scrubMaxDays} days to the archive. NOW restores live heat.`}>
                  <button
                    /* Unmissable NOW pill (council wish 13): quiet state chip at
                       the live edge; while scrubbed it becomes the loud
                       return-to-live action. */
                    className={`globe-scrubber-now ${replayDay ? 'globe-scrubber-now--return' : 'active'}`}
                    onClick={() => { scrubPosRef.current = 1; setReplayDay(null) }}
                    data-tip={replayDay ? 'Return to the live picture' : 'You are at the live edge'}
                  >{replayDay ? '◀ NOW' : '● NOW'}</button>
                  <div
                    className="globe-scrubber-track"
                    role="slider"
                    tabIndex={0}
                    aria-label="Time scrubber — whole history, log scale"
                    aria-valuemin={0}
                    aria-valuemax={scrubMaxDays}
                    aria-valuenow={scrubDaysBack}
                    aria-valuetext={replayDay ? `${scrubDaysBack} days back (${replayDay})` : 'now'}
                    onPointerDown={onScrubPointerDown}
                    onPointerMove={onScrubPointerMove}
                    onPointerUp={onScrubPointerUp}
                    onPointerCancel={onScrubPointerUp}
                    onKeyDown={e => {
                      if (e.key === 'ArrowLeft') { e.preventDefault(); scrubStepDays(1) }
                      else if (e.key === 'ArrowRight') { e.preventDefault(); scrubStepDays(-1) }
                      else if (e.key === 'Home') { e.preventDefault(); scrubStepDays(scrubMaxDays) }
                      else if (e.key === 'End') { e.preventDefault(); scrubPosRef.current = 1; setReplayDay(null) }
                    }}
                  >
                    <div className="globe-scrubber-fill" style={{ width: `${scrubThumbPos * 100}%` }} />
                    <div className="globe-scrubber-thumb" style={{ left: `${scrubThumbPos * 100}%` }} />
                  </div>
                  <span className="globe-scrubber-label">
                    {replayDay
                      ? `${new Date(replayDay + 'T00:00:00Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })}${
                          scrubDaysBack >= scrubMaxDays
                            ? (farEdgeKind() === 'archive-floor' ? ' · archive floor' : ` · ${REPLAY_ENDPOINT_CAP_DAYS}d replay cap`)
                            : ''
                        } · volume replay`
                      : 'NOW · live heat'}
                  </span>
                  {/* Council wish 13: layers with no history (events / ships /
                      hazards) keep showing TODAY while the heat replays the
                      past — say so instead of letting Jul-17 events pose as
                      May-12 events. */}
                  {replayDay && (() => {
                    const liveOnly = [
                      (acledConflicts?.length ?? 0) > 0 ? 'events' : null,
                      disasterEvents.length > 0 ? 'hazards' : null,
                      showVessels ? 'ships' : null,
                      showAircraft ? 'aircraft' : null,
                    ].filter(Boolean)
                    return liveOnly.length > 0 ? (
                      <span
                        className="globe-scrubber-livebadge"
                        data-tip="These marker layers have no replayable history — they always show the live picture, even while the heat replays a past day."
                      >
                        {liveOnly.join(' · ')}: live — not replayed
                      </span>
                    ) : null
                  })()}
                </div>
              )}
            </MapErrorBoundary>
            {/* The map key belongs to the GLOBE only. Hide it when the UNIVERSE
                tab is active OR a full-screen overlay is up (Investigation
                Workbench / dossier report inside it / Theme Compare) — those
                overlays establish trapped stacking contexts (workbench-overlay
                has backdrop-filter → its z-9700 dossier is pinned at z-60
                globally) so the Legend's z-800 would otherwise paint on top. */}
            {!universeOpen && !workbenchOpen && !compareTheme && <Legend
              showHeatmap={showHeatmap}
              // #179: flows render whenever a country/theme filter is active,
              // not only when the FLOWS toggle is on — the legend must follow
              // what the map actually shows.
              showFlows={showFlows || !!selectedCountryCode || !!filter.theme}
              showAircraft={showAircraft}
              showVessels={showVessels}
              showTerminator={showTerminator}
              activeCountry={filter.country}
              activeTheme={filter.theme}
              activeThemeLabel={selectedTheme?.thread?.label ?? selectedTheme?.labelHint ?? filter.themeLabel ?? selectedThread?.label ?? null}
              vesselCount={vesselData.length}
              vesselConnected={vesselConnected}
              aircraftError={aircraftError}
              conflictCount={acledConflicts?.length ?? 0}
              disasterCount={disasterEvents.length}
              anomalyCount={enhancedNodes.filter((n: any) => n.isAnomaly).length}
            />}
            {/* Universe tab: the same stories in the semantic projection —
                mounts OVER the map (map stays mounted; display:none crash
                lesson). An open thread travels to its orbit HERE (spec §7.3). */}
            {universeOpen && (
              <div className="universe-panel">
                <UniverseView
                  onThemeSelect={(themeId, label) => handleThemeSelect(themeId, undefined, undefined, undefined, label)}
                  activeTheme={selectedTheme?.theme ?? null}
                  activeThemeLabel={selectedTheme ? (selectedTheme.thread?.label ?? selectedTheme.labelHint ?? resolveThreadLabel(selectedTheme.theme)) : undefined}
                  hours={DAY_WINDOW_HOURS} /* universe field = live day (ambient) */
                  focusKind={focus.type === 'person' ? 'person' : filter.country ? 'country' : null}
                  focusValue={focus.type === 'person' ? focus.value : (filter.country ?? null)}
                  onPersonSelect={(name) => { setFocus('person', name, name); setMapFlyCountry(null) }}
                  onCountrySelect={(code) => { setMapFlyCountry(code); setRightPanelThemeCountry({ code, name: code }) }}
                />
              </div>
            )}
          </div>
        </div>

        )

        // #236 Task 6: the phone's console surface. Three surfaces from two
        // tabs, because the Lens changes shape with focus — see surfaceFor,
        // where the tab decides FIRST so Live can never resolve to the same
        // thing as the Lens. Computed only on the phone; the `isMobile &&`
        // short-circuit means desktop never evaluates the ladder.
        // Task 7 review: "is anything focused" was a THIRD hand-listing of the
        // focus states, free to drift from the two that decide what renders.
        // It is the same question consoleSlot already answers — anything but
        // `blank` — so it asks that instead. liveTab is false here on purpose:
        // this argument is about FOCUS, and surfaceFor applies the tab itself.
        const mobileSurface: MobileSurface | null = isMobile
          ? surfaceFor(consoleTab, consoleSlot(consoleFocus, false) !== 'blank')
          : null
        // #236 Task 7 rename: `threadsHidden` named the DESKTOP panel it
        // happened to hide. On the phone that panel is the Lens's FIELD — the
        // ranked list you open things from — so it is named for the role,
        // which is what the flag actually decides. Its only consumer is
        // `paused`; <LensPanel/> owns the visibility toggle off the same
        // `fieldVisible` rule, so the pane and its paused flag cannot drift.
        // The read pane is the exact mirror: it serves the two surfaces the
        // field does not, so it is hidden precisely when the field shows.
        // Both are derived from the one exported rule for that reason.
        const fieldHidden = mobileSurface !== null && !fieldVisible(mobileSurface)
        const readPaneHidden = mobileSurface !== null && fieldVisible(mobileSurface)

        {/* Panel 2: SIGNAL STREAM — the intel hub, swaps based on active context */}
        const streamPanel = (() => {
          // Live is the firehose, always. Without this the stream panel's
          // focus ladder wins and tapping Live with a thread open moved the
          // active pill while the screen did not change by one pixel — the
          // Lens-direction dead end, mirrored. Focus is NOT cleared: the open
          // thread is still there when the user taps back to the Lens.
          const liveTab = mobileSurface === 'live'
          // #236 Task 7 review: the ladder that used to live here — seven
          // guarded booleans plus the JSX chain that ranked them — now lives in
          // lib/lensScope `consoleSlot`, because the Lens needs the SAME answer
          // to name what this renders. It was transcribed there before; a
          // transcription is a copy, and a copy drifts. These booleans are now
          // views of one decision, kept so the ~40 call sites below read the
          // same as they always did.
          // Flywheel compound focus is IN that ladder: a freshly-opened
          // thread/theme outranks a standing person focus for the middle panel
          // (Pedro's call — "show the thread"); the person stays a scope chip
          // driving the map/list. Person wins the panel only when no
          // thread/theme is open. lensScope.test.ts pins that ordering.
          const slot = consoleSlot(consoleFocus, liveTab)
          const isStory = slot === 'story'
          const isThread = slot === 'thread'
          const isTheme = slot === 'theme'
          const isPerson = slot === 'person'
          const isCountry = slot === 'country'
          const isPublicAttention = slot === 'attention'
          const isChokepoint = slot === 'chokepoint'
          const closeAll = () => { setStoryQuery(null); setSelectedTheme(null); setSelectedThread(null); setThemeBackStack([]); setSelectedPublicAttention(null); setRightPanelThemeCountry(null); setSelectedCountry(null); setSelectedCountryCode(null); setShowFlows(false); setSelectedChokepoint(null); setSelectedConflictEvent(null); clearFocus(); setPrevStreamCtx(null); if (filter.theme) setTheme(null)
            // Story Lens (Task 10, Step 2): this is the ThemeDetail/EntityPanel/
            // ThreadFocusPanel/PublicAttentionPanel close path — the panel is
            // going back to a blank stream, so the lens must not linger over
            // nothing. Unconditional call is safe (exit() no-ops when inactive).
            // stripLensParam (issue 4) prevents resurrection. Inline exit, not
            // syncLensToThreadOpen(null) — see clearAll's comment above.
            storyLens.exit()
            stripLensParam()
            // 6.3a: on mobile, an analyst who entered from the Brief returns THERE
            // when the last reading panel closes — never a drop into the blank
            // Stream tab. Desktop unchanged (guarded on isMobile).
            if (isMobile && entrySource === 'brief') navigate('/brief') }
          // Smart back: one step up, not all the way to stream
          const handleStreamBack = () => {
            if (prevStreamCtx?.type === 'chokepoint') {
              setSelectedCountry(null); setSelectedCountryCode(null); setShowFlows(false); clearFocus()
              setPrevStreamCtx(null)
              // selectedChokepoint still set → ChokepointPanel reappears
            } else if (prevStreamCtx?.type === 'theme') {
              setSelectedCountry(null); setSelectedCountryCode(null); setShowFlows(false); clearFocus()
              setSelectedTheme({ theme: prevStreamCtx.theme, originCountry: prevStreamCtx.originCountry, originCountryName: prevStreamCtx.originCountryName })
              setPrevStreamCtx(null)
              // Story Lens (Task 10, spec-review fix): restoring A re-anchors to A.
              // PrevCtx('theme') carries no label — the back-restore path has
              // no cheap hint here (T11 gate L4 covers the doors that do).
              syncLensToThreadOpen(prevStreamCtx.theme)
            } else if (prevStreamCtx?.type === 'country') {
              handleCountryClick(prevStreamCtx.code)
              setMapFlyCountry(prevStreamCtx.code)
              setPrevStreamCtx(null)
            } else {
              closeAll()
            }
          }
          const handleThemeBack = () => {
            const [previous, ...rest] = themeBackStack
            if (!previous) {
              handleStreamBack()
              return
            }
            setSelectedTheme(previous)
            setThemeBackStack(rest)
            setRightPanelThemeCountry(previous.originCountry && previous.originCountryName
              ? { code: previous.originCountry, name: previous.originCountryName }
              : null)
            // Story Lens (Task 10, spec-review fix): restoring A re-anchors to A.
            // Same label source line 2109 already trusts (thread.label, else
            // the opener's labelHint) — T11 gate L4.
            syncLensToThreadOpen(previous.theme, previous.thread?.label ?? previous.labelHint)
          }
          const backLabel = prevStreamCtx?.type === 'chokepoint'
            ? `← ${prevStreamCtx.cp.name}`
            : prevStreamCtx?.type === 'theme'
              ? `← ${prevStreamCtx.theme.replace(/_/g, ' ').slice(0, 20)}`
              : '← STREAM'
          const selectedCountryName = selectedCountryCode
            ? resolveCountryName(selectedCountryCode, selectedCountry?.name)
            : ''
          const isBlankState = !isPerson && !isCountry && !isTheme && !isThread && !isPublicAttention && !isChokepoint
          let panelTitle = isBlankState ? (
            <>
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                Signal stream
                <PanelHelpButton panel="signal-stream" />
              </span>
              <span className="panel-subtitle">notable open signals</span>
            </>
          ) : (
            <>
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                Signal stream
                <PanelHelpButton panel="signal-stream" />
              </span>
              <span className="panel-subtitle">notable open signals</span>
            </>
          )
          if (isTheme) panelTitle = <>
            <button className="drill-back-btn" onClick={themeBackStack.length > 0 ? handleThemeBack : handleStreamBack} style={{ fontSize: 13, marginRight: 6 }}>
              {themeBackStack.length > 0 ? `← ${themeBackStack[0].theme.replace(/_/g, ' ').slice(0, 20)}` : '← STREAM'}
            </button>
            <span className="ph-ctx">{resolveThreadLabel(selectedTheme!.theme, selectedTheme!.thread?.label ?? selectedTheme!.labelHint).slice(0, 32)}</span>
          </>
          if (isStory) panelTitle = <>
            <button className="drill-back-btn" onClick={() => setStoryQuery(null)} style={{ fontSize: 13, marginRight: 6 }}>← STREAM</button>
            <span className="ph-ctx ph-ctx--story">STORY · {storyQuery!.slice(0, 30)}</span>
          </>
          if (isThread) panelTitle = <>
            <button className="drill-back-btn" onClick={handleStreamBack} style={{ fontSize: 13, marginRight: 6 }}>← STREAM</button>
            <span className="ph-ctx ph-ctx--live">{selectedThread!.label.slice(0, 32)}</span>
          </>
          if (isCountry) panelTitle = <>
            <button className="drill-back-btn" onClick={handleStreamBack} style={{ fontSize: 13, marginRight: 6 }}>{backLabel}</button>
            <span className="ph-ctx">{selectedCountryName}</span>
          </>
          if (isPerson) panelTitle = <>
            <button className="drill-back-btn" onClick={handleStreamBack} style={{ fontSize: 13, marginRight: 6 }}>← STREAM</button>
            <span className="ph-ctx ph-ctx--person">{focus.value}</span>
          </>
          if (isPublicAttention) panelTitle = <>
            <button className="drill-back-btn" onClick={closeAll} style={{ fontSize: 13, marginRight: 6 }}>← STREAM</button>
            <span className="ph-ctx ph-ctx--live">{selectedPublicAttention!.title.slice(0, 28)}</span>
          </>
          if (isChokepoint) panelTitle = <>
            <button className="drill-back-btn" onClick={() => setSelectedChokepoint(null)} style={{ fontSize: 13, marginRight: 6 }}>← STREAM</button>
            <span className="ph-ctx ph-ctx--live">{selectedChokepoint!.name}</span>
          </>
          // A3 scope strip: the blank SignalStream silently re-scopes to an
          // active country/person focus — name it and make it reversible.
          const streamScopeName = isBlankState
            ? (filter.country ? resolveCountryName(filter.country) : (filter.person || null))
            : null
          return (
            <div className="terminal-panel stream" data-tour="stream">
              <div className="panel-header">
                <div className="panel-header-title-wrap">{panelTitle}</div>
              </div>
              {streamScopeName && (
                <div className="stream-scope-strip" data-tip="The stream is scoped to your active focus">
                  <span>Scoped to <strong>{streamScopeName}</strong></span>
                  <button type="button" className="stream-scope-clear" onClick={clearAll} data-tip="Clear scope" aria-label="Clear scope">✕</button>
                </div>
              )}
              <div className="panel-content">
                {isStory ? (
                  <ResearchPlanPanel
                    query={storyQuery!}
                    hours={RESEARCH_WINDOW_HOURS} /* research plans read the week (former 168h floor) */
                    countryCode={filter.country}
                    onOpenThread={(id, label) => { setStoryQuery(null); handleResearchOpenThread(id, label) }}
                    onOpenCountry={(cc) => { setStoryQuery(null); handleResearchOpenCountry(cc) }}
                    onBranchQuery={(q) => setStoryQuery(q)}
                  />
                ) : isPerson ? (
                  <EntityPanel inline focusType="person" focusValue={focus.value!}
                    onClose={closeAll}
                    onThemeSelect={(theme) => handleThemeSelect(theme)}
                    onCountrySelect={(code) => { clearFocus(); handleCountryClick(code); setMapFlyCountry(code) }}
                    onSourceClick={(source) => setSelectedSourceProfile(source)}
                    onCompareClick={(other) => setComparePerson({ a: focus.value!, b: other })}
                    onPersonSelect={(name) => { setFocus('person', name, name); setMapFlyCountry(null) }}
                  />
                ) : isPublicAttention ? (
                  <PublicAttentionPanel
                    item={selectedPublicAttention!}
                    onClose={closeAll}
                    onThemeSelect={(theme, attentionContext) => handleThemeSelect(theme, undefined, undefined, attentionContext)}
                    onCountrySelect={(code) => { handleCountryClick(code); setMapFlyCountry(code) }}
                  />
                ) : isThread ? (
                  <ThreadFocusPanel
                    thread={selectedThread!}
                    hours={DAY_WINDOW_HOURS} /* investigative default = the day */
                    onClose={closeAll}
                    onCountrySelect={(code) => { handleCountryClick(code); setMapFlyCountry(code) }}
                    onSourceClick={(source) => setSelectedSourceProfile(source)}
                  />
                ) : isCountry ? (
                  <CountryBrief inline
                    countryCode={selectedCountryCode!}
                    countryName={selectedCountryName}
                    timeWindow={DAY_WINDOW_HOURS} /* country brief = the day; deeper history lives in deep-history/scrubber */
                    onClose={handleStreamBack}
                    onThemeSelect={(theme) => { handleThemeSelect(theme, selectedCountryCode!, selectedCountryName); setMapFlyCountry(selectedCountryCode!) }}
                    onSourceClick={(domain) => {
                      setPrevStreamCtx({ type: 'country', code: selectedCountryCode!, name: selectedCountryName })
                      setSelectedSourceProfile(domain)
                    }}
                    onAttentionItemClick={(q) => setExternalSearchQuery({ q, id: Date.now() })}
                  />
                ) : isTheme ? (
                  <ThemeDetail
                    theme={selectedTheme!.theme}
                    originCountry={selectedTheme!.originCountry}
                    originCountryName={selectedTheme!.originCountryName}
                    originAttention={selectedTheme!.originAttention}
                    threadContext={selectedTheme!.thread}
                    initialDrillCountry={selectedTheme!.originCountry}
                    hours={DAY_WINDOW_HOURS} /* investigative default = the day */
                    onClose={closeAll}
                    onThemeSelect={(theme, attentionContext) => handleThemeSelect(theme, undefined, undefined, attentionContext ?? selectedTheme!.originAttention)}
                    onCountryCardClick={(code, name) => { setMapFlyCountry(code); setRightPanelThemeCountry({ code, name }) }}
                    onPersonClick={(name) => {
                      setFocus('person', name, name)
                      setMapFlyCountry(null)
                    }}
                    onSourceClick={(source) => setSelectedSourceProfile(source)}
                    onCompareClick={(other) => setCompareTheme({ a: selectedTheme!.theme, b: other })}
                    onConflictChipClick={(code) => { handleCountryClick(code); setMapFlyCountry(code) }}
                    onLabelResolved={(themeId, label) => {
                      // Deep-link cold open: hand the resolved label to the
                      // surfaces that only had the opaque id (focus chip,
                      // stream header, universe orbit). Guarded no-ops keep
                      // the re-fired effect from churning state.
                      setSelectedTheme(prev => prev && prev.theme === themeId && prev.labelHint !== label
                        ? { ...prev, labelHint: label } : prev)
                      if (filter.theme === themeId && filter.themeLabel !== label) {
                        setTheme(themeId, filter.lockedBy, label)
                      }
                    }}
                  />
                ) : isChokepoint ? (
                  <ChokepointPanel
                    chokepoint={selectedChokepoint!}
                    vesselCount={chokepointCounts[selectedChokepoint!.id] || 0}
                    hours={DAY_WINDOW_HOURS} /* investigative default = the day */
                    onCountryClick={(code) => {
                      setPrevStreamCtx({ type: 'chokepoint', cp: selectedChokepoint! })
                      handleCountryClick(code); setMapFlyCountry(code)
                    }}
                  />
                ) : (
                  <SignalStream paused={readPaneHidden} />
                )}
              </div>
            </div>
          )
        })()

        {/* Panel 3: NARRATIVE THREADS — always visible, reactive to focus context */}
        const threadsPanel = (
        <div className="terminal-panel threads" data-tour="threads">
          <div className="panel-header">
            <div className="panel-header-title-wrap">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                Narrative threads
                <PanelHelpButton panel="narrative-threads" />
              </span>
              <span className="panel-subtitle">how topics spread over time</span>
            </div>
            <span className="honesty-chip" data-tip="Rank = composite of volume (log-damped) + movement + coherence — measured, never a raw count or source bias. Left border color = category family.">MEASURED · COMPOSITE RANK</span>
          </div>
          <div className="panel-content">
            <PanelErrorBoundary panelName="NARRATIVE THREADS">
              <NarrativeThreads
                paused={fieldHidden}
                activeThreadId={selectedTheme?.thread?.thread_id ?? selectedThread?.thread_id}
                onThreadSelect={(thread) => {
                  const target = resolveThreadThemeTarget(thread)
                  setSelectedTheme(target ? {
                    theme: target.theme,
                    originCountry: target.originCountry,
                    originCountryName: target.originCountryName,
                    thread: target.thread,
                  } : null)
                  // Flywheel compound focus: thread-open COMPOSES with the active
                  // focus instead of wiping it. No clearFocus() — an active
                  // filter.country/filter.person survives (the setters are
                  // compound, Tasks 1.1/1.2). setTheme() now SETS filter.theme to
                  // the opened thread's theme so it joins the compound frame as a
                  // chip; the country/person are preserved. The :930 guard
                  // (theme-id-only) and :921 guard (skip when a theme/thread is
                  // open) keep this from clobbering the origin country or snapping
                  // the thread closed. selectedCountryCode is left warm — the
                  // country panel reappears on Back; isThread/isTheme outrank it.
                  setTheme(target ? target.theme : null, undefined, target?.thread?.label ?? undefined)
                  setSelectedPublicAttention(null)
                  setSelectedChokepoint(null)
                  setRightPanelThemeCountry(null)
                  setThemeBackStack([])
                  setSelectedThread(target ? null : thread)
                  if (thread.top_countries[0]) setMapFlyCountry(thread.top_countries[0])
                  // Story Lens (Task 10, spec-review fix): THE lens's own
                  // panel — this is what wires the sibling walk (clicking a
                  // row under ◈ Measured neighborhood re-anchors here).
                  // labelHint = the clicked row's own label (T11 gate L4) —
                  // covers both an ordinary pool row AND a synthesized
                  // sibling row (L1), so re-anchoring to a primo/hermano
                  // never drops to the generic title while its own siblings
                  // fetch is in flight or degrades.
                  syncLensToThreadOpen(target ? target.theme : null, target?.thread?.label ?? thread.label)
                }}
                onCountrySelect={(code) => {
                if (selectedTheme) {
                  setPrevStreamCtx({
                    type: 'theme',
                    theme: selectedTheme.theme,
                    originCountry: selectedTheme.originCountry,
                    originCountryName: selectedTheme.originCountryName,
                  })
                  setSelectedTheme(null)
                  setTheme(null)
                }
                handleCountryClick(code)
                setMapFlyCountry(code)
              }} />
            </PanelErrorBoundary>
          </div>
        </div>

        )

        {/* Panel 4: CORRELATION MATRIX (retired — display:none at every
            breakpoint; stays mounted for behavioral parity, never in the grid) */}
        const matrixPanel = (
        <div className="terminal-panel matrix">
          <div className="panel-header">
            <div className="panel-header-title-wrap">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                Correlation matrix
                <PanelHelpButton panel="correlation-matrix" />
              </span>
              <span className="panel-subtitle">which countries share narratives</span>
            </div>
          </div>
          <div className="panel-content">
            <PanelErrorBoundary panelName="CORRELATION MATRIX">
              <CorrelationMatrix />
            </PanelErrorBoundary>
          </div>
        </div>

        )

        {/* Panel 5+6: BOTTOM DOCK — tabbed (#228 §3). On 16:9 laptops the old
            two-panel bottom row gave three interactive sections ~132px each;
            tabs give the active section the full row. */}
        const dockPanel = (
        <div className="terminal-panel dock" data-tour="anomaly-attention">
          <div className="panel-header dock-header">
            <div className="dock-tabs">
              <button
                className={`dock-tab ${dockTab === 'anomaly' ? 'active' : ''}`}
                onClick={() => { track('dock_tab', { tab: 'anomaly' }); setDockTab('anomaly') }}
                data-tip="Geo alerts and public attention vs 7-day baseline"
              >
                ANOMALY ALERT
              </button>
              <button
                className={`dock-tab ${dockTab === 'sources' ? 'active' : ''}`}
                onClick={() => { track('dock_tab', { tab: 'sources' }); setDockTab('sources') }}
                data-tip="Diversity of information sources"
              >
                SOURCE INTEGRITY
              </button>
              <button
                className={`dock-tab ${dockTab === 'radar' ? 'active' : ''}`}
                onClick={() => { track('dock_tab', { tab: 'radar' }); setDockTab('radar') }}
                data-tip="Under the radar: categories getting real signal that nothing has verified yet — re-scopes to your active focus"
              >
                UNDER THE RADAR
              </button>
              <button
                className={`dock-tab ${dockTab === 'markets' ? 'active' : ''}`}
                onClick={() => { track('dock_tab', { tab: 'markets' }); setDockTab('markets') }}
                data-tip="Descriptive market data — world basket + a focused country's own instruments. Level and trend only; not a claim news moved these, and never a trade signal."
              >
                MARKETS
              </button>
            </div>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {dockTab === 'anomaly' && <span className="honesty-chip" data-tip="Alerts are deviations vs each country's own 7-day baseline — never a raw volume ranking.">MEASURED · VS 7-DAY BASELINE</span>}
              {dockTab === 'anomaly' && <PanelHelpButton panel="anomaly-attention" />}
              {dockTab === 'sources' && <PanelHelpButton panel="source-integrity" />}
            </span>
          </div>
          <div className="panel-content">
            {dockTab === 'anomaly' && (
              <PanelErrorBoundary panelName="ANOMALY ALERT">
                <AnomalyPanel
                  onWikiClick={(q) => setExternalSearchQuery({ q, id: Date.now() })}
                  onPublicAttentionSelect={handlePublicAttentionSelect}
                  activeThemeLabel={selectedTheme?.thread?.label ?? selectedTheme?.labelHint ?? filter.themeLabel ?? selectedThread?.label ?? null}
                />
              </PanelErrorBoundary>
            )}
            {dockTab === 'sources' && (
              <PanelErrorBoundary
                key={`integrity-${filter.country ?? ''}-${filter.theme ?? ''}-${filter.person ?? ''}-${filter.entity ?? ''}`}
                panelName="SOURCE INTEGRITY"
              >
                <SourceIntegrityPanel
                  viewingLabel={
                    (selectedTheme
                      ? resolveThreadLabel(selectedTheme.theme, selectedTheme.thread?.label)
                      : null)
                    ?? selectedThread?.label
                    ?? selectedPublicAttention?.title
                    ?? selectedChokepoint?.name
                    ?? null
                  }
                />
              </PanelErrorBoundary>
            )}
            {dockTab === 'radar' && (
              <PanelErrorBoundary
                key={`radar-${filter.country ?? ''}-${filter.person ?? ''}-${filter.theme ?? ''}`}
                panelName="UNDER THE RADAR"
              >
                <UnderRadarLens
                  onOpenTopic={(slug) => handleThemeSelect(slug)}
                />
              </PanelErrorBoundary>
            )}
            {dockTab === 'markets' && (
              <PanelErrorBoundary panelName="MARKETS">
                <MarketsPanel />
              </PanelErrorBoundary>
            )}
          </div>
        </div>
        )

        if (isMobile) {
          // #236: the phone has two console surfaces and three states, named
          // by `mobileSurface` above. 'live' = the firehose; 'lens-focused' =
          // the thing you opened; 'lens-field' = the field you open things
          // from. The map is no longer a tab — it is a section INSIDE the Lens
          // (Task 8) — so the radar panel is not mounted here at all and its
          // rAF loop never runs on a phone. The correlation matrix was only
          // ever mounted-and-CSS-hidden here, so it is gone too.
          //
          // The DOCK is absorbed the same way, but "absorbed" has to mean the
          // sections exist: this comment used to say the dock was absorbed
          // while nothing rendered its panels, which is council R4 N29 — the
          // phone shipped with no Public Attention, no anomaly alerts, no
          // eclipse row and no source health at any tab. The dock PANEL
          // (`dockPanel`, with its four tabs and the radar/markets lanes it
          // also carries) is still not mounted on a phone; its two intel
          // panels are, as `attention` and `sources` sections of the Lens
          // sheet below.
          //
          // The two that ARE here KEEP ALIVE across tab taps — mounted once,
          // visibility toggled — as main.tsx's AppBriefKeepAlive does for the
          // routes (#239 slice 2). NOT because they are free while hidden:
          // SignalStream polls every 15s, drips every 3s and re-renders every
          // second, and NarrativeThreads polls every 5 min. They are kept
          // alive DESPITE that, because remounting measured worse — 0.7-1.5s
          // of blank panel and 2-4 re-fired requests on every tap. The
          // `paused` prop buys the hidden cost back on both: whichever pane is
          // hidden idles its timers and keeps its rows, so a tap costs neither
          // a refetch nor a blank panel.
          //
          // #236 Task 7: <LensPanel/> now owns which slot is showing and wears
          // the scope chrome. The two panels stay exactly where they were —
          // the Lens wraps them in `display: contents`, which generates no
          // box, so each still lays out as a direct child of this layout and
          // neither remounts when the scope changes. The read pane is passed
          // to the Lens but is ALSO the Live surface; that is why the Lens
          // takes `surface` rather than deciding from focus alone.
          //
          // mobileSurface is non-null here by construction — same `isMobile`.

          // The name of whatever thread is open, resolved once for BOTH intel
          // sections below. `thread.label` is only filled after the read lands;
          // `labelHint` is what a row/search/deep-link opener passes ahead of
          // it; `filter.themeLabel` covers a focus set from another surface.
          // Taking them in that order is what stops a section from printing a
          // raw `dynamic-topic-N` while the read is still in flight.
          const openThreadLabel =
            selectedTheme?.thread?.label ?? selectedTheme?.labelHint
            ?? filter.themeLabel ?? selectedThread?.label ?? null

          return (
            <div className={`terminal-layout mobile-tab-${consoleTab} lens-shell`}>
              <LensPanel
                surface={mobileSurface!}
                trail={lensTrail}
                /* Shorten the trail and peel the console in the same handler.
                   popPanel alone can reveal a scope the trail never visited
                   (peel a thread, find a country focus set under it) — appended
                   on top of the thread just closed, the breadcrumb would then
                   point back at it. Rewinding first lands the revealed scope at
                   the same depth. popPanel is the same function Escape and the
                   edge-swipe call, so all three agree. */
                onBack={() => { rewindLens(); popPanel() }}
                /* #236 Task 8: a country row in `where it lives` re-scopes the
                   Lens. The console's own opener, not FocusContext.setCountry
                   — the Lens scope is derived from this component's focus
                   state (consoleFocus.countryCode), so setting only the shared
                   filter would move the map while the breadcrumb and the read
                   kept naming the old scope. It resolves the display name
                   itself, which is why the section passes just the code.

                   setPerson(null) and setTheme(null) FIRST, or the tap does
                   nothing. Both clear a SHARED FOCUS dimension that
                   handleCountryClick leaves standing — nextFocusDims' `country`
                   case keeps person AND theme (focusReducer.ts:39, it nulls
                   only `thread`) — and each survivor outranks the country that
                   was just opened, so the panel, the heading and the breadcrumb
                   would all stay put while a country chip appeared. That is the
                   class popPanel's own comment above already documents ("the
                   slot showed the person while Back cleared the attention
                   underneath it: the screen did not change and the tap did
                   nothing").

                   The THEME half is subtler than the person half and was the
                   gate's measured failure. handleCountryClick DOES clear the
                   theme — but only `selectedTheme`, the panel, not
                   `filter.theme`, the focus. The effect above ("Open
                   ThemeDetail when theme is focused via FocusContext") then
                   sees filter.theme set and selectedTheme null and re-opens the
                   panel on the very next commit. A MutationObserver caught all
                   three frames: CountryBrief mounted, then 140ms later
                   ThemeDetail was back and the heading had reverted from
                   "Spain" to "Ceuta Migrant Crisis" while the URL kept
                   `&country=ES`. So the pivot was not losing a precedence
                   contest in consoleSlot — consoleSlot named ThemeDetail
                   because ThemeDetail was genuinely on screen. Clearing the
                   focus dimension is what stops it coming back.

                   resetLens() because this is a LATERAL PIVOT: it CLOSES the
                   thread it was measured from rather than opening on top of it,
                   so a plain append would leave a breadcrumb naming a scope
                   Back cannot reach. Measured: without it the crumb read
                   "← Ceuta Migrant Crisis" and the tap landed on The world.
                   See resetScope in lib/lensScope.ts.

                   Cleared HERE rather than inside handleCountryClick, which
                   ~24 call sites share: compound person+country is deliberate
                   (focusReducer keeps it on purpose) and is what the desktop
                   map is for — "Trump, in Israel" — and compound theme+country
                   is deliberate in the same way: it renders the country-scoped
                   ThemeDetail ("← Global · Spain · 5,618 signals", observed
                   live), and the effect above re-scopes it on purpose when the
                   country chip changes under it. Clearing either globally would
                   change every one of those doors to fix one. This file already
                   composes that way — the map's onCountrySelect calls
                   clearFocus() first, the compare panel calls
                   setComparePerson(null), the source and conflict panels close
                   their own panel — each before calling. The phone Lens has no
                   map for a standing chip to act on, and its whole contract is
                   that the surface re-scopes to what you tapped. */
                onOpenCountry={(cc) => { resetLens(); setPerson(null); setTheme(null); handleCountryClick(cc) }}
                /* A `connected` row re-scopes to that thread, through the same
                   opener every other thread door uses — so the trail, the read
                   and the story lens all move together. The label rides along
                   (handleThemeSelect's own `labelHint`) so the breadcrumb never
                   shows a raw dynamic-topic id while the read loads.

                   resetLens() for the SAME reason the country pivot above needs
                   it, and it is worth stating because "thread → thread" looks
                   like a push rather than a pivot: handleThemeSelect REPLACES
                   the open thread, and popPanel's thread/theme case nulls
                   selectedTheme outright — it never consumes themeBackStack,
                   which only the desktop drill-back button reads. So a plain
                   append would leave [field, thread A, thread B], a breadcrumb
                   reading "← thread A", and a Back that clears thread B and
                   lands on The world. Resetting first leaves [field, thread B]:
                   one honestly reachable step, which is what Back does. */
                onOpenThread={(id, label) => {
                  resetLens()
                  handleThemeSelect(id, undefined, undefined, undefined, label)
                }}
                /* The sections measure neighbours over the SAME thread pool the
                   field panel below them ranks — including its country scoping,
                   which changes which actors count as rare. */
                countryScope={filter.country}
                field={threadsPanel}
                read={streamPanel}
                /* Council R4 N29: the intel organ, back on the phone. The dock
                   panel above is NOT mounted here (see the note at the top of
                   this branch), so these two were unreachable at every tab —
                   a DOM scan returned zero `.anomaly-panel-container` and zero
                   `.source-panel-container` across Brief, Lens and Live. They
                   ride in as sections of the Lens's own sheet rather than as a
                   restored fourth tab, because that is what the arc's design
                   already says they are (mobile-native-ia-design.md §3: "Pulse
                   tab → §5 attention, always scoped"), and because both
                   panels already carry the phone stylesheet that surface was
                   going to use.

                   Passed as NODES, like `field` and `read`, so their doors keep
                   pointing at this component's openers instead of being
                   re-declared inside the Lens. Elements, not mounts: the sheet
                   renders them only while it is open.

                   Boundaried individually, exactly as the dock does — one lane
                   failing must cost its own section, never the sheet that is
                   now the only way to any of them.

                   Both read the SAME `openThreadLabel` chain (declared just
                   above this branch) rather than the dock's two different
                   expressions for the same fact — a thread opened from a phone
                   row has not resolved `thread.label` yet, and only the longer
                   chain finds its name meanwhile.

                   HONEST RESIDUAL, unchanged here on purpose: while a theme
                   filter is set, SourceIntegrityPanel does not consult
                   `viewingLabel` at all — buildSourceIntegrityScopeLabel takes
                   the `theme` branch and prints `getThemeLabel(id)`, which for
                   a dynamic topic is the prettified raw id ("Dynamic Topic
                   11877"). That is a leak in the shared scope-label lib, it
                   renders identically on the desktop dock today, and fixing it
                   there would change the desktop — out of scope for a mobile
                   reachability pass. Filed, not smuggled. */
                attention={
                  <PanelErrorBoundary panelName="ANOMALY ALERT">
                    <AnomalyPanel
                      onWikiClick={(q) => setExternalSearchQuery({ q, id: Date.now() })}
                      onPublicAttentionSelect={handlePublicAttentionSelect}
                      activeThemeLabel={openThreadLabel}
                    />
                  </PanelErrorBoundary>
                }
                sources={
                  <PanelErrorBoundary
                    key={`integrity-${filter.country ?? ''}-${filter.theme ?? ''}-${filter.person ?? ''}-${filter.entity ?? ''}`}
                    panelName="SOURCE INTEGRITY"
                  >
                    <SourceIntegrityPanel
                      viewingLabel={
                        (selectedTheme ? resolveThreadLabel(selectedTheme.theme, openThreadLabel ?? undefined) : null)
                        ?? selectedThread?.label
                        ?? selectedPublicAttention?.title
                        ?? selectedChokepoint?.name
                        ?? null
                      }
                    />
                  </PanelErrorBoundary>
                }
              />
            </div>
          )
        }

        return (
          <div ref={gridShellRef} className="terminal-layout-grid" style={{ height: gridShellH }}>
            <ReactGridLayout
              width={gridWidth}
              layout={gridLayout}
              gridConfig={{ cols: GRID_COLS, rowHeight: gridRowHeight, margin: [GRID_GAP, GRID_GAP], containerPadding: [GRID_GAP, GRID_GAP] }}
              dragConfig={{ handle: '.panel-header', cancel: 'button, input, a, select, textarea' }}
              resizeConfig={{ handles: ['n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw'] }}
              onLayoutChange={handleGridLayoutChange}
              onResizeStop={handleGridResizeStop}
            >
              <div key="radar" className="grid-slot">{radarPanel}</div>
              <div key="stream" className="grid-slot">{streamPanel}</div>
              <div key="threads" className="grid-slot">{threadsPanel}</div>
              <div key="dock" className="grid-slot">{dockPanel}</div>
            </ReactGridLayout>
            <div style={{ display: 'none' }}>{matrixPanel}</div>
          </div>
        )
      })()}

      {/* Flywheel Task 6.3c: the mobile Frame — a quiet pull-up sheet above the
          tab bar (the desktop strip is !isMobile). The ◎ detected relation
          renders ONLY inside it, never as a mid-read banner. */}
      {isMobile && (
        <FrameSheet
          raised={!!(filter.country || filter.theme || filter.person)}
          onOpenPin={(item) => {
            const p = new URLSearchParams(item.urlParams)
            if (item.type === 'theme' && p.get('theme')) handleThemeSelect(p.get('theme')!)
            else if (item.type === 'person') setFocus('person', decodeURIComponent(p.get('person') || item.title), item.title)
            else if (item.type === 'country' && p.get('country')) handleCountryClick(p.get('country')!)
          }}
          onScopeThread={(threadId, label) => handleThemeSelect(threadId, undefined, undefined, undefined, label)}
          onOpenReport={() => setWorkbenchOpen(true)}
        />
      )}

      {/* The mobile tab bar used to live here. It now renders once at the root
          (main.tsx → MobileTabBar) so /app and /brief share one bar — see
          #236 Task 6. */}

      {/* #236 Task 9: the mobile search sheet. Reachable from anywhere in the
          console — including over a full-screen read, which is the gap this
          closes (Task 7 measured elementFromPoint over the desktop command
          bar's search input returning ThemeDetail's z-9000 overlay at this
          width; the command bar itself is unreachable under a read on the
          phone). Rendered from App rather than main.tsx (unlike MobileTabBar)
          because its doors — handleThemeSelect, handleCountryClick, setFocus
          — all live here; mounting it at the root would mean prop-drilling
          them out through a second context for no reader-visible benefit,
          and search has never been a Brief-page affordance on desktop either
          (BriefNewspaper carries no SearchBar).
          Doors are wired IDENTICALLY to the desktop SearchBar's own props one
          screen up (~line 1697): a tapped thread/country/person result calls
          the exact same openers, which is what makes the Lens pivot "just
          happen" — the effects at :1245 (consoleTab -> 'lens') and :1259
          (focusLens(lensScope)) already run off this state, so nothing here
          calls either directly (MobileNavContext.tsx's own doc comment: only
          the console's derivation effect may call focusLens). */}
      {isMobile && (
        <SearchSheet
          onThemeSelect={handleThemeSelect}
          onCountrySelect={(code) => { handleCountryClick(code); setMapFlyCountry(code) }}
          onPersonSelect={(name) => { setFocus('person', name, name); setMapFlyCountry(null) }}
        />
      )}

      {/* Hover Tooltip */}
      <MapTooltip tooltip={tooltip} />

      {/* T3.3 conflict-event focus — the event is the subject, country is context */}
      {selectedConflictEvent && (
        <ConflictEventPanel
          event={selectedConflictEvent}
          timeRangeHours={DAY_WINDOW_HOURS} /* event context threads = the day */
          onClose={() => setSelectedConflictEvent(null)}
          onThemeSelect={(threadId) => { setSelectedConflictEvent(null); handleThemeSelect(threadId) }}
          onCountrySelect={(code) => { setSelectedConflictEvent(null); handleCountryClick(code); setMapFlyCountry(code) }}
        />
      )}

      {/* Briefing Modal */}
      {showBriefing && (
        <Briefing
          hours={DAY_WINDOW_HOURS} /* investigative default = the day */
          prefetchedData={prefetchedHours === DAY_WINDOW_HOURS ? prefetchedBriefing : null}
          prefetchedInsight={prefetchedHours === DAY_WINDOW_HOURS ? prefetchedInsight : null}
          onClose={() => setShowBriefing(false)}
          onCountrySelect={(code) => {
            setSelectedTheme(null)
            setRightPanelThemeCountry(null)
            setSelectedChokepoint(null)
            setPrevStreamCtx(null)
            clearFocus()
            handleCountryClick(code)
            setMapFlyCountry(code)
            setShowBriefing(false)
          }}
          onThemeSelect={(theme) => {
            setSelectedCountry(null)
            setSelectedCountryCode(null)
            setShowFlows(false)
            setSelectedChokepoint(null)
            setPrevStreamCtx(null)
            clearFocus()
            handleThemeSelect(theme)
            setShowBriefing(false)
          }}
        />
      )}

      {workbenchOpen && (
        <div className="workbench-overlay">
          <div className="workbench-overlay-header">
            <span className="workbench-overlay-title">INVESTIGATION WORKBENCH</span>
            <span className="workbench-overlay-model" data-tip="Pins freeze what you saw (route). Suggestions are live and re-ranked — pin one to capture it into the route.">
              LEFT your investigations · MIDDLE what you pinned (the frozen route) · RIGHT what Atlas suggests exploring — pin to capture
            </span>
            <button className="workbench-overlay-close" onClick={() => setWorkbenchOpen(false)}>×</button>
          </div>
          <div className="workbench-overlay-body">
            <div className="workbench-overlay-left">
              {/* Three-layer error architecture: a workbench throw (e.g. a
                  malformed record or response field under a 429 storm) must
                  degrade THIS panel, never reach RootErrorBoundary and blank
                  the whole app. */}
              <PanelErrorBoundary panelName="INVESTIGATION WORKBENCH">
                <WorkbenchPanel
                  refreshToken={wbRefresh + wbVersion}
                  onOpenThread={handleResearchOpenThread}
                  onOpenCountry={handleResearchOpenCountry}
                  onOpenParams={handleOpenParams}
                  onStartInvestigation={(q) => setResearchQuery(q)}
                  onClose={() => setWorkbenchOpen(false)}
                />
              </PanelErrorBoundary>
            </div>
            {/* Task 10 (#236): the research plan ("Atlas suggests") is a
                second, search-driven column — genuinely a desktop working
                surface, not a capture list. WorkbenchPanel tells a mobile
                analyst it lives on the computer; that claim would be false
                the moment this column rendered beside it on the same phone
                screen, so it does not mount at all below 768. Nothing moves
                to an overflow menu — it is simply absent, matching the
                honest line. */}
            {!isMobile && (
              <div className="workbench-overlay-right">
                {researchQuery ? (
                  <>
                    <div className="workbench-suggest-head" data-tip="Live anchors from the research plan for this investigation's query — re-ranked on every open, never frozen. Pin one to capture it into the route.">
                      <span className="workbench-suggest-label">ATLAS SUGGESTS</span>
                      <span className="workbench-suggest-query">{researchQuery}</span>
                    </div>
                    <PanelErrorBoundary panelName="ATLAS SUGGESTS">
                      <ResearchPlanPanel
                        query={researchQuery}
                        hours={RESEARCH_WINDOW_HOURS} /* research plans read the week (former 168h floor) */
                        onOpenThread={handleResearchOpenThread}
                        onOpenCountry={handleResearchOpenCountry}
                        onBranchQuery={(q) => setResearchQuery(q)}
                        onPinsChanged={() => setWbRefresh(t => t + 1)}
                      />
                    </PanelErrorBoundary>
                  </>
                ) : (
                  <div className="workbench-overlay-hint">
                    Create or select an investigation, then its research plan appears here.
                    Anchors open real Atlas surfaces; pin the useful ones.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ThemeDetail renders inside the stream panel — see stream panel below */}

      {/* CountryThemePanel: drill-in from ThemeDetail into a specific country — still a right-panel for now */}
      {selectedTheme && rightPanelThemeCountry && (
        <CountryThemePanel
          theme={selectedTheme.theme}
          countryCode={rightPanelThemeCountry.code}
          countryName={rightPanelThemeCountry.name}
          hours={DAY_WINDOW_HOURS} /* investigative default = the day */
          onClose={() => setRightPanelThemeCountry(null)}
          onBackToCountry={() => {
            if (rightPanelThemeCountry && selectedTheme) {
              setPrevStreamCtx({ type: 'theme', theme: selectedTheme.theme, originCountry: selectedTheme.originCountry, originCountryName: selectedTheme.originCountryName })
              handleCountryClick(rightPanelThemeCountry.code)
              setMapFlyCountry(rightPanelThemeCountry.code)
              setRightPanelThemeCountry(null)
            }
          }}
          onThemeSelect={(theme) => { handleThemeSelect(theme, rightPanelThemeCountry.code, rightPanelThemeCountry.name) }}
        />
      )}

      {selectedSourceProfile && (
        <SourceProfile 
          domain={selectedSourceProfile}
          hours={DAY_WINDOW_HOURS} /* investigative default = the day */
          onClose={() => setSelectedSourceProfile(null)}
          onThemeSelect={(theme) => { setSelectedSourceProfile(null); handleThemeSelect(theme); }}
          onCountrySelect={(code) => { setSelectedSourceProfile(null); handleCountryClick(code); setMapFlyCountry(code); }}
        />
      )}

      {/* W1 (2026-07-05): the force-graph workspace was RETIRED (D1 — the
          universe view is the spatial surface); pins live in the WORKBENCH. */}

      {comparePerson && (
        <PersonCompare
          personA={comparePerson.a}
          personB={comparePerson.b}
          onClose={() => setComparePerson(null)}
          onThemeSelect={(theme) => { setComparePerson(null); handleThemeSelect(theme); }}
          onCountrySelect={(code) => { setComparePerson(null); handleCountryClick(code); setMapFlyCountry(code); }}
          onSourceClick={(source) => setSelectedSourceProfile(source)}
        />
      )}

      {compareTheme && (
        <ThemeCompare
          themeA={compareTheme.a}
          themeB={compareTheme.b}
          hours={DAY_WINDOW_HOURS} /* investigative default = the day */
          onClose={() => setCompareTheme(null)}
          onThemeSelect={(theme) => { setCompareTheme(null); handleThemeSelect(theme); }}
          onCountryCardClick={(code) => { setCompareTheme(null); handleCountryClick(code); setMapFlyCountry(code); }}
          onPersonClick={(name) => { setCompareTheme(null); setFocus('person', name, name); setMapFlyCountry(null); }}
          onSourceClick={(source) => setSelectedSourceProfile(source)}
        />
      )}
      <OnboardingCoachmark
        runId={tourRunId}
        onOpenBrief={openBrief}
        onOpenWorkspace={() => setWorkbenchOpen(true)}
        entryContext={tourEntryContext}
      />
      {countryWalkthrough && (
        <CountryFocusWalkthrough
          countryName={countryWalkthrough}
          onDismiss={() => setCountryWalkthrough(null)}
        />
      )}

      {watchNamePrompt !== null && (
        <div className="watch-save-overlay" onClick={e => e.target === e.currentTarget && setWatchNamePrompt(null)}>
          <div className="watch-save-dialog">
            <div className="watch-save-title">Save as Watch</div>
            <input
              className="watch-save-input"
              value={watchNamePrompt}
              onChange={e => setWatchNamePrompt(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && watchNamePrompt.trim()) { addWatch(watchNamePrompt, filter); setWatchNamePrompt(null) }
                if (e.key === 'Escape') setWatchNamePrompt(null)
              }}
              placeholder="Watch name…"
              autoFocus
              maxLength={60}
            />
            <div className="watch-save-actions">
              <button className="watch-save-cancel" onClick={() => setWatchNamePrompt(null)}>Cancel</button>
              <button
                className="watch-save-confirm"
                disabled={!watchNamePrompt.trim()}
                onClick={() => { addWatch(watchNamePrompt, filter); setWatchNamePrompt(null) }}
              >Save Watch</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Main App with providers
function App() {
  return (
    <FocusProvider>
      <FocusDataProvider>
        <CrisisProvider>
          <WorkspaceProvider>
            <StoryLensBanner />
            <AppContent />
          </WorkspaceProvider>
        </CrisisProvider>
      </FocusDataProvider>
    </FocusProvider>
  )
}

export default App
