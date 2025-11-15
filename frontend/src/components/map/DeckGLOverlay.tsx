import { useControl } from 'react-map-gl'
import { useEffect } from 'react'
// @ts-ignore - deck.gl/mapbox types not available
import { MapboxOverlay } from '@deck.gl/mapbox'

export function DeckGLOverlay(props: any) {
  const overlay = useControl<any>(
    () => new MapboxOverlay({
      interleaved: true,
    })
  )

  // Update props when they change
  useEffect(() => {
    if (overlay && overlay.setProps) {
      overlay.setProps(props)
    }
  }, [overlay, props])

  return null
}
