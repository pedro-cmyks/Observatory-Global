import { useState, useEffect, useCallback } from 'react'
import Map from 'react-map-gl/maplibre'
import { DeckGL } from '@deck.gl/react'
import { ScatterplotLayer, ArcLayer } from '@deck.gl/layers'
import 'maplibre-gl/dist/maplibre-gl.css'
import './App.css'
import { getThemeLabel } from './lib/themeLabels'
import { SearchBar } from './components/SearchBar'
import { ThemeDetail } from './components/ThemeDetail'
import { Briefing } from './components/Briefing'

// Types
interface Node {
  id: string
  name: string
  lat: number
  lon: number
  intensity: number
  sentiment: number
  signalCount: number
}



interface Flow {
  source: [number, number]
  target: [number, number]
  sourceCountry: string
  targetCountry: string
  strength: number
}

interface CountryDetail {
  countryCode: string
  totalSignals: number
  sentiment: number
  themes: { name: string; count: number }[]
  sources: { name: string; count: number }[]
}

// Improved sentiment color with better visibility
const sentimentColor = (sentiment: number): [number, number, number, number] => {
  // Clamp sentiment to -1 to 1 range
  const s = Math.max(-1, Math.min(1, sentiment))

  if (s > 0.1) {
    // Positive: Green
    const intensity = Math.min(1, s * 2)
    return [50, Math.floor(200 + intensity * 55), 80, 220]
  } else if (s < -0.1) {
    // Negative: Red/Orange
    const intensity = Math.min(1, Math.abs(s) * 2)
    return [Math.floor(200 + intensity * 55), Math.floor(80 - intensity * 30), 50, 220]
  } else {
    // Neutral: Yellow/Amber
    return [250, 200, 50, 220]
  }
}

// Country names mapping
const countryNames: Record<string, string> = {
  'US': 'United States', 'UK': 'United Kingdom', 'GB': 'United Kingdom',
  'CA': 'Canada', 'AU': 'Australia', 'DE': 'Germany', 'FR': 'France',
  'JP': 'Japan', 'CN': 'China', 'IN': 'India', 'BR': 'Brazil',
  'MX': 'Mexico', 'RU': 'Russia', 'ZA': 'South Africa', 'NG': 'Nigeria',
  'EG': 'Egypt', 'SA': 'Saudi Arabia', 'AE': 'UAE', 'IL': 'Israel',
  'TR': 'Turkey', 'PK': 'Pakistan', 'ID': 'Indonesia', 'PH': 'Philippines',
  'VN': 'Vietnam', 'TH': 'Thailand', 'MY': 'Malaysia', 'SG': 'Singapore',
  'KR': 'South Korea', 'NZ': 'New Zealand', 'AR': 'Argentina', 'CL': 'Chile',
  'CO': 'Colombia', 'PE': 'Peru', 'VE': 'Venezuela', 'IT': 'Italy',
  'ES': 'Spain', 'PT': 'Portugal', 'NL': 'Netherlands', 'BE': 'Belgium',
  'CH': 'Switzerland', 'AT': 'Austria', 'PL': 'Poland', 'SE': 'Sweden',
  'NO': 'Norway', 'DK': 'Denmark', 'FI': 'Finland', 'IE': 'Ireland',
  'GR': 'Greece', 'UA': 'Ukraine', 'RO': 'Romania', 'CZ': 'Czech Republic',
  'HU': 'Hungary', 'IS': 'Iceland', 'AS': 'American Samoa', 'EI': 'Ireland'
}

function getCountryName(code: string): string {
  return countryNames[code] || code
}

// Country flag emoji from code
function getCountryFlag(code: string): string {
  const codePoints = code
    .toUpperCase()
    .split('')
    .map(char => 127397 + char.charCodeAt(0))
  return String.fromCodePoint(...codePoints)
}

