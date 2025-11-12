import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMapStore } from '../../store/mapStore'

const CountrySidebar: React.FC = () => {
  const { selectedHotspot, setSelectedHotspot } = useMapStore()

  const getIntensityColor = (intensity: number): string => {
    if (intensity < 0.3) return '#3B82F6'
    if (intensity < 0.6) return '#FCD34D'
    return '#EF4444'
  }

  const getIntensityLabel = (intensity: number): string => {
    if (intensity < 0.3) return 'Low'
    if (intensity < 0.6) return 'Medium'
    return 'High'
  }

  return (
    <AnimatePresence>
      {selectedHotspot && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelectedHotspot(null)}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.3)',
              zIndex: 15,
            }}
          />

          {/* Sidebar */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            style={{
              position: 'absolute',
              top: 0,
              right: 0,
              bottom: 0,
              width: '350px',
              maxWidth: '90vw',
              backgroundColor: 'white',
              boxShadow: '-2px 0 8px rgba(0,0,0,0.2)',
              zIndex: 20,
              overflowY: 'auto',
            }}
          >
            {/* Header */}
            <div
              style={{
                padding: '1.5rem',
                borderBottom: '1px solid #e0e0e0',
                position: 'sticky',
                top: 0,
                backgroundColor: 'white',
                zIndex: 1,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <h2 style={{ margin: '0 0 0.5rem 0', fontSize: '1.5rem', color: '#213547' }}>
                    {selectedHotspot.country_name}
                  </h2>
                  <div style={{ fontSize: '0.9rem', color: '#666' }}>
                    Code: {selectedHotspot.country_code}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedHotspot(null)}
                  style={{
                    padding: '0.5rem',
                    fontSize: '1.2rem',
                    backgroundColor: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: '#666',
                  }}
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Content */}
            <div style={{ padding: '1.5rem' }}>
              {/* Intensity Gauge */}
              <div style={{ marginBottom: '2rem' }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '0.5rem',
                  }}
                >
                  <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#333' }}>
                    Intensity
                  </span>
                  <span
                    style={{
                      fontSize: '0.9rem',
                      fontWeight: 600,
                      color: getIntensityColor(selectedHotspot.intensity),
                    }}
                  >
                    {getIntensityLabel(selectedHotspot.intensity)} (
                    {(selectedHotspot.intensity * 100).toFixed(0)}%)
                  </span>
                </div>
                <div
                  style={{
                    width: '100%',
                    height: '12px',
                    backgroundColor: '#f0f0f0',
                    borderRadius: '6px',
                    overflow: 'hidden',
                  }}
                >
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${selectedHotspot.intensity * 100}%` }}
                    transition={{ duration: 0.5 }}
                    style={{
                      height: '100%',
                      backgroundColor: getIntensityColor(selectedHotspot.intensity),
                    }}
                  />
                </div>
              </div>

              {/* Stats */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '1rem',
                  marginBottom: '2rem',
                }}
              >
                <div
                  style={{
                    padding: '1rem',
                    backgroundColor: '#f9f9f9',
                    borderRadius: '8px',
                  }}
                >
                  <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.25rem' }}>
                    Topics
                  </div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 600, color: '#213547' }}>
                    {selectedHotspot.topic_count}
                  </div>
                </div>
                <div
                  style={{
                    padding: '1rem',
                    backgroundColor: '#f9f9f9',
                    borderRadius: '8px',
                  }}
                >
                  <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.25rem' }}>
                    Confidence
                  </div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 600, color: '#213547' }}>
                    {(selectedHotspot.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              {/* Top Topics */}
              <div>
                <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#213547' }}>
                  Top Topics
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {selectedHotspot.top_topics.map((topic, index) => (
                    <div
                      key={index}
                      style={{
                        padding: '0.75rem',
                        backgroundColor: '#f9f9f9',
                        borderRadius: '6px',
                        borderLeft: `3px solid ${getIntensityColor(selectedHotspot.intensity)}`,
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                        }}
                      >
                        <span style={{ fontSize: '0.9rem', fontWeight: 500, color: '#333' }}>
                          {topic.label}
                        </span>
                        <span
                          style={{
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            color: '#646cff',
                            backgroundColor: '#eef',
                            padding: '0.2rem 0.5rem',
                            borderRadius: '12px',
                          }}
                        >
                          {topic.count}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

export default CountrySidebar
