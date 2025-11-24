import { useMemo, useState } from 'react'
import { useMapStore } from '../../../store/mapStore'
// @ts-ignore - deck.gl types not available
import { ScatterplotLayer } from '@deck.gl/layers'
import type { CountryHotspot } from '../../../lib/mapTypes'

export const useNodeLayer = () => {
    const { flowsData, setSelectedHotspot, selectedCountries } = useMapStore()
    const [hoverInfo, setHoverInfo] = useState<any>(null)

    const layer = useMemo(() => {
        if (!flowsData?.hotspots || flowsData.hotspots.length === 0) {
            return null
        }

        const data = selectedCountries.length > 0
            ? flowsData.hotspots.filter(h => selectedCountries.includes(h.country_code))
            : flowsData.hotspots

        return new ScatterplotLayer({
            id: 'node-layer',
            data: data,
            visible: true,
            pickable: true,
            opacity: 0.95,          // Increased opacity
            stroked: true,
            filled: true,
            radiusScale: 1,
            radiusMinPixels: 25,    // Increased from 20
            radiusMaxPixels: 70,    // Increased from 60
            lineWidthMinPixels: 3,  // Thicker stroke
            getPosition: (d: CountryHotspot) => {
                const pos: [number, number] = [d.longitude, d.latitude]
                console.log(`Node ${d.country_code} at:`, pos)
                return pos
            },
            getRadius: (d: CountryHotspot) => 25 + (d.topic_count * 3),  // Increased base
            getFillColor: (d: CountryHotspot) => {
                // More saturated colors
                if (d.intensity < 0.3) return [70, 140, 255, 240]    // Brighter blue
                if (d.intensity < 0.6) return [255, 200, 50, 240]    // Brighter yellow
                return [255, 60, 60, 240]                             // Brighter red
            },
            getLineColor: [255, 255, 255, 200],  // Slightly more opaque stroke
            onHover: (info: any) => {
                setHoverInfo(info)
                return true
            },
            onClick: (info: any) => {
                if (info.object) setSelectedHotspot(info.object)
                return true
            },
        })
    }, [flowsData, selectedCountries, setSelectedHotspot])

    return { layer, hoverInfo }
}
