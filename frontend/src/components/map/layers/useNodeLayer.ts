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
            visible: true, // Explicitly set visible
            pickable: true,
            opacity: 0.9,
            stroked: true,
            filled: true,
            radiusScale: 1,
            radiusMinPixels: 20,
            radiusMaxPixels: 60,
            lineWidthMinPixels: 2,
            getPosition: (d: CountryHotspot) => {
                const pos: [number, number] = [d.longitude, d.latitude]
                console.log(`Node ${d.country_code} at:`, pos)
                return pos
            },
            getRadius: (d: CountryHotspot) => 20 + (d.topic_count * 3),
            getFillColor: (d: CountryHotspot) => {
                if (d.intensity < 0.3) return [59, 130, 246, 230]
                if (d.intensity < 0.6) return [251, 191, 36, 230]
                return [239, 68, 68, 230]
            },
            getLineColor: [255, 255, 255, 180],
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
