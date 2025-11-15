import { useControl } from 'react-map-gl'
import { useEffect } from 'react'
// @ts-ignore - deck.gl/mapbox types not available
import { MapboxOverlay } from '@deck.gl/mapbox'

export function DeckGLOverlay(props: any) {
  const overlay = useControl<any>(
    () => new MapboxOverlay({
      interleaved: true,
      ...props
    })
  )

  // Update props when they change
  // useControl returns a wrapper with an 'implementation' property
  useEffect(() => {
    const impl = overlay?.implementation || overlay
    if (impl && typeof impl.setProps === 'function') {
      impl.setProps(props)
    }
  }, [overlay, props])

  return null
}
