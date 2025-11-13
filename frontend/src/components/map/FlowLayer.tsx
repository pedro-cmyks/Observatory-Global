import React, { useMemo } from 'react'
import { Layer, Source } from 'react-map-gl'
// @ts-ignore - turf types exist but package.json exports issue
import * as turf from '@turf/turf'
import { useMapStore } from '../../store/mapStore'
import { Flow } from '../../lib/mapTypes'

const createArcFeature = (flow: Flow) => {
  const from = turf.point(flow.from_coords)
  const to = turf.point(flow.to_coords)

  // Create a great circle arc
  const arc = turf.greatCircle(from, to, { npoints: 100 })

  return {
    type: 'Feature' as const,
    properties: {
      heat: flow.heat,
      similarity: flow.similarity,
      from: flow.from_country,
      to: flow.to_country,
      shared_topics: flow.shared_topics.join(', '),
      time_delta: flow.time_delta_minutes,
    },
    geometry: arc.geometry,
  }
}

const FlowLayer: React.FC = () => {
  const { flowsData, selectedCountries } = useMapStore()

  const geojsonData = useMemo(() => {
    if (!flowsData?.flows) {
      return {
        type: 'FeatureCollection' as const,
        features: [],
      }
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

    const features = flows.map(createArcFeature)

    return {
      type: 'FeatureCollection' as const,
      features,
    }
  }, [flowsData, selectedCountries])

  if (!geojsonData.features.length) return null

  return (
    <Source id="flows" type="geojson" data={geojsonData}>
      {/* Base flow lines */}
      <Layer
        id="flow-lines"
        type="line"
        paint={{
          'line-color': [
            'interpolate',
            ['linear'],
            ['get', 'heat'],
            0, '#3B82F6',
            0.5, '#FCD34D',
            1, '#EF4444'
          ],
          'line-width': [
            'interpolate',
            ['linear'],
            ['get', 'heat'],
            0, 1,
            1, 4
          ],
          'line-opacity': [
            'interpolate',
            ['linear'],
            ['get', 'heat'],
            0, 0.3,
            1, 0.8
          ],
        }}
      />

      {/* Animated pulse for high heat flows */}
      <Layer
        id="flow-pulse"
        type="line"
        paint={{
          'line-color': '#FFFFFF',
          'line-width': 2,
          'line-opacity': [
            'case',
            ['>', ['get', 'heat'], 0.7],
            0.6,
            0
          ],
        }}
      />
    </Source>
  )
}

export default FlowLayer
