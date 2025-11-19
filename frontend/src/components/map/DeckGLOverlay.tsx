import { useControl } from 'react-map-gl'
// @ts-ignore - deck.gl/mapbox types not available
import { MapboxOverlay } from '@deck.gl/mapbox'

interface DeckGLOverlayProps {
  layers: any[]
  interleaved?: boolean
}

export function DeckGLOverlay({ layers, interleaved = true }: DeckGLOverlayProps) {
  const overlay = useControl<MapboxOverlay>(
    () => new MapboxOverlay({
      layers,
      interleaved,
      // Use Mapbox's projection for proper globe support
      // This ensures layers stay attached to the globe during pitch/yaw rotations
    }),
    { position: 'top-left' }
  )

  overlay.setProps({ layers })

  return null
}
