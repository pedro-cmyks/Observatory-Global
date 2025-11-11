import React from 'react'

const MapPlaceholder: React.FC = () => {
  return (
    <div
      style={{
        width: '100%',
        height: '400px',
        backgroundColor: '#f0f0f0',
        borderRadius: '8px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        border: '2px dashed #ccc',
        marginBottom: '2rem',
        color: '#666',
      }}
    >
      <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🗺️</div>
      <h3 style={{ margin: '0 0 0.5rem 0', color: '#333' }}>Map Visualization</h3>
      <p style={{ margin: 0, fontSize: '0.9rem' }}>
        Set MAPBOX_TOKEN environment variable to enable interactive map
      </p>
      <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.85rem', color: '#999' }}>
        Future: Visualize trends by geographic location
      </p>
    </div>
  )
}

export default MapPlaceholder
