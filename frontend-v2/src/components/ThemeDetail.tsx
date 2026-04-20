import { useState, useEffect } from 'react'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { useFocus } from '../contexts/FocusContext'
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
    countryFraming?: Array<{
        country_code: string
        country_name: string
        signal_count: number
        avg_sentiment: number
        top_sub_themes: string[]
        sentiment_label: string
    }>
}

interface ThemeDetailProps {
    theme: string
    country?: string
    hours: number
    onClose: () => void
    onThemeSelect?: (theme: string) => void
}

export function ThemeDetail({ theme, country, hours, onClose, onThemeSelect }: ThemeDetailProps) {
    const [data, setData] = useState<ThemeData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const { setCountry } = useFocus()

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true)
            setError(null)
            try {
                const params = new URLSearchParams({ hours: hours.toString() })
                if (country) params.append('country_code', country)
                const url = `/api/v2/theme/${encodeURIComponent(theme)}?${params.toString()}`

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

    // Country code to flag emoji
    const getFlag = (code: string): string => {
        if (!code || code.length !== 2) return '🌐'
        const codePoints = code.toUpperCase().split('').map(c => 0x1F1E6 + c.charCodeAt(0) - 65)
        return String.fromCodePoint(...codePoints)
    }

    // Sentiment bar color for framing cards
    const getFramingSentimentColor = (s: number): string => {
        if (s > 0.5) return '#4ade80'
        if (s > -0.5) return '#94a3b8'
        if (s > -2.0) return '#f59e0b'
        return '#ef4444'
    }

    // Sentiment bar width (normalized to 0-100 from -10 to +10 scale)
    const getSentimentBarWidth = (s: number): number => {
        return Math.min(100, Math.max(5, ((s + 10) / 20) * 100))
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

                        {/* HOW IT'S COVERED — Framing Analysis */}
                        {data.countryFraming && data.countryFraming.length > 0 && (
                            <div className="theme-section framing-section">
                                <h3>How It's Covered</h3>
                                <p className="framing-subtitle">How different countries frame this topic</p>
                                <div className="framing-grid">
                                    {data.countryFraming.map(cf => (
                                        <div
                                            key={cf.country_code}
                                            className="framing-card"
                                            onClick={() => {
                                                setCountry(cf.country_code, 'stream')
                                            }}
                                        >
                                            <div className="framing-card-header">
                                                <span className="framing-flag">{getFlag(cf.country_code)}</span>
                                                <span className="framing-country-name">{cf.country_name}</span>
                                            </div>
                                            <div className="framing-stats">
                                                <span className="framing-signal-count">{cf.signal_count.toLocaleString()} signals</span>
                                                <span className="framing-tone" style={{ color: getFramingSentimentColor(cf.avg_sentiment) }}>
                                                    {cf.avg_sentiment > 0 ? '+' : ''}{cf.avg_sentiment.toFixed(1)} tone
                                                </span>
                                            </div>
                                            <div className="framing-sentiment-bar">
                                                <div
                                                    className="framing-sentiment-fill"
                                                    style={{
                                                        width: `${getSentimentBarWidth(cf.avg_sentiment)}%`,
                                                        backgroundColor: getFramingSentimentColor(cf.avg_sentiment)
                                                    }}
                                                />
                                            </div>
                                            <div className="framing-sub-themes">
                                                {cf.top_sub_themes.map(st => (
                                                    <span key={st} className="framing-chip">
                                                        {getThemeIcon(st)} {getThemeLabel(st)}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Timeline */}
                        {data.timeline.length > 0 && (
                            <div className="theme-section">
                                <h3>Activity Timeline</h3>
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
                                <div style={{ display: 'flex', gap: '12px', fontSize: '10px', color: 'var(--color-text-muted)', marginTop: '8px', justifyContent: 'center' }}>
                                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#4ade80' }}></span> Positive</span>
                                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#fbbf24' }}></span> Neutral</span>
                                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#f87171' }}></span> Negative</span>
                                </div>
                            </div>
                        )}

                        {/* Related Themes */}
                        {data.relatedThemes.length > 0 && (
                            <div className="theme-section">
                                <h3>Related Topics</h3>
                                <div className="related-chips">
                                    {data.relatedThemes.slice(0, 6).map(t => (
                                        <button
                                            key={t.theme}
                                            className="related-chip"
                                            onClick={() => onThemeSelect?.(t.theme)}
                                            style={{
                                                background: 'var(--color-bg-secondary)',
                                                border: '1px solid var(--color-border-subtle)',
                                                borderRadius: '16px',
                                                padding: '4px 12px',
                                                fontSize: '11px',
                                                color: 'var(--color-text-primary)',
                                                cursor: 'pointer',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '4px',
                                                transition: 'all 0.2s',
                                                marginBottom: '4px',
                                                marginRight: '4px'
                                            }}
                                        >
                                            {getThemeIcon(t.theme)} {getThemeLabel(t.theme)} ({t.count})
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Top Persons */}
                        {data.topPersons.length > 0 && (
                            <div className="theme-section">
                                <h3>People Mentioned</h3>
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
                                <h3>Top Sources</h3>
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
                            <h3>Recent Coverage ({data.signals.length})</h3>
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
                                            <div className="signal-persons">Person: {s.persons.join(', ')}</div>
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
