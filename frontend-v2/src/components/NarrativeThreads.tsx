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
    hourly_timeline: TimelinePoint[]
    top_countries: string[]
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

    // Cap narrative queries to 24h — at longer windows, all themes converge to 85-90% spread
    const cappedHours = Math.min(timeRangeToHours(timeRange), 24)
    const isCapped = timeRangeToHours(timeRange) > 24

    const fetchNarratives = useCallback(async () => {
        try {
            const res = await fetch(`/api/v2/narratives?hours=${cappedHours}&limit=5`)
            if (!res.ok) return
            const data = await res.json()
            setNarratives(data.narratives || [])
        } catch (e) {
            console.error('[NarrativeThreads] Fetch error', e)
        } finally {
            setLoading(false)
        }
    }, [cappedHours])

    // Initial fetch + 5-minute interval
    useEffect(() => {
        setLoading(true)
        fetchNarratives()
        const interval = setInterval(fetchNarratives, 5 * 60 * 1000)
        return () => clearInterval(interval)
    }, [fetchNarratives])

    const handleClick = (n: Narrative) => {
        setFocus('theme', n.theme_code, getThemeLabel(n.theme_code))
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

    return (
        <div className="narrative-threads-container">
            {isCapped && (
                <div className="narrative-cap-notice">
                    Showing last 24h — narratives are most meaningful at shorter windows
                </div>
            )}
            {narratives.map(n => {
                const isFocused = filter.theme === n.theme_code
                const trendArrow = n.trend === 'accelerating' ? '▲' : n.trend === 'fading' ? '▼' : '→'
                const spreadClass = n.spread_pct < 30 ? 'low' : n.spread_pct < 60 ? 'mid' : 'high'

                return (
                    <div
                        key={n.theme_code}
                        className={`narrative-row ${isFocused ? 'focused' : ''}`}
                        onClick={() => handleClick(n)}
                    >
                        {/* Row 1: Label + stats */}
                        <div className="narrative-header">
                            <div className="narrative-label">
                                <span className={`trend-arrow ${n.trend}`}>{trendArrow}</span>
                                <span>{getThemeLabel(n.theme_code)}</span>
                            </div>
                            <div className="narrative-stats">
                                {n.signal_count.toLocaleString()} sig · {n.country_count} ctry
                            </div>
                        </div>

                        {/* Row 2: Countries + age */}
                        <div className="narrative-detail">
                            <div className="narrative-countries">
                                {n.top_countries.map(c => (
                                    <span key={c} className="country-pip">{c}</span>
                                ))}
                            </div>
                            <span className="narrative-age">{timeAgo(n.first_seen)}</span>
                        </div>

                        {/* Row 3: Spread bar + trend */}
                        <div className="spread-row">
                            <div className="spread-track">
                                <div
                                    className={`spread-fill ${spreadClass}`}
                                    style={{ width: `${Math.min(n.spread_pct, 100)}%` }}
                                />
                            </div>
                            <span className="spread-label">{n.spread_pct}%</span>
                            <span className={`trend-label ${n.trend}`}>
                                {n.trend === 'accelerating' ? '▲ Accelerating' : n.trend === 'fading' ? '▼ Fading' : '→ Stable'}
                            </span>
                        </div>

                        {/* Row 4: Sparkline */}
                        <Sparkline data={n.hourly_timeline} trend={n.trend} />
                    </div>
                )
            })}
        </div>
    )
}
