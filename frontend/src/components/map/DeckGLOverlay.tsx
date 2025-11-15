import { useControl } from 'react-map-gl'
// @ts-ignore - deck.gl/mapbox types not available
import { MapboxOverlay } from '@deck.gl/mapbox'

interface DeckGLOverlayProps {
  layers: any[]
}

export function DeckGLOverlay(props: DeckGLOverlayProps) {
  const overlay = useControl(() => new MapboxOverlay({
    interleaved: true
  }))

  // Guard against calling setProps before overlay is ready
  if (overlay && overlay.setProps) {
    overlay.setProps({
      ...props,
      interleaved: true
    })
  }

  return null
}
