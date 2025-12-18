import React, { useState } from 'react'

export const Legend: React.FC = () => {
    const [collapsed, setCollapsed] = useState(false)

    if (collapsed) {
        return (
            <button
                onClick={() => setCollapsed(false)}
                style={{
                    position: 'fixed',
                    bottom: '20px',
                    left: '20px',
                    background: '#1e3a5f',
                    border: '1px solid #3d7ab8',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    color: '#8bb8e0',
                    cursor: 'pointer',
                    zIndex: 800,
                    fontSize: '12px'
                }}
            >
                📊 Legend
            </button>
        )
    }

    return (
        <div
            style={{
                position: 'fixed',
                bottom: '20px',
                left: '20px',
                background: 'linear-gradient(180deg, #0a1628 0%, #0d1f3c 100%)',
                border: '1px solid #1e3a5f',
                borderRadius: '12px',
                padding: '16px',
                minWidth: '220px',
                zIndex: 800,
                boxShadow: '0 4px 20px rgba(0,0,0,0.4)'
            }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h4 style={{ margin: 0, color: '#8bb8e0', fontSize: '12px', textTransform: 'uppercase' }}>Legend</h4>
                <button
                    onClick={() => setCollapsed(true)}
                    style={{ background: 'transparent', border: 'none', color: '#6ba3d6', cursor: 'pointer', fontSize: '14px' }}
                >
                    ✕
                </button>
            </div>

            <div style={{ marginBottom: '12px' }}>
                <div style={{ color: '#6ba3d6', fontSize: '10px', textTransform: 'uppercase', marginBottom: '6px' }}>Nodes (Countries)</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '11px', color: '#e2e8f0' }}>Size = Signal volume</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#4ade80', display: 'inline-block' }}></span>
                    <span style={{ fontSize: '11px', color: '#e2e8f0' }}>Positive tone</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#94a3b8', display: 'inline-block' }}></span>
                    <span style={{ fontSize: '11px', color: '#e2e8f0' }}>Neutral tone</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#f87171', display: 'inline-block' }}></span>
                    <span style={{ fontSize: '11px', color: '#e2e8f0' }}>Negative tone</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#fbbf24', boxShadow: '0 0 8px #fbbf24', display: 'inline-block' }}></span>
                    <span style={{ fontSize: '11px', color: '#e2e8f0' }}>Anomaly (pulsing)</span>
                </div>
            </div>

            <div>
                <div style={{ color: '#6ba3d6', fontSize: '10px', textTransform: 'uppercase', marginBottom: '6px' }}>Flows (Connections)</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <div style={{ width: '30px', height: '2px', background: 'linear-gradient(90deg, #3b82f6, #9333ea)' }}></div>
                    <span style={{ fontSize: '11px', color: '#e2e8f0' }}>Width = Correlation strength</span>
                </div>
                <div style={{ fontSize: '10px', color: '#94a3b8', fontStyle: 'italic' }}>
                    ⚠️ Non-directional. Shows shared attention, not causation.
                </div>
            </div>
        </div>
    )
}
