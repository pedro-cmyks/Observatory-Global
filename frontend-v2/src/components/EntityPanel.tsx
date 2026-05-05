import { useState, useEffect } from 'react'
import { getThemeLabel } from '../lib/themeLabels'
import { timeRangeToHours } from '../lib/timeRanges'
import { type TimeRange } from '../lib/timeRanges'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { Pin, PinOff } from 'lucide-react'
import './EntityPanel.css'

interface FocusNode {
    country_code: string
    signal_count: number
    avg_sentiment: number
    unique_sources: number
}

interface FocusData {
    summary: { total_signals: number; total_countries: number }
    nodes: FocusNode[]
    related_topics: Array<{ topic: string; count: number }>
    top_sources: Array<{ source: string; count: number; avg_sentiment: number }>
    headlines: Array<{ url: string; source: string; time: string | null }>
}

interface EntityPanelProps {
    focusType: 'person' | 'theme'
    focusValue: string
    timeRange: TimeRange
    onClose: () => void
    onThemeSelect?: (theme: string) => void
    onCountrySelect?: (code: string) => void
    onSourceClick?: (domain: string) => void
    onCompareClick?: (person: string) => void
    inline?: boolean
}

function sentimentColor(s: number): string {
    if (s > 0.5) return '#4ade80'
    if (s < -0.5) return '#f87171'
    return '#fbbf24'
}

function sentimentLabel(s: number): string {
    if (s > 1) return 'positive'
    if (s > 0.2) return 'slightly positive'
    if (s < -1) return 'negative'
    if (s < -0.2) return 'slightly negative'
    return 'neutral'
}

function formatCount(n: number): string {
    if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
    return String(n)
}

