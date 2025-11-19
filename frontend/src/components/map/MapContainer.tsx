import React, { useEffect, useRef, useState, useMemo } from 'react'
import Map, { MapRef, NavigationControl } from 'react-map-gl'
import type { ViewState } from 'react-map-gl'
import { useMapStore } from '../../store/mapStore'
import HotspotLayer from './HotspotLayer'
import FlowLayer from './FlowLayer'
import { DeckGLOverlay } from './DeckGLOverlay'
// @ts-ignore
import { H3HexagonLayer } from '@deck.gl/geo-layers'
import type { HexCell } from '../../lib/mapTypes'
import ViewModeToggle from './ViewModeToggle'
import CountrySidebar from './CountrySidebar'
import TimeWindowSelector from './TimeWindowSelector'
import CountryFilter from './CountryFilter'
import AutoRefreshControl from './AutoRefreshControl'
import DataStatusBar from './DataStatusBar'
import 'mapbox-gl/dist/mapbox-gl.css'

const MAPBOX_TOKEN = 'pk.eyJ1IjoicHZpbGxlZyIsImEiOiJjbWh3Nnptb28wNDB2Mm9weTFqdXZqM3VyIn0.ZnybOXNNDKL1HJFuklpyGg'

const MapContainer: React.FC = () => {
  const mapRef = useRef<MapRef>(null)
  const { viewMode, fetchFlowsData, fetchHexmapData, hexmapData, autoRefresh, refreshInterval } = useMapStore()

  // Track map view state for DeckGL overlay
  const [viewState, setViewState] = useState<ViewState>({
    longitude: 0,
    latitude: 20,
    zoom: 2,
    pitch: 0,
    bearing: 0,
    padding: { top: 0, bottom: 0, left: 0, right: 0 },
  })

  // Fetch data based on current view mode
  const fetchData = () => {
    if (viewMode === 'classic') {
      fetchFlowsData()
    } else {
      fetchHexmapData()
    }
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

  // Create deck.gl layers for heatmap mode
  const deckLayers = useMemo(() => {
    if (viewMode !== 'heatmap' || !hexmapData?.hexes || hexmapData.hexes.length === 0) {
      return []
    }

    // Color interpolation function: intensity (0-1) -> RGBA
    // Gradient: Green (low) -> Yellow -> Orange -> Red (high)
    const getColor = (intensity: number): [number, number, number, number] => {
      if (intensity < 0.33) {
        // Green to Yellow
        const t = intensity / 0.33
        return [Math.round(255 * t), 255, 0, 180]
      } else if (intensity < 0.66) {
        // Yellow to Orange
        const t = (intensity - 0.33) / 0.33
        return [255, Math.round(255 - 90 * t), 0, 200]
      } else {
        // Orange to Red
        const t = (intensity - 0.66) / 0.34
        return [255, Math.round(165 - 165 * t), 0, 220]
      }
    }

    // H3HexagonLayer - specifically designed for H3 hex rendering
    // Known issue: Hexes render on slightly smaller sphere than base globe
    // See: https://github.com/repo/issues/XX for tracking
    const hexLayer = new H3HexagonLayer({
      id: 'heatmap-hex-layer',
      data: hexmapData.hexes,
      pickable: true,
      filled: true,
      extruded: false,
      getHexagon: (d: HexCell) => d.h3_index,
      getFillColor: (d: HexCell) => getColor(d.intensity),
      getLineColor: [255, 255, 255, 80],
      lineWidthMinPixels: 1,
      // Enable high precision for globe projection
      highPrecision: true,
    })

    return [hexLayer]
  }, [viewMode, hexmapData])

  return (
    <div style={{ position: 'relative', width: '100%', height: '600px' }}>
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

        {/* Classic View Layers */}
        {viewMode === 'classic' && (
          <>
            <FlowLayer />
            <HotspotLayer />
          </>
        )}

        {/* Heatmap View - DeckGL Overlay (properly integrated) */}
        {viewMode === 'heatmap' && (
          <DeckGLOverlay layers={deckLayers} />
        )}
      </Map>

      {/* Controls - Top Left */}
      <div
        style={{
          position: 'absolute',
          top: '1rem',
          left: '1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
          zIndex: 10,
        }}
      >
        <ViewModeToggle />
        <TimeWindowSelector />
        <CountryFilter />
        <AutoRefreshControl />
      </div>

      {/* Country Sidebar */}
      <CountrySidebar />

      {/* Status Bar - Bottom */}
      <DataStatusBar />
    </div>
  )
}

export default MapContainer
