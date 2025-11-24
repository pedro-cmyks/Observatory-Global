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

            // RADAR PARAMETERS - Larger blurred circles for prominent field effect
            radiusScale: 1,
            radiusMinPixels: 150,   // Increased for more prominent field
            radiusMaxPixels: 500,   // Massive for weather storm effect
            lineWidthMinPixels: 0,
            opacity: 0.55,          // Increased for better visibility
            filled: true,
            stroked: false,

            // Data accessors
            getPosition: (d: any) => [d.longitude, d.latitude],
            getRadius: (d: any) => {
                // Much larger radius for higher intensity hotspots
                const baseRadius = 150
                const intensityBonus = d.intensity * 350 // 0-350 bonus
                return baseRadius + intensityBonus
            },
            getFillColor: (d: any) => {
                // Meteorological color scheme - more vibrant and visible
                const intensity = d.intensity
                if (intensity < 0.2) return [20, 50, 180, 130]        // Deep blue (very cold)
                if (intensity < 0.4) return [40, 160, 255, 170]       // Bright cyan (cold)
                if (intensity < 0.6) return [40, 255, 140, 210]       // Bright green (moderate)
                if (intensity < 0.8) return [255, 230, 40, 240]       // Bright yellow (warm)
                return [255, 40, 40, 255]                             // Bright red (very hot)
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

