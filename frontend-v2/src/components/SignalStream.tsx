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
    persons: string[]
}

interface Velocity {
    signals_per_minute: number | string
    delta: number | string
    percentage_change: number | string
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

// Filter out malformed GDELT document IDs and garbage headlines
const isValidHeadline = (title: string | null): boolean => {
    if (!title) return false
    // Filter out GDELT document ID prefix pattern like "26061264.Title Here"
    if (/^\d{6,}\./.test(title)) return false
    // Filter out hex-looking strings (GDELT document IDs)
    if (/^[A-Fa-f0-9\s\-]{20,}$/.test(title)) return false
    // Filter out titles starting with "Article" followed by hex
    if (/^Article\s+[A-Fa-f0-9]/i.test(title)) return false
    // Filter out titles that are just numbers/codes
    if (/^[\d\s\-_]{10,}$/.test(title)) return false
    // Filter out stock ticker / company holding patterns
    if (/\bHolding[s]?\s+In\s+Company\b/i.test(title)) return false
    // Must have at least 3 real words
    const words = title.split(' ').filter(w => w.length > 2)
    return words.length >= 3
}

// Headline-based noise filter: deprioritize sports, entertainment, celebrity content
const NOISE_HEADLINE_PATTERNS = [
    /\b(NFL|NBA|MLB|NHL|FIFA|UFC|ESPN|MLS|PGA|NASCAR|Premier League|Champions League|World Series|Super Bowl|March Madness)\b/i,
    /\b(touchdown|home run|batting average|playoff|halftime|quarterback|pitcher|goalkeeper|slam dunk|free throw)\b/i,
    /\b(injury rehab|game recap|season preview|draft pick|free agent|trade deadline|spring training)\b/i,
    /\b(Mahomes|LeBron|Brady|Kardashian|Swift|Bieber|Beyonce|Drake|Taylor Swift)\b/i,
    /\b(Oscar|Grammy|Emmy|Tony Award|Billboard|box office|blockbuster|streaming debut|red carpet|paparazzi|reality show|talent show)\b/i,
    /\b(horoscope|zodiac|astrology|daily crossword|recipe of the day|wedding trends|adizero|exact time you crave)\b/i,
    /\b(shopping guide|best deals|black friday|cyber monday|gift guide|discount code)\b/i,
]

const isGeopoliticallyRelevant = (signal: Signal): boolean => {
    if (!signal.headline) return true
    return !NOISE_HEADLINE_PATTERNS.some(re => re.test(signal.headline!))
}

const HIGH_PRIORITY_THEMES = [
    'WB_CONFLICT', 'CRISISLEX_CRISISLEXREC', 'EPU_POLICY', 'GOV_INTERGOVERNMENTAL', 
    'WB_MILITARY', 'SOC_PROTEST', 'TAX_FNCACT', 'ARMEDCONFLICT', 'TERRORISM'
]

const getSignalPriority = (signal: Signal): number => {
    // Priority 1 (highest): Has high priority geopolitical themes
    if (signal.themes.some(t => HIGH_PRIORITY_THEMES.some(hpt => t.includes(hpt)))) return 1
    // Priority 2: Normal news
    return 2
}

export const SignalStream: React.FC = () => {
    const { filter, setTheme, setCountry, setPerson } = useFocus()
    const { timeRange } = useFocusData()
    const [signals, setSignals] = useState<Signal[]>([])
    const [velocity, setVelocity] = useState<Velocity | null>(null)
    const [allowlist, setAllowlist] = useState<string[]>([])
    const [isHovered, setIsHovered] = useState(false)
    const listRef = useRef<HTMLDivElement>(null)
    const latestTimestampRef = useRef<string | null>(null)

    // Fetch allowlist once
    useEffect(() => {
        fetch('/api/indicators/allowlist')
            .then(r => r.ok ? r.json() : [])
            .then(data => {
                if (data.allowlist && Array.isArray(data.allowlist)) {
                    setAllowlist(data.allowlist)
                }
            })
            .catch(e => console.error('Error fetching allowlist', e))
    }, [])

    const getSourceClass = (source: string) => {
        if (!source) return ''
        const s = source.toLowerCase()
        if (allowlist.some(a => s.includes(a.toLowerCase()))) return 'source-trusted'
        if (s.includes('yahoo') || s.includes('msn') || s.includes('aol') || s.includes('newsbreak')) return 'source-tabloid'
        return ''
    }

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
                if (filter.person) params.append('person', filter.person)

                const res = await fetch(`/api/v2/signals?${params.toString()}`)
                if (!res.ok) return

                const data = await res.json()
                if (!isMounted) return

                const fetchedSignals = data.signals || []
                setSignals(fetchedSignals)

                if (fetchedSignals.length > 0) {
                    const now = new Date(fetchedSignals[0].timestamp).getTime()
                    const last60s = fetchedSignals.filter((s: Signal) => now - new Date(s.timestamp).getTime() <= 60000).length
                    const prev60s = fetchedSignals.filter((s: Signal) => {
                        const age = now - new Date(s.timestamp).getTime()
                        return age > 60000 && age <= 120000
                    }).length

                    const total2mins = fetchedSignals.filter((s: Signal) => now - new Date(s.timestamp).getTime() <= 120000).length

                    if (total2mins < 2) {
                        setVelocity({ signals_per_minute: '--', delta: '--', percentage_change: '--' })
                    } else {
                        const delta = last60s - prev60s
                        const pct = prev60s > 0 ? (delta / prev60s) * 100 : 0
                        setVelocity({
                            signals_per_minute: last60s,
                            delta: delta,
                            percentage_change: pct
                        })
                    }

                    latestTimestampRef.current = fetchedSignals[0].timestamp
                } else {
                    setVelocity({ signals_per_minute: '--', delta: '--', percentage_change: '--' })
                }
            } catch (e) {
                console.error('[SignalStream] Init fetch error', e)
            }
        }

        latestTimestampRef.current = null
        fetchInitial()

        return () => { isMounted = false }
    }, [filter.country, filter.theme, filter.person, timeRange])

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
                if (filter.person) params.append('person', filter.person)
                if (latestTimestampRef.current) params.append('since', latestTimestampRef.current)

                const res = await fetch(`/api/v2/signals?${params.toString()}`)
                if (!res.ok) return

                const data = await res.json()
                if (!isMounted) return

                setVelocity(data.velocity || null)

                if (data.signals && data.signals.length > 0) {
                    latestTimestampRef.current = data.signals[0].timestamp
                    setSignals(prev => {
                        const merged = [...data.signals, ...prev]
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
    }, [filter.country, filter.theme, filter.person, isHovered, timeRange])

    const handleThemeClick = (e: React.MouseEvent, theme: string) => {
        e.stopPropagation()
        setTheme(theme, 'stream')
    }

    const handleCountryClick = (e: React.MouseEvent, country: string) => {
        e.stopPropagation()
        setCountry(country, 'stream')
    }

    const handlePersonClick = (e: React.MouseEvent, person: string) => {
        e.stopPropagation()
        setPerson(person)
    }

    return (
        <div className="signal-stream-container">
            {/* Velocity Header */}
            {velocity && (
                <div className="velocity-banner">
                    <span className="velocity-label">VELOCITY: </span>
                    <span className="velocity-value">
                        {velocity.signals_per_minute === 0 && signals.length > 0 
                            ? `~${signals.length} signals in view` 
                            : `${velocity.signals_per_minute} ${velocity.signals_per_minute === '--' ? '' : 'sig/min'}`}
                    </span>
                    {velocity.delta !== '--' && velocity.signals_per_minute !== 0 && (
                        <span className={`velocity-delta ${Number(velocity.delta) >= 0 ? 'up' : 'down'}`}>
                            {Number(velocity.delta) >= 0 ? '▲' : '▼'} {Number(velocity.percentage_change) >= 0 ? '+' : ''}{Number(velocity.percentage_change).toFixed(1)}%
                        </span>
                    )}
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
                    signals
                        .filter(isGeopoliticallyRelevant)
                        .sort((a, b) => {
                            const pA = getSignalPriority(a)
                            const pB = getSignalPriority(b)
                            if (pA !== pB) return pA - pB
                            return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
                        })
                        .map(sig => {
                            const isValid = isValidHeadline(sig.headline)
                            
                            if (!isValid) {
                                return (
                                    <div key={sig.id} className={`signal-row compact-mode`}>
                                        <div className="signal-main" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                                            <span
                                                className="country-chip clickable"
                                                onClick={(e) => handleCountryClick(e, sig.country || '')}
                                            >
                                                {sig.country || 'GLO'}
                                            </span>
                                            <span className={`sentiment-indicator ${getSentimentClass(sig.sentiment)}`} />
                                            <span className={`source ${getSourceClass(sig.source)}`}>{sig.source}</span>
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
                                )
                            }
                            
                            return (
                                <div key={sig.id} className={`signal-row priority-${getSignalPriority(sig)}`}>
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
                                            <span className={`source ${getSourceClass(sig.source)}`}>{sig.source}</span>
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
                                                {sig.persons?.slice(0, 2).map(p => (
                                                    <span
                                                        key={p}
                                                        className="person-tag clickable"
                                                        onClick={(e) => handlePersonClick(e, p)}
                                                    >
                                                        {p}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )
                        })
                )}
            </div>
        </div>
    )
}
