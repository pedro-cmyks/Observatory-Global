/**
 * PROOF OF CONCEPT: Hexagonal Heatmap Layer
 *
 * This demonstrates the recommended approach using deck.gl + H3
 * for rendering dynamic hexagonal heatmaps on Mapbox GL.
 *
 * Dependencies needed:
 * npm install h3-js deck.gl @deck.gl/react @deck.gl/geo-layers
 */

import React, { useEffect, useState } from 'react'
import { DeckGL } from '@deck.gl/react'
import { H3HexagonLayer } from '@deck.gl/geo-layers'
import { Map } from 'react-map-gl'
import axios from 'axios'

// ============================================================================
// TYPES
// ============================================================================

interface HexagonData {
  h3_index: string
  intensity: number // 0.0 - 1.0
  country: string
  top_topic?: string
}

interface HexmapResponse {
  resolution: number
  time_window: string
  generated_at: string
  hexagons: HexagonData[]
  metadata: {
    total_hexagons: number
    filtered_hexagons: number
    max_intensity: number
  }
}

// ============================================================================
// CONSTANTS
// ============================================================================

const MAPBOX_TOKEN = process.env.REACT_APP_MAPBOX_TOKEN || ''

const INITIAL_VIEW_STATE = {
  longitude: 0,
  latitude: 20,
  zoom: 2,
  pitch: 45, // 3D tilt for better visualization
  bearing: 0
}

// Map zoom level to H3 resolution
const ZOOM_TO_RESOLUTION: { [key: number]: number } = {
  0: 1,  1: 1,
  2: 2,  3: 2,
  4: 3,  5: 3,
  6: 4,  7: 4,
  8: 5,  9: 5,
  10: 6, 11: 6,
  12: 7
}

// ============================================================================
// COLOR MAPPING
// ============================================================================

/**
 * Convert intensity (0-1) to RGBA color.
 * Uses thermal color scale: blue (cold) → cyan → green → yellow → red (hot)
 */
function intensityToRGBA(intensity: number): [number, number, number, number] {
  // Clamp intensity to [0, 1]
  const i = Math.max(0, Math.min(1, intensity))

  // Define color stops (value, [R, G, B, A])
  const stops: Array<[number, [number, number, number, number]]> = [
    [0.0, [0, 0, 139, 60]],      // Dark blue (barely visible)
    [0.2, [0, 0, 255, 100]],     // Blue
    [0.4, [0, 255, 255, 140]],   // Cyan
    [0.6, [0, 255, 0, 180]],     // Green
    [0.8, [255, 255, 0, 220]],   // Yellow
    [1.0, [255, 0, 0, 255]]      // Red (fully opaque)
  ]

  // Find the two stops to interpolate between
  let lowerStop = stops[0]
  let upperStop = stops[stops.length - 1]

  for (let idx = 0; idx < stops.length - 1; idx++) {
    if (i >= stops[idx][0] && i <= stops[idx + 1][0]) {
      lowerStop = stops[idx]
      upperStop = stops[idx + 1]
      break
    }
  }

  // Linear interpolation between the two stops
  const [lowerValue, lowerColor] = lowerStop
  const [upperValue, upperColor] = upperStop
  const t = (i - lowerValue) / (upperValue - lowerValue)

  return [
    Math.round(lowerColor[0] + t * (upperColor[0] - lowerColor[0])),
    Math.round(lowerColor[1] + t * (upperColor[1] - lowerColor[1])),
    Math.round(lowerColor[2] + t * (upperColor[2] - lowerColor[2])),
    Math.round(lowerColor[3] + t * (upperColor[3] - lowerColor[3]))
  ]
}

// ============================================================================
// CUSTOM HOOKS
// ============================================================================

/**
 * Fetch hexagon data from backend API based on current map state.
 */
