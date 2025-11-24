import { LayersList } from '@deck.gl/core'
import { ScatterplotLayer, ArcLayer } from '@deck.gl/layers'
import { LayerState } from './GlobalObservatory'
import { TimeWindow, FlowsResponse, CountryHotspot, Flow } from '../../lib/mapTypes'

interface GetLayersProps {
    activeLayers: LayerState
    timeWindow: TimeWindow
    data: FlowsResponse | null
    zoom: number
}

export const getLayers = ({ activeLayers, timeWindow, data, zoom }: GetLayersProps): LayersList => {
    const layers: LayersList = []

    if (!data) {
        console.log('[MapLayerManager] No data available')
        return layers
    }

    // Calculate zoom-based scale factor
    // At zoom 0-2 (global view): scale down significantly
    // At zoom 6+ (regional view): scale up
    const zoomScale = Math.pow(2, zoom - 2)  // Exponential scaling
    const minZoomScale = 0.3  // Don't go below 30% at global zoom
    const maxZoomScale = 4.0  // Don't exceed 400% at close zoom
    const scale = Math.max(minZoomScale, Math.min(maxZoomScale, zoomScale))

    console.log('[MapLayerManager] Generating layers with data:', {
        hotspots: data.hotspots?.length || 0,
        flows: data.flows?.length || 0,
        activeLayers,
        zoom,
        scale: scale.toFixed(2)
    })

    // Heatmap Layer (Gaussian Field)
    if (activeLayers.heatmap && data.hotspots && data.hotspots.length > 0) {
        console.log('[MapLayerManager] Adding HEATMAP layer')
        layers.push(
            new ScatterplotLayer({
                id: 'gaussian-heatmap-layer',
                data: data.hotspots,
                visible: true,
                pickable: true,
                radiusScale: scale,  // Zoom-responsive scaling
                radiusMinPixels: 40,  // Smaller minimum for global view
                radiusMaxPixels: 300,
                lineWidthMinPixels: 0,
                opacity: 0.65,
                filled: true,
                stroked: false,
                getPosition: (d: CountryHotspot) => [d.longitude, d.latitude],
                getRadius: (d: CountryHotspot) => {
                    // Base size adapts to zoom
                    const baseRadius = 50
                    const intensityBonus = d.intensity * 100
                    return baseRadius + intensityBonus
                },
                getFillColor: (d: CountryHotspot) => {
                    // Meteorological radar colors - more subtle and professional
                    const intensity = d.intensity
                    if (intensity < 0.2) return [30, 80, 200, 80]         // Deep blue, subtle
                    if (intensity < 0.4) return [50, 150, 255, 110]       // Sky blue
                    if (intensity < 0.6) return [50, 230, 150, 140]       // Green
                    if (intensity < 0.8) return [255, 200, 50, 170]       // Yellow-orange
                    return [255, 60, 60, 200]                              // Red, prominent
                }
            })
        )
    }

    // Flows Layer (Arcs)
    if (activeLayers.flows && data.flows && data.flows.length > 0) {
        console.log('[MapLayerManager] Adding FLOWS layer')
        layers.push(
            new ArcLayer({
                id: 'flows-arc-layer',
                data: data.flows,
                visible: true,
                pickable: true,
                widthUnits: 'pixels',
                widthScale: scale,  // Zoom-responsive scaling
                widthMinPixels: 8,   // Thinner at global zoom
                widthMaxPixels: 50,
                getWidth: (d: Flow) => Math.max(8, d.heat * 20),  // Reduced base width
                getSourcePosition: (d: Flow) => d.from_coords,
                getTargetPosition: (d: Flow) => d.to_coords,
                getSourceColor: [100, 180, 255, 180],  // Softer cyan
                getTargetColor: [255, 100, 100, 180],  // Softer red
                greatCircle: true
            })
        )
    }

    // Markers Layer (Hotspots)
    if (activeLayers.markers && data.hotspots && data.hotspots.length > 0) {
        console.log('[MapLayerManager] Adding MARKERS layer')
        layers.push(
            new ScatterplotLayer({
                id: 'markers-node-layer',
                data: data.hotspots,
                pickable: true,
                opacity: 0.95,
                stroked: true,
                filled: true,
                radiusScale: scale,  // Zoom-responsive scaling
                radiusMinPixels: 12,  // Smaller at global zoom
                radiusMaxPixels: 60,
                lineWidthMinPixels: 2,
                getPosition: (d: CountryHotspot) => [d.longitude, d.latitude],
                getRadius: (d: CountryHotspot) => 15 + (d.topic_count * 2),  // Reduced base size
                getFillColor: (d: CountryHotspot) => {
                    // Clearer marker colors
                    if (d.intensity < 0.3) return [80, 150, 255, 255]    // Blue
                    if (d.intensity < 0.6) return [255, 200, 60, 255]    // Yellow
                    return [255, 70, 70, 255]                             // Red
                },
                getLineColor: [255, 255, 255, 255],  // Bright white outline
                onClick: (info: any) => {
                    if (info.object) {
                        console.log('Clicked:', info.object.country_name)
                    }
                }
            })
        )
    }

    // TEST LAYER REMOVED - No longer needed, rendering confirmed working

    console.log('[MapLayerManager] Total layers generated:', layers.length)
    return layers
}
