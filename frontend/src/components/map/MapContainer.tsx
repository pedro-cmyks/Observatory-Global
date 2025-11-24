import React, { useEffect, useRef, useState, useMemo } from 'react'
import Map, { MapRef, NavigationControl } from 'react-map-gl'
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

const MAPBOX_TOKEN = 'pk.eyJ1IjoicHZpbGxlZ2ciOiJjbWh3Nnptb28wNDB2Mm9weTFqdXZqM3VyIn0.ZnybOXNNDKL1HJFuklpyGg'

const MapContainer = () => {
  const { viewMode, fetchFlowsData, autoRefresh, refreshInterval, flowsData, layersVisible } = useMapStore()

  // Deck.gl Layer Hooks
  const { layer: heatmapLayer, hoverInfo: heatmapHover } = useGaussianHeatmapLayer()
  const { layer: nodeLayer, hoverInfo: nodeHover } = useNodeLayer()
  const { layer: flowLayer } = useFlowLayer()

  // Prepare DeckGL layers - conditionally based on layer toggles
  const layers = useMemo(() => {
    const activeLayers = []

    console.log('[MapContainer] Building layers:', {
      hasFlowLayer: !!flowLayer,
      hasHeatmapLayer: !!heatmapLayer,
      hasNodeLayer: !!nodeLayer,
      layersVisible,
      viewMode
    })

    // Add layers based on visibility toggles
    if (flowLayer && layersVisible.flows) {
      console.log('[MapContainer] Adding flow layer')
      activeLayers.push(flowLayer)
    }

    if (heatmapLayer && layersVisible.heatmap) {
      console.log('[MapContainer] Adding heatmap layer')
      activeLayers.push(heatmapLayer)
    }

    if (nodeLayer && layersVisible.markers) {
      console.log('[MapContainer] Adding node layer')
      activeLayers.push(nodeLayer)
    }

    console.log('[MapContainer] Total active layers:', activeLayers.length)
    return activeLayers
  }, [heatmapLayer, nodeLayer, flowLayer, layersVisible, viewMode])

  const mapRef = useRef<MapRef>(null)

  // Unified Hover Info
  const hoverInfo = heatmapHover || nodeHover

  // Track map view state
  const [viewState, setViewState] = useState<ViewState>({
    longitude: 0,
    latitude: 20,
    zoom: 2,
    pitch: 0,
    bearing: 0,
  })

  // CRITICAL: Load data immediately on mount
  useEffect(() => {
    console.log('[MapContainer] Component mounted - fetching initial data')
    fetchFlowsData()
  }, []) // Empty deps = run once on mount

  // DEBUG: Log when data changes
  useEffect(() => {
    if (flowsData) {
      console.log('[MapContainer] Data loaded:', {
        hotspots: flowsData.hotspots?.length || 0,
        flows: flowsData.flows?.length || 0,
        metadata: flowsData.metadata
      })
      // @ts-ignore
      window.DEBUG_FLOWS_DATA = flowsData
    } else {
      console.log('[MapContainer] No data yet')
    }
  }, [flowsData])

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
        {layers.length > 0 && (
          <DeckGLOverlay layers={layers} />
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
