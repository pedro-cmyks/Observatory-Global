import React from 'react'

export const CorrelationMatrixPlaceholder: React.FC = () => {
    return (
        <div style={{ padding: 16, color: '#aaa', fontSize: 13, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', textAlign: 'center' }}>
            <div style={{ fontSize: 24, marginBottom: 12 }}>▦</div>
            <p style={{ fontWeight: 600, color: 'white', marginBottom: 8 }}>CORRELATION MATRIX</p>
            <p>Coming in Phase 2</p>
            <p style={{ marginTop: 8, opacity: 0.6, fontSize: 11 }}>Heatmap of theme co-occurrence between countries.</p>
        </div>
    )
}
