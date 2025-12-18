import React from 'react'

interface TooltipData {
    type: 'node' | 'flow'
    x: number
    y: number
    data: any
}

interface MapTooltipProps {
    tooltip: TooltipData | null
}

export const MapTooltip: React.FC<MapTooltipProps> = ({ tooltip }) => {
    if (!tooltip) return null

    const { type, x, y, data } = tooltip

    return (
        <div
            style={{
                position: 'fixed',
                left: x + 10,
                top: y + 10,
                background: 'rgba(10, 22, 40, 0.95)',
                border: '1px solid #1e3a5f',
                borderRadius: '8px',
                padding: '12px',
                minWidth: '180px',
                zIndex: 1000,
                pointerEvents: 'none',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
            }}
        >
            {type === 'node' && (
                <>
                    <div style={{ fontWeight: 'bold', color: '#fff', marginBottom: '8px', fontSize: '14px' }}>
                        {data.name || data.id}
                    </div>
                    <div style={{ fontSize: '12px', color: '#e2e8f0', marginBottom: '4px' }}>
                        Signals: <strong>{data.signalCount?.toLocaleString()}</strong>
                    </div>
                    <div style={{ fontSize: '12px', color: '#e2e8f0', marginBottom: '4px' }}>
                        Sentiment: <strong style={{ color: data.sentiment > 0 ? '#4ade80' : data.sentiment < 0 ? '#f87171' : '#94a3b8' }}>
                            {data.sentiment > 0 ? '+' : ''}{data.sentiment?.toFixed(2)}
                        </strong>
                    </div>
                    <div style={{ fontSize: '12px', color: '#e2e8f0', marginBottom: '4px' }}>
                        Sources: <strong>{data.sourceCount}</strong>
                    </div>
                    {data.anomalyMultiplier && data.anomalyMultiplier > 1.2 && (
                        <div style={{ fontSize: '12px', color: '#fbbf24', marginTop: '4px' }}>
                            ⚠️ {data.anomalyMultiplier?.toFixed(1)}× normal
                        </div>
                    )}
                    <div style={{ fontSize: '10px', color: '#6ba3d6', marginTop: '8px', fontStyle: 'italic' }}>
                        Click to focus on this country
                    </div>
                </>
            )}

            {type === 'flow' && (
                <>
                    <div style={{ fontWeight: 'bold', color: '#fff', marginBottom: '8px', fontSize: '14px' }}>
                        {data.sourceCountry} ↔ {data.targetCountry}
                    </div>
                    <div style={{ fontSize: '12px', color: '#e2e8f0', marginBottom: '4px' }}>
                        Strength: <strong>{(data.strength * 100).toFixed(0)}%</strong>
                    </div>
                    {data.sharedThemes?.length > 0 && (
                        <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                            Shared: {data.sharedThemes.slice(0, 3).join(', ')}
                        </div>
                    )}
                    <div style={{ fontSize: '10px', color: '#6ba3d6', marginTop: '8px', fontStyle: 'italic' }}>
                        Correlation, not causation
                    </div>
                </>
            )}
        </div>
    )
}

export type { TooltipData }
