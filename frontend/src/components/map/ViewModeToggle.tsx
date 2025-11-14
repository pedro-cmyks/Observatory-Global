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
        backgroundColor: 'rgba(26, 32, 44, 0.95)',
        borderRadius: '8px',
        padding: '8px',
        display: 'flex',
        gap: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
      }}
    >
      <button
        onClick={() => handleModeChange('classic')}
        style={{
          backgroundColor: viewMode === 'classic' ? '#4299e1' : 'transparent',
          color: viewMode === 'classic' ? '#ffffff' : '#a0aec0',
          border: '1px solid',
          borderColor: viewMode === 'classic' ? '#4299e1' : '#4a5568',
          borderRadius: '4px',
          padding: '6px 12px',
          fontSize: '14px',
          fontWeight: 500,
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => {
          if (viewMode !== 'classic') {
            e.currentTarget.style.backgroundColor = 'rgba(66, 153, 225, 0.1)'
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
          backgroundColor: viewMode === 'heatmap' ? '#4299e1' : 'transparent',
          color: viewMode === 'heatmap' ? '#ffffff' : '#a0aec0',
          border: '1px solid',
          borderColor: viewMode === 'heatmap' ? '#4299e1' : '#4a5568',
          borderRadius: '4px',
          padding: '6px 12px',
          fontSize: '14px',
          fontWeight: 500,
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => {
          if (viewMode !== 'heatmap') {
            e.currentTarget.style.backgroundColor = 'rgba(66, 153, 225, 0.1)'
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
