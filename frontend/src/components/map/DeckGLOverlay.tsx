import { useControl } from 'react-map-gl'
// @ts-ignore
import { MapboxOverlay } from '@deck.gl/mapbox'

interface DeckGLOverlayProps {
  layers: any[]
}

export function DeckGLOverlay(props: DeckGLOverlayProps) {
  console.log('[DeckGLOverlay] Render with layers:', props.layers.length)

  const overlay = useControl<any>(() => {
    console.log('[DeckGLOverlay] Initializing MapboxOverlay with interleaved: true')
    return new MapboxOverlay({
      interleaved: true // Critical for Globe projection alignment
    })
  })

  // Update layer configuration
  overlay.setProps({
    ...props,
    interleaved: true
  })

  return null
}
