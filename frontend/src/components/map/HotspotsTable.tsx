import React, { useMemo } from 'react'
import { useMapStore } from '../../store/mapStore'

const HotspotsTable: React.FC = () => {
  const { flowsData, loading, error } = useMapStore()

  // Sort hotspots by intensity (highest first)
  const sortedHotspots = useMemo(() => {
    if (!flowsData?.hotspots) return []
    return [...flowsData.hotspots].sort((a, b) => b.intensity - a.intensity)
  }, [flowsData])

  if (loading && !flowsData) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
        Loading data...
      </div>
    )
  }

  if (error) {
    return (
      <div
        style={{
          padding: '1rem',
          backgroundColor: '#fee',
          border: '1px solid #fcc',
          borderRadius: '8px',
          color: '#c00',
        }}
      >
        <strong>Error:</strong> {error}
      </div>
    )
  }

  if (!sortedHotspots.length) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
        No data available. Adjust time window or filters.
      </div>
    )
  }

  return (
    <div>
      <h2 style={{ marginTop: 0, marginBottom: '1.5rem', color: '#213547' }}>
        Narrative Activity by Country
      </h2>
      <p style={{ marginBottom: '1.5rem', color: '#666', fontSize: '0.9rem' }}>
        Showing {sortedHotspots.length} countries with trending topics. Data synchronized with map view.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {sortedHotspots.map((hotspot) => (
          <div
            key={hotspot.country_code}
            style={{
              backgroundColor: 'white',
              padding: '1.5rem',
              borderRadius: '8px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              border: '1px solid #e5e7eb',
            }}
          >
            {/* Country Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#213547' }}>
                  {hotspot.country_name} ({hotspot.country_code})
                </h3>
                <div style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.25rem' }}>
                  {hotspot.topic_count} topics • Intensity: {(hotspot.intensity * 100).toFixed(0)}%
                </div>
              </div>
              <div
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  backgroundColor: getIntensityColor(hotspot.intensity),
                  color: 'white',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                }}
              >
                {getIntensityLabel(hotspot.intensity)}
              </div>
            </div>

            {/* Top Topics */}
            {hotspot.top_topics && hotspot.top_topics.length > 0 && (
              <div>
                <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem', fontWeight: 600 }}>
                  Top Topics:
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {hotspot.top_topics.slice(0, 5).map((topic, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '0.5rem 0.75rem',
                        backgroundColor: '#f9fafb',
                        borderRadius: '4px',
                        fontSize: '0.875rem',
                      }}
                    >
                      <span style={{ color: '#374151', flex: 1 }}>{topic.label}</span>
                      <span
                        style={{
                          color: '#6b7280',
                          fontWeight: 600,
                          marginLeft: '1rem',
                        }}
                      >
                        {topic.count} mentions
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Confidence Indicator */}
            <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#9ca3af' }}>
              Confidence: {(hotspot.confidence * 100).toFixed(0)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// Helper functions
const getIntensityColor = (intensity: number): string => {
  if (intensity > 0.7) return '#ef4444' // Red (high)
  if (intensity > 0.4) return '#f59e0b' // Orange (medium)
  return '#3b82f6' // Blue (low)
}

const getIntensityLabel = (intensity: number): string => {
  if (intensity > 0.7) return 'High Activity'
  if (intensity > 0.4) return 'Medium Activity'
  return 'Low Activity'
}

export default HotspotsTable
