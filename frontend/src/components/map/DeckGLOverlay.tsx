import { useControl } from 'react-map-gl'
// @ts-ignore - deck.gl/mapbox types not available
import { MapboxOverlay } from '@deck.gl/mapbox'

export function DeckGLOverlay(props: any) {
  const overlay = useControl<any>(() => new MapboxOverlay({
    ...props,
    // Enable interleaved rendering for proper globe projection support
    // This ensures deck.gl layers are depth-tested with Mapbox 3D features
    interleaved: true,
  }))
  overlay.setProps({
    ...props,
    interleaved: true,
  })
  return null
}
