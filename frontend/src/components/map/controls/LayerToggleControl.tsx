import React from 'react'
import { useMapStore } from '../../../store/mapStore'

const LayerToggleControl: React.FC = () => {
  const { layersVisible, toggleLayer } = useMapStore()

  const layers = [
    { key: 'heatmap' as const, label: 'Heatmap', icon: '🌡️' },
    { key: 'flows' as const, label: 'Flows', icon: '💨' },
    { key: 'markers' as const, label: 'Markers', icon: '📍' },
  ]

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
      }}
    >
      {layers.map((layer) => (
        <button
          key={layer.key}
          onClick={() => toggleLayer(layer.key)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.3rem',
            padding: '0.4rem 0.75rem',
            backgroundColor: layersVisible[layer.key]
              ? 'rgba(59, 130, 246, 0.6)' // Blue when active
              : 'rgba(255, 255, 255, 0.05)', // Subtle when inactive
            color: layersVisible[layer.key] ? 'white' : 'rgba(255, 255, 255, 0.4)',
            border: layersVisible[layer.key]
              ? '1px solid rgba(59, 130, 246, 0.8)'
              : '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '6px',
            fontSize: '0.85rem',
            fontWeight: layersVisible[layer.key] ? 600 : 400,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            whiteSpace: 'nowrap',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-1px)'
            e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.3)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = 'none'
          }}
        >
          <span>{layer.icon}</span>
          <span className="hidden sm:inline">{layer.label}</span>
        </button>
      ))}
    </div>
  )
}

export default LayerToggleControl
