import { useControl } from 'react-map-gl'
// @ts-ignore - deck.gl/mapbox types not available
import { MapboxOverlay } from '@deck.gl/mapbox'

export function DeckGLOverlay(props: any) {
  const overlay = useControl<any>(() => new MapboxOverlay(props))
  overlay.setProps(props)
  return null
}
