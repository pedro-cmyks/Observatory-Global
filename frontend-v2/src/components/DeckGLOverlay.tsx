import { useControl } from 'react-map-gl/maplibre'
import { MapboxOverlay, type MapboxOverlayProps } from '@deck.gl/mapbox'

export function DeckGLOverlay(props: MapboxOverlayProps & {
    interleaved?: boolean
}) {
    const overlay = useControl<MapboxOverlay>(
        () => new MapboxOverlay({ interleaved: props.interleaved ?? true })
    )
    overlay.setProps(props)
    return null
}
