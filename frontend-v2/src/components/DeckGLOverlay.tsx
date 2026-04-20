import { useControl } from 'react-map-gl/maplibre'
import { MapboxOverlay, type MapboxOverlayProps } from '@deck.gl/mapbox'
import { useEffect, useRef } from 'react'

/**
 * DeckGL overlay that shares the same WebGL context as MapLibre (interleaved).
 * This allows both native MapLibre layers (country glow) and Deck.gl layers (nodes/arcs)
 * to render together on the same canvas.
 *
 * Key fix: We recreate the overlay when `interleaved` changes, and we always
 * call setProps on every render to push fresh layers into the overlay.
 */
export function DeckGLOverlay(props: MapboxOverlayProps & {
    interleaved?: boolean
}) {
    const overlayRef = useRef<MapboxOverlay | null>(null)

    const overlay = useControl<MapboxOverlay>(
        () => {
            const instance = new MapboxOverlay({
                ...props,
                interleaved: props.interleaved ?? true,
            })
            overlayRef.current = instance
            return instance
        }
    )

    // Push props every render — this is what actually sends layers to the GPU
    useEffect(() => {
        overlay.setProps(props)
    })

    return null
}
