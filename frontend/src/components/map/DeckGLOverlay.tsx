import { useControl } from 'react-map-gl'
// @ts-ignore - deck.gl/mapbox types not available
import { MapboxOverlay as DeckOverlay } from '@deck.gl/mapbox'

interface DeckGLOverlayProps {
  layers: any[]
  interleaved?: boolean
}

export function DeckGLOverlay(props: DeckGLOverlayProps) {
  // Use the exact pattern from deck.gl documentation
  const overlay = useControl<DeckOverlay>(() => new DeckOverlay(props))
  overlay.setProps(props)
  return null
}
