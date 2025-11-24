import { useEffect, useRef } from 'react'
import { useMap } from 'react-map-gl'
// @ts-ignore
import { MapboxOverlay } from '@deck.gl/mapbox'

interface DeckGLOverlayProps {
  layers: any[]
}

export function DeckGLOverlay(props: DeckGLOverlayProps) {
  console.log('[DeckGLOverlay] Render with layers:', props.layers.length)

  const { current: map } = useMap()
  const overlayRef = useRef<any>(null)

  useEffect(() => {
    if (!map) {
      console.log('[DeckGLOverlay] Map not ready yet')
      return
    }

    // Wait for map to be fully loaded
    if (!map.isStyleLoaded()) {
      console.log('[DeckGLOverlay] Waiting for map style to load...')
      const checkStyle = () => {
        if (map.isStyleLoaded()) {
          console.log('[DeckGLOverlay] Map style loaded, initializing overlay')
          initOverlay()
        }
      }
      map.on('style.load', checkStyle)
      map.on('load', checkStyle)
      return () => {
        map.off('style.load', checkStyle)
        map.off('load', checkStyle)
      }
    }

    initOverlay()

    function initOverlay() {
      if (!overlayRef.current) {
        console.log('[DeckGLOverlay] Creating MapboxOverlay with', props.layers.length, 'layers')
        try {
          overlayRef.current = new MapboxOverlay({
            interleaved: false,  // CRITICAL: Disable interleaved mode for globe projection
            layers: props.layers
          })
          map.addControl(overlayRef.current)
          console.log('[DeckGLOverlay] ✅ Overlay successfully added to map (interleaved=false for globe)')
        } catch (error) {
          console.error('[DeckGLOverlay] ❌ Failed to add overlay:', error)
        }
      } else {
        // Update existing overlay
        overlayRef.current.setProps({
          layers: props.layers
        })
        console.log('[DeckGLOverlay] Overlay updated with', props.layers.length, 'layers')
      }
    }

    return () => {
      // Don't remove overlay on every update, only on unmount
    }
  }, [map, props.layers])

  // Clean up on unmount only
  useEffect(() => {
    return () => {
      if (overlayRef.current && map) {
        console.log('[DeckGLOverlay] Cleaning up overlay on unmount')
        map.removeControl(overlayRef.current)
        overlayRef.current = null
      }
    }
  }, [])

  return null
}
