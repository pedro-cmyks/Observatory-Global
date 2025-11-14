import React from 'react'
import { useMapStore } from '../../store/mapStore'
import type { ViewMode } from '../../lib/mapTypes'

const ViewModeToggle: React.FC = () => {
  const { viewMode, setViewMode } = useMapStore()

  const handleModeChange = (mode: ViewMode) => {
    setViewMode(mode)
  }

  return (
    <div
      style={{
        backgroundColor: 'rgba(33, 37, 71, 0.95)',
        borderRadius: '8px',
        padding: '0.5rem',
        display: 'flex',
        gap: '0.5rem',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
      }}
    >
      <button
        onClick={() => handleModeChange('classic')}
        style={{
          padding: '0.5rem 1rem',
          fontSize: '0.875rem',
          fontWeight: 600,
          backgroundColor: viewMode === 'classic' ? '#646cff' : 'transparent',
          color: viewMode === 'classic' ? 'white' : 'rgba(255, 255, 255, 0.7)',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => {
          if (viewMode !== 'classic') {
            e.currentTarget.style.backgroundColor = 'rgba(100, 108, 255, 0.2)'
          }
        }}
        onMouseLeave={(e) => {
          if (viewMode !== 'classic') {
            e.currentTarget.style.backgroundColor = 'transparent'
          }
        }}
      >
        Classic View
      </button>
      <button
        onClick={() => handleModeChange('heatmap')}
        style={{
          padding: '0.5rem 1rem',
          fontSize: '0.875rem',
          fontWeight: 600,
          backgroundColor: viewMode === 'heatmap' ? '#646cff' : 'transparent',
          color: viewMode === 'heatmap' ? 'white' : 'rgba(255, 255, 255, 0.7)',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => {
          if (viewMode !== 'heatmap') {
            e.currentTarget.style.backgroundColor = 'rgba(100, 108, 255, 0.2)'
          }
        }}
        onMouseLeave={(e) => {
          if (viewMode !== 'heatmap') {
            e.currentTarget.style.backgroundColor = 'transparent'
          }
        }}
      >
        Heatmap View
      </button>
    </div>
  )
}

export default ViewModeToggle
