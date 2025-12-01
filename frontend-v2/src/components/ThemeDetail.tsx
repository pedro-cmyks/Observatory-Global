```
import { useState, useEffect } from 'react'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import './ThemeDetail.css'


interface Signal {
    timestamp: string
    country: string
    source: string
    url: string
    sentiment: number
    otherThemes: string[]
    persons: string[]
}

interface TimelinePoint {
    hour: string
    count: number
    sentiment: number
}

interface ThemeDetailProps {
    theme: string
    country?: string
    hours: number
    onClose: () => void
}

export function ThemeDetail({ theme, country, hours, onClose }: ThemeDetailProps) {
    const [signals, setSignals] = useState<Signal[]>([])
    const [timeline, setTimeline] = useState<TimelinePoint[]>([])
    const [loading, setLoading] = useState(true)
    const [total, setTotal] = useState(0)

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true)
            try {
                const url = `http://localhost:8000/api/v2/theme/${encodeURIComponent(theme)}?hours=${hours}${country ? `&country_code=${country}` : ''}`
const res = await fetch(url)
const data = await res.json()
setSignals(data.signals || [])
setTimeline(data.timeline || [])
setTotal(data.total || 0)
            } catch (error) {
    console.error('Failed to fetch theme details:', error)
}
setLoading(false)
        }
fetchData()
    }, [theme, country, hours])

const formatTime = (iso: string) => {
    const date = new Date(iso)
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    })
}

const getSentimentStyle = (sentiment: number) => {
    if (sentiment > 0.1) return { color: '#4ade80' }
    if (sentiment < -0.1) return { color: '#f87171' }
    return { color: '#fbbf24' }
}

return (
    <div className="theme-detail-overlay" onClick={onClose}>
        <div className="theme-detail-panel" onClick={e => e.stopPropagation()}>
            <button className="theme-detail-close" onClick={onClose}>×</button>

            <div className="theme-detail-header">
                <span className="theme-detail-icon">{getThemeIcon(theme)}</span>
                <div>
                    <h2>{getThemeLabel(theme)}</h2>
                    <p className="theme-detail-meta">
                        {country ? `${country} • ` : ''}{total} signals • Last {hours}h
                    </p>
                </div>
            </div>

            {loading ? (
                <div className="theme-detail-loading">Loading...</div>
            ) : (
                <>
                    {/* Mini Timeline */}
                    {timeline.length > 0 && (
                        <div className="theme-timeline">
                            <h3>Activity Timeline</h3>
                            <div className="timeline-chart">
                                {timeline.map((t, i) => (
                                    <div
                                        key={i}
                                        className="timeline-bar"
                                        style={{
                                            height: `${Math.max(10, (t.count / Math.max(...timeline.map(x => x.count))) * 100)}%`,
                                            backgroundColor: t.sentiment > 0 ? '#4ade80' : t.sentiment < 0 ? '#f87171' : '#fbbf24'
                                        }}
                                        title={`${formatTime(t.hour)}: ${t.count} signals`}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Signals List */}
                    <div className="theme-signals">
                        <h3>Recent Coverage ({signals.length})</h3>
                        <div className="signals-list">
                            {signals.map((signal, i) => (
                                <div key={i} className="signal-item">
                                    <div className="signal-header">
                                        <span className="signal-source">{signal.source || 'Unknown'}</span>
                                        <span className="signal-time">{formatTime(signal.timestamp)}</span>
                                    </div>
                                    <div className="signal-meta">
                                        <span className="signal-country">{signal.country}</span>
                                        <span
                                            className="signal-sentiment"
                                            style={getSentimentStyle(signal.sentiment)}
                                        >
                                            {signal.sentiment > 0 ? '+' : ''}{signal.sentiment.toFixed(2)}
                                        </span>
                                    </div>
                                    {signal.persons.length > 0 && (
                                        <div className="signal-persons">
                                            👤 {signal.persons.join(', ')}
                                        </div>
                                    )}
                                    {signal.url && (
                                        <a
                                            href={signal.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="signal-link"
                                        >
                                            View Source →
                                        </a>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </>
            )}
        </div>
    </div>
)
}
