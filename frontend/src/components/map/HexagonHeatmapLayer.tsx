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
        getHexagon: (d: HexCell) => d.h3_index,
        getFillColor: (d: HexCell) => {
          // Color based on intensity: blue (low) -> yellow (medium) -> red (high)
          const intensity = d.intensity
          if (intensity > 0.7) {
            // High intensity: Red
            return [239, 68, 68, 200] // #EF4444 with alpha
          } else if (intensity > 0.4) {
            // Medium intensity: Yellow
            return [252, 211, 77, 180] // #FCD34D with alpha
          } else {
            // Low intensity: Blue
            return [59, 130, 246, 160] // #3B82F6 with alpha
          }
        },
        getElevation: 0,
        elevationScale: 0,
        opacity: 0.6,
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
      }}
    />
  )
}

export default HexagonHeatmapLayer
