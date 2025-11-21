import React, { useMemo } from 'react'
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

  const layers = useMemo(() => {
    if (!hexmapData?.hexes) {
      return []
    }

    const layer = new H3HexagonLayer({
      id: 'h3-hexagon-layer',
      data: hexmapData.hexes,
      pickable: true,
      wireframe: false,
      filled: true,
      extruded: true, // Enable 3D elevation
      // Ensure proper coordinate system for globe wrapping
      coordinateSystem: 0, // COORDINATE_SYSTEM.LNGLAT

      // **FIX: Add coverage parameter to expand hexagon visual size**
      coverage: 0.9,

      // **FIX: Add elevation scaling for 3D depth effect**
      elevationScale: 100,

      getHexagon: (d: HexCell) => d.h3_index,

      getFillColor: (d: HexCell): [number, number, number, number] => {
        const intensity = d.intensity
        // Color gradient: Red (high) → Yellow (medium) → Green (low)
        // With appropriate opacity for blending
        if (intensity > 0.7) {
          return [255, 0, 0, 200]  // Red, 78% opacity
        } else if (intensity > 0.4) {
          return [255, 255, 0, 180]  // Yellow, 70% opacity
        } else {
          return [0, 255, 0, 160]  // Green, 63% opacity
        }
      },

      // **FIX: Add elevation based on intensity for 3D effect**
      getElevation: (d: HexCell) => d.intensity * 1000,

      // Smooth opacity for gradient effect
      opacity: 0.8,

      updateTriggers: {
        getFillColor: [hexmapData],
        getElevation: [hexmapData],
      },
    })

    return [layer]
  }, [hexmapData])

  return (
    <DeckGL
      viewState={viewState}
      layers={layers}
      controller={false} // Map handles controller
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none', // Let map handle events
        // **FIX: Restore blur filter for smooth gradient effect**
        filter: 'blur(12px)',
        // Ensure layer wraps with globe
        transform: 'translateZ(0)',
        willChange: 'transform',
        zIndex: 1000,
      }}
    />
  )
}

export default HexagonHeatmapLayer
