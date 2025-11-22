import React, { useEffect, useRef, useState, useMemo } from 'react'
import Map, { MapRef, NavigationControl, Marker } from 'react-map-gl'
import type { ViewState } from 'react-map-gl'
import { useMapStore } from '../../store/mapStore'
import { useGaussianHeatmapLayer } from './layers/useGaussianRadarLayer'
import { useNodeLayer } from './layers/useNodeLayer'
import { useFlowLayer } from './layers/useFlowLayer'
import { DeckGLOverlay } from './DeckGLOverlay'
import MapTooltip from './MapTooltip'
import MapControlBar from './MapControlBar'
import CountrySidebar from '../sidebar/CountrySidebar'
import DataStatusBar from './DataStatusBar'
import 'mapbox-gl/dist/mapbox-gl.css'

const MAPBOX_TOKEN = 'pk.eyJ1IjoicHZpbGxlZyIsImEiOiJjbWh3Nnptb28wNDB2Mm9weTFqdXZqM3VyIn0.ZnybOXNNDKL1HJFuklpyGg'

const MapContainer: React.FC = () => {
  const mapRef = useRef<MapRef>(null)
  const { viewMode, fetchFlowsData, autoRefresh, refreshInterval, flowsData, setSelectedHotspot } = useMapStore()

  // Deck.gl Layer Hooks
  const { layer: heatmapLayer, hoverInfo: heatmapHover } = useGaussianHeatmapLayer()
  const { layer: nodeLayer, hoverInfo: nodeHover } = useNodeLayer()
  const { layer: flowLayer } = useFlowLayer()

  // Unified Hover Info
  const hoverInfo = heatmapHover || nodeHover

  // Track map view state
  const [viewState, setViewState] = useState<ViewState>({
    longitude: 0,
    latitude: 20,
    zoom: 2,
    pitch: 0,
    bearing: 0,
    padding: { top: 0, bottom: 0, left: 0, right: 0 },
  })

  // Fetch data based on current view mode
  // Always fetch flows data because Gaussian Heatmap now depends on it (hotspots)
  const fetchData = () => {
    fetchFlowsData()
  }

  // Fetch data when view mode changes
  useEffect(() => {
    fetchData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMode])

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      fetchData()
    }, refreshInterval)

    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, refreshInterval, viewMode])

  // Prepare DeckGL layers based on view mode
  const deckLayers = useMemo(() => {
    const layers = []

    console.log('[MapContainer] View mode:', viewMode)
    console.log('[MapContainer] Layer availability:', {
      flowLayer: !!flowLayer,
      heatmapLayer: !!heatmapLayer,
      nodeLayer: !!nodeLayer
    })

    // DEBUG: Add a test text layer that's ALWAYS visible
    // @ts-ignore
    if (window.deck && window.deck.TextLayer) {
      // @ts-ignore
      layers.push(new window.deck.TextLayer({
        id: 'test-layer',
        data: [{ position: [0, 0], text: 'DATA LAYER LOADED' }],
        getPosition: (d: any) => d.position,
        getText: (d: any) => d.text,
        getSize: 32,
        getColor: [255, 0, 0],
      }))
    }

    // Always show flows (Winds) in both modes
    if (flowLayer) {
      layers.push(flowLayer)
      console.log('[MapContainer] Added flowLayer')
    }

    if (viewMode === 'heatmap' && heatmapLayer) {
      layers.push(heatmapLayer)
      console.log('[MapContainer] Added heatmapLayer')
    }

    if (viewMode === 'classic' && nodeLayer) {
      layers.push(nodeLayer)
      console.log('[MapContainer] Added nodeLayer')
    }

    console.log('[MapContainer] Total layers:', layers.length)
    return layers
  }, [viewMode, heatmapLayer, nodeLayer, flowLayer])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100vh', overflow: 'hidden' }}>
      {/* Map */}
      <Map
        ref={mapRef}
        {...viewState}
        onMove={(evt) => setViewState(evt.viewState)}
        style={{ width: '100%', height: '100%' }}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        mapboxAccessToken={MAPBOX_TOKEN}
        projection={{ name: 'globe' }}
      >
        <NavigationControl position="top-right" />

        {/* Unified Radar View Architecture */}

        {/* All layers are now managed by DeckGLOverlay */}
        {deckLayers.length > 0 && (
          <DeckGLOverlay layers={deckLayers} />
        )}

      </Map>

      {/* Unified Tooltip */}
      {hoverInfo && hoverInfo.object && (
        <MapTooltip info={hoverInfo} />
      )}

      {/* Top Control Bar */}
      <MapControlBar />

      {/* Country Sidebar */}
      <CountrySidebar />

      {/* Status Bar - Bottom */}
      <DataStatusBar />
    </div>
  )
}

export default MapContainer

// Forced HMR update for Phase 3 UI changes
