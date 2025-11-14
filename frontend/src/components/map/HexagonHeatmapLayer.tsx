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
    if (!hexmapData?.hexes) return []

    return [
      new H3HexagonLayer({
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
          // Color based on intensity: blue (low) -> yellow (medium) -> red (high)
          // Increased alpha for better blending
          const intensity = d.intensity
          if (intensity > 0.7) {
            // High intensity: Red with high alpha for smooth blending
            return [239, 68, 68, 220] // #EF4444
          } else if (intensity > 0.4) {
            // Medium intensity: Yellow
            return [252, 211, 77, 200] // #FCD34D
          } else {
            // Low intensity: Blue
            return [59, 130, 246, 180] // #3B82F6
          }
        },
        getElevation: 0,
        elevationScale: 0,
        // Increased opacity for better visibility after blur
        opacity: 0.8,
        updateTriggers: {
          getFillColor: [hexmapData],
        },
      }),
    ]
  }, [hexmapData])

  return (
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
        // Gaussian blur for smooth "blob" effect
        filter: 'blur(12px)',
        // Ensure layer wraps with globe
        transform: 'translateZ(0)',
        willChange: 'transform',
      }}
    />
  )
}

export default HexagonHeatmapLayer
