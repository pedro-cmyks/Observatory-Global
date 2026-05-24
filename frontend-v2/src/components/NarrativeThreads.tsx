import React, { useEffect, useState, useCallback } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import { timeRangeToHours } from '../lib/timeRanges'
import { resolveCountryName } from '../lib/countryNames'
import { getNarrativeFetchLimit, getNarrativesForDisplay } from '../lib/narrativeThreadLimits'
import './NarrativeThreads.css'

const THREAD_COLORS = [
    { gradient: 'linear-gradient(90deg, #f97316, #fbbf24)', accent: '#f97316' },
    { gradient: 'linear-gradient(90deg, #6366f1, #818cf8)', accent: '#6366f1' },
    { gradient: 'linear-gradient(90deg, #14b8a6, #22d3ee)', accent: '#14b8a6' },
    { gradient: 'linear-gradient(90deg, #8b5cf6, #a78bfa)', accent: '#8b5cf6' },
    { gradient: 'linear-gradient(90deg, #22c55e, #84cc16)', accent: '#22c55e' },
]

interface TimelinePoint {
    hour: string
    count: number
}

interface Narrative {
    thread_id: string
    label: string
    anchor_topics: string[]
    parent_domain: string | null
    signal_count: number
    country_count: number
    source_count: number
    first_seen: string | null
    changed_10h: number
    trend: 'accelerating' | 'stable' | 'fading'
    confidence_pct: number
    sentiment_swing_10h: number | null
    top_entities: string[]
    hourly_timeline: TimelinePoint[]
    top_countries: string[]
    top_country_names: string[]
    // Enrichment: public attention signals
    has_public_interest?: boolean
    trending_keywords?: string[]
    has_wiki_activity?: boolean
    wiki_views?: number
}

// Sparkline SVG component
const Sparkline: React.FC<{ data: TimelinePoint[], trend: string }> = ({ data, trend }) => {
    if (!data || data.length < 2) return null

    const width = 200
    const height = 26
    const padding = 2
    const max = Math.max(...data.map(d => d.count), 1)

    const points = data.map((d, i) => {
        const x = padding + (i / (data.length - 1)) * (width - padding * 2)
        const y = height - padding - ((d.count / max) * (height - padding * 2))
        return `${x},${y}`
    }).join(' ')

    // Area fill polygon
    const firstX = padding
    const lastX = padding + ((data.length - 1) / (data.length - 1)) * (width - padding * 2)
    const areaPoints = `${firstX},${height} ${points} ${lastX},${height}`

    const strokeColor = trend === 'accelerating' ? '#ef4444' : trend === 'fading' ? '#64748b' : '#60a5fa'

    return (
        <svg className="narrative-sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
            <polygon points={areaPoints} fill={strokeColor} />
            <polyline points={points} stroke={strokeColor} />
        </svg>
    )
}

// Format time ago
const timeAgo = (isoString: string | null): string => {
    if (!isoString) return ''
    const diff = Date.now() - new Date(isoString).getTime()
    const hours = Math.floor(diff / 3600000)
    if (hours < 1) return 'Started < 1h ago'
    if (hours < 24) return `Started ${hours}h ago`
    const days = Math.floor(hours / 24)
    return `Started ${days}d ago`
}

const normalizeTrend = (trend: string): Narrative['trend'] => {
    if (trend === 'surging') return 'accelerating'
    if (trend === 'fading') return 'fading'
    return 'stable'
}

const normalizeThread = (thread: any): Narrative => ({
    thread_id: thread.thread_id,
    label: thread.label || thread.summary || thread.thread_id,
    anchor_topics: thread.anchor_topics || [],
    parent_domain: thread.parent_domain || null,
    signal_count: thread.signal_count || 0,
    country_count: thread.country_count || 0,
    source_count: thread.source_count || 0,
    first_seen: thread.first_seen || null,
    changed_10h: thread.changed_10h || 0,
    trend: normalizeTrend(thread.trend),
    confidence_pct: Math.round((thread.avg_confidence || 0) * 1000) / 10,
    sentiment_swing_10h: thread.sentiment_swing_10h ?? null,
    top_entities: thread.top_entities || thread.top_people || [],
    hourly_timeline: thread.hourly_timeline || [],
    top_countries: thread.top_countries || [],
    top_country_names: thread.top_country_names || [],
})

interface NarrativeThreadsProps {
    onCountrySelect?: (code: string) => void
}

