import React, { useMemo, useEffect } from 'react'
import { useMapStore } from '../../store/mapStore'
// @ts-ignore - deck.gl types not available
import DeckGL from '@deck.gl/react'
// @ts-ignore - deck.gl types not available
import { H3HexagonLayer } from '@deck.gl/geo-layers'
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

    const layer = new H3HexagonLayer({
      id: 'h3-hexagon-layer',
      data: hexmapData.hexes,
      pickable: true,
      wireframe: false,
      filled: true,
      extruded: false,
      // Ensure proper coordinate system for globe wrapping
      coordinateSystem: 0, // COORDINATE_SYSTEM.LNGLAT
      getHexagon: (d: HexCell) => d.h3_index,
      getFillColor: (d: HexCell) => {
        // DEBUG: Use very bright, solid colors with full opacity for testing
        const intensity = d.intensity
        if (intensity > 0.7) {
          return [255, 0, 0, 255] // Bright red, full opacity
        } else if (intensity > 0.4) {
          return [255, 255, 0, 255] // Bright yellow, full opacity
        } else {
          return [0, 255, 0, 255] // Bright green, full opacity
        }
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
    return [layer]
  }, [hexmapData])

  // DEBUG: Log render
  useEffect(() => {
    console.log('🎨 DeckGL rendering with', layers.length, 'layers')
    if (layers.length > 0) {
      console.log('Layer IDs:', layers.map(l => l.id))
    }
  }, [layers])

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
          zIndex: 1000, // DEBUG: Force high z-index
        }}
      />
    </>
  )
}

export default HexagonHeatmapLayer
