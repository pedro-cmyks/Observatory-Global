import { useState, useEffect } from 'react'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import './CountryThemePanel.css'

interface CountryThemePanelProps {
    theme: string
    countryCode: string
    countryName: string
    hours: number
    onClose: () => void
    onBackToCountry?: () => void
    onThemeSelect?: (theme: string) => void
}

interface ThemeCountryData {
    total: number
    avgSentiment: number
    timeline: Array<{ hour: string; count: number; sentiment: number }>
    relatedThemes: Array<{ theme: string; count: number }>
    topSources: Array<{ name: string; count: number; sentiment: number }>
    signals: Array<{
        timestamp: string
        source: string
        url: string
        sentiment: number
        persons: string[]
    }>
}

const getFlag = (code: string): string => {
    if (!code || code.length !== 2) return '🌐'
    const pts = code.toUpperCase().split('').map(c => 0x1F1E6 + c.charCodeAt(0) - 65)
    return String.fromCodePoint(...pts)
}

const getSentimentColor = (s: number) =>
    s > 0.1 ? '#4ade80' : s < -0.1 ? '#f87171' : '#fbbf24'

export function CountryThemePanel({
    theme, countryCode, countryName, hours, onClose, onBackToCountry, onThemeSelect
}: CountryThemePanelProps) {
    const [data, setData] = useState<ThemeCountryData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        setLoading(true)
        setError(null)
        const params = new URLSearchParams({ hours: hours.toString(), country_code: countryCode })
        fetch(`/api/v2/theme/${encodeURIComponent(theme)}?${params}`)
            .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
            .then(setData)
            .catch(e => setError(String(e)))
            .finally(() => setLoading(false))
    }, [theme, countryCode, hours])

    return (
        <div className="country-theme-panel">
            {/* Header */}
            <div className="ctp-header">
                <div className="ctp-title-row">
                    <span className="ctp-icon">{getThemeIcon(theme)}</span>
                    <div className="ctp-titles">
                        <span className="ctp-theme-name">{getThemeLabel(theme)}</span>
                        <span className="ctp-country-name">{getFlag(countryCode)} {countryName}</span>
                    </div>
                    <button className="ctp-close" onClick={onClose}>×</button>
                </div>
                <div className="ctp-nav">
                    {onBackToCountry && (
                        <button className="ctp-back-btn" onClick={onBackToCountry}>
                            ← {countryName} brief
                        </button>
                    )}
                </div>
            </div>

            {loading && <div className="ctp-loading">Loading…</div>}
            {error && <div className="ctp-error">Error: {error}</div>}

            {data && !loading && (
                <div className="ctp-body">
                    {/* Stats */}
                    <div className="ctp-stats">
                        <div className="ctp-stat">
                            <span className="ctp-stat-value">{data.total}</span>
                            <span className="ctp-stat-label">Signals</span>
                        </div>
                        <div className="ctp-stat">
                            <span className="ctp-stat-value" style={{ color: getSentimentColor(data.avgSentiment) }}>
                                {data.avgSentiment > 0 ? '+' : ''}{data.avgSentiment.toFixed(2)}
                            </span>
                            <span className="ctp-stat-label">Avg Tone</span>
                        </div>
                    </div>

                    {/* Timeline */}
                    {data.timeline.length > 0 && (
                        <section className="ctp-section">
                            <h4>Activity</h4>
                            <div className="ctp-timeline">
                                {data.timeline.map((t, i) => (
                                    <div
                                        key={i}
                                        className="ctp-bar"
                                        style={{
                                            height: `${Math.max(10, (t.count / Math.max(...data.timeline.map(x => x.count))) * 100)}%`,
                                            backgroundColor: getSentimentColor(t.sentiment)
                                        }}
                                        title={`${t.count} signals`}
                                    />
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Related Topics */}
                    {data.relatedThemes.length > 0 && (
                        <section className="ctp-section">
                            <h4>Related Topics</h4>
                            <div className="ctp-chips">
                                {data.relatedThemes.slice(0, 6).map(t => (
                                    <button key={t.theme} className="ctp-chip" onClick={() => onThemeSelect?.(t.theme)}>
                                        <span>{getThemeIcon(t.theme)} {getThemeLabel(t.theme)}</span>
                                        <span className="ctp-chip-count">{t.count}</span>
                                    </button>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Top Sources */}
                    {data.topSources.length > 0 && (
                        <section className="ctp-section">
                            <h4>Sources</h4>
                            <div className="ctp-source-list">
                                {data.topSources.slice(0, 5).map(s => (
                                    <div key={s.name} className="ctp-source-row">
                                        <span className="ctp-source-name">{s.name}</span>
                                        <span className="ctp-source-count">{s.count}</span>
                                        <span className="ctp-source-tone" style={{ color: getSentimentColor(s.sentiment) }}>
                                            {s.sentiment > 0 ? '+' : ''}{s.sentiment.toFixed(1)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Recent Coverage */}
                    {data.signals.length > 0 && (
                        <section className="ctp-section">
                            <h4>Recent Coverage ({data.total})</h4>
                            <div className="ctp-articles">
                                {data.signals.slice(0, 8).map((s, i) => (
                                    <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" className="ctp-article">
                                        <div className="ctp-article-meta">
                                            <span className="ctp-article-source">{s.source}</span>
                                            <span className="ctp-article-tone" style={{ color: getSentimentColor(s.sentiment) }}>
                                                {s.sentiment > 0 ? '+' : ''}{s.sentiment.toFixed(1)}
                                            </span>
                                        </div>
                                        {s.persons.length > 0 && (
                                            <div className="ctp-article-persons">
                                                {s.persons.slice(0, 2).join(', ')}
                                            </div>
                                        )}
                                        <div className="ctp-article-time">
                                            {new Date(s.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                    </a>
                                ))}
                            </div>
                        </section>
                    )}
                </div>
            )}
        </div>
    )
}
