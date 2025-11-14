import React, { useState, useEffect } from 'react'
import { healthCheck } from '../lib/api'
import MapContainer from '../components/map/MapContainer'
import HotspotsTable from '../components/map/HotspotsTable'
import ErrorBoundary from '../components/ErrorBoundary'

const Home: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<'checking' | 'ok' | 'error'>('checking')

  // Check API health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await healthCheck()
        setApiStatus('ok')
      } catch (err) {
        console.error('API health check failed:', err)
        setApiStatus('error')
      }
    }
    checkHealth()
  }, [])

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      {/* Header */}
      <header
        style={{
          backgroundColor: '#646cff',
          color: 'white',
          padding: '2rem',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}
      >
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <h1 style={{ margin: '0 0 0.5rem 0', fontSize: '2.5rem' }}>
            🌍 Observatory Global
          </h1>
          <p style={{ margin: 0, fontSize: '1.1rem', opacity: 0.9 }}>
            Global Narrative Observatory - Real-time Trends Analysis
          </p>
          <div style={{ marginTop: '1rem', fontSize: '0.9rem' }}>
            API Status:{' '}
            {apiStatus === 'checking' && '⏳ Checking...'}
            {apiStatus === 'ok' && '✅ Connected'}
            {apiStatus === 'error' && '❌ Disconnected'}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
        {/* Interactive Map */}
        <div style={{ marginBottom: '2rem' }}>
          <ErrorBoundary>
            <MapContainer />
          </ErrorBoundary>
        </div>

        {/* Country Hotspots Table - Synchronized with Map */}
        <div
          style={{
            backgroundColor: 'white',
            padding: '2rem',
            borderRadius: '8px',
            marginBottom: '2rem',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          }}
        >
          <HotspotsTable />
        </div>
      </main>

      {/* Footer */}
      <footer
        style={{
          backgroundColor: '#333',
          color: 'white',
          padding: '2rem',
          textAlign: 'center',
          marginTop: '4rem',
        }}
      >
        <p style={{ margin: 0 }}>
          Observatory Global © 2025 | Data sources: GDELT, Google Trends, Wikipedia
        </p>
      </footer>
    </div>
  )
}

export default Home
