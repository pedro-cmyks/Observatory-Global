import React, { useState, useEffect } from 'react'
import { useMapStore } from '../../store/mapStore'
import { formatDistanceToNow } from 'date-fns'

const refreshIntervals = [
  { value: 60000, label: '1 min' },
  { value: 300000, label: '5 min' },
  { value: 900000, label: '15 min' },
]

const AutoRefreshControl: React.FC = () => {
  const {
    autoRefresh,
    setAutoRefresh,
    refreshInterval,
    setRefreshInterval,
    fetchFlowsData,
    lastUpdate,
    loading,
  } = useMapStore()

  const [countdown, setCountdown] = useState(refreshInterval)

  useEffect(() => {
    if (!autoRefresh || !lastUpdate) return

    const interval = setInterval(() => {
      const elapsed = Date.now() - lastUpdate.getTime()
      const remaining = Math.max(0, refreshInterval - elapsed)
      setCountdown(remaining)
    }, 1000)

    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval, lastUpdate])

  const handleManualRefresh = () => {
    fetchFlowsData()
  }

  const formatCountdown = (ms: number): string => {
    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
  }

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
        Auto-Refresh
      </div>

      <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <input
          type="checkbox"
          checked={autoRefresh}
          onChange={(e) => setAutoRefresh(e.target.checked)}
          style={{ cursor: 'pointer' }}
        />
        <span style={{ fontSize: '0.75rem' }}>Enabled</span>
      </label>

      {autoRefresh && (
        <>
          <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '0.5rem' }}>
            {refreshIntervals.map((interval) => (
              <button
                key={interval.value}
                onClick={() => setRefreshInterval(interval.value)}
                style={{
                  flex: 1,
                  padding: '0.4rem 0.5rem',
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  backgroundColor: refreshInterval === interval.value ? '#646cff' : '#f0f0f0',
                  color: refreshInterval === interval.value ? 'white' : '#333',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                {interval.label}
              </button>
            ))}
          </div>

          <div style={{ fontSize: '0.7rem', color: '#666', textAlign: 'center' }}>
            Next: {formatCountdown(countdown)}
          </div>
        </>
      )}

      <button
        onClick={handleManualRefresh}
        disabled={loading}
        style={{
          width: '100%',
          marginTop: '0.5rem',
          padding: '0.5rem',
          fontSize: '0.75rem',
          fontWeight: 600,
          backgroundColor: loading ? '#ccc' : '#646cff',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: loading ? 'not-allowed' : 'pointer',
        }}
      >
        {loading ? 'Refreshing...' : 'Refresh Now'}
      </button>

      {lastUpdate && (
        <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '0.5rem', textAlign: 'center' }}>
          Updated {formatDistanceToNow(lastUpdate, { addSuffix: true })}
        </div>
      )}
    </div>
  )
}

export default AutoRefreshControl
