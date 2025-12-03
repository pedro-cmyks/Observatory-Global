import { useState, useEffect } from 'react'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import './ThemeDetail.css'

interface ThemeData {
    theme: string
    country: string | null
    total: number
    avgSentiment: number
    signals: Array<{
        timestamp: string
        country: string
        source: string
        url: string
        sentiment: number
        otherThemes: string[]
        persons: string[]
    }>
    countryBreakdown: Array<{ code: string; count: number; sentiment: number }>
    relatedThemes: Array<{ theme: string; count: number }>
    topSources: Array<{ name: string; count: number; sentiment: number }>
    topPersons: Array<{ name: string; count: number }>
    timeline: Array<{ hour: string; count: number; sentiment: number }>
}

interface ThemeDetailProps {
    theme: string
    country?: string
    hours: number
    onClose: () => void
}

export function ThemeDetail({ theme, country, hours, onClose }: ThemeDetailProps) {
    const [data, setData] = useState<ThemeData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true)
            setError(null)
            try {
                const params = new URLSearchParams({ hours: hours.toString() })
                if (country) params.append('country_code', country)
                const url = `http://localhost:8000/api/v2/theme/${encodeURIComponent(theme)}?${params.toString()}`

                const res = await fetch(url)
                if (!res.ok) throw new Error(`HTTP ${res.status}`)

                const json = await res.json()
                setData(json)
            } catch (e) {
                setError(e instanceof Error ? e.message : 'Failed to load')
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [theme, country, hours])

    const getSentimentColor = (s: number) =>
        s > 0.1 ? '#4ade80' : s < -0.1 ? '#f87171' : '#fbbf24'

    const formatTime = (iso: string) => {
        const d = new Date(iso)
        return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
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
                            {country || 'Global'} • {data?.total || 0} signals • Last {hours}h
                        </p>
                    </div>
                </div>

                {loading && <div className="theme-detail-loading">Loading...</div>}
                {error && <div className="theme-detail-error">Error: {error}</div>}

                {data && !loading && (
                    <>
                        {/* Summary Stats */}
                        <div className="theme-stats-row">
                            <div className="theme-stat">
                                <span className="theme-stat-value">{data.total}</span>
                                <span className="theme-stat-label">Signals</span>
                            </div>
                            <div className="theme-stat">
                                <span className="theme-stat-value" style={{ color: getSentimentColor(data.avgSentiment) }}>
                                    {data.avgSentiment > 0 ? '+' : ''}{data.avgSentiment.toFixed(2)}
                                </span>
                                <span className="theme-stat-label">Avg Sentiment</span>
                            </div>
                            <div className="theme-stat">
                                <span className="theme-stat-value">{data.countryBreakdown.length}</span>
                                <span className="theme-stat-label">Countries</span>
                            </div>
                            <div className="theme-stat">
                                <span className="theme-stat-value">{data.topSources.length}</span>
                                <span className="theme-stat-label">Sources</span>
                            </div>
                        </div>

                        {/* Timeline */}
                        {data.timeline.length > 0 && (
                            <div className="theme-section">
                                <h3>📊 Activity Timeline</h3>
                                <div className="timeline-chart">
                                    {data.timeline.map((t, i) => (
                                        <div
                                            key={i}
                                            className="timeline-bar"
                                            style={{
                                                height: `${Math.max(10, (t.count / Math.max(...data.timeline.map(x => x.count))) * 100)}%`,
                                                backgroundColor: getSentimentColor(t.sentiment)
                                            }}
                                            title={`${formatTime(t.hour)}: ${t.count} signals`}
                                        />
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Related Themes */}
                        {data.relatedThemes.length > 0 && (
                            <div className="theme-section">
                                <h3>🔗 Related Topics</h3>
                                <div className="related-chips">
                                    {data.relatedThemes.slice(0, 6).map(t => (
                                        <span key={t.theme} className="related-chip">
                                            {getThemeIcon(t.theme)} {getThemeLabel(t.theme)} ({t.count})
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Top Persons */}
                        {data.topPersons.length > 0 && (
                            <div className="theme-section">
                                <h3>👤 People Mentioned</h3>
                                <div className="person-list">
                                    {data.topPersons.slice(0, 5).map(p => (
                                        <span key={p.name} className="person-tag">
                                            {p.name} ({p.count})
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Top Sources */}
                        {data.topSources.length > 0 && (
                            <div className="theme-section">
                                <h3>📰 Top Sources</h3>
                                <div className="source-list">
                                    {data.topSources.map(s => (
                                        <div key={s.name} className="source-item">
                                            <span className="source-name">{s.name}</span>
                                            <span className="source-count">{s.count}</span>
                                            <span className="source-sentiment" style={{ color: getSentimentColor(s.sentiment) }}>
                                                {s.sentiment > 0 ? '+' : ''}{s.sentiment.toFixed(2)}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Recent Coverage */}
                        <div className="theme-section">
                            <h3>📋 Recent Coverage ({data.signals.length})</h3>
                            <div className="signals-list">
                                {data.signals.slice(0, 20).map((s, i) => (
                                    <div key={i} className="signal-item">
                                        <div className="signal-header">
                                            <span className="signal-source">{s.source || 'Unknown'}</span>
                                            <span className="signal-time">{formatTime(s.timestamp)}</span>
                                        </div>
                                        <div className="signal-meta">
                                            <span className="signal-country">{s.country}</span>
                                            <span className="signal-sentiment" style={{ color: getSentimentColor(s.sentiment) }}>
                                                {s.sentiment > 0 ? '+' : ''}{s.sentiment.toFixed(2)}
                                            </span>
                                        </div>
                                        {s.persons.length > 0 && (
                                            <div className="signal-persons">👤 {s.persons.join(', ')}</div>
                                        )}
                                        {s.url && (
                                            <a href={s.url} target="_blank" rel="noopener noreferrer" className="signal-link">
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