function useHexagonData(
  resolution: number,
  timeWindow: string = '24h',
  threshold: number = 0.1
) {
  const [data, setData] = useState<HexagonData[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setError(null)

      try {
        const response = await axios.get<HexmapResponse>('/v1/hexmap', {
          params: {
            resolution,
            time_window: timeWindow,
            threshold
          }
        })

        setData(response.data.hexagons)
      } catch (err) {
        setError('Failed to load hexagon data')
        console.error('Hexmap fetch error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [resolution, timeWindow, threshold])

  return { data, loading, error }
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const HexagonHeatmapDemo: React.FC = () => {
  const [viewState, setViewState] = useState(INITIAL_VIEW_STATE)
  const [hoveredHex, setHoveredHex] = useState<HexagonData | null>(null)
  const [timeWindow, setTimeWindow] = useState<string>('24h')
  const [show3D, setShow3D] = useState(true)
  const [smoothing, setSmoothing] = useState(false)

  // Calculate H3 resolution based on zoom level
  const resolution = ZOOM_TO_RESOLUTION[Math.floor(viewState.zoom)] || 3

  // Fetch hexagon data
  const { data: hexData, loading, error } = useHexagonData(resolution, timeWindow)

  // Create deck.gl layer
  const layers = [
    new H3HexagonLayer({
      id: 'hex-heatmap',
      data: hexData,

      // Data accessors
      getHexagon: (d: HexagonData) => d.h3_index,
      getFillColor: (d: HexagonData) => intensityToRGBA(d.intensity),
      getElevation: (d: HexagonData) => show3D ? d.intensity * 5000 : 0,

      // Styling
      extruded: show3D,
      coverage: 0.95, // 95% hex fill (small gaps for definition)
      elevationScale: 1,
      material: {
        ambient: 0.4,
        diffuse: 0.6,
        shininess: 32,
        specularColor: [255, 255, 255]
      },

      // Interaction
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 100],
      onHover: (info) => setHoveredHex(info.object),

      // Performance
      updateTriggers: {
        getFillColor: [hexData],
        getElevation: [hexData, show3D]
      },

      // Smooth transitions
      transitions: {
        getFillColor: {
          duration: 500,
          easing: (t) => t * (2 - t) // Ease out quad
        },
        getElevation: {
          duration: 500,
          easing: (t) => t * (2 - t)
        }
      }
    })
  ]

  return (
    <div style={{ position: 'relative', width: '100%', height: '600px' }}>
      {/* DeckGL + Mapbox */}
      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller={true}
        layers={layers}
        onViewStateChange={({ viewState }) => setViewState(viewState)}
        style={{
          filter: smoothing ? 'blur(8px)' : 'none' // Gaussian blur for blob effect
        }}
      >
        <Map
          mapboxAccessToken={MAPBOX_TOKEN}
          mapStyle="mapbox://styles/mapbox/dark-v11"
          style={{ width: '100%', height: '100%' }}
        />
      </DeckGL>

      {/* Controls */}
      <div style={styles.controls}>
        <h3 style={styles.controlsTitle}>Hexagonal Heatmap Controls</h3>

        {/* Time Window */}
        <div style={styles.controlGroup}>
          <label style={styles.label}>Time Window:</label>
          <select
            value={timeWindow}
            onChange={(e) => setTimeWindow(e.target.value)}
            style={styles.select}
          >
            <option value="1h">Last 1 Hour</option>
            <option value="6h">Last 6 Hours</option>
            <option value="12h">Last 12 Hours</option>
            <option value="24h">Last 24 Hours</option>
          </select>
        </div>

        {/* 3D Toggle */}
        <div style={styles.controlGroup}>
          <label style={styles.label}>
            <input
              type="checkbox"
              checked={show3D}
              onChange={(e) => setShow3D(e.target.checked)}
              style={styles.checkbox}
            />
            3D Elevation
          </label>
        </div>

        {/* Smoothing Toggle */}
        <div style={styles.controlGroup}>
          <label style={styles.label}>
            <input
              type="checkbox"
              checked={smoothing}
              onChange={(e) => setSmoothing(e.target.checked)}
              style={styles.checkbox}
            />
            Blob Smoothing (Blur)
          </label>
        </div>

        {/* Stats */}
        <div style={styles.stats}>
          <p><strong>Resolution:</strong> {resolution}</p>
          <p><strong>Zoom:</strong> {viewState.zoom.toFixed(1)}</p>
          <p><strong>Hexagons:</strong> {hexData.length.toLocaleString()}</p>
          {loading && <p style={styles.loading}>Loading...</p>}
          {error && <p style={styles.error}>{error}</p>}
        </div>
      </div>

      {/* Hover Tooltip */}
      {hoveredHex && (
        <div style={styles.tooltip}>
          <h4 style={styles.tooltipTitle}>{hoveredHex.country}</h4>
          <p><strong>Intensity:</strong> {(hoveredHex.intensity * 100).toFixed(0)}%</p>
          {hoveredHex.top_topic && (
            <p><strong>Top Topic:</strong> {hoveredHex.top_topic}</p>
          )}
          <p style={styles.tooltipHint}>H3: {hoveredHex.h3_index.slice(0, 12)}...</p>
        </div>
      )}

      {/* Color Legend */}
      <div style={styles.legend}>
        <h4 style={styles.legendTitle}>Intensity</h4>
        <div style={styles.legendGradient} />
        <div style={styles.legendLabels}>
          <span>Cold</span>
          <span>Hot</span>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// STYLES
// ============================================================================

const styles: { [key: string]: React.CSSProperties } = {
  controls: {
    position: 'absolute',
    top: '1rem',
    left: '1rem',
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    color: 'white',
    padding: '1rem',
    borderRadius: '8px',
    minWidth: '250px',
    zIndex: 10
  },
  controlsTitle: {
    margin: '0 0 1rem 0',
    fontSize: '16px',
    fontWeight: 'bold'
  },
  controlGroup: {
    marginBottom: '0.75rem'
  },
  label: {
    display: 'block',
    fontSize: '14px',
    marginBottom: '0.25rem'
  },
  select: {
    width: '100%',
    padding: '0.5rem',
    borderRadius: '4px',
    border: 'none',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    color: 'white'
  },
  checkbox: {
    marginRight: '0.5rem'
  },
  stats: {
    marginTop: '1rem',
    paddingTop: '1rem',
    borderTop: '1px solid rgba(255, 255, 255, 0.2)',
    fontSize: '13px'
  },
  loading: {
    color: '#FFD700',
    fontStyle: 'italic'
  },
  error: {
    color: '#FF6B6B',
    fontSize: '12px'
  },
  tooltip: {
    position: 'absolute',
    bottom: '1rem',
    right: '1rem',
    backgroundColor: 'rgba(0, 0, 0, 0.9)',
    color: 'white',
    padding: '1rem',
    borderRadius: '8px',
    maxWidth: '300px',
    zIndex: 10,
    pointerEvents: 'none'
  },
  tooltipTitle: {
    margin: '0 0 0.5rem 0',
    fontSize: '16px',
    fontWeight: 'bold'
  },
  tooltipHint: {
    fontSize: '11px',
    color: 'rgba(255, 255, 255, 0.6)',
    marginTop: '0.5rem'
  },
  legend: {
    position: 'absolute',
    bottom: '1rem',
    left: '1rem',
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    color: 'white',
    padding: '1rem',
    borderRadius: '8px',
    width: '200px',
    zIndex: 10
  },
  legendTitle: {
    margin: '0 0 0.5rem 0',
    fontSize: '14px',
    fontWeight: 'bold'
  },
  legendGradient: {
    height: '20px',
    background: 'linear-gradient(to right, #00008B, #0000FF, #00FFFF, #00FF00, #FFFF00, #FF0000)',
    borderRadius: '4px',
    marginBottom: '0.25rem'
  },
  legendLabels: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '12px',
    color: 'rgba(255, 255, 255, 0.7)'
  }
}

export default HexagonHeatmapDemo
