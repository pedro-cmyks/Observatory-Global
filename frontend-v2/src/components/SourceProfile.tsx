import { useState, useEffect } from 'react'
import { getThemeLabel } from '../lib/themeLabels'
import './SourceProfile.css'

interface SourceProfileData {
    source: string
    summary: {
        total_signals: number
        avg_sentiment: number
        total_countries: number
    }
    top_themes: Array<{ theme: string, count: number, sentiment: number }>
    top_countries: Array<{ country_code: string, count: number, sentiment: number }>
    timeline: Array<{ time: string | null, count: number, sentiment: number }>
}

interface SourceProfileProps {
    domain: string
    hours: number
    onClose: () => void
    onThemeSelect?: (theme: string) => void
    onCountrySelect?: (code: string) => void
}

function sentimentColor(s: number): string {
    if (s > 0.5) return '#4ade80'
    if (s < -0.5) return '#f87171'
    return '#fbbf24'
}

function formatCount(n: number): string {
    if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
    return String(n)
}

export function SourceProfile({ domain, hours, onClose, onThemeSelect, onCountrySelect }: SourceProfileProps) {
    const [data, setData] = useState<SourceProfileData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        setLoading(true)
        setError(null)
        const params = new URLSearchParams({ hours: String(hours) })
        fetch(`/api/v2/source/${encodeURIComponent(domain)}/profile?${params}`)
            .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
            .then(json => {
                if (json.error) throw new Error(json.error)
                setData(json)
            })
            .catch(e => setError(e.message))
            .finally(() => setLoading(false))
    }, [domain, hours])

    const maxThemeCount = data?.top_themes.reduce((max, t) => Math.max(max, t.count), 0) || 1
    const maxCountryCount = data?.top_countries.reduce((max, c) => Math.max(max, c.count), 0) || 1

    return (
        <div className="source-profile">
            <div className="source-profile-header">
                <div className="source-profile-title">
                    <h2>{domain}</h2>
                </div>
                <button className="source-profile-close" onClick={onClose}>×</button>
            </div>

            {loading && (
                <div className="source-loading">
                    <div className="spinner"></div>
                    <div style={{ marginTop: '1rem' }}>Profiling source...</div>
                </div>
            )}

            {error && (
                <div className="source-error">
                    Failed to load profile for {domain}<br />
                    {error}
                </div>
            )}

            {!loading && data && (
                <>
                    <div className="source-profile-section">
                        <h3>Source Footprint</h3>
                        <div className="source-metrics-grid">
                            <div className="source-metric">
                                <div className="source-metric-value">{formatCount(data.summary.total_signals)}</div>
                                <div className="source-metric-label">Signals</div>
                            </div>
                            <div className="source-metric">
                                <div className="source-metric-value">{data.summary.total_countries}</div>
                                <div className="source-metric-label">Countries</div>
                            </div>
                            <div className="source-metric">
                                <div className="source-metric-value" style={{ color: sentimentColor(data.summary.avg_sentiment) }}>
                                    {data.summary.avg_sentiment > 0 ? '+' : ''}{data.summary.avg_sentiment.toFixed(2)}
                                </div>
                                <div className="source-metric-label">Avg Tone</div>
                            </div>
                        </div>
                    </div>

                    {data.top_themes.length > 0 && (
                        <div className="source-profile-section">
                            <h3>Thematic Focus</h3>
                            <div className="source-theme-list">
                                {data.top_themes.map(t => (
                                    <div 
                                        key={t.theme} 
                                        className="source-theme-row" 
                                        style={{ cursor: onThemeSelect ? 'pointer' : 'default' }}
                                        onClick={() => onThemeSelect?.(t.theme)}
                                    >
                                        <span className="source-theme-name" title={getThemeLabel(t.theme)}>{getThemeLabel(t.theme)}</span>
                                        <div className="source-bar-wrap">
                                            <div 
                                                className="source-bar" 
                                                style={{ width: `${(t.count / maxThemeCount) * 100}%`, background: sentimentColor(t.sentiment) }}
                                            />
                                        </div>
                                        <span className="source-count">{formatCount(t.count)}</span>
                                        <span className="source-sentiment" style={{ color: sentimentColor(t.sentiment) }}>
                                            {t.sentiment > 0 ? '+' : ''}{t.sentiment.toFixed(1)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {data.top_countries.length > 0 && (
                        <div className="source-profile-section">
                            <h3>Geographic Focus</h3>
                            <div className="source-country-list">
                                {data.top_countries.map(c => (
                                    <div 
                                        key={c.country_code} 
                                        className="source-country-row"
                                        style={{ cursor: onCountrySelect ? 'pointer' : 'default' }}
                                        onClick={() => onCountrySelect?.(c.country_code)}
                                    >
                                        <span className="source-country-code">{c.country_code}</span>
                                        <div className="source-bar-wrap">
                                            <div 
                                                className="source-bar" 
                                                style={{ width: `${(c.count / maxCountryCount) * 100}%`, background: sentimentColor(c.sentiment) }}
                                            />
                                        </div>
                                        <span className="source-count">{formatCount(c.count)}</span>
                                        <span className="source-sentiment" style={{ color: sentimentColor(c.sentiment) }}>
                                            {c.sentiment > 0 ? '+' : ''}{c.sentiment.toFixed(1)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}