// Generate narrative summary
function generateNarrative(country: CountryDetail): string {
  const sentiment = country.sentiment
  const signals = country.totalSignals
  const topTheme = country.themes[0]?.name || ''

  let moodWord = sentiment > 0.1 ? 'positive' :
    sentiment < -0.1 ? 'negative' : 'neutral'

  let volumeWord = signals > 1000 ? 'high' :
    signals > 100 ? 'moderate' : 'low'

  const themeLabel = getThemeLabel(topTheme)

  return `${volumeWord.charAt(0).toUpperCase() + volumeWord.slice(1)} news activity with ${moodWord} sentiment. Coverage is dominated by ${themeLabel.toLowerCase()} topics.`
}

// Sentiment color
function getSentimentColor(sentiment: number): string {
  if (sentiment > 0.1) return '#4ade80'  // Green
  if (sentiment < -0.1) return '#f87171' // Red
  return '#fbbf24' // Yellow
}

// Sentiment label
function getSentimentLabel(sentiment: number): string {
  if (sentiment > 0.2) return 'Very Positive'
  if (sentiment > 0.1) return 'Positive'
  if (sentiment > -0.1) return 'Neutral'
  if (sentiment > -0.2) return 'Negative'
  return 'Very Negative'
}

// Theme icons
function getThemeIcon(theme: string): string {
  const upper = theme.toUpperCase()
  if (upper.includes('ECONOMY') || upper.includes('ECON')) return '💰'
  if (upper.includes('GOVERNMENT') || upper.includes('GOV')) return '🏛️'
  if (upper.includes('MILITARY') || upper.includes('WAR')) return '⚔️'
  if (upper.includes('HEALTH') || upper.includes('DISEASE')) return '🏥'
  if (upper.includes('ENVIRONMENT') || upper.includes('CLIMATE')) return '🌍'
  if (upper.includes('TECH') || upper.includes('CYBER')) return '💻'
  if (upper.includes('CRIME') || upper.includes('ARREST')) return '🚨'
  if (upper.includes('PROTEST') || upper.includes('UNREST')) return '✊'
  if (upper.includes('ELECTION') || upper.includes('VOTE')) return '🗳️'
  if (upper.includes('ENERGY') || upper.includes('OIL')) return '⚡'
  if (upper.includes('FOREST') || upper.includes('OCEAN')) return '🌊'
  if (upper.includes('ETHNICITY') || upper.includes('LANGUAGE')) return '🗣️'
  if (upper.includes('POLICY')) return '📋'
  if (upper.includes('JOB') || upper.includes('EMPLOY')) return '💼'
  return '📰'
}

// Initial map view
const INITIAL_VIEW = {
  longitude: 0,
  latitude: 20,
  zoom: 1.5,
  pitch: 0,
  bearing: 0
}

