import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import MapGL from 'react-map-gl/maplibre'
import type { MapRef } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import './App.css'
import { useCrisis } from './contexts/CrisisContext'
import { useTheme } from './contexts/ThemeContext'
import { SearchBar } from './components/SearchBar'
import { Briefing } from './components/Briefing'
import { ThemeDetail } from './components/ThemeDetail'
import { CountryBrief } from './components/CountryBrief'
import { EqualEarthMap } from './components/EqualEarthMap'
import { computeCountryHeatStates } from './lib/countryHeatStates'
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
import { InvestigationWorkspace } from './components/InvestigationWorkspace'
import { FocusIndicator } from './components/FocusIndicator'
import { TIME_RANGE_OPTIONS, TIME_RANGE_LABELS, timeRangeToHours } from './lib/timeRanges'
import { Globe, ClipboardList, FolderOpen, HelpCircle, BookmarkPlus, MoreHorizontal, Settings, ChevronDown } from './lib/icons'
import { CHOKEPOINTS, haversineKm, getChokepointVesselCounts, getCountryChokepoints, type Chokepoint } from './lib/chokepoints'
import { resolveCountryName } from './lib/countryNames'
import type { PublicAttentionOrigin } from './lib/publicAttention'
import { prefetchBriefing } from './lib/briefingPrefetch'
import { resolveThreadThemeTarget } from './lib/threadThemeTarget'
import { buildHistoricalCoverageCue } from './lib/historicalCoverageCue'
import ResearchPlanPanel from './components/ResearchPlanPanel'
import WorkbenchPanel from './components/WorkbenchPanel'
import { createInvestigation } from './lib/workbench'

// Terminal Panels
import { NarrativeThreads, type LivingThreadSelection } from './components/NarrativeThreads'
import { ThreadFocusPanel } from './components/ThreadFocusPanel'
import { SignalStream } from './components/SignalStream'
import { OnboardingCoachmark } from './components/OnboardingCoachmark'
import { CountryFocusWalkthrough, COUNTRY_WALKTHROUGH_KEY } from './components/CountryFocusWalkthrough'
import { CorrelationMatrix } from './components/CorrelationMatrix'
import { AnomalyPanel } from './components/AnomalyPanel'
import { SourceIntegrityPanel } from './components/SourceIntegrityPanel'
import { PanelErrorBoundary } from './components/PanelErrorBoundary'
import { ChokepointPanel } from './components/ChokepointPanel'
import { AtlasLoader } from './components/AtlasLoader'
import { PanelHelpButton } from './components/PanelHelpDrawer'
import { Legend } from './components/Legend'
import { useUrlSync } from './hooks/useUrlSync'
import { useSavedWatches } from './hooks/useSavedWatches'
import { useIsMobile } from './hooks/useIsMobile'







interface FeatureCollection {
  type: 'FeatureCollection'
  features: any[]
}

const emptyFeatureCollection = (): FeatureCollection => ({ type: 'FeatureCollection', features: [] })
const DEG_TO_RAD = Math.PI / 180

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

function setGeoJsonData(map: any, sourceId: string, data: FeatureCollection) {
  const source = map.getSource(sourceId)
  if (source?.setData) {
    source.setData(data)
    return
  }
  if (!source) {
    map.addSource(sourceId, { type: 'geojson', data })
  }
}

function ensureLayer(map: any, layer: any) {
  // Guard: during a tab switch / teardown the map can be undefined or mid-
  // removal; calling getLayer then throws and crash-loops the whole console.
  if (!map || typeof map.getLayer !== 'function') return
  if (!map.getLayer(layer.id)) {
    map.addLayer(layer)
  }
}

