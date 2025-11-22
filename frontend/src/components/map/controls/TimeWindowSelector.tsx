import React from 'react'
import { useMapStore } from '../../../store/mapStore'
import { TimeWindow } from '../../../lib/mapTypes'

const timeWindows: { value: TimeWindow; label: string }[] = [
  { value: '1h', label: '1 Hour' },
  { value: '6h', label: '6 Hours' },
  { value: '12h', label: '12 Hours' },
  { value: '24h', label: '24 Hours' },
]

const TimeWindowSelector: React.FC = () => {
  const { timeWindow, setTimeWindow, loading } = useMapStore()

  return (
    <div
      style={{
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderRadius: '8px',
        padding: '0.75rem',
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
      }}
    >
      <div style={{ fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.5rem', color: '#333' }}>
        Time Window
      </div>
      <div style={{ display: 'flex', gap: '0.25rem' }}>
        {timeWindows.map((tw) => (
          <button
            key={tw.value}
            onClick={() => setTimeWindow(tw.value)}
            disabled={loading}
            style={{
              padding: '0.4rem 0.8rem',
              fontSize: '0.75rem',
              fontWeight: 600,
              backgroundColor: timeWindow === tw.value ? '#646cff' : '#f0f0f0',
              color: timeWindow === tw.value ? 'white' : '#333',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {tw.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default TimeWindowSelector
