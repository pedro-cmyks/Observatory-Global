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
    originCountry?: string
    originCountryName?: string
    hours: number

    onClose: () => void
    onThemeSelect?: (theme: string) => void
    onCountryCardClick?: (code: string, name: string) => void
}

export function ThemeDetail({ theme, originCountry, originCountryName, hours, onClose, onThemeSelect, onCountryCardClick }: ThemeDetailProps) {
    const [data, setData] = useState<ThemeData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [insight, setInsight] = useState<string | null>(null)
    const [insightLoading, setInsightLoading] = useState(false)
    const [insightFailed, setInsightFailed] = useState(false)
    const [selectedSource, setSelectedSource] = useState<string | null>(null)
    const [drillCountry, setDrillCountry] = useState<string | null>(null)
    const [drillCountryName, setDrillCountryName] = useState<string | null>(null)

    // Reset drill state when theme changes
    useEffect(() => {
        setDrillCountry(null)
        setDrillCountryName(null)
    }, [theme])

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true)
            setError(null)
            setInsight(null)
            setSelectedSource(null)
            try {
                const params = new URLSearchParams({ hours: hours.toString() })
                if (drillCountry) params.append('country_code', drillCountry)
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
    }, [theme, hours, drillCountry])

    const [insightError, setInsightError] = useState<string | null>(null)

    // Fetch AI insight async after main data loads
    useEffect(() => {
        if (!theme) return
        setInsightLoading(true)
        setInsightFailed(false)
        setInsightError(null)
        setInsight(null)
        const params = new URLSearchParams({ hours: hours.toString() })
        fetch(`/api/v2/theme/${encodeURIComponent(theme)}/insight?${params}`)
            .then(r => r.json().catch(() => null))
            .then(json => {
                if (json?.insight) {
                    setInsight(json.insight)
                } else {
                    setInsightFailed(true)
                    setInsightError(json?.error ?? null)
                }
            })
            .catch(() => { setInsightFailed(true); setInsightError(null) })
            .finally(() => setInsightLoading(false))
    }, [theme, hours])

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
        <div className="theme-detail-overlay">
            <div className="theme-detail-panel">
                <button className="theme-detail-close" onClick={onClose} style={{ display: 'none' }} />


                <div className="theme-detail-header">
                    <span className="theme-detail-icon">{getThemeIcon(theme)}</span>
                    <div style={{ flex: 1 }}>
                        <h2>{getThemeLabel(theme)}</h2>
                        {drillCountry ? (
                            <p className="theme-detail-meta">
                                <button
                                    className="drill-back-btn"
                                    onClick={() => { setDrillCountry(null); setDrillCountryName(null) }}
                                >
                                    ← Global
                                </button>
                                {' · '}{getFlag(drillCountry)} {drillCountryName} · {data?.total || 0} signals
                            </p>
                        ) : (
                            <p className="theme-detail-meta">
                                Global · {data?.total || 0} signals · Last {hours}h
                                {originCountryName && (
                                    <span className="origin-country-hint"> · opened from {getFlag(originCountry!)} {originCountryName}</span>
                                )}
                            </p>
                        )}
                    </div>
                </div>

                {loading && <div className="theme-detail-loading">Loading...</div>}
                {error && <div className="theme-detail-error">Error: {error}</div>}

                {data && !loading && (
                    <>
                        {/* AI Coverage Insight */}
                        <div className="theme-insight-block">
                            {insightLoading && !insight && (
                                <div className="theme-insight-loading">
                                    <span className="insight-pulse" />
                                    Analyzing coverage patterns…
                                </div>
                            )}
                            {insight && (() => {
                                const paragraphs = insight
                                    .split('\n')
                                    .map(l => l.replace(/^#{1,3}\s*/, '').trim())
                                    .join('\n')
                                    .split(/\n{2,}/)
                                    .map(p => p.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim())
                                    .filter(p => p.length > 0)
                                return paragraphs.map((p, i) => (
                                    <p key={i} className="theme-insight-text">{p}</p>
                                ))
                            })()}
                            {insightFailed && !insightLoading && !insight && (
                                <p className="theme-insight-unavailable">
                                    {insightError === 'insight_unavailable'
                                        ? 'AI analysis not configured — add ANTHROPIC_API_KEY to .env and restart the backend'
                                        : insightError === 'insight_no_credits'
                                        ? 'AI analysis unavailable — Anthropic account has no credits (top up at console.anthropic.com)'
                                        : 'Coverage analysis unavailable'}
                                </p>
                            )}
                        </div>

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

                        {/* HOW IT'S COVERED — Framing Analysis (hidden when drilled into a country) */}
                        {!drillCountry && data.countryFraming && data.countryFraming.length > 0 && (() => {
                            // Assign ranks by volume BEFORE reordering
                            const withRank = data.countryFraming.map((cf, idx) => ({ ...cf, volumeRank: idx + 1 }))
                            let framing = withRank

                            if (originCountry) {
                                const originIdx = framing.findIndex(c => c.country_code === originCountry)
                                if (originIdx > 0) {
                                    const [originEntry] = framing.splice(originIdx, 1)
                                    framing = [originEntry, ...framing]
                                } else if (originIdx === -1) {
                                    const fallback = data.countryBreakdown.find(c => c.code === originCountry)
                                    if (fallback) {
                                        // Find rank by comparing to countryBreakdown order
                                        const breakdownRank = data.countryBreakdown.findIndex(c => c.code === originCountry) + 1
                                        framing = [{
                                            country_code: originCountry,
                                            country_name: originCountryName || originCountry,
                                            signal_count: fallback.count,
                                            avg_sentiment: fallback.sentiment,
                                            top_sub_themes: [],
                                            sentiment_label: fallback.sentiment > 0 ? 'positive' : 'negative',
                                            volumeRank: breakdownRank || framing.length + 1
                                        }, ...framing]
                                    }
                                }
                            }
                            const totalFramingSignals = framing.reduce((s, c) => s + c.signal_count, 0)
                            const extraCountries = data.countryBreakdown.length - data.countryFraming.length
                            return (
                                <div className="theme-section framing-section">
                                    <div className="framing-header-row">
                                        <h3 data-help="Each card shows how a country's media frames this topic. Tone ranges from −10 (critical) to +10 (supportive). Click any card to see country-specific signals.">How It's Covered</h3>
                                        <span className="framing-scope">
                                            top {data.countryFraming.length} of {data.countryBreakdown.length} countries by volume
                                        </span>
                                        <span className="framing-info-btn" title="Each card shows how a country's media covers this topic. Sentiment (tone) ranges from −10 to +10 on the GDELT scale — negative means the topic is framed critically, positive means supportively. Sub-themes show which related topics co-occur most in that country's coverage. Click any card to see that country's panel.">?</span>
                                    </div>
                                    <div className="framing-grid">
                                        {framing.map((cf, idx) => {
                                            const sharePct = totalFramingSignals > 0
                                                ? Math.round((cf.signal_count / totalFramingSignals) * 100)
                                                : 0
                                            const isOrigin = cf.country_code === originCountry
                                            return (
                                                <div
                                                    key={cf.country_code}
                                                    className={`framing-card${isOrigin ? ' framing-card-origin' : ''}`}
                                                    onClick={() => onCountryCardClick
                                                        ? onCountryCardClick(cf.country_code, cf.country_name)
                                                        : (setDrillCountry(cf.country_code), setDrillCountryName(cf.country_name))
                                                    }
                                                    title={`See ${cf.country_name}'s coverage in the side panel`}
                                                >
                                                    <div className="framing-card-header">
                                                        <span className="framing-rank">#{(cf as any).volumeRank ?? idx + 1}</span>
                                                        <span className="framing-flag">{getFlag(cf.country_code)}</span>
                                                        <span className="framing-country-name">{cf.country_name}</span>
                                                    </div>
                                                    <div className="framing-stats">
                                                        <span className="framing-signal-count">
                                                            {cf.signal_count.toLocaleString()} sig
                                                            <span className="framing-share"> · {sharePct}%</span>
                                                        </span>
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
                                            )
                                        })}
                                    </div>
                                    {extraCountries > 0 && (
                                        <p className="framing-more-note">
                                            + {extraCountries} {extraCountries === 1 ? 'country' : 'countries'} with lower volume
                                        </p>
                                    )}
                                </div>
                            )
                        })()}

                        {/* Timeline */}
                        {data.timeline.length > 0 && (
                            <div className="theme-section">
                                <h3 data-help="Hourly signal volume over the selected time window. Colors show average sentiment: green = positive, yellow = neutral, red = negative.">Activity Timeline</h3>
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
                                <h3 data-help="Topics that frequently co-occur with this one in the same signals. Higher count = stronger co-occurrence. Click to open that topic.">Related Topics</h3>
                                <div className="related-grid">
                                    {data.relatedThemes.slice(0, 8).map(t => (
                                        <button
                                            key={t.theme}
                                            className="related-chip"
                                            onClick={() => onThemeSelect?.(t.theme)}
                                        >
                                            <span className="related-chip-icon">{getThemeIcon(t.theme)}</span>
                                            <span className="related-chip-label">{getThemeLabel(t.theme)}</span>
                                            <span className="related-chip-count">{t.count}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Top Persons */}
                        {data.topPersons.length > 0 && (
                            <div className="theme-section">
                                <h3>People Mentioned</h3>
                                <div className="person-pills">
                                    {data.topPersons.slice(0, 8).map(p => (
                                        <span
                                            key={p.name}
                                            className="person-pill"
                                            title={`${p.count} mentions in this topic`}
                                        >
                                            {p.name}
                                            <span className="person-pill-count">{p.count}</span>
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
                                        <div
                                            key={s.name}
                                            className={`source-item ${selectedSource === s.name ? 'source-active' : ''}`}
                                            onClick={() => setSelectedSource(selectedSource === s.name ? null : s.name)}
                                        >
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
                            <h3>
                                Recent Coverage
                                {selectedSource
                                    ? <span className="coverage-filter-label"> · {selectedSource} <button className="coverage-filter-clear" onClick={() => setSelectedSource(null)}>×</button></span>
                                    : <span className="coverage-count-label"> ({data.signals.length})</span>
                                }
                            </h3>
                            {selectedSource && data.signals.filter(s => s.source === selectedSource).length === 0 && (
                                <p className="coverage-source-empty">
                                    No recent signals from {selectedSource} in the last 200 fetched.
                                    This source has {data.topSources.find(s => s.name === selectedSource)?.count ?? 0} total signals over the period —
                                    try a longer time window or view all signals.
                                </p>
                            )}
                            <div className="signals-list">
                                {data.signals
                                    .filter(s => !selectedSource || s.source === selectedSource)
                                    .slice(0, 20).map((s, i) => (
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
