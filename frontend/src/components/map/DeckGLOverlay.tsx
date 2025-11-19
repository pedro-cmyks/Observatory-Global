import { useControl } from 'react-map-gl'
// @ts-ignore - deck.gl/mapbox types not available
import { MapboxOverlay } from '@deck.gl/mapbox'

interface DeckGLOverlayProps {
  layers: any[]
  interleaved?: boolean
}

export function DeckGLOverlay({ layers, interleaved = true }: DeckGLOverlayProps) {
  const overlay = useControl<MapboxOverlay>(
    () => new MapboxOverlay({ layers, interleaved }),
    { position: 'top-left' }
  )

  overlay.setProps({ layers })

  return null
}
