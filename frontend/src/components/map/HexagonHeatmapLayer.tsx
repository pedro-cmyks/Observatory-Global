import React, { useMemo } from 'react'
import { useMapStore } from '../../store/mapStore'
import DeckGL from '@deck.gl/react'
import { H3HexagonLayer } from '@deck.gl/geo-layers'
import type { MapViewState } from '@deck.gl/core'

const HexagonHeatmapLayer: React.FC = () => {
  const { hexmapData, mapZoom, setMapZoom } = useMapStore()

  // Convert intensity to color (thermal colormap: blue → cyan → yellow → red)
  const intensityToColor = (intensity: number): [number, number, number, number] => {
    // Clamp intensity to [0, 1]
    const i = Math.max(0, Math.min(1, intensity))

    if (i < 0.25) {
      // Blue to Cyan (0.0 - 0.25)
      const t = i / 0.25
      return [
        Math.round(0 + t * 0),
        Math.round(0 + t * 255),
        Math.round(255 - t * 0),
        200, // Alpha
      ]
    } else if (i < 0.5) {
      // Cyan to Green (0.25 - 0.5)
      const t = (i - 0.25) / 0.25
      return [
        Math.round(0 + t * 0),
        Math.round(255 - t * 55),
        Math.round(255 - t * 255),
        200,
      ]
    } else if (i < 0.75) {
      // Green to Yellow (0.5 - 0.75)
      const t = (i - 0.5) / 0.25
      return [
        Math.round(0 + t * 255),
        Math.round(200 + t * 55),
        Math.round(0),
        200,
      ]
    } else {
      // Yellow to Red (0.75 - 1.0)
      const t = (i - 0.75) / 0.25
      return [
        Math.round(255),
        Math.round(255 - t * 255),
        Math.round(0),
        200,
      ]
    }
  }

  // Create deck.gl H3HexagonLayer
  const hexLayer = useMemo(() => {
    if (!hexmapData || !hexmapData.hexes || hexmapData.hexes.length === 0) {
      return null
    }

    return new H3HexagonLayer({
      id: 'h3-hexagon-layer',
      data: hexmapData.hexes,
      getHexagon: (d) => d.h3_index,
      getFillColor: (d) => intensityToColor(d.intensity),
      getElevation: 0, // Flat hexagons (no 3D elevation)
      elevationScale: 1,
      extruded: false,
      filled: true,
      stroked: false,
      coverage: 0.95, // 95% fill for slight gaps (helps define hex edges)
      opacity: 0.8,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 100],
      updateTriggers: {
        getFillColor: hexmapData.hexes,
      },
    })
  }, [hexmapData])

  if (!hexLayer) {
    return null
  }

  const viewState: MapViewState = {
    longitude: 0,
    latitude: 20,
    zoom: mapZoom,
    pitch: 0,
    bearing: 0,
  }

  return (
    <DeckGL
      viewState={viewState}
      layers={[hexLayer]}
      controller={false} // Let react-map-gl handle controls
      onViewStateChange={({ viewState: newViewState }) => {
        if ((newViewState as MapViewState).zoom !== undefined) {
          setMapZoom((newViewState as MapViewState).zoom)
        }
      }}
      style={{
        position: 'absolute',
        top: '0px',
        left: '0px',
        width: '100%',
        height: '100%',
        pointerEvents: 'none', // Let map handle interactions
        // Gaussian blur for blob effect
        filter: 'blur(8px)',
      }}
    />
  )
}

export default HexagonHeatmapLayer
