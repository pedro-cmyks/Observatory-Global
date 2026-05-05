import React, { useState, useEffect, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import MapGL from 'react-map-gl/maplibre'
import type { MapRef } from 'react-map-gl/maplibre'
import { DeckGLOverlay } from './components/DeckGLOverlay'
import { ScatterplotLayer, ArcLayer } from '@deck.gl/layers'
import 'maplibre-gl/dist/maplibre-gl.css'
import './App.css'
import { calculateNodeRadius, getThemedArcColors } from './lib/mapUtils'
import { createTerminatorLayer } from './layers/TerminatorLayer'
import { useCrisis } from './contexts/CrisisContext'
import { useTheme } from './contexts/ThemeContext'
import { SearchBar } from './components/SearchBar'
import { Briefing } from './components/Briefing'
import { ThemeDetail } from './components/ThemeDetail'
import { CountryBrief } from './components/CountryBrief'
import { FocusProvider, useFocus } from './contexts/FocusContext'
import { FocusDataProvider, useFocusData } from './contexts/FocusDataContext'

import { MapTooltip, type TooltipData } from './components/MapTooltip'
import { CrisisProvider } from './contexts/CrisisContext'
import { SettingsPanel } from './components/SettingsPanel'
import { CountryThemePanel } from './components/CountryThemePanel'
import { EntityPanel } from './components/EntityPanel'
import { TIME_RANGE_OPTIONS, TIME_RANGE_LABELS, timeRangeToHours } from './lib/timeRanges'
import { Globe, ClipboardList } from 'lucide-react'
import { CHOKEPOINTS, haversineKm, getChokepointVesselCounts, getCountryChokepoints, type Chokepoint } from './lib/chokepoints'

// Terminal Panels
import { NarrativeThreads } from './components/NarrativeThreads'
import DiscoveryPanel from './components/DiscoveryPanel'
import { CorrelationMatrix } from './components/CorrelationMatrix'
import { AnomalyPanel } from './components/AnomalyPanel'
import { SourceIntegrityPanel } from './components/SourceIntegrityPanel'
import { PanelErrorBoundary } from './components/PanelErrorBoundary'
import { ChokepointPanel } from './components/ChokepointPanel'
import { AtlasLoader } from './components/AtlasLoader'
import { useUrlSync } from './hooks/useUrlSync'







interface Flow {
  source: [number, number]
  target: [number, number]
  sourceCountry: string
  targetCountry: string
  strength: number
}

interface CountryDetail {
  countryCode: string
  name?: string
  totalSignals: number
  sentiment: number
  themes: { name: string; count: number }[]
  sources: { name: string; count: number }[]
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

// Clickable info badge that shows a styled popup explaining what each panel does
function InfoBadge({ text }: { text: string }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <span ref={ref} style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(o => !o) }}
        style={{
          background: 'none', border: '1px solid rgba(100,116,139,0.35)',
          borderRadius: '50%', width: '14px', height: '14px',
          cursor: 'pointer', padding: 0, color: '#64748b',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '9px', lineHeight: 1, flexShrink: 0
        }}
        title="What does this panel show?"
      >?</button>
      {open && (
        <div style={{
          position: 'absolute', top: '18px', left: '50%', transform: 'translateX(-50%)',
          width: '230px', background: '#1a2332', border: '1px solid rgba(100,116,139,0.3)',
          borderRadius: '6px', padding: '10px 12px', fontSize: '11px', color: '#94a3b8',
          lineHeight: '1.6', zIndex: 9999, boxShadow: '0 8px 24px rgba(0,0,0,0.7)',
          pointerEvents: 'auto'
        }}>
          {text}
        </div>
      )}
    </span>
  )
}

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

