import { useMemo, useState } from 'react'
import { useMapStore } from '../../../store/mapStore'
// @ts-ignore - deck.gl types not available
import { HeatmapLayer } from '@deck.gl/aggregation-layers'

export const useGaussianHeatmapLayer = () => {
    const { flowsData, selectedCountries } = useMapStore()
    const [hoverInfo, setHoverInfo] = useState<any>(null)

    const layer = useMemo(() => {
        if (!flowsData?.hotspots || flowsData.hotspots.length === 0) {
            return null
        }

        // Filter by selected countries if any
        const data = selectedCountries.length > 0
            ? flowsData.hotspots.filter(h => selectedCountries.includes(h.country_code))
            : flowsData.hotspots

        // Transform to points that HeatmapLayer expects
        const heatmapData = data.flatMap(hotspot => {
            // Create multiple points per hotspot for better gaussian effect
            const baseWeight = hotspot.intensity * hotspot.topic_count
            return [{
                position: [hotspot.longitude, hotspot.latitude],
                weight: baseWeight
            }]
        })

        console.log('[useGaussianRadarLayer] Creating heatmap with', heatmapData.length, 'points')

        return new HeatmapLayer({
            id: 'gaussian-heatmap-layer',
            data: heatmapData,
            visible: true,
            pickable: true,

            // RADAR PARAMETERS - Weather-style visualization
            radiusPixels: 200,    // Massive gaussian blur for field effect
            intensity: 4,         // Higher intensity to make sparse points glow
            threshold: 0.01,      // Show even very faint signals

            // Weather radar color scheme: Cold (blue) → Hot (red)
            colorRange: [
                [0, 0, 128, 80],       // Deep blue (very cold)
                [0, 128, 255, 140],    // Cyan (cold)
                [0, 255, 128, 180],    // Green (moderate)
                [255, 255, 0, 220],    // Yellow (warm)
                [255, 128, 0, 240],    // Orange (hot)
                [255, 0, 0, 255]       // Red (very hot)
            ],

            // Data accessors
            getPosition: (d: any) => d.position,
            getWeight: (d: any) => d.weight,

            // Interaction
            onHover: (info: any) => {
                setHoverInfo(info)
                return true
            },

            updateTriggers: {
                getPosition: [flowsData],
                getWeight: [flowsData]
            }
        })
    }, [flowsData, selectedCountries])

    return { layer, hoverInfo }
}

