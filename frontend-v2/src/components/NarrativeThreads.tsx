import React, { useEffect, useState, useCallback } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import { timeRangeToHours } from '../lib/timeRanges'
import { getThemeLabel } from '../lib/themeLabels'
import './NarrativeThreads.css'

interface TimelinePoint {
    hour: string
    count: number
}

interface Narrative {
    theme_code: string
    label: string
    signal_count: number
    country_count: number
    source_count: number
    first_seen: string | null
    velocity: number
    trend: 'accelerating' | 'stable' | 'fading'
    spread_pct: number
    avg_sentiment: number
    top_persons: string[]
    hourly_timeline: TimelinePoint[]
    top_countries: string[]
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

export const NarrativeThreads: React.FC = () => {
    const [narratives, setNarratives] = useState<Narrative[]>([])
    const [loading, setLoading] = useState(true)
    const { filter, setFocus, setMapFlyCountry } = useFocus()
    const { timeRange } = useFocusData()

    // Cap to 24h when browsing globally (spread_pct becomes meaningless at wider windows);
    // when a country is selected, use the full range so client-side filtering has real data.
    const rawHours = timeRangeToHours(timeRange)
    const cappedHours = filter.country ? rawHours : Math.min(rawHours, 24)
    const isCapped = !filter.country && rawHours > 24

    // When a country is active, fetch more threads so we can filter client-side
    const fetchLimit = filter.country ? 20 : 5

    const fetchNarratives = useCallback(async () => {
        try {
            const res = await fetch(`/api/v2/narratives?hours=${cappedHours}&limit=${fetchLimit}`)
            if (!res.ok) return
            const data = await res.json()
            setNarratives(data.narratives || [])
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
    const displayedNarratives = filter.country
        ? narratives.filter(n => n.top_countries.includes(filter.country!)).slice(0, 5)
        : narratives

    const handleClick = (n: Narrative) => {
        setFocus('theme', n.theme_code, n.label || getThemeLabel(n.theme_code))
        if (n.top_countries.length > 0) {
            setMapFlyCountry(n.top_countries[0])
        }
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
                    Showing narratives active in {filter.country}
                </div>
            )}
            {isCapped && !filter.country && (
                <div className="narrative-cap-notice">
                    Showing last 24h — narratives are most meaningful at shorter windows
                </div>
            )}
            {displayedNarratives.map(n => {
                const isFocused = filter.theme === n.theme_code
                // Dim conditions:
                //  - a theme is locked AND it's not this row → dim
                //  - a country is locked AND this thread doesn't cover that country → dim
                const dimByTheme = !!filter.theme && filter.theme !== n.theme_code
                const dimByCountry = !!filter.country && !n.top_countries.includes(filter.country)
                const isDimmed = dimByTheme || dimByCountry
                const trendArrow = n.trend === 'accelerating' ? '▲' : n.trend === 'fading' ? '▼' : '→'
                const spreadClass = n.spread_pct < 30 ? 'low' : n.spread_pct < 60 ? 'mid' : 'high'
                // Plain-language hover hint — falls back to label when no description is available.
                // Using native title attribute so it works without any new component plumbing.
                const rowHint = `${n.label || getThemeLabel(n.theme_code)} — ${n.signal_count.toLocaleString()} signals across ${n.country_count} countries. Click to open the topic breakdown.`

                return (
                    <div
                        key={n.theme_code}
                        className={`narrative-row ${isFocused ? 'focused' : ''} ${isDimmed ? 'dimmed' : ''}`}
                        data-tip={rowHint}
                        onClick={() => handleClick(n)}
                    >
                        {/* Row 1: Label + stats */}
                        <div className="narrative-header">
                            <div className="narrative-label">
                                <span className={`sentiment-dot ${n.avg_sentiment > 0.1 ? 'pos' : n.avg_sentiment < -0.1 ? 'neg' : 'neu'}`} data-tip={`Avg sentiment: ${n.avg_sentiment > 0.1 ? 'positive (supportive framing)' : n.avg_sentiment < -0.1 ? 'negative (critical or conflict framing)' : 'neutral'}`} />
                                <span className={`trend-arrow ${n.trend}`}>{trendArrow}</span>
                                <span>{n.label || getThemeLabel(n.theme_code)}</span>
                            </div>
                            <div className="narrative-stats">
                                <span data-tip="Total media signals (articles, posts) mentioning this topic in the selected time window">{n.signal_count.toLocaleString()} sig</span>
                                {' · '}
                                <span data-tip="Number of distinct countries where this topic is being covered">{n.country_count} ctry</span>
                            </div>
                        </div>

                        {/* Row 2: Countries, Persons, attention badges + age */}
                        <div className="narrative-detail">
                            <div className="narrative-entities">
                                {n.top_countries.map(c => (
                                    <span key={c} className="country-pip">{c}</span>
                                ))}
                                {n.top_persons.map(p => (
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
                            <div className="spread-track" data-tip="Geographic spread: how widely this topic is covered across countries. 100% = present in every country we track">
                                <div
                                    className={`spread-fill ${spreadClass}`}
                                    style={{ width: `${Math.min(n.spread_pct, 100)}%` }}
                                />
                            </div>
                            <span className="spread-label" data-tip="Geographic spread: % of tracked countries covering this topic">{n.spread_pct}%</span>
                            <span className={`trend-label ${n.trend}`} data-tip="Trend: Accelerating = volume growing, Fading = volume declining, Stable = consistent">
                                {n.trend === 'accelerating' ? '▲ Accelerating' : n.trend === 'fading' ? '▼ Fading' : '→ Stable'}
                            </span>
                        </div>

                        {/* Row 4: Sparkline */}
                        <div data-tip="Signal volume over time — each point is one hour. Rising = growing coverage, falling = cooling off.">
                            <Sparkline data={n.hourly_timeline} trend={n.trend} />
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
