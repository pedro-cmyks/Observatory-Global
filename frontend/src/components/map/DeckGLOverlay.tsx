import { useControl } from 'react-map-gl'
import { useEffect } from 'react'
// @ts-ignore - deck.gl/mapbox types not available
import { MapboxOverlay } from '@deck.gl/mapbox'

interface DeckGLOverlayProps {
  layers: any[]
}

export function DeckGLOverlay({ layers }: DeckGLOverlayProps) {
  const overlay = useControl<any>(
    () => new MapboxOverlay({
      interleaved: true,
    })
  )

  // Update layers when they change
  // Only depend on layers, not the entire props object
  useEffect(() => {
    if (!overlay) return

    const impl = overlay.implementation || overlay
    if (impl && typeof impl.setProps === 'function') {
      impl.setProps({ layers })
    }
  }, [overlay, layers])

  return null
}
