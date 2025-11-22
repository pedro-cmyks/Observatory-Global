import React from 'react'
import { CountryHotspot } from '../../lib/mapTypes'

interface MapTooltipProps {
    info: {
        object?: CountryHotspot
        x: number
        y: number
    } | null
}

const MapTooltip: React.FC<MapTooltipProps> = ({ info }) => {
    if (!info || !info.object) return null

    const { object, x, y } = info
    const { country_name, intensity, top_topics, dominant_sentiment, avg_sentiment_score } = object

    // Helper for sentiment color (duplicated from Sidebar for now, could be shared util)
    const getSentimentColor = (sentiment: string) => {
        switch (sentiment) {
            case 'very_negative': return '#ef4444'
            case 'negative': return '#f97316'
            case 'positive': return '#10b981'
            case 'very_positive': return '#3b82f6'
            default: return '#9ca3af'
        }
    }

    return (
        <div
            style={{
                position: 'absolute',
                zIndex: 100,
                pointerEvents: 'none',
                left: x,
                top: y,
                transform: 'translate(-50%, -100%)',
                marginTop: -12,
                backgroundColor: 'rgba(15, 23, 42, 0.95)', // Dark slate
                backdropFilter: 'blur(8px)',
                color: 'white',
                padding: '12px',
                borderRadius: '8px',
                fontSize: '12px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                border: '1px solid rgba(255,255,255,0.1)',
                minWidth: '220px',
            }}
        >
            <div style={{
                fontWeight: 700,
                marginBottom: '8px',
                fontSize: '14px',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                paddingBottom: '4px'
            }}>
                {country_name}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ color: '#94a3b8' }}>Intensity</span>
                <span style={{
                    color: intensity > 0.7 ? '#ef4444' : intensity > 0.4 ? '#f59e0b' : '#10b981',
                    fontWeight: 700
                }}>
                    {(intensity * 100).toFixed(0)}%
                </span>
            </div>

            {dominant_sentiment && (
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ color: '#94a3b8' }}>Sentiment</span>
                    <span style={{
                        color: getSentimentColor(dominant_sentiment),
                        fontWeight: 600,
                        textTransform: 'capitalize'
                    }}>
                        {dominant_sentiment.replace('_', ' ')}
                        {avg_sentiment_score !== undefined && (
                            <span style={{ opacity: 0.7, marginLeft: '4px', fontSize: '10px' }}>
                                ({avg_sentiment_score > 0 ? '+' : ''}{avg_sentiment_score.toFixed(1)})
                            </span>
                        )}
                    </span>
                </div>
            )}

            {top_topics && top_topics.length > 0 && (
                <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                    <div style={{ color: '#94a3b8', marginBottom: '4px', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Top Themes
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {top_topics.slice(0, 3).map((t, i) => (
                            <span key={i} style={{
                                backgroundColor: 'rgba(255,255,255,0.1)',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                fontSize: '11px'
                            }}>
                                {t.label}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

export default MapTooltip
