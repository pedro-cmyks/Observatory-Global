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
        console.log('[useFlowLayer] Sample flow heat values:', flows.slice(0, 3).map(f => ({
            from: f.from_country,
            to: f.to_country,
            heat: f.heat,
            width: Math.max(20, f.heat * 40)
        })))

        return new ArcLayer({
            id: 'flow-layer',
            data: flows,
            visible: true,
            pickable: true,

            // CRITICAL: Use pixel-based width for zoom-independence
            widthUnits: 'pixels',     // Width in screen pixels, not meters
            widthScale: 1,            // No additional scaling
            widthMinPixels: 25,       // Increased for maximum global visibility
            widthMaxPixels: 60,       // Increased cap for prominence

            // WINDS - VERY THICK lines visible at GLOBAL scale
            getWidth: (d: Flow) => Math.max(25, d.heat * 50), // Increased to 25-50px range
            getSourcePosition: (d: Flow) => d.from_coords,
            getTargetPosition: (d: Flow) => d.to_coords,

            // Very bright gradient showing direction: Cyan (source) → Red (target)
            // Maximum opacity for visibility
            getSourceColor: [80, 200, 255, 240],   // Bright cyan (origin) - very high alpha
            getTargetColor: [255, 80, 80, 240],    // Bright red (destination) - very high alpha

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
