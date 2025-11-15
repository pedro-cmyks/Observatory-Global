import React, { useEffect, useRef, useState, useMemo } from 'react'
import Map, { MapRef, NavigationControl } from 'react-map-gl'
import type { ViewState } from 'react-map-gl'
import { useMapStore } from '../../store/mapStore'
import HotspotLayer from './HotspotLayer'
import FlowLayer from './FlowLayer'
import { DeckGLOverlay } from './DeckGLOverlay'
// @ts-ignore
import { H3HexagonLayer } from '@deck.gl/geo-layers'
// @ts-ignore
import { ScatterplotLayer } from '@deck.gl/layers'
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

  // Create deck.gl layers for heatmap mode
  const deckLayers = useMemo(() => {
    if (viewMode !== 'heatmap' || !hexmapData?.hexes) {
      console.log('⚠️ No heatmap layers - mode:', viewMode, 'data:', !!hexmapData)
      return []
    }

    console.log('🎨 Creating deck.gl layers with', hexmapData.hexes.length, 'hexes')

    // Test layer with circles
    const testLayer = new ScatterplotLayer({
      id: 'test-scatterplot',
      data: hexmapData.hexes.slice(0, 10),
      getPosition: (d: HexCell): [number, number] => {
        const index = hexmapData.hexes.indexOf(d)
        const lon = -95 + (Math.random() - 0.5) * 10
        const lat = 36 + (Math.random() - 0.5) * 10
        if (index < 3) console.log(`Test point ${index}: [${lon}, ${lat}]`)
        return [lon, lat]
      },
      getFillColor: [255, 0, 0, 255],
      getRadius: 50000,
      radiusMinPixels: 20,
      radiusMaxPixels: 100,
      pickable: true,
    })

    // H3 hexagon layer
    const hexLayer = new H3HexagonLayer({
      id: 'h3-hexagon-layer',
      data: hexmapData.hexes,
      pickable: true,
      wireframe: false,
      filled: true,
      extruded: false,
      getHexagon: (d: HexCell) => d.h3_index,
      getFillColor: (d: HexCell): [number, number, number, number] => {
        const intensity = d.intensity
        return intensity > 0.7
          ? [255, 0, 0, 255]
          : intensity > 0.4
          ? [255, 255, 0, 255]
          : [0, 255, 0, 255]
      },
      getElevation: 0,
      elevationScale: 0,
      opacity: 1.0,
    })

    console.log('✅ Layers created:', [testLayer.id, hexLayer.id])
    return [testLayer, hexLayer]
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
