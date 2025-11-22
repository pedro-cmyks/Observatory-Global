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
            widthMinPixels: 18,       // Increased from 12 for better global visibility
            widthMaxPixels: 50,       // Increased cap

            // WINDS - THICK lines visible at GLOBAL scale
            getWidth: (d: Flow) => Math.max(20, d.heat * 40), // Increased from 15/30 to 20/40
            getSourcePosition: (d: Flow) => d.from_coords,
            getTargetPosition: (d: Flow) => d.to_coords,

            // Bright gradient showing direction: Blue (source) → Red (target)
            // Increased opacity for better visibility
            getSourceColor: [100, 200, 255, 220],  // Bright cyan (origin) - increased alpha
            getTargetColor: [255, 100, 100, 220],  // Bright red (destination) - increased alpha

            // FIX: Remove getHeight - let greatCircle handle arc elevation naturally
            // The getHeight parameter was causing z-ordering issues with globe projection
            greatCircle: true,       // Follow Earth's curvature (handles elevation automatically)

            updateTriggers: {
                getWidth: [flowsData],
                getSourcePosition: [flowsData],
                getTargetPosition: [flowsData]
            }
        })
    }, [flowsData, selectedCountries])

    return { layer }
}
