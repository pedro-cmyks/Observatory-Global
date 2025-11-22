import { useMemo, useState } from 'react'
import { useMapStore } from '../../../store/mapStore'
// @ts-ignore - deck.gl types not available
import { ScatterplotLayer } from '@deck.gl/layers'

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

        console.log('[useGaussianRadarLayer] Creating gaussian field with', data.length, 'hotspots')

        // FIX: HeatmapLayer doesn't work with globe projection
        // Using ScatterplotLayer with large radius + low opacity for gaussian effect
        return new ScatterplotLayer({
            id: 'gaussian-radar-layer',
            data: data,
            visible: true,
            pickable: true,

            // RADAR PARAMETERS - Large blurred circles for field effect
            radiusScale: 1,
            radiusMinPixels: 80,   // Large minimum for gaussian field
            radiusMaxPixels: 300,  // Massive for storm effect
            lineWidthMinPixels: 0,
            opacity: 0.4,          // Low opacity for layering effect
            filled: true,
            stroked: false,

            // Data accessors
            getPosition: (d: any) => [d.longitude, d.latitude],
            getRadius: (d: any) => {
                // Larger radius for higher intensity hotspots
                const baseRadius = 100
                const intensityBonus = d.intensity * 200 // 0-200 bonus
                return baseRadius + intensityBonus
            },
            getFillColor: (d: any) => {
                // Weather radar color scheme based on intensity
                const intensity = d.intensity
                if (intensity < 0.2) return [0, 0, 128, 100]       // Deep blue (very cold)
                if (intensity < 0.4) return [0, 128, 255, 140]     // Cyan (cold)
                if (intensity < 0.6) return [0, 255, 128, 180]     // Green (moderate)
                if (intensity < 0.8) return [255, 255, 0, 220]     // Yellow (warm)
                return [255, 0, 0, 255]                            // Red (very hot)
            },

            // Interaction
            onHover: (info: any) => {
                setHoverInfo(info)
                return true
            },

            updateTriggers: {
                getPosition: [flowsData],
                getRadius: [flowsData],
                getFillColor: [flowsData]
            }
        })
    }, [flowsData, selectedCountries])

    return { layer, hoverInfo }
}

