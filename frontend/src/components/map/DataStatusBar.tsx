import React, { useState, useEffect } from 'react'
import { useMapStore } from '../../store/mapStore'
import { formatDistanceToNow } from 'date-fns'

type HealthStatus = 'healthy' | 'degraded' | 'down'

const DataStatusBar: React.FC = () => {
  const { lastUpdate, loading, error, fetchFlowsData, fetchHexmapData, viewMode, flowsData, hexmapData } = useMapStore()
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('healthy')
  const [showErrorDetails, setShowErrorDetails] = useState(false)

  // Determine health status based on error and data availability
  useEffect(() => {
    const checkHealth = () => {
      if (error) {
        // Check if we have any data despite the error
        const hasData = (viewMode === 'classic' && flowsData) || (viewMode === 'heatmap' && hexmapData)
        setHealthStatus(hasData ? 'degraded' : 'down')
      } else if (loading) {
        setHealthStatus('degraded')
      } else {
        setHealthStatus('healthy')
      }
    }

    checkHealth()
  }, [error, loading, viewMode, flowsData, hexmapData])

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

  const handleRetry = () => {
    if (viewMode === 'classic') {
      fetchFlowsData()
    } else {
      fetchHexmapData()
    }
  }

  const getErrorDetails = () => {
    if (!error) return null

    const isNetworkError = error.toLowerCase().includes('network') || error.toLowerCase().includes('fetch')
    const is404 = error.toLowerCase().includes('404')
    const is500 = error.toLowerCase().includes('500') || error.toLowerCase().includes('503')

    return {
      type: is404 ? '404 Not Found' : is500 ? 'Server Error' : isNetworkError ? 'Network Error' : 'Error',
      endpoint: viewMode === 'classic' ? '/v1/flows' : '/v1/hexmap',
      suggestion: is404
        ? 'Endpoint not available. Backend may need updating.'
        : is500
        ? 'Backend service error. Please try again.'
        : isNetworkError
        ? 'Cannot connect to backend. Check if services are running.'
        : 'An unexpected error occurred.',
    }
  }

  const errorDetails = getErrorDetails()

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
        flexDirection: 'column',
        gap: '0.5rem',
        fontSize: '0.85rem',
        zIndex: 10,
      }}
    >
      {/* Main status bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
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

          {loading && (
            <div style={{ opacity: 0.8 }}>
              Loading {viewMode} data...
            </div>
          )}

          {error && (
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <div style={{ color: '#ff6b6b', cursor: 'pointer' }} onClick={() => setShowErrorDetails(!showErrorDetails)}>
                {errorDetails?.type}: {viewMode === 'classic' ? 'Flows' : 'Hexmap'} endpoint
                <span style={{ marginLeft: '0.5rem' }}>{showErrorDetails ? '▲' : '▼'}</span>
              </div>
              <button
                onClick={handleRetry}
                style={{
                  padding: '0.25rem 0.75rem',
                  fontSize: '0.75rem',
                  backgroundColor: '#4299e1',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Retry
              </button>
            </div>
          )}
        </div>

        {/* Right side - Sources */}
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div style={{ opacity: 0.8 }}>Data sources:</div>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <span title="GDELT Global Knowledge Graph">📰 GDELT</span>
            <span title="Google Trends (currently degraded)" style={{ opacity: 0.5 }}>
              📈 Trends
            </span>
            <span title="Wikipedia (currently degraded)" style={{ opacity: 0.5 }}>
              📚 Wiki
            </span>
          </div>
        </div>
      </div>

      {/* Error details panel */}
      {error && showErrorDetails && errorDetails && (
        <div
          style={{
            backgroundColor: 'rgba(255, 107, 107, 0.1)',
            border: '1px solid rgba(255, 107, 107, 0.3)',
            borderRadius: '4px',
            padding: '0.75rem',
            fontSize: '0.8rem',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div>
              <strong>Endpoint:</strong> {errorDetails.endpoint}
            </div>
            <div>
              <strong>Error:</strong> {error}
            </div>
            <div>
              <strong>Suggestion:</strong> {errorDetails.suggestion}
            </div>
            <div style={{ opacity: 0.7, fontSize: '0.75rem', marginTop: '0.25rem' }}>
              💡 Check browser console (F12) for detailed error logs
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DataStatusBar