// Extracted layer building function to prevent re-renders breaking Layer IDs
function buildLayers({
  enhancedNodes, visibleFlows, showFlows,
  isGlobe, sizeBoost, themeId, crisisEnabled, showTerminator,
  selectedCountryCode, timeRange, showAircraft, aircraftData,
  showVessels, vesselData, activeChokepoints, themeFocused, acledConflicts
}: any) {
  const terminatorLayer = createTerminatorLayer({
    visible: showTerminator && !crisisEnabled,
    opacity: 0.5,
  })

  const hasActiveCp = activeChokepoints.length > 0

  return [
    // Terminator layer (bottommost)
    terminatorLayer,

    // Chokepoint zones — geographic rings at strategic straits
    showVessels && new ScatterplotLayer({
      id: `chokepoint-zones-${isGlobe ? 'globe' : 'flat'}`,
      data: CHOKEPOINTS,
      getPosition: (d: Chokepoint) => [d.lon, d.lat],
      getRadius: (d: Chokepoint) => d.radiusKm * 1000,
      radiusUnits: 'meters',
      getFillColor: (d: Chokepoint) => {
        if (activeChokepoints.includes(d.id)) return [0, 220, 200, 18]
        return hasActiveCp ? [80, 80, 80, 6] : [0, 180, 160, 10]
      },
      getLineColor: (d: Chokepoint) => {
        if (activeChokepoints.includes(d.id)) return [0, 255, 210, 160]
        return hasActiveCp ? [80, 80, 80, 20] : [0, 180, 160, 45]
      },
      stroked: true,
      lineWidthMinPixels: 1,
      lineWidthMaxPixels: 2,
      pickable: true,
      updateTriggers: {
        getFillColor: [activeChokepoints],
        getLineColor: [activeChokepoints],
      },
    }),

    // Aircraft Layer — altitude-coded; filtered to focused country or cruise-only globally
    showAircraft && new ScatterplotLayer({
      id: `aircraft-${isGlobe ? 'globe' : 'flat'}`,
      data: aircraftData,
      getPosition: (d: any) => [d.longitude, d.latitude, d.baro_altitude || 0],
      getFillColor: (d: any) => {
        const alt = d.baro_altitude || 0
        if (alt > 10000) return [255, 255, 255, 200]  // cruise: white
        if (alt > 5000) return [255, 210, 80, 180]  // mid: amber
        return [255, 140, 40, 160]  // low: orange
      },
      getRadius: (d: any) => (d.baro_altitude || 0) > 10000 ? 2 : 3,
      radiusUnits: 'pixels',
      radiusMinPixels: 1,
      radiusMaxPixels: 4,
      pickable: true,
    }),

    // Vessel Layer — maritime traffic near geopolitical chokepoints
    showVessels && new ScatterplotLayer({
      id: `vessels-${isGlobe ? 'globe' : 'flat'}`,
      data: vesselData,
      getPosition: (d: any) => [d.longitude, d.latitude, 0],
      getFillColor: (d: any) => d.speed > 10 ? [0, 220, 200, 230] : [0, 180, 160, 150],
      getRadius: (d: any) => d.speed > 14 ? 4 : 3,
      radiusUnits: 'pixels',
      radiusMinPixels: 2,
      radiusMaxPixels: 5,
      pickable: true,
    }),

    // Flow arcs
    (showFlows || !!selectedCountryCode || themeFocused) && new ArcLayer({
      id: `flows-${isGlobe ? 'globe' : 'flat'}`,
      data: visibleFlows,
      getSourcePosition: (d: Flow) => d.source,
      getTargetPosition: (d: Flow) => d.target,
      getSourceColor: (d: Flow) => getThemedArcColors(themeId, d.strength).source,
      getTargetColor: (d: Flow) => getThemedArcColors(themeId, d.strength).target,
      getWidth: () => 1.5,
      opacity: 0.4,
      greatCircle: true,
      pickable: true,
      updateTriggers: {
        getSourceColor: [themeId],
        getTargetColor: [themeId],
        data: [timeRange]
      },
    }),

    // Anomaly Pulse Ring
    new ScatterplotLayer({
      id: `nodes-anomaly-pulse-${isGlobe ? 'globe' : 'flat'}`,
      data: enhancedNodes.filter((n: any) => n.isAnomaly),
      getPosition: (d: any) => [d.lon, d.lat],
      getRadius: (d: any) => calculateNodeRadius(d.signalCount, sizeBoost) * 1.5,
      getFillColor: [239, 68, 68, 0],
      getLineColor: [239, 68, 68, 255],
      lineWidthMinPixels: 2,
      stroked: true,
      pickable: false,
      updateTriggers: {
        getRadius: [sizeBoost],
      },
    }),

    // ACLED Conflicts Layer — Renders intense 'X' or 'Pulse' at conflict sites
    acledConflicts && acledConflicts.length > 0 && new ScatterplotLayer({
      id: `acled-conflicts-${isGlobe ? 'globe' : 'flat'}`,
      data: acledConflicts,
      getPosition: (d: any) => [d.location.longitude, d.location.latitude],
      // Intensity based on fatalities
      getRadius: (d: any) => Math.min(Math.max(4, Math.sqrt(d.fatalities || 1) * 3), 15) * sizeBoost,
      getFillColor: (d: any) => {
        // Red for battles/explosions, Orange for riots
        if (d.type.includes('Battle') || d.type.includes('Explosion')) return [239, 68, 68, 220]
        if (d.type.includes('Riot') || d.type.includes('Protest')) return [249, 115, 22, 200]
        return [234, 179, 8, 180] // Yellow for other
      },
      getLineColor: [255, 255, 255, 80],
      stroked: true,
      lineWidthMinPixels: 1,
      radiusUnits: 'pixels',
      radiusMinPixels: 4,
      pickable: true,
      updateTriggers: {
        getRadius: [sizeBoost]
      }
    }),

    // Node dots removed — country territory click via Mapbox fill layer handles selection
  ].filter(Boolean)
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

function AppContent() {
  const navigate = useNavigate()

  // Sync filter state ↔ URL params for shareable links
  useUrlSync()

  // State
  const [selectedCountry, setSelectedCountry] = useState<CountryDetail | null>(null)
  const [selectedCountryCode, setSelectedCountryCode] = useState<string | null>(null)
  const [selectedTheme, setSelectedTheme] = useState<{ theme: string, originCountry?: string, originCountryName?: string } | null>(null)
  const [selectedChokepoint, setSelectedChokepoint] = useState<Chokepoint | null>(null)
  const [rightPanelThemeCountry, setRightPanelThemeCountry] = useState<{ code: string, name: string } | null>(null)
  // One-level back navigation for the stream panel
  type PrevCtx = { type: 'chokepoint'; cp: Chokepoint } | { type: 'theme'; theme: string; originCountry?: string; originCountryName?: string }
  const [prevStreamCtx, setPrevStreamCtx] = useState<PrevCtx | null>(null)
  const [showBriefing, setShowBriefing] = useState(false)
  // const [timeWindow, setTimeWindow] = useState(24) // Replaced by context
  const [viewState, setViewState] = useState(INITIAL_VIEW)
  const [tooltip, setTooltip] = useState<TooltipData | null>(null)

  const mapRef = useRef<MapRef>(null)
  const isGlobe = false
  const hasAutoFocused = useRef(false)

  const [showWelcome, setShowWelcome] = useState(
    () => sessionStorage.getItem('atlas-welcome-seen') !== 'true'
  )
  const dismissWelcome = (openBrief = false) => {
    setShowWelcome(false)
    sessionStorage.setItem('atlas-welcome-seen', 'true')
    if (openBrief) setShowBriefing(true)
  }
  // Focus hook for click-to-focus
  const { setFocus, focus, clearFocus, filter, setTheme, mapFlyCountry, setMapFlyCountry } = useFocus()

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
  // Tracks when the 13MB GeoJSON source has actually finished loading
  const [heatSourceReady, setHeatSourceReady] = useState(false)
  // First-time affordance hint on the map
  const [showMapHint, setShowMapHint] = useState(false)

  // Settings toggles
  const [showTerminator, setShowTerminator] = useState(false)
  const [sizeBoost, setSizeBoost] = useState(false)
  const [showFlows, setShowFlows] = useState(false)

  // Fetch country detail
  const fetchCountryDetail = async (countryCode: string) => {
    try {
      const hours = timeRangeToHours(timeRange)
      const res = await fetch(`/api/v2/country/${countryCode}?hours=${hours}`)
      const data = await res.json()
      setSelectedCountry(data)
    } catch (error) {
      console.error('Failed to fetch country detail:', error)
    }
  }

  // Click handlers
  const handleCountryClick = (countryCode: string) => {
    setSelectedCountryCode(countryCode)
    setShowFlows(true)
    fetchCountryDetail(countryCode)
    // Dismiss the affordance hint on first country click
    setShowMapHint(false);
    sessionStorage.setItem('atlas-map-hinted', 'true');
  }

  // Theme selection handlers
  const handleThemeSelect = (theme: string, countryCode?: string, countryName?: string) => {
    setSelectedTheme({ theme, originCountry: countryCode, originCountryName: countryName })
    if (countryCode && countryName) {
      setRightPanelThemeCountry({ code: countryCode, name: countryName })
    } else {
      setRightPanelThemeCountry(null)
    }
  }

  // Focus-aware data from provider - auto-refetches when focus/range changes
  const { nodes, flows, unfilteredFlows, acledConflicts, loading, refetch, timeRange, setTimeRange } = useFocusData()

  // Auto-focus on hottest region at load
  useEffect(() => {
    if (nodes.length > 0 && !hasAutoFocused.current && mapReady) {
      hasAutoFocused.current = true
      const hottest = nodes.reduce((max, n) => (n.signalCount > max.signalCount ? n : max), nodes[0])
      mapRef.current?.getMap()?.flyTo({
        center: [hottest.lon, hottest.lat],
        zoom: 2.5,
        duration: 2500,
        essential: true
      })
    }
  }, [nodes, mapReady])

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

  // Open ThemeDetail when theme is focused via FocusContext (e.g. NarrativeThreads click)
  useEffect(() => {
    if (filter.theme && (!selectedTheme || selectedTheme.theme !== filter.theme)) {
      setSelectedTheme({ theme: filter.theme })
      setRightPanelThemeCountry(null)
    }
  }, [filter.theme])

  // Close CountryBrief when country focus is cleared externally (pill X button)
  useEffect(() => {
    if (!filter.country && selectedCountryCode) {
      setSelectedCountry(null)
      setSelectedCountryCode(null)
      setShowFlows(false)
      setRightPanelThemeCountry(null)
    }
  }, [filter.country])

  // Modal Stack Logic (Escape key)
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showBriefing) {
          setShowBriefing(false)
        } else if (selectedTheme) {
          setSelectedTheme(null)
          setTheme(null)
        } else if (selectedCountry || selectedCountryCode) {
          setSelectedCountry(null)
          setSelectedCountryCode(null)
          setShowFlows(false)
          clearFocus()
        }
      }
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [showBriefing, selectedTheme, selectedCountry])

  // Auto-refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(refetch, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [refetch])

  // Zoom-adaptive flow limiting to reduce visual clutter
  const visibleFlows = useMemo(() => {
    // Determine the base set of flows:
    // If we have a country selected, use the unfiltered map-level flows to ensure
    // we see all connections for that country, even if nodes are focus-filtered.
    let baseFlows = selectedCountryCode ? (unfilteredFlows || flows) : flows;
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

  // Merge anomaly data into nodes for coloring and pulse — capped at 100
  const enhancedNodes = useMemo(() => {
    const anomalyMap = new Map(anomalies.map((a: any) => [a.country_code, a]))
    return nodes.slice(0, 100).map(n => {
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

  // Update MapLibre native country heat feature-states when node data changes
  // Must wait for heatSourceReady (GeoJSON downloaded), not just mapReady
  useEffect(() => {
    const map = mapRef.current?.getMap()
    if (!map || !heatSourceReady || enhancedNodes.length === 0) return

    const currentCodes = new Set<string>()
    const counts = enhancedNodes.map(n => n.signalCount)
    const logMin = Math.log(Math.min(...counts) + 1)
    const logMax = Math.log(Math.max(...counts, 1) + 1)
    const logRange = Math.max(logMax - logMin, 0.001)

    enhancedNodes.forEach(node => {
      // Range-normalized: lowest active country = 0.15, highest = 1.0
      // Ensures all 36+ countries show visible color regardless of volume gap
      const normalized = (Math.log(node.signalCount + 1) - logMin) / logRange
      const intensity = 0.15 + normalized * 0.85
      map.setFeatureState(
        { source: 'country-heat', id: node.id },
        { intensity }
      )
      currentCodes.add(node.id)
    })

    // Clear countries no longer in the data
    prevHeatCountries.current.forEach(code => {
      if (!currentCodes.has(code)) {
        map.setFeatureState(
          { source: 'country-heat', id: code },
          { intensity: 0 }
        )
      }
    })

    prevHeatCountries.current = currentCodes
  }, [enhancedNodes, heatSourceReady])

  // Toggle country heat layer visibility when GLOW button is pressed
  useEffect(() => {
    const map = mapRef.current?.getMap()
    if (!map || !mapReady) return

    if (map.getLayer('country-heat-fill')) {
      map.setPaintProperty('country-heat-fill', 'fill-opacity', showHeatmap ? 0.3 : 0)
    }
    if (map.getLayer('country-heat-glow')) {
      map.setLayoutProperty('country-heat-glow', 'visibility', showHeatmap ? 'visible' : 'none')
    }
  }, [showHeatmap, mapReady])

  // Memoize completely stabilized array block to crush Globe re-render flicker
  const layers = useMemo(() => {
    const builtLayers = buildLayers({
      enhancedNodes, visibleFlows, showFlows,
      isGlobe, sizeBoost, themeId, crisisEnabled, showTerminator,
      selectedCountryCode, timeRange,
      showAircraft, aircraftData: filteredAircraftData,
      showVessels, vesselData,
      activeChokepoints,
      themeFocused: !!filter.theme,
      acledConflicts
    })
    return builtLayers
  }, [enhancedNodes, visibleFlows, showFlows, isGlobe, sizeBoost, themeId, crisisEnabled, showTerminator, selectedCountryCode, timeRange, showAircraft, filteredAircraftData, showVessels, vesselData, activeChokepoints, filter.theme, acledConflicts])

  // Total signals for stats
  const totalSignals = nodes.reduce((sum, n) => sum + n.signalCount, 0)

  // Prefetch briefing data so the modal opens instantly
  const [prefetchedBriefing, setPrefetchedBriefing] = useState<any>(null)
  const [prefetchedInsight, setPrefetchedInsight] = useState<string | null>(null)
  useEffect(() => {
    fetch('/api/v2/briefing?hours=24').then(r => r.json()).then(setPrefetchedBriefing).catch(() => { })
    fetch('/api/v2/briefing/insight?hours=24').then(r => r.json()).then(d => { if (d.insight) setPrefetchedInsight(d.insight) }).catch(() => { })
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

  // Affordance hint: show 2s after map is ready, skip if already seen this session
  useEffect(() => {
    if (!mapReady) return;
    if (sessionStorage.getItem('atlas-map-hinted') === 'true') return;
    const t = setTimeout(() => setShowMapHint(true), 2000);
    return () => clearTimeout(t);
  }, [mapReady]);

  return (
    <div className={`app ${crisisEnabled ? 'crisis-mode' : ''}`}>
      <AtlasLoader visible={!appReady} />
      {/* Command Bar */}
      <header className="command-bar">
        <div className="command-bar-left">
          <h1 className="brand" onClick={() => navigate('/')} style={{ cursor: 'pointer' }} title="Back to home"><Globe size={16} /> ATLAS</h1>
        </div>
        <div className="command-bar-center">
          <SearchBar
            onThemeSelect={handleThemeSelect}
            onCountrySelect={(code) => { handleCountryClick(code); setMapFlyCountry(code) }}
          />
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
        </div>
        <div className="command-bar-right">
          <div className="stats">
            {loading ? '...' : `${nodes.length} countries · ${totalSignals.toLocaleString()} signals`}
          </div>
          {/* <CrisisToggle /> - Hidden per visual clarity update */}
          <button className="cmd-btn" onClick={() => {
            setShowBriefing(true)
            setSelectedTheme(null)
          }}>
            <ClipboardList size={13} /> BRIEF
          </button>
          <SettingsPanel
            showTerminator={showTerminator}
            onToggleTerminator={setShowTerminator}
            sizeBoost={sizeBoost}
            onToggleSizeBoost={setSizeBoost}
          />
        </div>
      </header>

      <div className="terminal-layout">
        {/* Panel 1: GLOBAL RADAR */}
        <div className="terminal-panel radar">
          <div className="panel-header">
            <div className="panel-header-title-wrap">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                GLOBE
                <InfoBadge text="Narrative activity by country. Glowing areas show higher media volume. FLOW lines show information pathways between countries. PLANE and SHIPS show live real-world assets at strategic locations." />
              </span>
              <span className="panel-subtitle">narrative activity by country</span>
            </div>
            <div className="panel-header-controls">
              <button
                className={`layer-btn ${showHeatmap ? 'active' : ''}`}
                onClick={() => setShowHeatmap(!showHeatmap)}
              >
                GLOW
              </button>
              <button
                className={`layer-btn ${showFlows ? 'active' : ''}`}
                onClick={() => setShowFlows(!showFlows)}
              >
                FLOW
              </button>
              <button
                className={`layer-btn ${showAircraft ? 'active' : ''} ${showAircraft && aircraftError ? 'layer-btn-error' : ''}`}
                onClick={() => setShowAircraft(!showAircraft)}
                title={showAircraft && aircraftError ? 'No aircraft data available' : undefined}
              >
                PLANE {showAircraft && aircraftError && '⚠'}
              </button>
              <button
                className={`layer-btn ${showVessels ? 'active' : ''} ${activeChokepoints.length > 0 && !showVessels ? 'layer-btn-hint' : ''}`}
                onClick={() => setShowVessels(!showVessels)}
                title={
                  showVessels
                    ? `${vesselData.length} vessels at chokepoints${vesselConnected ? ' · live' : ' · connecting...'}`
                    : activeChokepoints.length > 0
                      ? `${activeChokepoints.length} relevant chokepoint(s) for this country`
                      : 'Show vessels near strategic chokepoints'
                }
              >
                SHIPS{showVessels && vesselData.length > 0 ? ` ${vesselData.length}` : ''}{showVessels && !vesselConnected ? ' ⏳' : ''}
              </button>
            </div>
          </div>
          <div className="panel-content" onClick={() => showWelcome && dismissWelcome()}>
            <MapErrorBoundary>
              <MapGL
                ref={mapRef}
                mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
                attributionControl={false}
                projection={isGlobe ? 'globe' : 'mercator'}
                {...viewState}
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
                  map.addLayer({
                    id: 'country-heat-fill',
                    type: 'fill',
                    source: 'country-heat',
                    paint: {
                      'fill-color': [
                        'interpolate', ['linear'],
                        ['coalesce', ['feature-state', 'intensity'], 0],
                        0, 'rgba(0, 0, 0, 0)',
                        0.05, 'rgba(15, 30, 90, 30)',
                        0.15, 'rgba(30, 55, 130, 50)',
                        0.35, 'rgba(170, 110, 30, 80)',
                        0.6, 'rgba(215, 70, 15, 110)',
                        1.0, 'rgba(235, 35, 10, 140)'
                      ],
                      'fill-opacity': 0.45
                    }
                  })

                  // Layer 2: Border glow — wide blurred line bleeds heat beyond borders
                  map.addLayer({
                    id: 'country-heat-glow',
                    type: 'line',
                    source: 'country-heat',
                    paint: {
                      'line-color': [
                        'interpolate', ['linear'],
                        ['coalesce', ['feature-state', 'intensity'], 0],
                        0, 'rgba(0, 0, 0, 0)',
                        0.05, 'rgba(20, 35, 100, 20)',
                        0.15, 'rgba(35, 60, 140, 40)',
                        0.35, 'rgba(190, 120, 30, 60)',
                        0.6, 'rgba(225, 75, 15, 90)',
                        1.0, 'rgba(245, 45, 10, 120)'
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

                  setMapReady(true)
                }}
              >
                <DeckGLOverlay
                  interleaved={true}
                  layers={layers}
                  getTooltip={({ object, layer }) => {
                    if (!object) return null
                    if (layer?.id?.startsWith('flows')) return null
                    if (layer?.id?.startsWith('chokepoint-zones')) {
                      const cp = object as Chokepoint
                      const count = chokepointCounts[cp.id] || 0
                      const active = activeChokepoints.includes(cp.id)
                      return `${cp.name}${active ? ' ◈' : ''}\n${count > 0 ? `${count} vessels tracked` : 'No vessels tracked yet'}\n${cp.description}`
                    }
                    if (layer?.id?.startsWith('aircraft')) {
                      const altFt = object.baro_altitude ? Math.round(object.baro_altitude / 0.3048) : 0
                      const hdg = object.true_track !== null ? `HDG: ${Math.round(object.true_track)}°` : ''
                      return `${object.callsign || 'Unknown'} (${object.origin_country})\nAlt: ${(object.baro_altitude || 0).toLocaleString()}m / ${altFt.toLocaleString()}ft\n${hdg}`
                    }
                    if (layer?.id?.startsWith('vessels')) {
                      const spd = object.speed != null ? `${object.speed} kn` : '—'
                      const hdg = object.heading && object.heading < 360 ? `  HDG: ${Math.round(object.heading)}°` : ''
                      return `${object.name}\nMMSI ${object.mmsi}  ·  ${spd}${hdg}`
                    }
                    return null
                  }}
                  onHover={(info: any) => {
                    if (!info.object) {
                      setTooltip(null)
                      return
                    }
                    if (info.layer?.id?.startsWith('flows')) {
                      setTooltip({ type: 'flow', x: info.x, y: info.y, data: info.object })
                    }
                  }}
                  onClick={(info: any) => {
                    if (!info.object || !info.layer) return
                    if (info.layer.id?.startsWith('chokepoint-zones')) {
                      const cp = info.object as Chokepoint
                      setSelectedChokepoint(prev => prev?.id === cp.id ? null : cp)
                      setMapFlyCountry(cp.primaryCountry)
                    }
                  }}
                />
              </MapGL>
              <div className="globe-vignette" />
              {showWelcome && (
                <div className="welcome-card" onClick={(e) => {
                  e.stopPropagation()
                  dismissWelcome(true)
                }}>
                  <span className="welcome-label">Atlas tracks how the world covers the news</span>
                  <span className="welcome-action">Click a country or search a topic →</span>
                  <button
                    className="welcome-close"
                    onClick={(e) => { e.stopPropagation(); dismissWelcome() }}
                    title="Dismiss"
                  >×</button>
                </div>
              )}
            </MapErrorBoundary>
          </div>
          {showMapHint && (
            <div className="map-hint" onClick={() => {
              setShowMapHint(false);
              sessionStorage.setItem('atlas-map-hinted', 'true');
            }}>
              ↑ click any country to explore
            </div>
          )}
        </div>

        {/* Panel 2: SIGNAL STREAM — the intel hub, swaps based on active context */}
        {(() => {
          const isPerson = focus.type === 'person' && !!focus.value
          const isCountry = !!selectedCountry && !isPerson
          const isTheme = !!selectedTheme && !isPerson && !isCountry
          const isChokepoint = !!selectedChokepoint && !isPerson && !isCountry && !isTheme
          const closeAll = () => { setSelectedTheme(null); setRightPanelThemeCountry(null); setSelectedCountry(null); setSelectedCountryCode(null); setShowFlows(false); setSelectedChokepoint(null); clearFocus(); setPrevStreamCtx(null); if (filter.theme) setTheme(null) }
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
            } else {
              closeAll()
            }
          }
          const backLabel = prevStreamCtx?.type === 'chokepoint'
            ? `← ${prevStreamCtx.cp.name}`
            : prevStreamCtx?.type === 'theme'
              ? `← ${prevStreamCtx.theme.replace(/_/g, ' ').slice(0, 20)}`
              : '← STREAM'
          const isBlankState = !isPerson && !isCountry && !isTheme && !isChokepoint
          let panelTitle = isBlankState ? (
            <>
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                WHAT'S HAPPENING
              </span>
              <span className="panel-subtitle">top topics right now — click to explore</span>
            </>
          ) : (
            <>
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                SIGNAL STREAM
                <InfoBadge text="Live feed of individual media signals from GDELT. Each row is a news article mentioning a geopolitical event. Click a country code or theme tag to filter the stream. Geopolitical signals appear first." />
              </span>
              <span className="panel-subtitle">live signals, last 15 min</span>
            </>
          )
          if (isTheme) panelTitle = <>
            <button className="drill-back-btn" onClick={handleStreamBack} style={{ fontSize: 13, marginRight: 6 }}>← STREAM</button>
            <span style={{ color: '#94a3b8' }}>{selectedTheme!.theme.replace(/_/g, ' ').slice(0, 26)}</span>
          </>
          if (isCountry) panelTitle = <>
            <button className="drill-back-btn" onClick={handleStreamBack} style={{ fontSize: 13, marginRight: 6 }}>{backLabel}</button>
            <span style={{ color: '#94a3b8' }}>{selectedCountry!.name || selectedCountry!.countryCode}</span>
          </>
          if (isPerson) panelTitle = <>
            <button className="drill-back-btn" onClick={handleStreamBack} style={{ fontSize: 13, marginRight: 6 }}>← STREAM</button>
            <span style={{ color: '#a78bfa' }}>{focus.value}</span>
          </>
          if (isChokepoint) panelTitle = <>
            <button className="drill-back-btn" onClick={() => setSelectedChokepoint(null)} style={{ fontSize: 13, marginRight: 6 }}>← STREAM</button>
            <span style={{ color: '#2dd4bf' }}>{selectedChokepoint!.name}</span>
          </>
          return (
            <div className="terminal-panel stream">
              <div className="panel-header">
                <div className="panel-header-title-wrap">{panelTitle}</div>
              </div>
              <div className="panel-content">
                {isPerson ? (
                  <EntityPanel inline focusType="person" focusValue={focus.value!} timeRange={timeRange}
                    onClose={closeAll}
                    onThemeSelect={(theme) => handleThemeSelect(theme)}
                    onCountrySelect={(code) => { clearFocus(); handleCountryClick(code); setMapFlyCountry(code) }}
                  />
                ) : isCountry ? (
                  <CountryBrief inline
                    countryCode={selectedCountry!.countryCode}
                    countryName={selectedCountry!.name || selectedCountry!.countryCode}
                    timeWindow={timeRangeToHours(timeRange)}
                    onClose={handleStreamBack}
                    onThemeSelect={(theme) => { handleThemeSelect(theme, selectedCountry!.countryCode, selectedCountry!.name || selectedCountry!.countryCode); setMapFlyCountry(selectedCountry!.countryCode) }}
                  />
                ) : isTheme ? (
                  <ThemeDetail
                    theme={selectedTheme!.theme}
                    originCountry={selectedTheme!.originCountry}
                    originCountryName={selectedTheme!.originCountryName}
                    hours={timeRangeToHours(timeRange)}
                    onClose={closeAll}
                    onThemeSelect={(theme) => handleThemeSelect(theme)}
                    onCountryCardClick={(code, name) => { setMapFlyCountry(code); setRightPanelThemeCountry({ code, name }) }}
                    onPersonClick={(name) => {
                      setFocus('person', name, name)
                      setMapFlyCountry(null)
                    }}
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
                  <DiscoveryPanel
                    hours={timeRangeToHours(timeRange)}
                    onThemeSelect={(code) => handleThemeSelect(code)}
                  />
                )}
              </div>
            </div>
          )
        })()}

        {/* Panel 3: NARRATIVE THREADS — always visible, reactive to focus context */}
        <div className="terminal-panel threads">
          <div className="panel-header">
            <div className="panel-header-title-wrap">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                NARRATIVE THREADS
                <InfoBadge text="Top geopolitical topics trending globally right now. Each thread shows signal volume, country spread, sentiment trend, and the key people being mentioned. Click any thread to open a full topic breakdown." />
              </span>
              <span className="panel-subtitle">how topics spread over time</span>
            </div>
          </div>
          <div className="panel-content">
            <PanelErrorBoundary panelName="NARRATIVE THREADS">
              <NarrativeThreads />
            </PanelErrorBoundary>
          </div>
        </div>

        {/* Panel 4: CORRELATION MATRIX */}
        <div className="terminal-panel matrix">
          <div className="panel-header">
            <div className="panel-header-title-wrap">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                CORRELATION MATRIX
                <InfoBadge text="Shows how strongly pairs of countries share the same narratives. Brighter green = stronger co-coverage of the same topic. Switch between Country×Country and Theme×Theme views." />
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

        {/* Panel 5: ANOMALY ALERT */}
        <div className="terminal-panel anomaly">
          <div className="panel-header">
            <div className="panel-header-title-wrap">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                ANOMALY ALERT
                <InfoBadge text="Detects statistical spikes in media volume. A country or theme is flagged when its current signal count is significantly above its 7-day rolling baseline (z-score threshold). Also tracks global theme-level surges." />
              </span>
              <span className="panel-subtitle">unusual activity vs 7-day baseline</span>
            </div>
          </div>
          <div className="panel-content">
            <PanelErrorBoundary panelName="ANOMALY ALERT">
              <AnomalyPanel />
            </PanelErrorBoundary>
          </div>
        </div>

        {/* Panel 6: SOURCE INTEGRITY */}
        <div className="terminal-panel integrity">
          <div className="panel-header">
            <div className="panel-header-title-wrap">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                SOURCE INTEGRITY
                <InfoBadge text="Monitors quality and diversity of active data sources. High Top Source Share means one outlet is dominating the feed (potential bias). Quality score is based on allowlisted vs unknown sources." />
              </span>
              <span className="panel-subtitle">diversity of information sources</span>
            </div>
          </div>
          <div className="panel-content">
            <PanelErrorBoundary panelName="SOURCE INTEGRITY">
              <SourceIntegrityPanel />
            </PanelErrorBoundary>
          </div>
        </div>
      </div>

      {/* Hover Tooltip */}
      <MapTooltip tooltip={tooltip} />

      {/* Briefing Modal */}
      {showBriefing && (
        <Briefing
          hours={timeRangeToHours(timeRange)}
          prefetchedData={prefetchedBriefing}
          prefetchedInsight={prefetchedInsight}
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
    </div>
  )
}

// Main App with providers
function App() {
  return (
    <FocusProvider>
      <FocusDataProvider>
        <CrisisProvider>
          <AppContent />
        </CrisisProvider>
      </FocusDataProvider>
    </FocusProvider>
  )
}

export default App
