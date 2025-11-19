import React, { useEffect, useRef, useState, useMemo } from 'react'
import Map, { MapRef, NavigationControl } from 'react-map-gl'
import type { ViewState } from 'react-map-gl'
import { useMapStore } from '../../store/mapStore'
import HotspotLayer from './HotspotLayer'
import FlowLayer from './FlowLayer'
import { DeckGLOverlay } from './DeckGLOverlay'
// @ts-ignore
import { HeatmapLayer } from '@deck.gl/aggregation-layers'
import { cellToLatLng } from 'h3-js'
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

    // Convert H3 hexes to point data for HeatmapLayer
    const pointData = hexmapData.hexes.map((hex: HexCell) => {
      const [lat, lng] = cellToLatLng(hex.h3_index)
      return {
        position: [lng, lat] as [number, number],
        weight: hex.intensity
      }
    })

    // HeatmapLayer with smooth Gaussian gradients
    const heatmapLayer = new HeatmapLayer({
      id: 'heatmap-layer',
      data: pointData,
      getPosition: (d: { position: [number, number]; weight: number }) => d.position,
      getWeight: (d: { position: [number, number]; weight: number }) => d.weight,
      aggregation: 'SUM',
      radiusPixels: 60,
      intensity: 1,
      threshold: 0.05,
      // Color gradient: green (low) -> yellow -> orange -> red (high)
      colorRange: [
        [0, 255, 0, 100],      // Green (low intensity)
        [255, 255, 0, 150],    // Yellow
        [255, 165, 0, 180],    // Orange
        [255, 0, 0, 220]       // Red (high intensity)
      ],
    })

    return [heatmapLayer]
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
        {viewMode === 'heatmap' && deckLayers.length > 0 && (
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
