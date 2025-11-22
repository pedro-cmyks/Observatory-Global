import { useMemo } from 'react'
import { useMapStore } from '../../../store/mapStore'
// @ts-ignore - deck.gl types not available
import { ArcLayer } from '@deck.gl/layers'
import type { Flow } from '../../../lib/mapTypes'

export const useFlowLayer = () => {
    const { flowsData, selectedCountries } = useMapStore()

    const layer = useMemo(() => {
        if (!flowsData?.flows || flowsData.flows.length === 0) {
            return null
        }

        // Filter flows by selected countries
        let flows = flowsData.flows
        if (selectedCountries.length > 0) {
            flows = flows.filter(
                (flow) =>
                    selectedCountries.includes(flow.from_country) ||
                    selectedCountries.includes(flow.to_country)
            )
        }

        console.log('[useFlowLayer] Rendering', flows.length, 'flows with GLOBAL-SCALE visibility')

        return new ArcLayer({
            id: 'flow-layer',
            data: flows,
            visible: true,
            pickable: true,

            // CRITICAL: Use pixel-based width for zoom-independence
            widthUnits: 'pixels',     // Width in screen pixels, not meters
            widthScale: 1,            // No additional scaling
            widthMinPixels: 12,       // Minimum 12px for global visibility
            widthMaxPixels: 40,       // Cap at 40px

            // WINDS - THICK lines visible at GLOBAL scale
            getWidth: (d: Flow) => Math.max(15, d.heat * 30), // 15-30px for global visibility
            getSourcePosition: (d: Flow) => d.from_coords,
            getTargetPosition: (d: Flow) => d.to_coords,

            // Bright gradient showing direction: Blue (source) → Red (target)
            getSourceColor: [100, 200, 255, 255],  // Bright cyan (origin)
            getTargetColor: [255, 100, 100, 255],  // Bright red (destination)

            getHeight: 1.5,          // Much higher arc (1.5x radius) to avoid clipping into globe
            greatCircle: true,       // Follow Earth's curvature

            updateTriggers: {
                getWidth: [flowsData],
                getSourcePosition: [flowsData],
                getTargetPosition: [flowsData]
            }
        })
    }, [flowsData, selectedCountries])

    return { layer }
}
