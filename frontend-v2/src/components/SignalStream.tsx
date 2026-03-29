import React, { useEffect, useState, useRef } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import { timeRangeToHours } from '../lib/timeRanges'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import './SignalStream.css'

interface Signal {
    id: number
    timestamp: string
    country: string
    source: string
    url: string
    headline: string | null
    sentiment: number
    themes: string[]
}

interface Velocity {
    signals_per_minute: number
    delta: number
    percentage_change: number
}

// Helper to determine sentiment color
const getSentimentClass = (sentiment: number) => {
    if (sentiment > 0.1) return 'positive'
    if (sentiment < -0.1) return 'negative'
    return 'neutral'
}

// Format timestamp to HH:MM
const formatTime = (ts: string) => {
    const d = new Date(ts)
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })
}

export const SignalStream: React.FC = () => {
    const { filter, setTheme, setCountry } = useFocus()
    const { timeRange } = useFocusData()
    const [signals, setSignals] = useState<Signal[]>([])
    const [velocity, setVelocity] = useState<Velocity | null>(null)
    const [isHovered, setIsHovered] = useState(false)
    const listRef = useRef<HTMLDivElement>(null)
    const latestTimestampRef = useRef<string | null>(null)

    // Fetch initial signals when filter or timeRange changes
    useEffect(() => {
        let isMounted = true

        const fetchInitial = async () => {
            try {
                const params = new URLSearchParams()
                params.append('limit', '50')
                params.append('hours', timeRangeToHours(timeRange).toString())
                if (filter.country) params.append('country_code', filter.country)
                if (filter.theme) params.append('theme', filter.theme)

                const res = await fetch(`/api/v2/signals?${params.toString()}`)
                if (!res.ok) return

                const data = await res.json()
                if (!isMounted) return

                setSignals(data.signals || [])
                setVelocity(data.velocity || null)
                
                if (data.signals && data.signals.length > 0) {
                    // Update latest timestamp
                    latestTimestampRef.current = data.signals[0].timestamp
                }
            } catch (e) {
                console.error('[SignalStream] Init fetch error', e)
            }
        }

        // Reset latest timestamp when time range changes
        latestTimestampRef.current = null
        fetchInitial()

        return () => { isMounted = false }
    }, [filter.country, filter.theme, timeRange])

    // Poll for new signals
    useEffect(() => {
        let isMounted = true

        const pollSignals = async () => {
            if (isHovered) return // Pause on hover

            try {
                const params = new URLSearchParams()
                params.append('limit', '50')
                params.append('hours', timeRangeToHours(timeRange).toString())
                if (filter.country) params.append('country_code', filter.country)
                if (filter.theme) params.append('theme', filter.theme)
                if (latestTimestampRef.current) params.append('since', latestTimestampRef.current)

                const res = await fetch(`/api/v2/signals?${params.toString()}`)
                if (!res.ok) return

                const data = await res.json()
                if (!isMounted) return

                setVelocity(data.velocity || null)

                if (data.signals && data.signals.length > 0) {
                    latestTimestampRef.current = data.signals[0].timestamp
                    setSignals(prev => {
                        // Prepend new signals and keep max 100
                        const merged = [...data.signals, ...prev]
                        // Simple deduplication in case of exact same timestamp
                        const unique = merged.filter((v, i, a) => a.findIndex(t => (t.id === v.id)) === i)
                        return unique.slice(0, 100)
                    })
                }
            } catch (e) {
                console.error('[SignalStream] Poll error', e)
            }
        }

        const interval = setInterval(pollSignals, 15000)
        return () => {
            isMounted = false
            clearInterval(interval)
        }
    }, [filter.country, filter.theme, isHovered, timeRange])

    const handleThemeClick = (e: React.MouseEvent, theme: string) => {
        e.stopPropagation()
        setTheme(theme, 'stream')
    }

    const handleCountryClick = (e: React.MouseEvent, country: string) => {
        e.stopPropagation()
        setCountry(country, 'stream')
    }

    return (
        <div className="signal-stream-container">
            {/* Velocity Header */}
            {velocity && (
                <div className="velocity-banner">
                    <span className="velocity-label">VELOCITY: </span>
                    <span className="velocity-value">{velocity.signals_per_minute} sig/min</span>
                    <span className={`velocity-delta ${velocity.delta >= 0 ? 'up' : 'down'}`}>
                        {velocity.delta >= 0 ? '▲' : '▼'} {velocity.percentage_change >= 0 ? '+' : ''}{velocity.percentage_change}%
                    </span>
                </div>
            )}

            {/* Stream List */}
            <div 
                className="signal-list" 
                ref={listRef}
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
            >
                {signals.length === 0 ? (
                    <div className="empty-state">No signals found</div>
                ) : (
                    signals.map(sig => (
                        <div key={sig.id} className="signal-row">
                            <div className="signal-meta">
                                <span className="time">{formatTime(sig.timestamp)}</span>
                                <span 
                                    className="country-chip clickable" 
                                    onClick={(e) => handleCountryClick(e, sig.country || '')}
                                >
                                    {sig.country || 'GLO'}
                                </span>
                                <span className={`sentiment-indicator ${getSentimentClass(sig.sentiment)}`} />
                            </div>
                            
                            <div className="signal-main">
                                <div className="headline">
                                    <a href={sig.url} target="_blank" rel="noreferrer">
                                        {sig.headline || `Signal from ${sig.source}`}
                                    </a>
                                </div>
                                <div className="signal-footer">
                                    <span className="source">{sig.source}</span>
                                    <div className="themes">
                                        {sig.themes.slice(0, 3).map(t => (
                                            <span 
                                                key={t} 
                                                className="theme-tag clickable"
                                                onClick={(e) => handleThemeClick(e, t)}
                                            >
                                                {getThemeIcon(t)} {getThemeLabel(t)}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}
