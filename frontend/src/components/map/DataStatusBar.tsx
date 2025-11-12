import React, { useState, useEffect } from 'react'
import { useMapStore } from '../../store/mapStore'
import { formatDistanceToNow } from 'date-fns'

type HealthStatus = 'healthy' | 'degraded' | 'down'

const DataStatusBar: React.FC = () => {
  const { lastUpdate, loading, error } = useMapStore()
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('healthy')

  // Mock health check - in production, this would be a real API call
  useEffect(() => {
    const checkHealth = () => {
      if (error) {
        setHealthStatus('down')
      } else if (loading) {
        setHealthStatus('degraded')
      } else {
        setHealthStatus('healthy')
      }
    }

    checkHealth()
  }, [error, loading])

  const getStatusIcon = (status: HealthStatus) => {
    switch (status) {
      case 'healthy':
        return '🟢'
      case 'degraded':
        return '🟡'
      case 'down':
        return '🔴'
    }
  }

  const getStatusLabel = (status: HealthStatus) => {
    switch (status) {
      case 'healthy':
        return 'Healthy'
      case 'degraded':
        return 'Degraded'
      case 'down':
        return 'Down'
    }
  }

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: 'rgba(33, 37, 71, 0.95)',
        color: 'white',
        padding: '0.75rem 1.5rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '0.85rem',
        zIndex: 10,
      }}
    >
      {/* Left side - Status */}
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>{getStatusIcon(healthStatus)}</span>
          <span style={{ fontWeight: 600 }}>Backend: {getStatusLabel(healthStatus)}</span>
        </div>

        {lastUpdate && !error && (
          <div style={{ opacity: 0.8 }}>
            Updated {formatDistanceToNow(lastUpdate, { addSuffix: true })}
          </div>
        )}

        {error && (
          <div style={{ color: '#ff6b6b' }}>
            Error: {error}
          </div>
        )}
      </div>

      {/* Right side - Sources */}
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <div style={{ opacity: 0.8 }}>Active sources:</div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <span title="GDELT">📰 GDELT</span>
          <span title="Google Trends">📈 Trends</span>
          <span title="Wikipedia">📚 Wiki</span>
        </div>
      </div>
    </div>
  )
}

export default DataStatusBar