function App() {
  // State
  const [nodes, setNodes] = useState<Node[]>([])
  const [flows, setFlows] = useState<Flow[]>([])
  const [selectedCountry, setSelectedCountry] = useState<CountryDetail | null>(null)
  const [selectedTheme, setSelectedTheme] = useState<{ theme: string, country?: string } | null>(null)
  const [showBriefing, setShowBriefing] = useState(false)
  const [timeWindow, setTimeWindow] = useState(24)
  const [loading, setLoading] = useState(true)
  const [viewState, setViewState] = useState(INITIAL_VIEW)

  // Layer visibility
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [showNodes, setShowNodes] = useState(true)
  const [showFlows, setShowFlows] = useState(true)

  // Fetch data
  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [nodesRes, flowsRes] = await Promise.all([
        fetch(`http://localhost:8000/api/v2/nodes?hours=${timeWindow}`),
        fetch(`http://localhost:8000/api/v2/flows?hours=${timeWindow}`)
      ])

      const nodesData = await nodesRes.json()
      const flowsData = await flowsRes.json()

      setNodes(nodesData.nodes || [])
      setFlows(flowsData.flows || [])
    } catch (error) {
      console.error('Failed to fetch data:', error)
    }
    setLoading(false)
  }, [timeWindow])

  // Fetch country detail
  const fetchCountryDetail = async (countryCode: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v2/country/${countryCode}?hours=${timeWindow}`)
      const data = await res.json()
      setSelectedCountry(data)
    } catch (error) {
      console.error('Failed to fetch country detail:', error)
    }
  }

  // Theme selection handlers
  const handleThemeSelect = (theme: string, country?: string) => {
    setSelectedTheme({ theme, country })
  }

  const handleThemeClick = (themeName: string) => {
    if (selectedCountry) {
      setSelectedTheme({ theme: themeName, country: selectedCountry.countryCode })
    }
  }

  // Initial fetch and refresh on time window change
  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Auto-refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(fetchData, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [fetchData])

  // Deck.gl layers - NO MORE HEATMAP
  const layers = [
    // Flow arcs (bottom layer)
    showFlows && new ArcLayer({
      id: 'flows',
      data: flows,
      getSourcePosition: (d: Flow) => d.source,
      getTargetPosition: (d: Flow) => d.target,
      getSourceColor: [0, 255, 255, 180],
      getTargetColor: [255, 0, 255, 180],
      getWidth: (d: Flow) => Math.max(1, Math.log(d.strength) * 2),
      greatCircle: true
    }),

    // Outer glow layer (creates halo effect)
    showHeatmap && new ScatterplotLayer({
      id: 'nodes-glow-outer',
      data: nodes,
      getPosition: (d: Node) => [d.lon, d.lat],
      getRadius: (d: Node) => Math.sqrt(d.signalCount) * 800,
      getFillColor: (d: Node) => {
        const color = sentimentColor(d.sentiment)
        return [color[0], color[1], color[2], 30]
      },
      radiusMinPixels: 20,
      radiusMaxPixels: 100,
      pickable: false
    }),

    // Middle glow layer
    showHeatmap && new ScatterplotLayer({
      id: 'nodes-glow-middle',
      data: nodes,
      getPosition: (d: Node) => [d.lon, d.lat],
      getRadius: (d: Node) => Math.sqrt(d.signalCount) * 500,
      getFillColor: (d: Node) => {
        const color = sentimentColor(d.sentiment)
        return [color[0], color[1], color[2], 60]
      },
      radiusMinPixels: 15,
      radiusMaxPixels: 70,
      pickable: false
    }),

    // Inner glow layer
    showHeatmap && new ScatterplotLayer({
      id: 'nodes-glow-inner',
      data: nodes,
      getPosition: (d: Node) => [d.lon, d.lat],
      getRadius: (d: Node) => Math.sqrt(d.signalCount) * 300,
      getFillColor: (d: Node) => {
        const color = sentimentColor(d.sentiment)
        return [color[0], color[1], color[2], 100]
      },
      radiusMinPixels: 10,
      radiusMaxPixels: 50,
      pickable: false
    }),

    // Core node (solid, pickable)
    showNodes && new ScatterplotLayer({
      id: 'nodes-core',
      data: nodes,
      getPosition: (d: Node) => [d.lon, d.lat],
      getRadius: (d: Node) => Math.sqrt(d.signalCount) * 150,
      getFillColor: (d: Node) => sentimentColor(d.sentiment),
      getLineColor: [255, 255, 255, 200],
      lineWidthMinPixels: 1,
      stroked: true,
      pickable: true,
      onClick: ({ object }: { object: Node }) => {
        if (object) {
          fetchCountryDetail(object.id)
        }
      },
      radiusMinPixels: 6,
      radiusMaxPixels: 30,
      transitions: {
        getRadius: 300,
        getFillColor: 300
      }
    })
  ].filter(Boolean)

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1>🌐 OBSERVATORY GLOBAL</h1>
        <SearchBar
          onThemeSelect={handleThemeSelect}
          onCountrySelect={(code) => fetchCountryDetail(code)}
        />
        <button className="briefing-btn" onClick={() => setShowBriefing(true)}>
          📋 Briefing
        </button>
        <div className="stats">
          {loading ? 'Loading...' : `${nodes.length} countries • ${nodes.reduce((sum, n) => sum + n.signalCount, 0).toLocaleString()} signals`}
        </div>
      </header>

      {/* Time controls */}
      <div className="controls">
        {[1, 6, 12, 24, 48, 168].map(hours => (
          <button
            key={hours}
            className={timeWindow === hours ? 'active' : ''}
            onClick={() => setTimeWindow(hours)}
          >
            {hours < 24 ? `${hours}H` : hours === 24 ? '24H' : hours === 48 ? '2D' : '1W'}
          </button>
        ))}
        <span className="separator">|</span>
        <button
          className={showHeatmap ? 'active' : ''}
          onClick={() => setShowHeatmap(!showHeatmap)}
        >
          GLOW
        </button>
        <button
          className={showFlows ? 'active' : ''}
          onClick={() => setShowFlows(!showFlows)}
        >
          FLOW
        </button>
        <button
          className={showNodes ? 'active' : ''}
          onClick={() => setShowNodes(!showNodes)}
        >
          NODES
        </button>
      </div>

      {/* Map */}
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState }) => setViewState(viewState)}
        controller={true}
        layers={layers}
        getTooltip={({ object }) => object && `${object.name}: ${object.signalCount} signals`}
      >
        <Map
          mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
          attributionControl={false}
        />
      </DeckGL>

      {/* Narrative Sidebar */}
      {selectedCountry && (
        <aside className="sidebar">
          <button className="close" onClick={() => setSelectedCountry(null)}>×</button>

          {/* Country Header with Flag */}
          <div className="country-header">
            <span className="country-flag">{getCountryFlag(selectedCountry.countryCode)}</span>
            <div>
              <h2>{getCountryName(selectedCountry.countryCode)}</h2>
              <span className="country-code">{selectedCountry.countryCode}</span>
            </div>
          </div>

          {/* Narrative Summary */}
          <div className="narrative-box">
            <p className="narrative">
              {generateNarrative(selectedCountry)}
            </p>
          </div>

          {/* Key Metrics */}
          <div className="metrics-row">
            <div className="metric">
              <span className="metric-value">{selectedCountry.totalSignals.toLocaleString()}</span>
              <span className="metric-label">Signals</span>
            </div>
            <div className="metric">
              <span className="metric-value sentiment" style={{
                color: getSentimentColor(selectedCountry.sentiment)
              }}>
                {getSentimentLabel(selectedCountry.sentiment)}
              </span>
              <span className="metric-label">Mood</span>
            </div>
          </div>

          {/* Dominant Narratives */}
          <div className="section">
            <h3>📰 DOMINANT NARRATIVES</h3>
            <div className="theme-chips">
              {selectedCountry.themes.slice(0, 5).map((t, i) => (
                <div
                  key={t.name}
                  className="theme-chip clickable"
                  style={{
                    opacity: 1 - (i * 0.15)
                  }}
                  onClick={() => handleThemeClick(t.name)}
                >
                  <span className="theme-icon">{getThemeIcon(t.name)}</span>
                  <span className="theme-label">{getThemeLabel(t.name)}</span>
                  <span className="theme-count">{t.count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Source Diversity */}
          <div className="section">
            <h3>🔗 SOURCE DIVERSITY</h3>
            <div className="source-bar">
              <div className="source-fill" style={{
                width: `${Math.min(100, selectedCountry.sources.length * 20)}%`
              }} />
            </div>
            <p className="source-summary">
              {selectedCountry.sources.length} unique sources
              {selectedCountry.sources.length < 3 ? ' (low diversity ⚠️)' :
                selectedCountry.sources.length > 10 ? ' (high diversity ✓)' : ''}
            </p>
            <div className="source-list">
              {selectedCountry.sources.slice(0, 3).map(s => (
                <span key={s.name} className="source-tag">{s.name}</span>
              ))}
            </div>
          </div>
        </aside>
      )}

      {/* Theme Detail Modal */}
      {selectedTheme && (
        <ThemeDetail
          theme={selectedTheme.theme}
          country={selectedTheme.country}
          hours={timeWindow}
          onClose={() => setSelectedTheme(null)}
        />
      )}

      {/* Briefing Modal */}
      {showBriefing && (
        <Briefing
          hours={timeWindow}
          onClose={() => setShowBriefing(false)}
          onCountrySelect={(code) => { fetchCountryDetail(code); setShowBriefing(false) }}
          onThemeSelect={(theme) => { setSelectedTheme({ theme }); setShowBriefing(false) }}
        />
      )}
    </div>
  )
}

export default App
