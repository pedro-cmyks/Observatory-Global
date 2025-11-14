import React, { useEffect, useRef } from 'react'
import Map, { MapRef, NavigationControl } from 'react-map-gl'
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
  const { fetchFlowsData, fetchHexmapData, autoRefresh, refreshInterval, viewMode, setMapZoom } = useMapStore()

  // Initial data fetch
  useEffect(() => {
    if (viewMode === 'heatmap') {
      fetchHexmapData()
    } else {
      fetchFlowsData()
    }
  }, [fetchFlowsData, fetchHexmapData, viewMode])

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      if (viewMode === 'heatmap') {
        fetchHexmapData()
      } else {
        fetchFlowsData()
      }
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval, fetchFlowsData, fetchHexmapData, viewMode])

  // Track zoom changes
  const handleMoveEnd = () => {
    if (mapRef.current) {
      const map = mapRef.current.getMap()
      const zoom = map.getZoom()
      setMapZoom(zoom)
    }
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: '600px' }}>
      {/* Map */}
      <Map
        ref={mapRef}
        initialViewState={{
          longitude: 0,
          latitude: 20,
          zoom: 2,
        }}
        style={{ width: '100%', height: '100%' }}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        mapboxAccessToken={MAPBOX_TOKEN}
        onMoveEnd={handleMoveEnd}
      >
        <NavigationControl position="top-right" />

        {/* Conditional rendering based on view mode */}
        {viewMode === 'classic' && (
          <>
            <FlowLayer />
            <HotspotLayer />
          </>
        )}
      </Map>

      {/* Hexagon Heatmap Layer (deck.gl overlay) */}
      {viewMode === 'heatmap' && <HexagonHeatmapLayer />}

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
