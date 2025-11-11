import React, { useState, useEffect } from 'react'
import { getTopTrends, healthCheck, Topic } from '../lib/api'
import CountryPicker from '../components/CountryPicker'
import TopicList from '../components/TopicList'
import MapPlaceholder from '../components/MapPlaceholder'

const Home: React.FC = () => {
  const [country, setCountry] = useState('CO')
  const [topics, setTopics] = useState<Topic[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
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

  const loadTrends = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await getTopTrends(country, 10)
      setTopics(data.topics)
    } catch (err: any) {
      console.error('Error loading trends:', err)
      setError(err.message || 'Failed to load trends')
    } finally {
      setLoading(false)
    }
  }

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
        {/* Map Placeholder */}
        <MapPlaceholder />

        {/* Controls */}
        <div
          style={{
            backgroundColor: 'white',
            padding: '2rem',
            borderRadius: '8px',
            marginBottom: '2rem',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          }}
        >
          <h2 style={{ marginTop: 0, color: '#213547' }}>Explore Trends</h2>

          <CountryPicker
            selectedCountry={country}
            onCountryChange={setCountry}
            disabled={loading}
          />

          <button
            onClick={loadTrends}
            disabled={loading || apiStatus !== 'ok'}
            style={{
              padding: '0.75rem 2rem',
              fontSize: '1rem',
              fontWeight: 600,
              backgroundColor: loading ? '#ccc' : '#646cff',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Loading...' : 'Load Trends'}
          </button>

          {error && (
            <div
              style={{
                marginTop: '1rem',
                padding: '1rem',
                backgroundColor: '#fee',
                border: '1px solid #fcc',
                borderRadius: '8px',
                color: '#c00',
              }}
            >
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>

        {/* Topics */}
        {topics.length > 0 && (
          <div
            style={{
              backgroundColor: '#f9f9f9',
              padding: '2rem',
              borderRadius: '8px',
            }}
          >
            <TopicList topics={topics} />
          </div>
        )}
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