function setLayerVisibility(map: any, layerId: string, visible: boolean) {
  if (!map || typeof map.getLayer !== 'function') return
  if (map.getLayer(layerId)) {
    map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none')
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

// Initial map view
const INITIAL_VIEW = {
  longitude: 0,
  latitude: 20,
  zoom: 1.5,
  pitch: 0,
  bearing: 0
}

const getNodePriority = (node: NodeData) => [
  node.heat ?? node.intensity ?? 0,
  node.signalCount ?? 0,
]

const pickTopAttentionNode = (nodes: NodeData[]) => nodes.reduce((max, node) => {
  const [nodeHeat, nodeSignals] = getNodePriority(node)
  const [maxHeat, maxSignals] = getNodePriority(max)
  if (nodeHeat !== maxHeat) return nodeHeat > maxHeat ? node : max
  return nodeSignals > maxSignals ? node : max
}, nodes[0])

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

  // Sync filter state ↔ URL params for shareable links
  useUrlSync()

  const { trackVisit, setIsOpen, items: workspaceItems, sessionItems } = useWorkspace()

  // State
  const [selectedCountry, setSelectedCountry] = useState<CountryDetail | null>(null)
  const [selectedCountryCode, setSelectedCountryCode] = useState<string | null>(null)
  type SelectedTheme = {
    theme: string,
    originCountry?: string,
    originCountryName?: string,
    originAttention?: PublicAttentionOrigin,
    thread?: { thread_id: string, label: string },
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
  // Workbench (Phase 2, #213): investigation memory overlay + research plan
  const [workbenchOpen, setWorkbenchOpen] = useState(false)
  const [researchQuery, setResearchQuery] = useState<string | null>(null)
  const [wbRefresh, setWbRefresh] = useState(0)
  const [tourRunId, setTourRunId] = useState(0)
  // A4: one-time contextual walkthrough on the first country selection.
  const [countryWalkthrough, setCountryWalkthrough] = useState<string | null>(null)
  const countryWalkthroughDone = useRef<boolean>(
    (() => { try { return !!localStorage.getItem(COUNTRY_WALKTHROUGH_KEY) } catch { return true } })()
  )
  // #152 command-bar layout: overflow "···" menu (TOUR + Settings), controlled
  // settings panel, and compact time-range dropdown for narrow viewports.
  const [moreMenuOpen, setMoreMenuOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [timeMenuOpen, setTimeMenuOpen] = useState(false)
  // Bottom dock active tab (#228 §3): anomaly | sources. The HEAT tab was
  // removed (#231) — heat is a map property (drives country color), not a
  // bottom list. The composite now colors the map directly.
  const [dockTab, setDockTab] = useState<'anomaly' | 'sources'>('anomaly')
  // Mobile L2 IA: instead of a long scroll of the desktop cockpit, show one
  // full-screen surface at a time via a bottom tab bar. Default to the live
  // stream (the L2 value). Desktop ignores this.
  const isMobile = useIsMobile()
  const [mobileTab, setMobileTab] = useState<'map' | 'stream' | 'threads' | 'pulse'>('stream')

  useEffect(() => {
    if (!moreMenuOpen && !timeMenuOpen) return
    const onDown = (e: MouseEvent) => {
      const el = e.target as HTMLElement
      if (!el.closest('.cmd-more-wrap') && !el.closest('.time-compact')) {
        setMoreMenuOpen(false)
        setTimeMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [moreMenuOpen, timeMenuOpen])
  const { watches, add: addWatch } = useSavedWatches()
  const [watchNamePrompt, setWatchNamePrompt] = useState<string | null>(null)
  const entrySource = useMemo(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get('entry')
  }, [])
  const tourEntryContext = entrySource === 'brief'
    ? 'You came in from the Brief. Atlas will show the full console first, then you can keep exploring the country or narrative you selected.'
    : undefined
  // const [timeWindow, setTimeWindow] = useState(24) // Replaced by context
  const [viewState, setViewState] = useState(INITIAL_VIEW)
  const [tooltip] = useState<TooltipData | null>(null)

  // Comparison & Overlay states
  const [selectedSourceProfile, setSelectedSourceProfile] = useState<string | null>(null)
  const [comparePerson, setComparePerson] = useState<{ a: string, b: string } | null>(null)
  const [compareTheme, setCompareTheme] = useState<{ a: string, b: string } | null>(null)

  const mapRef = useRef<MapRef>(null)
  const isGlobe = false
  // #212 / ADR-0005: Equal Earth is a parallel switchable view. Default Mercator
  // (zero prod risk) until visual sign-off; persisted so the choice sticks.
  // Equal-area is the DEFAULT since 2026-07-01 (Pedro's visual sign-off — the
  // ADR-0005 P6 gate): equal-area honesty + no WebGL (mobile blank-map class
  // gone). Mercator remains available via Settings; explicit choice persists.
  const [eeResetNonce, setEeResetNonce] = useState(0)
  const [mapProjection, setMapProjection] = useState<'mercator' | 'equalEarth'>(
    () => (localStorage.getItem('atlas.mapProjection') === 'mercator' ? 'mercator' : 'equalEarth'),
  )
  const toggleProjection = useCallback(() => {
    setMapProjection(p => {
      const next = p === 'mercator' ? 'equalEarth' : 'mercator'
      localStorage.setItem('atlas.mapProjection', next)
      return next
    })
  }, [])

  // Focus hook for click-to-focus
  const { setFocus, focus, clearFocus, setCountry, filter, setTheme, mapFlyCountry, setMapFlyCountry, isActive } = useFocus()

  // Theme for layer styling
  const { themeId } = useTheme()

  // Layer visibility
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [showAircraft, setShowAircraft] = useState(false)
  const [aircraftData, setAircraftData] = useState([])
  const [aircraftError, setAircraftError] = useState(false)
  const [showVessels, setShowVessels] = useState(false)
  const [vesselData, setVesselData] = useState([])
  const [vesselConnected, setVesselConnected] = useState(false)
  // #231: baseline-normalized composite heat (velocity/surprise/diversity/
  // voice) per country. The map fill must use THIS, not /nodes volume-rank
  // heat (which made the US permanently reddest). Keyed by ISO2.
  const [heatComposite, setHeatComposite] = useState<Map<string, number>>(new Map())

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

  // Map readiness gate — prevents DeckGL from crashing before WebGL context is ready
  const [mapReady, setMapReady] = useState(false)
  // Map-load watchdog: the basemap style is an EXTERNAL carto CDN fetch. On a
  // flaky mobile network it can stall, onLoad never fires, and the map stays
  // blank ("no carga nada"). If the map isn't ready after a grace period, remount
  // it (via key) to re-request the style. Capped so it can't loop.
  const [mapRetry, setMapRetry] = useState(0)
  // Mobile map fix: the app opens on the Stream tab, so the map panel is laid
  // out at 0×0 (collapsed). MapLibre initialised in a 0-size container loads the
  // style but never fetches/renders tiles, and a later resize() doesn't recover
  // it → a permanently blank map. Fix: don't MOUNT MapGL until its container is
  // really sized (the first time the Map tab is shown). Desktop is always sized.
  const [mapEverShown, setMapEverShown] = useState(!isMobile)
  useEffect(() => {
    if (!isMobile || mobileTab === 'map') setMapEverShown(true)
  }, [isMobile, mobileTab])
  useEffect(() => {
    // Don't burn the (capped) retries before the map is even mounted.
    if (mapReady || mapRetry >= 2 || !mapEverShown) return
    const t = setTimeout(() => {
      if (!mapReady) setMapRetry(r => r + 1)
    }, 9000)
    return () => clearTimeout(t)
  }, [mapReady, mapRetry, mapEverShown])

  // T5.1: instrument the App console open (the denominator for time-to-value).
  useEffect(() => { track('app_open') }, [])

  // Tracks when the 13MB GeoJSON source has actually finished loading
  const [heatSourceReady, setHeatSourceReady] = useState(false)

  // When switching to Equal Earth, MapLibre unmounts — gate its readiness off so
  // its layer effects never touch a torn-down map (the `this.style.getLayer`
  // crash). Returning to Mercator remounts MapGL; its onLoad sets these true.
  useEffect(() => {
    if (mapProjection !== 'mercator') {
      setMapReady(false)
      setHeatSourceReady(false)
    }
  }, [mapProjection])

  // Settings toggles
  const [showTerminator, setShowTerminator] = useState(false)
  const [sizeBoost, setSizeBoost] = useState(false)
  const [showFlows, setShowFlows] = useState(false)

  // Click handlers
  function handleCountryClick(countryCode: string) {
    setSelectedPublicAttention(null)
    setSelectedThread(null)
    // Country nav must take the stream slot: clear any open ThemeDetail so the
    // isCountry branch wins (else focus/chip update but the stream stays on the
    // old theme — the anomaly/map→country-while-theme-open bug). Flows that keep
    // a theme (ThemeDetail country card → right panel) don't go through here.
    setSelectedTheme(null)
    setThemeBackStack([])
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
  }, [clearFocus])

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
  }

  function handleResearchOpenCountry(countryCode: string) {
    handleCountryClick(countryCode)
    setMapFlyCountry(countryCode)
    setWorkbenchOpen(false)
  }

  // Theme selection handlers
  const handleThemeSelect = (theme: string, countryCode?: string, countryName?: string, originAttention?: PublicAttentionOrigin) => {
    // T5.1: a thread open is a value moment (the analyst reached real narrative).
    track('thread_open')
    trackOnce('first_value_moment', { kind: 'thread' })
    setSelectedPublicAttention(null)
    setSelectedThread(null)
    // Custom query threads are synthetic — they must not pollute FocusContext
    // (which would fire focus-data fetches against a non-existent theme code).
    if (!theme.startsWith('query-thread::')) setTheme(theme)
    const nextTheme = { theme, originCountry: countryCode, originCountryName: countryName, originAttention }
    setSelectedTheme(prev => {
      if (prev && prev.theme !== theme) {
        setThemeBackStack(stack => [prev, ...stack].slice(0, 5))
      }
      return nextTheme
    })
    setRightPanelThemeCountry(null)
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

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const attention = params.get('attention')
    const theme = params.get('theme')
    const country = params.get('country') || undefined
    // Brief → console deep-link without attention: open the theme detail on mount.
    // Atlas-topic slugs (e.g. "disease-outbreak") resolve to the gated theme view.
    if (theme && !attention) {
      handleThemeSelect(theme, country, country ? resolveCountryName(country) : undefined)
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
      return
    }
    handlePublicAttentionSelect({ title })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Focus-aware data from provider - auto-refetches when focus/range changes
  const { nodes, flows, unfilteredFlows, acledConflicts, loading, isRefetching, refetch, timeRange, setTimeRange, meta: focusMeta } = useFocusData()

  // #231: fetch the baseline-normalized heat composite for map color (after
  // timeRange is in scope). Falls back silently to volume if unavailable.
  // Fetch ALL countries (not a top-N) and min-max normalize the real value
  // band onto [0.1, 1.0] so the full blue→red gradient is used — the raw
  // composite clusters in a narrow band (~0.36–0.72), which mapped to a flat
  // orange and left most of the world dark (#231 follow-up, Pedro's review).
  useEffect(() => {
    let cancelled = false
    const h = timeRangeToHours(timeRange)
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
  }, [timeRange])

  // Initial map stays global. The hotspot reset button performs focused fly-to on demand.

  // Fly to top country when theme clicked in NarrativeThreads
  useEffect(() => {
    if (!mapFlyCountry || !mapReady) return
    const node = nodes.find(n => n.id === mapFlyCountry)
    const coord = node ? [node.lon, node.lat] : COUNTRY_COORDS[mapFlyCountry.toUpperCase()] ?? null
    if (coord) {
      mapRef.current?.getMap()?.flyTo({
        center: coord as [number, number],
        zoom: node ? 3 : 4,
        duration: 2000,
        essential: true
      })
    }
    setMapFlyCountry(null)
  }, [mapFlyCountry, mapReady])

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

  // Sync Global Focus to CountrySlide-over + fly to country
  useEffect(() => {
    if (focus.type === 'country' && focus.value && focus.value !== selectedCountryCode) {
      handleCountryClick(focus.value)
      const node = nodes.find(n => n.id === focus.value)
      if (node && mapReady) {
        mapRef.current?.getMap()?.flyTo({
          center: [node.lon, node.lat],
          zoom: 3,
          duration: 2000,
          essential: true
        })
      }
    }
  }, [focus.type, focus.value, selectedCountryCode])

  // Open ThemeDetail when theme is focused via FocusContext (e.g. NarrativeThreads click)
  useEffect(() => {
    const filterCountry = filter.country || undefined
    if (filter.theme && (!selectedTheme || selectedTheme.theme !== filter.theme || selectedTheme.originCountry !== filterCountry)) {
      const countryName = filter.country ? resolveCountryName(filter.country) : undefined
      setSelectedTheme({ theme: filter.theme, originCountry: filterCountry, originCountryName: countryName })
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

  // Back navigation: pop the topmost open panel. Used by Escape (desktop) and
  // by swipe-right-from-the-edge (mobile, like a native app). Order = most
  // recently opened first.
  const popPanel = useCallback((): boolean => {
    if (showBriefing) { setShowBriefing(false); return true }
    if (selectedSourceProfile) { setSelectedSourceProfile(null); return true }
    if (rightPanelThemeCountry) { setRightPanelThemeCountry(null); return true }
    if (focus.type === 'person') { clearFocus(); return true }
    if (selectedTheme) { setSelectedTheme(null); setTheme(null); return true }
    if (selectedCountry || selectedCountryCode) {
      setSelectedCountry(null)
      setSelectedCountryCode(null)
      setShowFlows(false)
      clearFocus()
      return true
    }
    return false
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showBriefing, selectedSourceProfile, rightPanelThemeCountry, focus.type, selectedTheme, selectedCountry, selectedCountryCode])

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

  // On mobile, secondary panels (thread detail, person, source, country drill-in)
  // render inside the Stream slot. Opening one from the Map/Threads tab would
  // leave it on a hidden tab — so bring the Stream tab forward automatically.
  useEffect(() => {
    if (!isMobile) return
    if (
      selectedTheme || focus.type === 'person' || selectedSourceProfile ||
      rightPanelThemeCountry || selectedCountry || selectedCountryCode ||
      selectedPublicAttention
    ) {
      setMobileTab('stream')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMobile, selectedTheme, focus.type, selectedSourceProfile, rightPanelThemeCountry, selectedCountry, selectedCountryCode, selectedPublicAttention])

  // The map lives in a tab panel that is display:none on other tabs; MapLibre
  // can't size a hidden container, so resize it once the Map tab is shown.
  useEffect(() => {
    if (!isMobile || mobileTab !== 'map') return
    const t = setTimeout(() => mapRef.current?.getMap()?.resize(), 120)
    return () => clearTimeout(t)
  }, [isMobile, mobileTab])

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
    const baseFlows = selectedCountryCode
      ? (flows.length ? flows : (unfilteredFlows || []))
      : flows;
    let filteredFlows = [...baseFlows];

    if (selectedCountryCode) {
      filteredFlows = filteredFlows.filter(f =>
        f.sourceCountry === selectedCountryCode ||
        f.targetCountry === selectedCountryCode
      );
    }

    const zoom = viewState?.zoom ?? 1.5
    const maxFlows = zoom < 2 ? 25 : zoom < 4 ? 40 : 60
    return filteredFlows
      .sort((a, b) => (b.strength || 0) - (a.strength || 0))
      .slice(0, maxFlows)
  }, [flows, unfilteredFlows, viewState?.zoom, selectedCountryCode])

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

  // Track which countries have heat state set (for cleanup on data change)
  const prevHeatCountries = useRef<Set<string>>(new Set())

  // Per-country heat + intensity — SINGLE SOURCE OF TRUTH for both the MapLibre
  // map (feature-states below) and the Equal Earth map (#212). See
  // lib/countryHeatStates. entityFocus mirrors the prior inline logic.
  const heatStates = useMemo(() => {
    const entityFocus = !selectedCountryCode && isActive && !!focus.value
      && (focus.type === 'person' || focus.type === 'theme')
    return computeCountryHeatStates({
      enhancedNodes,
      heatComposite,
      visibleFlows,
      selectedCountryCode,
      entityFocus,
    })
  }, [enhancedNodes, heatComposite, visibleFlows, selectedCountryCode, isActive, focus.type, focus.value])

  // Update MapLibre native country heat feature-states when node data changes
  // Must wait for heatSourceReady (GeoJSON downloaded), not just mapReady
  useEffect(() => {
    if (mapProjection !== 'mercator') return
    const map = mapRef.current?.getMap()
    if (!map || !heatSourceReady || heatStates.size === 0) return

    // heatStates is computed by the shared helper (single source of truth with
    // the Equal Earth map). Here we just push it into MapLibre feature-states.
    const currentCodes = new Set<string>()
    heatStates.forEach((st, code) => {
      map.setFeatureState(
        { source: 'country-heat', id: code },
        { intensity: st.intensity, heat: st.heat }
      )
      currentCodes.add(code)
    })

    // Clear countries no longer in the data
    prevHeatCountries.current.forEach(code => {
      if (!currentCodes.has(code)) {
        map.setFeatureState(
          { source: 'country-heat', id: code },
          { intensity: 0, heat: 0 }
        )
      }
    })

    prevHeatCountries.current = currentCodes
  }, [heatStates, heatSourceReady, mapProjection])

  // Toggle country heat layer visibility when GLOW button is pressed
  useEffect(() => {
    if (mapProjection !== 'mercator') return
    const map = mapRef.current?.getMap()
    if (!map || !mapReady) return

    if (map.getLayer('country-heat-fill')) {
      map.setPaintProperty('country-heat-fill', 'fill-opacity', showHeatmap ? 0.5 : 0)
    }
    if (map.getLayer('country-heat-glow')) {
      map.setLayoutProperty('country-heat-glow', 'visibility', showHeatmap ? 'visible' : 'none')
    }
  }, [showHeatmap, mapReady, mapProjection])

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
        features: enhancedNodes.filter((node: any) => node.isAnomaly).map((node: any) => ({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [node.lon, node.lat] },
          properties: {
            signalCount: node.signalCount || 0,
            radius: Math.min(Math.max(6, Math.sqrt(node.signalCount || 1) * (sizeBoost ? 1.5 : 0.8)), 24),
          },
        })),
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
      terminator: buildTerminatorData(showTerminator && !crisisEnabled),
    }
  }, [
    activeChokepoints,
    acledConflicts,
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
  ])

  useEffect(() => {
    if (mapProjection !== 'mercator') return
    const map = mapRef.current?.getMap()
    if (!map || !mapReady) return

    setGeoJsonData(map, 'atlas-flows', nativeOverlayData.flows)
    setGeoJsonData(map, 'atlas-anomaly', nativeOverlayData.anomaly)
    setGeoJsonData(map, 'atlas-chokepoints', nativeOverlayData.chokepoints)
    setGeoJsonData(map, 'atlas-aircraft', nativeOverlayData.aircraft)
    setGeoJsonData(map, 'atlas-vessels', nativeOverlayData.vessels)
    setGeoJsonData(map, 'atlas-acled', nativeOverlayData.acled)
    setGeoJsonData(map, 'atlas-terminator', nativeOverlayData.terminator)

    ensureLayer(map, {
      id: 'atlas-terminator-fill',
      type: 'fill',
      source: 'atlas-terminator',
      paint: {
        'fill-color': 'rgba(0, 8, 25, 1)',
        'fill-opacity': ['coalesce', ['get', 'opacity'], 0],
      },
    })
    ensureLayer(map, {
      id: 'atlas-flows-line',
      type: 'line',
      source: 'atlas-flows',
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: {
        'line-color': themeId === 'retro-radar' ? 'rgba(74, 222, 128, 0.55)' : 'rgba(100, 140, 180, 0.52)',
        'line-width': ['interpolate', ['linear'], ['coalesce', ['get', 'strength'], 0], 0, 0.8, 1, 3],
        'line-opacity': 0.45,
      },
    })
    ensureLayer(map, {
      id: 'atlas-anomaly-ring',
      type: 'circle',
      source: 'atlas-anomaly',
      paint: {
        'circle-radius': ['coalesce', ['get', 'radius'], 8],
        'circle-color': 'rgba(239, 68, 68, 0)',
        'circle-stroke-color': 'rgba(239, 68, 68, 0.95)',
        'circle-stroke-width': 2,
      },
    })
    ensureLayer(map, {
      id: 'atlas-chokepoints-circle',
      type: 'circle',
      source: 'atlas-chokepoints',
      paint: {
        'circle-radius': ['case', ['get', 'active'], 18, 11],
        'circle-color': ['case', ['get', 'active'], 'rgba(0, 220, 200, 0.16)', 'rgba(0, 180, 160, 0.08)'],
        'circle-stroke-color': ['case', ['get', 'active'], 'rgba(0, 255, 210, 0.8)', 'rgba(0, 180, 160, 0.35)'],
        'circle-stroke-width': ['case', ['get', 'active'], 2, 1],
      },
    })
    ensureLayer(map, {
      id: 'atlas-aircraft-circle',
      type: 'circle',
      source: 'atlas-aircraft',
      paint: {
        'circle-radius': ['case', ['>', ['coalesce', ['get', 'alt'], 0], 10000], 2, 3],
        'circle-color': [
          'case',
          ['>', ['coalesce', ['get', 'alt'], 0], 10000],
          'rgba(255, 255, 255, 0.78)',
          ['>', ['coalesce', ['get', 'alt'], 0], 5000],
          'rgba(255, 210, 80, 0.72)',
          'rgba(255, 140, 40, 0.68)',
        ],
      },
    })
    ensureLayer(map, {
      id: 'atlas-vessels-circle',
      type: 'circle',
      source: 'atlas-vessels',
      paint: {
        'circle-radius': ['case', ['>', ['coalesce', ['get', 'speed'], 0], 14], 4, 3],
        'circle-color': ['case', ['>', ['coalesce', ['get', 'speed'], 0], 10], 'rgba(0, 220, 200, 0.9)', 'rgba(0, 180, 160, 0.6)'],
      },
    })
    ensureLayer(map, {
      id: 'atlas-acled-circle',
      type: 'circle',
      source: 'atlas-acled',
      paint: {
        'circle-radius': ['coalesce', ['get', 'radius'], 5],
        'circle-color': [
          'case',
          ['in', 'Battle', ['coalesce', ['get', 'type'], '']],
          'rgba(239, 68, 68, 0.86)',
          ['in', 'Explosion', ['coalesce', ['get', 'type'], '']],
          'rgba(239, 68, 68, 0.86)',
          ['in', 'Riot', ['coalesce', ['get', 'type'], '']],
          'rgba(249, 115, 22, 0.78)',
          'rgba(234, 179, 8, 0.7)',
        ],
        'circle-stroke-color': 'rgba(255, 255, 255, 0.32)',
        'circle-stroke-width': 1,
      },
    })

    setLayerVisibility(map, 'atlas-flows-line', showFlows || !!selectedCountryCode || !!filter.theme)
    setLayerVisibility(map, 'atlas-anomaly-ring', !crisisEnabled)
    setLayerVisibility(map, 'atlas-chokepoints-circle', showVessels)
    setLayerVisibility(map, 'atlas-aircraft-circle', showAircraft)
    setLayerVisibility(map, 'atlas-vessels-circle', showVessels)
    setLayerVisibility(map, 'atlas-acled-circle', (acledConflicts?.length ?? 0) > 0)
    setLayerVisibility(map, 'atlas-terminator-fill', showTerminator && !crisisEnabled)
  }, [
    acledConflicts,
    crisisEnabled,
    filter.theme,
    mapReady,
    nativeOverlayData,
    selectedCountryCode,
    showAircraft,
    showFlows,
    showTerminator,
    showVessels,
    themeId,
    mapProjection,
  ])

  useEffect(() => {
    if (mapProjection !== 'mercator') return
    const map = mapRef.current?.getMap()
    if (!map || !mapReady) return

    const handleChokepointClick = (e: any) => {
      const feature = e.features?.[0]
      if (!feature) return
      const cp = CHOKEPOINTS.find(item => item.id === feature.properties?.id)
      if (!cp) return
      setSelectedChokepoint(prev => prev?.id === cp.id ? null : cp)
      setMapFlyCountry(cp.primaryCountry)
    }
    const enter = () => { map.getCanvas().style.cursor = 'pointer' }
    const leave = () => { map.getCanvas().style.cursor = '' }

    // T3.3 P-FOCUS: a conflict event click centers the EVENT (panel + fly to its
    // exact location), instead of falling through to the country fill.
    const handleAcledClick = (e: any) => {
      const p = e.features?.[0]?.properties
      if (!p) return
      const ev: ConflictEventFocus = {
        type: p.type || '', country: p.country || '', place: p.place || '',
        actor1: p.actor1 || '', actor2: p.actor2 || '', date: p.date || '',
        fatalities: Number(p.fatalities) || 0, mentions: Number(p.mentions) || 0,
        lat: p.lat != null && p.lat !== '' ? Number(p.lat) : null,
        lon: p.lon != null && p.lon !== '' ? Number(p.lon) : null,
      }
      setSelectedConflictEvent(ev)
      if (ev.lat != null && ev.lon != null) {
        map.flyTo({ center: [ev.lon, ev.lat], zoom: 5, duration: 1200 })
      }
    }

    map.on('click', 'atlas-chokepoints-circle', handleChokepointClick)
    map.on('mouseenter', 'atlas-chokepoints-circle', enter)
    map.on('mouseleave', 'atlas-chokepoints-circle', leave)
    map.on('click', 'atlas-acled-circle', handleAcledClick)
    map.on('mouseenter', 'atlas-acled-circle', enter)
    map.on('mouseleave', 'atlas-acled-circle', leave)

    return () => {
      // The map may already be torn down (projection switch unmounts MapGL):
      // map.getLayer() reaches into a destroyed `this.style` and throws. Guard
      // on map.style and swallow teardown races.
      try {
        if (!(map as any).style) return
        if (map.getLayer('atlas-chokepoints-circle')) {
          map.off('click', 'atlas-chokepoints-circle', handleChokepointClick)
          map.off('mouseenter', 'atlas-chokepoints-circle', enter)
          map.off('mouseleave', 'atlas-chokepoints-circle', leave)
        }
        if (map.getLayer('atlas-acled-circle')) {
          map.off('click', 'atlas-acled-circle', handleAcledClick)
          map.off('mouseenter', 'atlas-acled-circle', enter)
          map.off('mouseleave', 'atlas-acled-circle', leave)
        }
      } catch { /* map already removed */ }
    }
  }, [mapReady, setMapFlyCountry, mapProjection])

  // Total signals for stats
  const totalSignals = nodes.reduce((sum, n) => sum + n.signalCount, 0)
  const historicalCoverageCue = buildHistoricalCoverageCue({
    source: focusMeta.source,
    coverage: focusMeta.coverage,
  })
  const openBrief = () => {
    const params = new URLSearchParams()
    params.set('range', timeRange)
    if (selectedCountryCode) params.set('country', selectedCountryCode)
    navigate(`/brief?${params.toString()}`)
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

  // Prefetch briefing data so the modal opens instantly — keyed to current timeRange
  const [prefetchedBriefing, setPrefetchedBriefing] = useState<any>(null)
  const [prefetchedInsight, setPrefetchedInsight] = useState<string | null>(null)
  const [prefetchedHours, setPrefetchedHours] = useState<number>(0)
  const [externalSearchQuery, setExternalSearchQuery] = useState<{ q: string; id: number } | undefined>(undefined)
  useEffect(() => {
    const h = timeRangeToHours(timeRange)
    setPrefetchedBriefing(null)
    setPrefetchedInsight(null)
    prefetchBriefing(h) // warm sessionStorage so /brief loads without spinner
    fetch(`/api/v2/briefing?hours=${h}`).then(r => r.json()).then(d => { setPrefetchedBriefing(d); setPrefetchedHours(h) }).catch(() => { })
    fetch(`/api/v2/briefing/insight?hours=${h}`).then(r => r.json()).then(d => { if (d.insight) setPrefetchedInsight(d.insight) }).catch(() => { })
  }, [timeRange])

  // Show loader until nodes AND map are ready; hard cap at 10s
  const [appReady, setAppReady] = useState(false)
  useEffect(() => {
    if (!loading && nodes.length > 0 && mapReady) setAppReady(true)
  }, [loading, nodes.length, mapReady])
  useEffect(() => {
    const t = setTimeout(() => setAppReady(true), 10000)
    return () => clearTimeout(t)
  }, [])


  return (
    <div className={`app ${crisisEnabled ? 'crisis-mode' : ''}`}>
      <AtlasLoader visible={!appReady} />
      {/* Command Bar */}
      <header className="command-bar">
        <div className="command-bar-left">
          <h1 className="brand" onClick={() => navigate('/')} style={{ cursor: 'pointer' }} data-tip="Back to home"><Globe size={16} /> ATLAS</h1>
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
              onStartInvestigation={(q) => {
                createInvestigation(q)
                setResearchQuery(q)
                setWorkbenchOpen(true)
                setWbRefresh(t => t + 1)
              }}
              externalQuery={externalSearchQuery}
            />
          </div>
          <div className="time-controls">
            {TIME_RANGE_OPTIONS.map(range => (
              <button
                key={range}
                className={`time-btn ${timeRange === range ? 'active' : ''}`}
                onClick={() => setTimeRange(range)}
              >
                {TIME_RANGE_LABELS[range]}
              </button>
            ))}
          </div>
          {/* Compact range dropdown — replaces the button row on narrow
              viewports (#152) so it can never collide with the search bar. */}
          <div className="time-compact">
            <button
              className="time-btn active time-compact-trigger"
              onClick={() => setTimeMenuOpen(open => !open)}
              data-tip="Time window"
            >
              {TIME_RANGE_LABELS[timeRange]} <ChevronDown size={11} />
            </button>
            {timeMenuOpen && (
              <div className="cmd-menu time-compact-menu">
                {TIME_RANGE_OPTIONS.map(range => (
                  <button
                    key={range}
                    className={`cmd-menu-item ${timeRange === range ? 'active' : ''}`}
                    onClick={() => { setTimeRange(range); setTimeMenuOpen(false) }}
                  >
                    {TIME_RANGE_LABELS[range]}
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            className={`time-btn workbench-btn ${workbenchOpen ? 'active' : ''}`}
            data-tip="Investigation Workbench: research plans, pins, and saved routes"
            onClick={() => setWorkbenchOpen(open => !open)}
          >
            WORKBENCH
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
          {/* <CrisisToggle /> - Hidden per visual clarity update */}
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
            className="cmd-btn workspace-cmd-btn"
            data-tour="workspace-button"
            onClick={() => setIsOpen(true)}
            data-tip="Open Investigation Workspace"
          >
            <FolderOpen size={13} /> <span className="cmd-btn-label">WORKSPACE</span>
            {(workspaceItems.length + sessionItems.length) > 0 && (
              <span className="cmd-count">{workspaceItems.length + sessionItems.length}</span>
            )}
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
              </div>
            )}
          </div>
          <SettingsPanel
            showTerminator={showTerminator}
            onToggleTerminator={setShowTerminator}
            sizeBoost={sizeBoost}
            onToggleSizeBoost={setSizeBoost}
            mapProjection={mapProjection}
            onToggleProjection={toggleProjection}
            open={settingsOpen}
            onClose={() => setSettingsOpen(false)}
          />
        </div>
      </header>

      {/* A1: persistent focus chip — shows what's focused and gives one ✕ to
          return to the whole, unfocused view (the missing country deselect). */}
      <FocusIndicator onClear={clearAll} />

      <div className="coverage-disclaimer" data-tip="Atlas colors countries by deviation from each country's recent baseline. Raw volume increases evidence density, but it is not treated as real-world importance.">
        Coverage bias: map heat is baseline-normalized; raw volume is evidence density, not importance.
      </div>

      <div className={`terminal-layout${isMobile ? ` mobile-tab-${mobileTab}` : ''}`}>
        {/* Panel 1: GLOBAL RADAR */}
        <div className="terminal-panel radar" data-tour="globe">
          <div className="panel-header">
            <div className="panel-header-title-wrap">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                GLOBE
                <PanelHelpButton panel="globe" />
              </span>
              <span className="panel-subtitle">narrative activity by country</span>
            </div>
            <div className="panel-header-controls">
              <button
                className={`layer-btn ${showHeatmap ? 'active' : ''}`}
                onClick={() => setShowHeatmap(!showHeatmap)}
                data-tip="Country heat layer — color = composite anomaly (velocity, surprise, source diversity, local voice) vs each country's own baseline, NOT raw volume. A small country spiking above its norm outranks a high-volume one. Border thickness = signal volume (evidence density)."
              >
                HEAT
              </button>
              <button
                className={`layer-btn ${showFlows ? 'active' : ''}`}
                onClick={() => setShowFlows(!showFlows)}
                data-tip="Narrative flows — arcs connect countries sharing dominant media themes. Width = co-occurrence strength. Non-directional."
              >
                FLOW
              </button>
              <button
                className={`layer-btn ${showAircraft ? 'active' : ''} ${showAircraft && aircraftError ? 'layer-btn-error' : ''} ${!showAircraft && (filter.country || filter.theme) ? 'layer-btn-hint' : ''}`}
                onClick={() => setShowAircraft(!showAircraft)}
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
                onClick={() => setShowVessels(!showVessels)}
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
                  // The ↺ was MapLibre-only — dead on the default EE map
                  // (Pedro 2026-07-02): reset EE's transform + clear focus.
                  if (mapProjection === 'equalEarth') {
                    setSelectedCountry(null)
                    setSelectedCountryCode(null)
                    setShowFlows(false)
                    clearFocus()
                    setMapFlyCountry(null)
                    setEeResetNonce(n => n + 1)
                    return
                  }
                  const map = mapRef.current?.getMap()
                  // #147: after rotating/tilting users get lost — pitch and
                  // bearing were never restored. First press on a tilted map
                  // resets to the flat north-up default; pressing again (map
                  // already flat) flies to the hotspot as before.
                  const isTilted = map
                    ? Math.abs(map.getPitch()) > 1 || Math.abs(map.getBearing()) > 1
                    : false
                  if (isTilted) {
                    map?.flyTo({
                      center: [INITIAL_VIEW.longitude, INITIAL_VIEW.latitude],
                      zoom: INITIAL_VIEW.zoom,
                      pitch: 0,
                      bearing: 0,
                      duration: 1200,
                      essential: true,
                    })
                    return
                  }
                  setSelectedCountry(null)
                  setSelectedCountryCode(null)
                  setShowFlows(false)
                  clearFocus()
                  if (nodes.length > 0) {
                    const hottest = pickTopAttentionNode(nodes)
                    map?.flyTo({ center: [hottest.lon, hottest.lat], zoom: 2.5, duration: 1800, essential: true })
                  } else {
                    setViewState(INITIAL_VIEW)
                  }
                }}
                data-tip="Tilted or rotated: reset to flat north-up view. Already flat: fly to highest-attention region"
                aria-label="Reset map view or fly to highest-attention region"
              >
                ↺
              </button>
            </div>
          </div>
          <div className="panel-content">
            <MapErrorBoundary>
              {mapProjection === 'equalEarth' ? (
                <EqualEarthMap
                  heatStates={heatStates}
                  showHeatmap={showHeatmap}
                  selectedCountryCode={selectedCountryCode}
                  flyCountry={mapFlyCountry}
                  resetNonce={eeResetNonce}
                  overlay={nativeOverlayData}
                  onMarkerClick={(kind, p) => {
                    // Mirrors the MapLibre layer handlers (parity audit).
                    if (kind === 'chokepoint') {
                      const cp = CHOKEPOINTS.find(item => item.id === p?.id)
                      if (!cp) return
                      setSelectedChokepoint(prev => prev?.id === cp.id ? null : cp)
                      setMapFlyCountry(cp.primaryCountry)
                    } else {
                      setSelectedConflictEvent({
                        type: String(p.type || ''), country: String(p.country || ''), place: String(p.place || ''),
                        actor1: String(p.actor1 || ''), actor2: String(p.actor2 || ''), date: String(p.date || ''),
                        fatalities: Number(p.fatalities) || 0, mentions: Number(p.mentions) || 0,
                        lat: p.lat != null && p.lat !== '' ? Number(p.lat) : null,
                        lon: p.lon != null && p.lon !== '' ? Number(p.lon) : null,
                      })
                    }
                  }}
                  onCountryClick={(gdelt, name) => {
                    handleCountryClick(gdelt)
                    setFocus('country', gdelt, name || gdelt)
                    setMapFlyCountry(gdelt)
                  }}
                />
              ) : mapEverShown ? (
              <MapGL
                key={`map-${mapRetry}`}
                ref={mapRef}
                mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
                attributionControl={false}
                projection={isGlobe ? 'globe' : 'mercator'}
                {...viewState}
                onError={(e: any) => { console.warn('[map] load error', e?.error?.message || e) }}
                onMove={evt => setViewState(evt.viewState as any)}
                onLoad={(e) => {
                  const map = e.target

                  // Atmosphere
                  if (typeof (map as any).setFog === 'function') {
                    ; (map as any).setFog({
                      'color': 'rgba(10, 15, 26, 0.8)',
                      'horizon-blend': 0.08,
                      'high-color': '#1a3050',
                      'space-color': '#050510',
                      'star-intensity': 0.15
                    })
                  }

                  // Country heat source — loads GeoJSON once, colors driven by feature-state
                  map.addSource('country-heat', {
                    type: 'geojson',
                    data: '/data/countries.geojson',
                    promoteId: 'ISO_A2'
                  })

                  // Layer 1: Country shape fill
                  // fill-color uses 'heat' (z-score deviation from baseline) so a small country
                  // spiking above its own norm appears redder than the US on a quiet day
                  map.addLayer({
                    id: 'country-heat-fill',
                    type: 'fill',
                    source: 'country-heat',
                    paint: {
                      // Stops span the normalized [0.1,1.0] heat band with a
                      // full cool→hot ramp (blue→cyan→amber→red) so the world
                      // reads like a weather radar, not a flat orange (#231).
                      'fill-color': [
                        'interpolate', ['linear'],
                        ['coalesce', ['feature-state', 'heat'], 0],
                        0, 'rgba(0, 0, 0, 0)',
                        0.1, 'rgba(20, 50, 120, 40)',
                        0.3, 'rgba(25, 90, 150, 60)',
                        0.5, 'rgba(40, 140, 120, 75)',
                        0.65, 'rgba(190, 130, 30, 95)',
                        0.82, 'rgba(220, 75, 20, 115)',
                        1.0, 'rgba(238, 35, 10, 145)'
                      ],
                      'fill-opacity': 0.5
                    }
                  })

                  // Layer 2: Border glow — color driven by heat, width by intensity (volume)
                  map.addLayer({
                    id: 'country-heat-glow',
                    type: 'line',
                    source: 'country-heat',
                    paint: {
                      'line-color': [
                        'interpolate', ['linear'],
                        ['coalesce', ['feature-state', 'heat'], 0],
                        0, 'rgba(0, 0, 0, 0)',
                        0.1, 'rgba(30, 60, 140, 30)',
                        0.3, 'rgba(35, 110, 160, 50)',
                        0.5, 'rgba(50, 160, 130, 65)',
                        0.65, 'rgba(205, 140, 35, 80)',
                        0.82, 'rgba(230, 80, 20, 100)',
                        1.0, 'rgba(248, 45, 10, 125)'
                      ],
                      'line-width': [
                        'interpolate', ['linear'],
                        ['coalesce', ['feature-state', 'intensity'], 0],
                        0, 0,
                        0.05, 2,
                        0.5, 6,
                        1.0, 10
                      ],
                      'line-blur': 4,
                      'line-opacity': 0.7
                    }
                  })

                  // Listen for GeoJSON source to finish downloading
                  const onSourceData = (e: any) => {
                    if (e.sourceId === 'country-heat' && e.isSourceLoaded) {
                      setHeatSourceReady(true)
                      map.off('sourcedata', onSourceData)
                    }
                  }
                  if (map.isSourceLoaded('country-heat')) {
                    setHeatSourceReady(true)
                  } else {
                    map.on('sourcedata', onSourceData)
                  }

                  // Fallback: if sourcedata event doesn't fire within 3s, force ready
                  setTimeout(() => setHeatSourceReady(true), 3000)

                  // Country territory click — ISO_A2 → GDELT/FIPS mapping for mismatches
                  const ISO_TO_GDELT: Record<string, string> = {
                    CN: 'CH', ID: 'RI', RS: 'RB', XK: 'KV', MK: 'MK',
                    CD: 'CG', CG: 'CF', TZ: 'TZ', KR: 'KS', KP: 'KN',
                    PS: 'GZ', EI: 'EI',
                  }
                  map.on('click', 'country-heat-fill', (e: any) => {
                    if (!e.features?.length) return
                    const props = e.features[0].properties
                    const iso = props?.ISO_A2 || props?.ISO_A2_EH || ''
                    if (!iso || iso === '-99') return
                    const gdelt = ISO_TO_GDELT[iso] || iso
                    handleCountryClick(gdelt)
                    setFocus('country', gdelt, props?.NAME || gdelt)
                    setMapFlyCountry(gdelt)
                  })
                  map.on('mouseenter', 'country-heat-fill', () => {
                    map.getCanvas().style.cursor = 'pointer'
                  })
                  map.on('mouseleave', 'country-heat-fill', () => {
                    map.getCanvas().style.cursor = ''
                  })

                  // iOS Safari (and other mobile GPUs) can silently DROP the
                  // WebGL context under memory pressure — the map goes blank
                  // with no JS error and never recovers on its own. Catch the
                  // loss and force a remount so MapLibre rebuilds the context.
                  // (Capped so a genuinely unsupported device can't loop.)
                  try {
                    map.getCanvas().addEventListener('webglcontextlost', (ev: Event) => {
                      ev.preventDefault()
                      console.warn('[map] webgl context lost — remounting')
                      setMapReady(false)
                      setMapRetry(r => (r < 4 ? r + 1 : r))
                    }, { once: true })
                  } catch { /* canvas not ready — ignore */ }

                  setMapReady(true)
                }}
              >
              </MapGL>
              ) : (
                <div className="map-lazy-placeholder" />
              )}
              <div className="globe-vignette" />
            </MapErrorBoundary>
            <Legend
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
              vesselCount={vesselData.length}
              vesselConnected={vesselConnected}
              aircraftError={aircraftError}
              conflictCount={acledConflicts?.length ?? 0}
              anomalyCount={enhancedNodes.filter((n: any) => n.isAnomaly).length}
            />
          </div>
        </div>

        {/* Panel 2: SIGNAL STREAM — the intel hub, swaps based on active context */}
        {(() => {
          const isPerson = focus.type === 'person' && !!focus.value
          const isThread = !!selectedThread && !isPerson
          const isTheme = !!selectedTheme && !isPerson && !isThread
          const isCountry = !!selectedCountryCode && !isPerson && !isTheme && !isThread
          const isPublicAttention = !!selectedPublicAttention && !isPerson && !isCountry && !isTheme
          const isChokepoint = !!selectedChokepoint && !isPerson && !isCountry && !isTheme && !isPublicAttention
          const closeAll = () => { setSelectedTheme(null); setSelectedThread(null); setThemeBackStack([]); setSelectedPublicAttention(null); setRightPanelThemeCountry(null); setSelectedCountry(null); setSelectedCountryCode(null); setShowFlows(false); setSelectedChokepoint(null); setSelectedConflictEvent(null); clearFocus(); setPrevStreamCtx(null); if (filter.theme) setTheme(null) }
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
                SIGNAL STREAM
                <PanelHelpButton panel="signal-stream" />
              </span>
              <span className="panel-subtitle">notable open signals</span>
            </>
          ) : (
            <>
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                SIGNAL STREAM
                <PanelHelpButton panel="signal-stream" />
              </span>
              <span className="panel-subtitle">notable open signals</span>
            </>
          )
          if (isTheme) panelTitle = <>
            <button className="drill-back-btn" onClick={themeBackStack.length > 0 ? handleThemeBack : handleStreamBack} style={{ fontSize: 13, marginRight: 6 }}>
              {themeBackStack.length > 0 ? `← ${themeBackStack[0].theme.replace(/_/g, ' ').slice(0, 20)}` : '← STREAM'}
            </button>
            <span style={{ color: '#94a3b8' }}>{(selectedTheme!.thread?.label || selectedTheme!.theme.replace(/_/g, ' ')).slice(0, 32)}</span>
          </>
          if (isThread) panelTitle = <>
            <button className="drill-back-btn" onClick={handleStreamBack} style={{ fontSize: 13, marginRight: 6 }}>← STREAM</button>
            <span style={{ color: '#2dd4bf' }}>{selectedThread!.label.slice(0, 32)}</span>
          </>
          if (isCountry) panelTitle = <>
            <button className="drill-back-btn" onClick={handleStreamBack} style={{ fontSize: 13, marginRight: 6 }}>{backLabel}</button>
            <span style={{ color: '#94a3b8' }}>{selectedCountryName}</span>
          </>
          if (isPerson) panelTitle = <>
            <button className="drill-back-btn" onClick={handleStreamBack} style={{ fontSize: 13, marginRight: 6 }}>← STREAM</button>
            <span style={{ color: '#a78bfa' }}>{focus.value}</span>
          </>
          if (isPublicAttention) panelTitle = <>
            <button className="drill-back-btn" onClick={closeAll} style={{ fontSize: 13, marginRight: 6 }}>← STREAM</button>
            <span style={{ color: '#2dd4bf' }}>{selectedPublicAttention!.title.slice(0, 28)}</span>
          </>
          if (isChokepoint) panelTitle = <>
            <button className="drill-back-btn" onClick={() => setSelectedChokepoint(null)} style={{ fontSize: 13, marginRight: 6 }}>← STREAM</button>
            <span style={{ color: '#2dd4bf' }}>{selectedChokepoint!.name}</span>
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
                {isPerson ? (
                  <EntityPanel inline focusType="person" focusValue={focus.value!} timeRange={timeRange}
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
                    timeRange={timeRange}
                    onClose={closeAll}
                    onThemeSelect={(theme, attentionContext) => handleThemeSelect(theme, undefined, undefined, attentionContext)}
                    onCountrySelect={(code) => { handleCountryClick(code); setMapFlyCountry(code) }}
                  />
                ) : isThread ? (
                  <ThreadFocusPanel
                    thread={selectedThread!}
                    hours={timeRangeToHours(timeRange)}
                    onClose={closeAll}
                    onCountrySelect={(code) => { handleCountryClick(code); setMapFlyCountry(code) }}
                    onSourceClick={(source) => setSelectedSourceProfile(source)}
                  />
                ) : isCountry ? (
                  <CountryBrief inline
                    countryCode={selectedCountryCode!}
                    countryName={selectedCountryName}
                    timeWindow={timeRangeToHours(timeRange)}
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
                    hours={timeRangeToHours(timeRange)}
                    onClose={closeAll}
                    onThemeSelect={(theme, attentionContext) => handleThemeSelect(theme, undefined, undefined, attentionContext ?? selectedTheme!.originAttention)}
                    onCountryCardClick={(code, name) => { setMapFlyCountry(code); setRightPanelThemeCountry({ code, name }) }}
                    onPersonClick={(name) => {
                      setFocus('person', name, name)
                      setMapFlyCountry(null)
                    }}
                    onSourceClick={(source) => setSelectedSourceProfile(source)}
                    onCompareClick={(other) => setCompareTheme({ a: selectedTheme!.theme, b: other })}
                  />
                ) : isChokepoint ? (
                  <ChokepointPanel
                    chokepoint={selectedChokepoint!}
                    vesselCount={chokepointCounts[selectedChokepoint!.id] || 0}
                    hours={timeRangeToHours(timeRange)}
                    onCountryClick={(code) => {
                      setPrevStreamCtx({ type: 'chokepoint', cp: selectedChokepoint! })
                      handleCountryClick(code); setMapFlyCountry(code)
                    }}
                  />
                ) : (
                  <SignalStream />
                )}
              </div>
            </div>
          )
        })()}

        {/* Panel 3: NARRATIVE THREADS — always visible, reactive to focus context */}
        <div className="terminal-panel threads" data-tour="threads">
          <div className="panel-header">
            <div className="panel-header-title-wrap">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                NARRATIVE THREADS
                <PanelHelpButton panel="narrative-threads" />
              </span>
              <span className="panel-subtitle">how topics spread over time</span>
            </div>
          </div>
          <div className="panel-content">
            <PanelErrorBoundary panelName="NARRATIVE THREADS">
              <NarrativeThreads
                activeThreadId={selectedTheme?.thread?.thread_id ?? selectedThread?.thread_id}
                onThreadSelect={(thread) => {
                  const target = resolveThreadThemeTarget(thread)
                  setSelectedTheme(target ? {
                    theme: target.theme,
                    originCountry: target.originCountry,
                    originCountryName: target.originCountryName,
                    thread: target.thread,
                  } : null)
                  setTheme(null)
                  setSelectedCountry(null)
                  setSelectedCountryCode(null)
                  setSelectedPublicAttention(null)
                  setSelectedChokepoint(null)
                  setRightPanelThemeCountry(null)
                  setThemeBackStack([])
                  clearFocus()
                  setSelectedThread(target ? null : thread)
                  if (thread.top_countries[0]) setMapFlyCountry(thread.top_countries[0])
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

        {/* Panel 4: CORRELATION MATRIX */}
        <div className="terminal-panel matrix">
          <div className="panel-header">
            <div className="panel-header-title-wrap">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                CORRELATION MATRIX
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

        {/* Panel 5+6: BOTTOM DOCK — tabbed (#228 §3). On 16:9 laptops the old
            two-panel bottom row gave three interactive sections ~132px each;
            tabs give the active section the full row. */}
        <div className="terminal-panel dock" data-tour="anomaly-attention">
          <div className="panel-header dock-header">
            <div className="dock-tabs">
              <button
                className={`dock-tab ${dockTab === 'anomaly' ? 'active' : ''}`}
                onClick={() => setDockTab('anomaly')}
                data-tip="Geo alerts and public attention vs 7-day baseline"
              >
                ANOMALY ALERT
              </button>
              <button
                className={`dock-tab ${dockTab === 'sources' ? 'active' : ''}`}
                onClick={() => setDockTab('sources')}
                data-tip="Diversity of information sources"
              >
                SOURCE INTEGRITY
              </button>
            </div>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
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
                    selectedTheme?.thread?.label
                    ?? selectedTheme?.theme
                    ?? selectedThread?.label
                    ?? selectedPublicAttention?.title
                    ?? selectedChokepoint?.name
                    ?? null
                  }
                />
              </PanelErrorBoundary>
            )}
          </div>
        </div>
      </div>

      {/* Mobile L2 bottom navigation — one full-screen surface at a time */}
      {isMobile && (
        <nav className="mobile-tabbar" aria-label="Console sections" data-tour="mobile-tabs">
          <button className={mobileTab === 'map' ? 'active' : ''} onClick={() => setMobileTab('map')}>
            <span className="mobile-tab-glyph">◍</span>Map
          </button>
          <button className={mobileTab === 'threads' ? 'active' : ''} onClick={() => setMobileTab('threads')}>
            <span className="mobile-tab-glyph">⌗</span>Threads
          </button>
          <button className={mobileTab === 'stream' ? 'active' : ''} onClick={() => setMobileTab('stream')}>
            <span className="mobile-tab-glyph">≋</span>Stream
          </button>
          <button className={mobileTab === 'pulse' ? 'active' : ''} onClick={() => setMobileTab('pulse')}>
            <span className="mobile-tab-glyph">◎</span>Pulse
          </button>
        </nav>
      )}

      {/* Hover Tooltip */}
      <MapTooltip tooltip={tooltip} />

      {/* T3.3 conflict-event focus — the event is the subject, country is context */}
      {selectedConflictEvent && (
        <ConflictEventPanel
          event={selectedConflictEvent}
          timeRangeHours={timeRangeToHours(timeRange)}
          onClose={() => setSelectedConflictEvent(null)}
          onThemeSelect={(threadId) => { setSelectedConflictEvent(null); handleThemeSelect(threadId) }}
          onCountrySelect={(code) => { setSelectedConflictEvent(null); handleCountryClick(code); setMapFlyCountry(code) }}
        />
      )}

      {/* Briefing Modal */}
      {showBriefing && (
        <Briefing
          hours={timeRangeToHours(timeRange)}
          prefetchedData={prefetchedHours === timeRangeToHours(timeRange) ? prefetchedBriefing : null}
          prefetchedInsight={prefetchedHours === timeRangeToHours(timeRange) ? prefetchedInsight : null}
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
            <button className="workbench-overlay-close" onClick={() => setWorkbenchOpen(false)}>×</button>
          </div>
          <div className="workbench-overlay-body">
            <div className="workbench-overlay-left">
              <WorkbenchPanel
                refreshToken={wbRefresh}
                onOpenThread={handleResearchOpenThread}
                onOpenCountry={handleResearchOpenCountry}
                onStartInvestigation={(q) => setResearchQuery(q)}
              />
            </div>
            <div className="workbench-overlay-right">
              {researchQuery ? (
                <ResearchPlanPanel
                  query={researchQuery}
                  hours={Math.max(timeRangeToHours(timeRange), 168)}
                  onOpenThread={handleResearchOpenThread}
                  onOpenCountry={handleResearchOpenCountry}
                  onBranchQuery={(q) => setResearchQuery(q)}
                  onPinsChanged={() => setWbRefresh(t => t + 1)}
                />
              ) : (
                <div className="workbench-overlay-hint">
                  Create or select an investigation, then its research plan appears here.
                  Anchors open real Atlas surfaces; pin the useful ones.
                </div>
              )}
            </div>
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
          hours={timeRangeToHours(timeRange)}
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
          hours={timeRangeToHours(timeRange)}
          onClose={() => setSelectedSourceProfile(null)}
          onThemeSelect={(theme) => { setSelectedSourceProfile(null); handleThemeSelect(theme); }}
          onCountrySelect={(code) => { setSelectedSourceProfile(null); handleCountryClick(code); setMapFlyCountry(code); }}
        />
      )}

      {/* The force-graph workspace is a desktop power surface (pointer pan/zoom);
          hide it on phones — pins/investigations stay reachable via WORKBENCH. */}
      {!isMobile && (
      <PanelErrorBoundary panelName="WORKSPACE">
      <InvestigationWorkspace
        onNavigate={(params) => {
          const next = new URLSearchParams(params.replace(/^\?/, ''))
          const source = next.get('source')
          const theme = next.get('theme')
          const country = next.get('country')
          const person = next.get('person')
          const attention = next.get('attention')

          if (attention) {
            handlePublicAttentionSelect({ title: attention })
            return
          }
          if (source) {
            setSelectedSourceProfile(source)
            return
          }
          if (theme && country) {
            handleThemeSelect(theme, country, country, attention ? { title: attention } : undefined)
            setMapFlyCountry(country)
            return
          }
          if (theme) {
            handleThemeSelect(theme, undefined, undefined, attention ? { title: attention } : undefined)
            return
          }
          if (country) {
            handleCountryClick(country)
            setMapFlyCountry(country)
            return
          }
          if (person) {
            setFocus('person', person, person)
            setMapFlyCountry(null)
            return
          }

          window.location.search = params;
        }}
      />
      </PanelErrorBoundary>
      )}

      {comparePerson && (
        <PersonCompare
          personA={comparePerson.a}
          personB={comparePerson.b}
          timeRange={timeRange}
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
          hours={timeRangeToHours(timeRange)}
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
        onOpenWorkspace={() => setIsOpen(true)}
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
            <AppContent />
          </WorkspaceProvider>
        </CrisisProvider>
      </FocusDataProvider>
    </FocusProvider>
  )
}

export default App