export function EntityPanel({ focusType, focusValue, timeRange, onClose, onThemeSelect, onCountrySelect, onSourceClick, onCompareClick, inline }: EntityPanelProps) {
    const cls = `entity-panel${inline ? ' entity-panel--inline' : ''}`
    const [data, setData] = useState<FocusData | null>(null)
    const [loading, setLoading] = useState(true)
    const hours = timeRangeToHours(timeRange)
    const { pinItem, unpinItem, isPinned } = useWorkspace()

    useEffect(() => {
        setLoading(true)
        setData(null)
        const params = new URLSearchParams({
            focus_type: focusType,
            value: focusValue,
            hours: String(hours)
        })
        fetch(`/api/v2/focus?${params}`)
            .then(r => r.ok ? r.json() : null)
            .then(json => { if (json) setData(json) })
            .catch(() => {})
            .finally(() => setLoading(false))
    }, [focusType, focusValue, hours])

    const displayName = focusType === 'person'
        ? focusValue.replace(/\b\w/g, c => c.toUpperCase())
        : getThemeLabel(focusValue)

    const globalSentiment = data?.nodes?.length
        ? data.nodes.reduce((sum, n) => sum + n.avg_sentiment * n.signal_count, 0) /
          data.nodes.reduce((sum, n) => sum + n.signal_count, 0)
        : null

    const totalSources = data?.nodes?.reduce((sum, n) => sum + n.unique_sources, 0) ?? 0
    const topNodes = data?.nodes?.slice(0, 10) ?? []

    return (
        <div className={cls}>
            {/* Header */}
            <div className="entity-header">
                <div className="entity-header-meta">
                    <span className="entity-type-tag">
                        {focusType === 'person' ? 'PERSON' : 'THEME'}
                    </span>
                    <span className="entity-timerange">{timeRange}</span>
                </div>
                <button className="entity-close" onClick={onClose}>×</button>
            </div>

            <div className="entity-title-block">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <h2 className="entity-name">{displayName}</h2>
                        <button 
                            onClick={() => {
                                const pinnedId = `${focusType}-${focusValue}`
                                if (isPinned(pinnedId)) {
                                    unpinItem(pinnedId)
                                } else {
                                    const params = new URLSearchParams()
                                    params.set(focusType, focusValue)
                                    pinItem({
                                        id: pinnedId,
                                        type: focusType,
                                        title: displayName,
                                        urlParams: `?${params.toString()}`
                                    })
                                }
                            }}
                            title={isPinned(`${focusType}-${focusValue}`) ? `Unpin ${focusType}` : `Pin ${focusType} to Workspace`}
                            style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', color: isPinned(`${focusType}-${focusValue}`) ? '#10b981' : '#94a3b8', width: '24px', height: '24px', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', transition: 'all 0.2s' }}
                        >
                            {isPinned(`${focusType}-${focusValue}`) ? <PinOff size={12} /> : <Pin size={12} />}
                        </button>
                    </div>
                    {focusType === 'person' && onCompareClick && (
                        <button 
                            className="entity-compare-btn"
                            onClick={() => {
                                const other = prompt("Enter name of person to compare with:");
                                if (other) onCompareClick(other);
                            }}
                            style={{ background: 'transparent', border: '1px solid #6366f1', color: '#a5b4fc', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
                        >
                            Compare With...
                        </button>
                    )}
                </div>
                {data && (
                    <div className="entity-subtitle">
                        <span>{formatCount(data.summary.total_signals)} signals</span>
                        <span className="entity-dot">·</span>
                        <span>{data.summary.total_countries} countries</span>
                        {globalSentiment !== null && (
                            <>
                                <span className="entity-dot">·</span>
                                <span style={{ color: sentimentColor(globalSentiment) }}>
                                    {sentimentLabel(globalSentiment)}
                                </span>
                            </>
                        )}
                    </div>
                )}
            </div>

            {loading && (
                <div className="entity-loading">
                    {Array.from({ length: 8 }).map((_, i) => (
                        <div key={i} className="entity-skeleton" style={{ width: `${70 + Math.random() * 25}%` }} />
                    ))}
                </div>
            )}

            {!loading && data && (
                <div className="entity-body">

                    {/* Trust Indicators */}
                    <div className="entity-section">
                        <div className="entity-section-label">Trust Indicators</div>
                        <div className="entity-indicators">
                            <div className="entity-indicator">
                                <span className="indicator-label">Source Diversity</span>
                                <span className="indicator-value">{Math.min(totalSources, 999)}</span>
                            </div>
                            <div className="entity-indicator">
                                <span className="indicator-label">Countries Reporting</span>
                                <span className="indicator-value">{data.summary.total_countries}</span>
                            </div>
                            <div className="entity-indicator">
                                <span className="indicator-label">Global Sentiment</span>
                                <span className="indicator-value" style={{ color: globalSentiment !== null ? sentimentColor(globalSentiment) : undefined }}>
                                    {globalSentiment !== null ? globalSentiment.toFixed(2) : '—'}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Top Countries */}
                    {topNodes.length > 0 && (
                        <div className="entity-section">
                            <div className="entity-section-label">Coverage by Country</div>
                            <div className="entity-country-list">
                                {topNodes.map((node, i) => (
                                    <div
                                        key={node.country_code}
                                        className="entity-country-row"
                                        onClick={() => onCountrySelect?.(node.country_code)}
                                    >
                                        <span className="entity-country-rank">#{i + 1}</span>
                                        <span className="entity-country-code">{node.country_code}</span>
                                        <div className="entity-country-bar-wrap">
                                            <div
                                                className="entity-country-bar"
                                                style={{
                                                    width: `${(node.signal_count / topNodes[0].signal_count) * 100}%`,
                                                    background: sentimentColor(node.avg_sentiment)
                                                }}
                                            />
                                        </div>
                                        <span className="entity-country-count">{formatCount(node.signal_count)}</span>
                                        <span className="entity-country-sentiment" style={{ color: sentimentColor(node.avg_sentiment) }}>
                                            {node.avg_sentiment > 0 ? '+' : ''}{node.avg_sentiment.toFixed(1)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Top Themes */}
                    {data.related_topics.length > 0 && (
                        <div className="entity-section">
                            <div className="entity-section-label">Related Themes</div>
                            <div className="entity-themes">
                                {data.related_topics.slice(0, 10).map(t => (
                                    <button
                                        key={t.topic}
                                        className="entity-theme-chip"
                                        onClick={() => onThemeSelect?.(t.topic)}
                                        title={`${t.count} signals`}
                                    >
                                        {getThemeLabel(t.topic)}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Top Sources */}
                    {data.top_sources.length > 0 && (
                        <div className="entity-section">
                            <div className="entity-section-label">Top Sources</div>
                            <div className="entity-sources">
                                {data.top_sources.slice(0, 6).map(s => (
                                    <div 
                                        key={s.source} 
                                        className="entity-source-row"
                                        style={{ cursor: onSourceClick ? 'pointer' : 'default' }}
                                        onClick={() => onSourceClick?.(s.source)}
                                    >
                                        <span className="entity-source-name">{s.source}</span>
                                        <span className="entity-source-count">{formatCount(s.count)}</span>
                                        <span className="entity-source-sentiment" style={{ color: sentimentColor(s.avg_sentiment) }}>
                                            {s.avg_sentiment > 0 ? '+' : ''}{s.avg_sentiment.toFixed(1)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Recent Coverage */}
                    {data.headlines.length > 0 && (
                        <div className="entity-section">
                            <div className="entity-section-label">Recent Coverage</div>
                            <div className="entity-headlines">
                                {data.headlines.slice(0, 8).map((h, i) => (
                                    <a
                                        key={i}
                                        href={h.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="entity-headline"
                                    >
                                        <span className="entity-headline-source">{h.source}</span>
                                        <span className="entity-headline-url">
                                            {h.url.replace(/^https?:\/\/[^/]+/, '').slice(0, 60) || h.url.slice(0, 60)}
                                        </span>
                                    </a>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {!loading && !data && (
                <div className="entity-empty">No data available for this {focusType}</div>
            )}
        </div>
    )
}
