import React, { useEffect, useRef, useState } from 'react'
import Map, { MapRef, NavigationControl } from 'react-map-gl'
import type { ViewState } from 'react-map-gl'
import { useMapStore } from '../../store/mapStore'
import HotspotLayer from './HotspotLayer'
import FlowLayer from './FlowLayer'
import HexagonHeatmapLayer from './HexagonHeatmapLayer'
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
  const { viewMode, fetchFlowsData, fetchHexmapData, autoRefresh, refreshInterval } = useMapStore()

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

  // Initial data fetch
  useEffect(() => {
    fetchData()

    // DEBUG: Pan to USA when switching to heatmap (hexagons are located there)
    if (viewMode === 'heatmap') {
      console.log('🗺️ Panning to USA where hexagons are located...')
      setViewState({
        longitude: -95,
        latitude: 36,
        zoom: 4,
        pitch: 0,
        bearing: 0,
        padding: { top: 0, bottom: 0, left: 0, right: 0 },
      })
    } else {
      // Reset to global view for classic mode
      setViewState({
        longitude: 0,
        latitude: 20,
        zoom: 2,
        pitch: 0,
        bearing: 0,
        padding: { top: 0, bottom: 0, left: 0, right: 0 },
      })
    }
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
    <div style={{ position: 'relative', width: '100%', height: '600px' }}>
      {/* Map */}
      <Map
        ref={mapRef}
        {...viewState}
        onMove={(evt) => setViewState(evt.viewState)}
        style={{ width: '100%', height: '100%' }}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        mapboxAccessToken={MAPBOX_TOKEN}
      >
        <NavigationControl position="top-right" />

        {/* Classic View Layers */}
        {viewMode === 'classic' && (
          <>
            <FlowLayer />
            <HotspotLayer />
          </>
        )}
      </Map>

      {/* Heatmap View Overlay (DeckGL) */}
      {viewMode === 'heatmap' && (
        <HexagonHeatmapLayer viewState={viewState} />
      )}

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
