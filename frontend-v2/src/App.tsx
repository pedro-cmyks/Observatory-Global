import { useState, useEffect, useCallback } from 'react'
import Map from 'react-map-gl/maplibre'
import { DeckGL } from '@deck.gl/react'
import { ScatterplotLayer, ArcLayer } from '@deck.gl/layers'
import { HeatmapLayer } from '@deck.gl/aggregation-layers'
import { scaleLinear } from 'd3-scale'
import 'maplibre-gl/dist/maplibre-gl.css'
import './App.css'

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

interface HeatmapPoint {
  lat: number
  lon: number
  weight: number
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

// Sentiment to color scale (red = negative, yellow = neutral, green = positive)
const sentimentColor = (sentiment: number): [number, number, number, number] => {
  const scale = scaleLinear<string>()
    .domain([-1, 0, 1])
    .range(['#ff4444', '#ffff44', '#44ff44'])
  const hex = scale(sentiment)
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return [r, g, b, 200]
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
  const [heatmapPoints, setHeatmapPoints] = useState<HeatmapPoint[]>([])
  const [flows, setFlows] = useState<Flow[]>([])
  const [selectedCountry, setSelectedCountry] = useState<CountryDetail | null>(null)
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
      const [nodesRes, heatmapRes, flowsRes] = await Promise.all([
        fetch(`http://localhost:8000/api/v2/nodes?hours=${timeWindow}`),
        fetch(`http://localhost:8000/api/v2/heatmap?hours=${timeWindow}`),
        fetch(`http://localhost:8000/api/v2/flows?hours=${timeWindow}`)
      ])

      const nodesData = await nodesRes.json()
      const heatmapData = await heatmapRes.json()
      const flowsData = await flowsRes.json()

      setNodes(nodesData.nodes || [])
      setHeatmapPoints(heatmapData.points || [])
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

  // Initial fetch and refresh on time window change
  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Auto-refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(fetchData, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [fetchData])

  // Deck.gl layers
  const layers = [
    // Heatmap layer (bottom)
    showHeatmap && new HeatmapLayer({
      id: 'heatmap',
      data: heatmapPoints,
      getPosition: (d: HeatmapPoint) => [d.lon, d.lat],
      getWeight: (d: HeatmapPoint) => d.weight,
      radiusPixels: 60,
      intensity: 1,
      threshold: 0.1,
      colorRange: [
        [255, 255, 178, 50],
        [254, 204, 92, 100],
        [253, 141, 60, 150],
        [240, 59, 32, 200],
        [189, 0, 38, 255]
      ]
    }),

    // Flow arcs (middle)
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

    // Country nodes (top)
    showNodes && new ScatterplotLayer({
      id: 'nodes',
      data: nodes,
      getPosition: (d: Node) => [d.lon, d.lat],
      getRadius: (d: Node) => Math.sqrt(d.signalCount) * 500,
      getFillColor: (d: Node) => sentimentColor(d.sentiment),
      getLineColor: [255, 255, 255, 100],
      lineWidthMinPixels: 1,
      pickable: true,
      onClick: ({ object }: { object: Node }) => {
        if (object) {
          fetchCountryDetail(object.id)
        }
      },
      radiusMinPixels: 8,
      radiusMaxPixels: 50
    })
  ].filter(Boolean)

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1>🌐 OBSERVATORY GLOBAL</h1>
        <div className="stats">
          {loading ? 'Loading...' : `${nodes.length} countries • ${heatmapPoints.length} signals`}
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
          HEAT
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

      {/* Sidebar */}
      {selectedCountry && (
        <aside className="sidebar">
          <button className="close" onClick={() => setSelectedCountry(null)}>×</button>

          <h2>{selectedCountry.countryCode}</h2>

          <div className="metric">
            <span className="label">Signals</span>
            <span className="value">{selectedCountry.totalSignals.toLocaleString()}</span>
          </div>

          <div className="metric">
            <span className="label">Sentiment</span>
            <span className="value" style={{
              color: selectedCountry.sentiment > 0 ? '#44ff44' :
                selectedCountry.sentiment < 0 ? '#ff4444' : '#ffff44'
            }}>
              {selectedCountry.sentiment.toFixed(2)}
            </span>
          </div>

          <h3>Top Themes</h3>
          <ul className="themes">
            {selectedCountry.themes.slice(0, 5).map(t => (
              <li key={t.name}>
                <span>{t.name}</span>
                <span>{t.count}</span>
              </li>
            ))}
          </ul>

          <h3>Sources</h3>
          <ul className="sources">
            {selectedCountry.sources.slice(0, 3).map(s => (
              <li key={s.name}>
                <span>{s.name}</span>
                <span>{s.count}</span>
              </li>
            ))}
          </ul>
        </aside>
      )}
    </div>
  )
}

export default App
