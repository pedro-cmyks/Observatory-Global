import React, { useState, useEffect, useMemo, useRef } from 'react'
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
import { FocusIndicator } from './components/FocusIndicator'
import { MapTooltip, type TooltipData } from './components/MapTooltip'
import { CrisisProvider } from './contexts/CrisisContext'
import { SettingsPanel } from './components/SettingsPanel'
import { TIME_RANGE_OPTIONS, TIME_RANGE_LABELS, timeRangeToHours } from './lib/timeRanges'
import { Globe, ClipboardList } from 'lucide-react'

// Terminal Panels
import { SignalStream } from './components/SignalStream'
import { NarrativeThreads } from './components/NarrativeThreads'
import { CorrelationMatrix } from './components/CorrelationMatrix'
import { AnomalyPanel } from './components/AnomalyPanel'
import { SourceIntegrityPanel } from './components/SourceIntegrityPanel'
import { PanelErrorBoundary } from './components/PanelErrorBoundary'







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
  enhancedNodes, visibleFlows, showNodes, showFlows,
  isGlobe, sizeBoost, themeId, crisisEnabled, showTerminator,
  selectedCountryCode, timeRange
}: any) {
  const terminatorLayer = createTerminatorLayer({
    visible: showTerminator && !crisisEnabled,
    opacity: 0.5,
  })

  return [
    // Terminator layer (bottommost)
    terminatorLayer,

    // Country heat fill + blur is handled by MapLibre native layers (not deck.gl)
    // See handleMapLoad() and useEffect for feature-state updates

    // Flow arcs
    (showFlows || !!selectedCountryCode) && new ArcLayer({
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

    // Core node (solid, pickable)
    showNodes && new ScatterplotLayer({
      id: `nodes-core-${isGlobe ? 'globe' : 'flat'}`,
      data: enhancedNodes,
      getPosition: (d: any) => [d.lon, d.lat],
      getRadius: (d: any) => calculateNodeRadius(d.signalCount, sizeBoost),
      getFillColor: () => [220, 230, 255, 220],
      getLineColor: [255, 255, 255, 180],
      lineWidthMinPixels: 1.5,
      stroked: true,
      pickable: true,
      radiusMinPixels: 4,
      radiusMaxPixels: 14,
      updateTriggers: {
        getRadius: [sizeBoost]
      },
      transitions: {
        getRadius: 300
      }
    })
  ].filter(Boolean)
}

function AppContent() {
  // State
  const [selectedCountry, setSelectedCountry] = useState<CountryDetail | null>(null)
  const [selectedCountryCode, setSelectedCountryCode] = useState<string | null>(null)
  const [selectedTheme, setSelectedTheme] = useState<{ theme: string, country?: string } | null>(null)
  const [showBriefing, setShowBriefing] = useState(false)
  // const [timeWindow, setTimeWindow] = useState(24) // Replaced by context
  const [viewState, setViewState] = useState(INITIAL_VIEW)
  const [tooltip, setTooltip] = useState<TooltipData | null>(null)

  // Globe mapping
  const mapRef = useRef<MapRef>(null)
  const [isGlobe, setIsGlobe] = useState(() => localStorage.getItem('atlas-globe-mode') === 'true')
  const hasAutoFocused = useRef(false)

  const toggleGlobe = () => {
    const next = !isGlobe
    setIsGlobe(next)
    
    // Smoothly adjust view state for the mode
    setViewState(prev => ({
      ...prev,
      zoom: next ? 1.8 : 1.5,
      pitch: next ? 15 : 0
    }))
    
    localStorage.setItem('atlas-globe-mode', String(next))
  }

  // Focus hook for click-to-focus
  const { setFocus } = useFocus()

  // Theme for layer styling
  const { themeId } = useTheme()

  // Layer visibility
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [showNodes, setShowNodes] = useState(true)

  // Map readiness gate — prevents DeckGL from crashing before WebGL context is ready
  const [mapReady, setMapReady] = useState(false)
  // Tracks when the 13MB GeoJSON source has actually finished loading
  const [heatSourceReady, setHeatSourceReady] = useState(false)

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
  }

  // Theme selection handlers
  const handleThemeSelect = (theme: string, country?: string) => {
    setSelectedTheme({ theme, country })
  }

  // Focus-aware data from provider - auto-refetches when focus/range changes
  const { nodes, flows, unfilteredFlows, loading, refetch, timeRange, setTimeRange } = useFocusData()

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

  // Modal Stack Logic (Escape key)
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showBriefing) {
          setShowBriefing(false)
        } else if (selectedTheme) {
          setSelectedTheme(null)
        } else if (selectedCountry || selectedCountryCode) {
          setSelectedCountry(null)
          setSelectedCountryCode(null)
          setShowFlows(false)
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
    const maxSignals = Math.max(...enhancedNodes.map(n => n.signalCount), 1)

    enhancedNodes.forEach(node => {
      // Log-normalized intensity: spreads the scale so mid-range countries are visible
      const intensity = Math.min(Math.log(node.signalCount + 1) / Math.log(maxSignals + 1), 1)
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
    const vis = showHeatmap ? 'visible' : 'none'
    if (map.getLayer('country-heat-fill')) {
      map.setLayoutProperty('country-heat-fill', 'visibility', vis)
    }
    if (map.getLayer('country-heat-glow')) {
      map.setLayoutProperty('country-heat-glow', 'visibility', vis)
    }
  }, [showHeatmap, mapReady])

  // Memoize completely stabilized array block to crush Globe re-render flicker
  const layers = useMemo(() => {
    const builtLayers = buildLayers({
      enhancedNodes, visibleFlows, showNodes, showFlows,
      isGlobe, sizeBoost, themeId, crisisEnabled, showTerminator,
      selectedCountryCode, timeRange
    })
    console.log('[DEBUG] buildLayers output count:', builtLayers.length, { mapReady, enhancedNodesCount: enhancedNodes.length })
    return builtLayers
  }, [enhancedNodes, visibleFlows, showNodes, showFlows, isGlobe, sizeBoost, themeId, crisisEnabled, showTerminator, selectedCountryCode, timeRange])

  // Total signals for stats
  const totalSignals = nodes.reduce((sum, n) => sum + n.signalCount, 0)

  return (
    <div className={`app ${crisisEnabled ? 'crisis-mode' : ''}`}>
      {/* Command Bar */}
      <header className="command-bar">
        <div className="command-bar-left">
          <h1 className="brand"><Globe size={16} /> ATLAS</h1>
          <FocusIndicator />
        </div>
        <div className="command-bar-center">
          <SearchBar
            onThemeSelect={handleThemeSelect}
            onCountrySelect={(code) => handleCountryClick(code)}
            onSourceSelect={(source) => setFocus('source', source, source)}
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
            {loading ? '...' : `${nodes.length} ctry • ${totalSignals.toLocaleString()} sig`}
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
            <span>GLOBE</span>
            <div className="panel-header-controls">
              <button
                className={`layer-btn ${isGlobe ? 'active' : ''}`}
                onClick={toggleGlobe}
                title={isGlobe ? 'Switch to flat map' : 'Switch to 3D globe'}
              >
                3D
              </button>
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
                className={`layer-btn ${showNodes ? 'active' : ''}`}
                onClick={() => setShowNodes(!showNodes)}
              >
                NODES
              </button>
            </div>
          </div>
          <div className="panel-content">
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
                    ;(map as any).setFog({
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
                    promoteId: 'ISO3166-1-Alpha-2'
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
                        0,    'rgba(0, 0, 0, 0)',
                        0.05, 'rgba(15, 30, 90, 50)',
                        0.15, 'rgba(30, 55, 130, 80)',
                        0.35, 'rgba(170, 110, 30, 120)',
                        0.6,  'rgba(215, 70, 15, 160)',
                        1.0,  'rgba(235, 35, 10, 200)'
                      ],
                      'fill-opacity': 0.75
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
                        0,    'rgba(0, 0, 0, 0)',
                        0.05, 'rgba(20, 35, 100, 40)',
                        0.15, 'rgba(35, 60, 140, 70)',
                        0.35, 'rgba(190, 120, 30, 100)',
                        0.6,  'rgba(225, 75, 15, 135)',
                        1.0,  'rgba(245, 45, 10, 170)'
                      ],
                      'line-width': [
                        'interpolate', ['linear'],
                        ['coalesce', ['feature-state', 'intensity'], 0],
                        0,   0,
                        0.05, 2,
                        0.5,  6,
                        1.0,  10
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

                  setMapReady(true)
                }}
              >
                <DeckGLOverlay
                  interleaved={true}
                  layers={layers}
                  getTooltip={({ object, layer }) => {
                    if (!object) return null
                    if (layer?.id?.startsWith('flows')) return null
                    if (layer?.id?.startsWith('nodes-core')) return null
                    if (selectedCountryCode) {
                      const isConnected = visibleFlows.some(f => f.sourceCountry === object.id || f.targetCountry === object.id)
                      if (isConnected && object.id !== selectedCountryCode) {
                        return `${object.name} — click to explore`
                      }
                    }
                    return `${object.name}: ${object.signalCount} signals`
                  }}
                  onHover={(info: any) => {
                    if (!info.object) {
                      setTooltip(null)
                      return
                    }
                    if (info.layer?.id?.startsWith('nodes-core')) {
                      setTooltip({ type: 'node', x: info.x, y: info.y, data: info.object })
                    } else if (info.layer?.id?.startsWith('flows')) {
                      setTooltip({ type: 'flow', x: info.x, y: info.y, data: info.object })
                    }
                  }}
                  onClick={({ object, layer }: any) => {
                    if (layer?.id?.startsWith('nodes-core') && object) {
                      handleCountryClick(object.id)
                      setFocus('country', object.id, object.name || object.id)
                    }
                  }}
                />
              </MapGL>
              <div className="globe-vignette" />
            </MapErrorBoundary>
          </div>
        </div>

        {/* Panel 2: SIGNAL STREAM */}
        <div className="terminal-panel stream">
          <div className="panel-header">SIGNAL STREAM</div>
          <div className="panel-content">
            <PanelErrorBoundary panelName="SIGNAL STREAM">
              <SignalStream />
            </PanelErrorBoundary>
          </div>
        </div>

        {/* Panel 3: NARRATIVE THREADS */}
        <div className="terminal-panel threads">
          <div className="panel-header">NARRATIVE THREADS</div>
          <div className="panel-content">
            <PanelErrorBoundary panelName="NARRATIVE THREADS">
              <NarrativeThreads />
            </PanelErrorBoundary>
          </div>
        </div>

        {/* Panel 4: CORRELATION MATRIX */}
        <div className="terminal-panel matrix">
          <div className="panel-header">CORRELATION MATRIX</div>
          <div className="panel-content">
            <PanelErrorBoundary panelName="CORRELATION MATRIX">
              <CorrelationMatrix />
            </PanelErrorBoundary>
          </div>
        </div>

        {/* Panel 5: ANOMALY ALERT */}
        <div className="terminal-panel anomaly">
          <div className="panel-header">ANOMALY ALERT</div>
          <div className="panel-content">
            <PanelErrorBoundary panelName="ANOMALY ALERT">
              <AnomalyPanel />
            </PanelErrorBoundary>
          </div>
        </div>

        {/* Panel 6: SOURCE INTEGRITY */}
        <div className="terminal-panel integrity">
          <div className="panel-header">SOURCE INTEGRITY</div>
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
          onClose={() => setShowBriefing(false)}
          onCountrySelect={(code) => {
            fetchCountryDetail(code)
            setShowBriefing(false)
          }}
          onThemeSelect={(theme) => {
            handleThemeSelect(theme)
            setShowBriefing(false)
          }}
        />
      )}

      {/* Theme Detail Overlay */}
      {selectedTheme && (
        <ThemeDetail
          theme={selectedTheme.theme}
          country={selectedTheme.country}
          hours={timeRangeToHours(timeRange)}
          onClose={() => setSelectedTheme(null)}
          onThemeSelect={(theme) => handleThemeSelect(theme)}
        />
      )}

      {/* Country Brief Slide-over */}
      {selectedCountry && (
        <CountryBrief
          countryCode={selectedCountry.countryCode}
          countryName={selectedCountry.name || selectedCountry.countryCode}
          timeWindow={timeRangeToHours(timeRange)}
          onClose={() => {
            setSelectedCountry(null)
            setSelectedCountryCode(null)
            setShowFlows(false)
          }}
          onThemeSelect={(theme) => handleThemeSelect(theme)}
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