export const NarrativeThreads: React.FC<NarrativeThreadsProps> = ({ onCountrySelect }) => {
    const [narratives, setNarratives] = useState<Narrative[]>([])
    const [effectiveHours, setEffectiveHours] = useState<number | null>(null)
    const [loading, setLoading] = useState(true)
    const { filter, setFocus, setCountry, setMapFlyCountry } = useFocus()
    const { timeRange } = useFocusData()

    // Cap to 24h when browsing globally (spread_pct becomes meaningless at wider windows);
    // when a country is selected, use the full range so client-side filtering has real data.
    const rawHours = timeRangeToHours(timeRange)
    const cappedHours = filter.country ? rawHours : Math.min(rawHours, 24)
    const isCapped = !filter.country && rawHours > 24

    // Fetch enough rows for the panel to use the available vertical space.
    const fetchLimit = getNarrativeFetchLimit(!!filter.country)

    const fetchNarratives = useCallback(async () => {
        try {
            const res = await fetch(`/api/v2/threads?hours=${cappedHours}&limit=${fetchLimit}`)
            if (!res.ok) return
            const data = await res.json()
            setNarratives((data.threads || []).map(normalizeThread))
            setEffectiveHours(data.hours ?? null)
        } catch (e) {
            console.error('[NarrativeThreads] Fetch error', e)
        } finally {
            setLoading(false)
        }
    }, [cappedHours, fetchLimit])

    // Initial fetch + 5-minute interval; re-fetch when country changes
    useEffect(() => {
        setLoading(true)
        fetchNarratives()
        const interval = setInterval(fetchNarratives, 5 * 60 * 1000)
        return () => clearInterval(interval)
    }, [fetchNarratives])

    // When country is active, show only threads that include that country
    const displayedNarratives = getNarrativesForDisplay(narratives, filter.country ?? undefined)

    const handleClick = (n: Narrative) => {
        const anchorTopic = n.anchor_topics[0] || n.thread_id.split('--')[0]
        setFocus('theme', anchorTopic, n.label)
        if (n.top_countries.length > 0) {
            setMapFlyCountry(n.top_countries[0])
            onCountrySelect?.(n.top_countries[0])
        }
    }

    const handleCountryPipClick = (e: React.MouseEvent, code: string) => {
        e.stopPropagation()
        setCountry(code)
        setMapFlyCountry(code)
        onCountrySelect?.(code)
    }

    // Loading skeleton
    if (loading && narratives.length === 0) {
        return (
            <div className="narrative-threads-container">
                {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="narrative-skeleton">
                        <div className="skeleton-line" />
                        <div className="skeleton-line" />
                        <div className="skeleton-line" />
                        <div className="skeleton-line" />
                    </div>
                ))}
            </div>
        )
    }

    if (narratives.length === 0) {
        return (
            <div className="narrative-threads-container">
                <div className="narrative-empty">No active narratives in this time range</div>
            </div>
        )
    }

    if (displayedNarratives.length === 0 && filter.country) {
        return (
            <div className="narrative-threads-container">
                <div className="narrative-empty">No top narrative threads found for {filter.country} in this window</div>
            </div>
        )
    }

    return (
        <div className="narrative-threads-container">
            {filter.country && (
                <div className="narrative-country-filter-notice">
                    Threads active in {filter.country}: signal counts are global
                </div>
            )}
            {isCapped && !filter.country && (
                <div className="narrative-cap-notice">
                    Showing last 24h: narratives are most meaningful at shorter windows
                </div>
            )}
            {effectiveHours != null && effectiveHours < cappedHours && (
                <div className="narrative-cap-notice">
                    Thread details show last {effectiveHours}h · counts reflect full {cappedHours}h window
                </div>
            )}
            {displayedNarratives.map(n => {
                const anchorTopic = n.anchor_topics[0] || n.thread_id.split('--')[0]
                const isFocused = filter.theme === anchorTopic
                // Dim conditions:
                //  - a theme is locked AND it's not this row -> dim
                //  - a country is locked AND this thread doesn't cover that country -> dim
                const dimByTheme = !!filter.theme && filter.theme !== anchorTopic
                const dimByCountry = !!filter.country && !n.top_countries.includes(filter.country)
                const isDimmed = dimByTheme || dimByCountry
                const trendArrow = n.trend === 'accelerating' ? '▲' : n.trend === 'fading' ? '▼' : '→'
                // Plain-language hover hint; falls back to label when no description is available.
                const rowHint = `${n.label}: ${n.signal_count.toLocaleString()} signals across ${n.country_count} countries from ${n.source_count} sources. Click to open the topic breakdown.`
                const domainLabel = (n.parent_domain || 'living thread').replace(/-/g, ' ')

                const colorIdx = displayedNarratives.indexOf(n) % THREAD_COLORS.length
                const threadColor = THREAD_COLORS[colorIdx]
                return (
                    <div
                        key={n.thread_id}
                        className={`narrative-row ${isFocused ? 'focused' : ''} ${isDimmed ? 'dimmed' : ''}`}
                        data-tip={rowHint}
                        onClick={() => handleClick(n)}
                        style={{ borderLeftColor: threadColor.accent }}
                    >
                        {/* Row 1: Label + stats */}
                        <div className="narrative-header">
                            <div className="narrative-label">
                                <span className={`sentiment-dot ${n.sentiment_swing_10h && n.sentiment_swing_10h > 0.1 ? 'pos' : n.sentiment_swing_10h && n.sentiment_swing_10h < -0.1 ? 'neg' : 'neu'}`} data-tip={`10h sentiment swing: ${n.sentiment_swing_10h == null ? 'not available' : n.sentiment_swing_10h.toFixed(2)}`} />
                                <span className={`trend-arrow ${n.trend}`}>{trendArrow}</span>
                                <span className="narrative-label-text">
                                    {n.label}
                                    <span className="narrative-cluster-label">
                                        {domainLabel}
                                    </span>
                                    {n.top_countries.length > 0 && (
                                        <span className="narrative-label-country">
                                            {' · '}{resolveCountryName(n.top_countries[0])}
                                        </span>
                                    )}
                                </span>
                            </div>
                            <span className="narrative-count" data-tip={`${n.signal_count.toLocaleString()} media signals in the selected window`}>
                                {n.signal_count > 999 ? `${(n.signal_count / 1000).toFixed(1)}k` : n.signal_count}
                                {n.signal_count < 10 && (
                                    <span className="coverage-badge coverage-badge--thin" data-tip={`Only ${n.signal_count} signals — treat as indicative only`}>thin</span>
                                )}
                                {n.signal_count >= 10 && n.signal_count < 50 && (
                                    <span className="coverage-badge coverage-badge--limited" data-tip={`${n.signal_count} signals — limited coverage`}>~</span>
                                )}
                            </span>
                        </div>

                        {/* Row 2: Countries, Persons, attention badges + age */}
                        <div className="narrative-detail">
                            <div className="narrative-entities">
                                {n.top_countries.map(c => (
                                    <button key={c} className={`country-pip country-pip--btn${filter.country === c ? ' country-pip--active' : ''}`} onClick={e => handleCountryPipClick(e, c)} data-tip={`Focus on ${c}`}>{c}</button>
                                ))}
                                {n.top_entities.map(p => (
                                    <span key={p} className="person-pip">{p}</span>
                                ))}
                                {n.has_public_interest && (
                                    <span className="attention-badge search" data-tip={`Trending searches: ${(n.trending_keywords || []).join(', ')}`}>
                                        SEARCH
                                    </span>
                                )}
                                {n.has_wiki_activity && (
                                    <span className="attention-badge wiki" data-tip={`${(n.wiki_views || 0).toLocaleString()} Wikipedia views`}>
                                        WIKI {n.wiki_views && n.wiki_views > 1000 ? `${Math.round(n.wiki_views / 1000)}K` : ''}
                                    </span>
                                )}
                            </div>
                            <span className="narrative-age">{timeAgo(n.first_seen)}</span>
                        </div>

                        {/* Row 3: Spread bar + trend */}
                        <div className="spread-row">
                            <div className="narrative-grad-bar-track" data-tip="Atlas confidence: assignment confidence from the living-thread contract.">
                                <div
                                    className="narrative-grad-bar-fill"
                                    style={{
                                        width: `${Math.min(n.confidence_pct, 100)}%`,
                                        background: threadColor.gradient,
                                    }}
                                />
                            </div>
                            <span className="spread-label" data-tip="Atlas confidence for this living thread">{n.confidence_pct}%</span>
                            <span className={`trend-label ${n.trend}`} data-tip="Trend: Accelerating = volume growing, Fading = volume declining, Stable = consistent">
                                {n.trend === 'accelerating' ? '▲ Accelerating' : n.trend === 'fading' ? '▼ Fading' : '→ Stable'}
                            </span>
                        </div>

                        {/* Row 4: Sparkline */}
                        <div data-tip="Signal volume over time: each point is one hour. Rising = growing coverage, falling = cooling off.">
                            <Sparkline data={n.hourly_timeline} trend={n.trend} />
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
