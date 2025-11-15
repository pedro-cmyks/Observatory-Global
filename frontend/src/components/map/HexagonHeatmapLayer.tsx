import React, { useMemo, useEffect } from 'react'
import { useMapStore } from '../../store/mapStore'
// @ts-ignore - deck.gl types not available
import DeckGL from '@deck.gl/react'
// @ts-ignore - deck.gl types not available
import { H3HexagonLayer } from '@deck.gl/geo-layers'
// @ts-ignore - deck.gl types not available
import { ScatterplotLayer } from '@deck.gl/layers'
import type { ViewState } from 'react-map-gl'
import type { HexCell } from '../../lib/mapTypes'

interface HexagonHeatmapLayerProps {
  viewState: ViewState
}

const HexagonHeatmapLayer: React.FC<HexagonHeatmapLayerProps> = ({ viewState }) => {
  const { hexmapData } = useMapStore()

  // DEBUG: Step 1 - Verify data flow
  useEffect(() => {
    console.group('🗺️ HexagonHeatmapLayer Debug - Step 1: Data Flow')
    console.log('Component mounted:', !!hexmapData)
    console.log('Hexes count:', hexmapData?.hexes?.length ?? 0)
    console.log('First hex sample:', hexmapData?.hexes?.[0])
    console.log('ViewState:', viewState)
    console.groupEnd()
  }, [hexmapData, viewState])

  const layers = useMemo(() => {
    if (!hexmapData?.hexes) {
      console.warn('⚠️ No hexmap data available for rendering')
      return []
    }

    console.log('✅ Creating H3HexagonLayer with', hexmapData.hexes.length, 'hexes')

    // DEBUG: Log first few H3 indices
    console.log('Sample H3 indices:', hexmapData.hexes.slice(0, 3).map(h => h.h3_index))

    // DEBUG: Test accessor functions
    const testHex = hexmapData.hexes[0]
    console.log('🔬 Testing accessor on first hex:', testHex)
    console.log('  getHexagon result:', testHex.h3_index)
    console.log('  getFillColor result:', testHex.intensity > 0.7 ? [255, 0, 0, 255] : [0, 255, 0, 255])

    // DEBUG: Try ScatterplotLayer instead to test if coordinates work
    // Import h3-js dynamically
    console.log('🧪 TESTING: Using ScatterplotLayer instead of H3HexagonLayer')

    const testLayer = new ScatterplotLayer({
      id: 'test-scatterplot',
      data: hexmapData.hexes.slice(0, 10), // Just first 10 for testing
      getPosition: (d: HexCell) => {
        // We'll use approximate center of USA for now
        const index = hexmapData.hexes.indexOf(d)
        const lon = -95 + (Math.random() - 0.5) * 10
        const lat = 36 + (Math.random() - 0.5) * 10
        console.log(`Test point ${index}: [${lon}, ${lat}]`)
        return [lon, lat]
      },
      getFillColor: [255, 0, 0, 255], // Bright red
      getRadius: 50000, // 50km radius (very large, impossible to miss)
      radiusMinPixels: 20, // At least 20 pixels
      radiusMaxPixels: 100,
      pickable: true,
    })

    const layer = new H3HexagonLayer({
      id: 'h3-hexagon-layer',
      data: hexmapData.hexes,
      pickable: true,
      wireframe: false,
      filled: true,
      extruded: false,
      // Ensure proper coordinate system for globe wrapping
      coordinateSystem: 0, // COORDINATE_SYSTEM.LNGLAT
      getHexagon: (d: HexCell) => {
        const hex = d.h3_index
        // DEBUG: Log first few hexagon accesses
        if (hexmapData.hexes.indexOf(d) < 3) {
          console.log(`  Accessor called for hex ${hexmapData.hexes.indexOf(d)}: ${hex}`)
        }
        return hex
      },
      getFillColor: (d: HexCell): [number, number, number, number] => {
        // DEBUG: Use very bright, solid colors with full opacity for testing
        const intensity = d.intensity
        const color: [number, number, number, number] = intensity > 0.7
          ? [255, 0, 0, 255]  // Bright red, full opacity
          : intensity > 0.4
          ? [255, 255, 0, 255]  // Bright yellow, full opacity
          : [0, 255, 0, 255]  // Bright green, full opacity

        // DEBUG: Log first few color calculations
        if (hexmapData.hexes.indexOf(d) < 3) {
          console.log(`  Color for hex ${hexmapData.hexes.indexOf(d)} (intensity=${intensity}):`, color)
        }
        return color
      },
      getElevation: 0,
      elevationScale: 0,
      // DEBUG: Full opacity for testing
      opacity: 1.0,
      updateTriggers: {
        getFillColor: [hexmapData],
      },
    })

    console.log('Layer created:', layer)
    console.log('Test layer created:', testLayer)

    // Return BOTH layers for testing
    return [testLayer, layer]
  }, [hexmapData])

  // DEBUG: Log render and check DOM
  useEffect(() => {
    console.log('🎨 DeckGL rendering with', layers.length, 'layers')
    if (layers.length > 0) {
      console.log('Layer IDs:', layers.map(l => l.id))
    }

    // Check if DeckGL canvas exists in DOM
    setTimeout(() => {
      const deckCanvas = document.querySelector('canvas[id^="deckgl"]') as HTMLCanvasElement | null
      console.log('🖼️ DeckGL canvas found:', !!deckCanvas)
      if (deckCanvas) {
        console.log('  Canvas dimensions:', {
          width: deckCanvas.width,
          height: deckCanvas.height,
          style: deckCanvas.style.cssText
        })
      }
    }, 100)
  }, [layers])

  // DEBUG: Log viewState details
  useEffect(() => {
    console.log('📍 ViewState update:', {
      longitude: viewState.longitude,
      latitude: viewState.latitude,
      zoom: viewState.zoom,
      pitch: viewState.pitch,
      bearing: viewState.bearing
    })
  }, [viewState])

  return (
    <>
      {/* DEBUG: Visual indicator that overlay is mounting */}
      <div
        style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          background: 'rgba(255, 0, 0, 0.8)',
          color: 'white',
          padding: '10px',
          borderRadius: '4px',
          zIndex: 2000,
          fontSize: '12px',
          fontFamily: 'monospace',
        }}
      >
        🔥 HEATMAP OVERLAY ACTIVE
        <br />
        Hexes: {hexmapData?.hexes?.length ?? 0}
        <br />
        Layers: {layers.length}
        <br />
        ViewState: {viewState.zoom.toFixed(1)} @ ({viewState.latitude.toFixed(1)}, {viewState.longitude.toFixed(1)})
      </div>

      <DeckGL
        viewState={viewState}
        layers={layers}
        controller={false} // Map handles controller
        style={{
          position: 'absolute',
          top: '0px',
          left: '0px',
          width: '100%',
          height: '100%',
          pointerEvents: 'none', // Let map handle events
          // DEBUG: Temporarily removed blur to test if hexagons render at all
          // filter: 'blur(12px)',
          // Ensure layer wraps with globe
          transform: 'translateZ(0)',
          willChange: 'transform',
          zIndex: '1000', // DEBUG: Force high z-index
          // DEBUG: Add semi-transparent background to verify canvas is visible
          backgroundColor: 'rgba(255, 0, 255, 0.2)', // Magenta tint
        }}
      />
    </>
  )
}

export default HexagonHeatmapLayer
