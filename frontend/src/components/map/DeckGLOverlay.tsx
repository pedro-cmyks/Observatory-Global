import { useControl } from 'react-map-gl'
// @ts-ignore - deck.gl/mapbox types not available
import { MapboxOverlay as DeckOverlay } from '@deck.gl/mapbox'

interface DeckGLOverlayProps {
  layers: any[]
  interleaved?: boolean
}

export function DeckGLOverlay(props: DeckGLOverlayProps) {
  // Use the exact pattern from deck.gl documentation
  // Pass interleaved option to DeckOverlay constructor for proper compositing with Mapbox
  const overlay = useControl<DeckOverlay>(
    () => new DeckOverlay({ interleaved: props.interleaved ?? false })
  )
  overlay.setProps(props)
  return null
}
