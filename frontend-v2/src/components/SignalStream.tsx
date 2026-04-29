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

interface GeopoliticalEvent {
    type: 'event'
    id: number
    timestamp: string
    action: {
        code: string
        label: string
        quad_class: number
        quad_label: string
        goldstein_scale: number | null
        is_root: boolean
    }
    actor1: { name: string, country_code: string } | null
    actor2: { name: string, country_code: string } | null
    location: { name: string, country_code: string, latitude: number, longitude: number }
    meta: { mentions: number, avg_tone: number, source_url: string }
}

type StreamItem = (Signal & { type: 'signal' }) | GeopoliticalEvent

interface Velocity {
    signals_per_minute: number | string
    delta: number | string
    percentage_change: number | string
}

// Extract readable domain from a URL
const extractDomain = (url: string): string => {
    try {
        const host = new URL(url).hostname.replace(/^www\./, '')
        return host.split('.').slice(-2).join('.')
    } catch {
        return ''
    }
}

// Clean CAMEO actor name: title-case, drop generic codes
const cleanActorName = (name: string, countryCode: string | null): string => {
    if (!name) return countryCode || '?'
    // Title-case the name
    return name.toLowerCase().replace(/\b\w/g, c => c.toUpperCase())
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
    // Reject if >30% of words are alphanumeric codes (product IDs, tickers)
    const allWords = title.split(' ')
    const codeWords = allWords.filter(w => /^[A-Z0-9]{4,}$/.test(w))
    if (allWords.length > 0 && codeWords.length / allWords.length > 0.3) return false
    // Must have at least 3 real words
    const words = allWords.filter(w => w.length > 2)
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
    // Product / lifestyle / food
    /\b(wedding trend|destination wedding|bridal|wedding dress)\b/i,
    /\b(recipe|best restaurant|food craving|crave food|meal prep|grocery)\b/i,
    /\b(adizero|yeezy|air max|ultraboost|running shoe|sneaker release)\b/i,
    /\b(earn per share|stock tip|portfolio tip|dividend yield|market cap today)\b/i,
    /\b(horoscope|zodiac sign|birth chart|mercury retrograde)\b/i,
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
    const [items, setItems] = useState<StreamItem[]>([])
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

                const [sigRes, evtRes] = await Promise.all([
                    fetch(`/api/v2/signals?${params.toString()}`),
                    fetch(`/api/v2/events?${params.toString()}`)
                ])
                
                let fetchedSignals: StreamItem[] = []
                if (sigRes.ok) {
                    const data = await sigRes.json()
                    fetchedSignals = (data.signals || []).map((s: Signal) => ({ ...s, type: 'signal' }))
                }
                
                let fetchedEvents: StreamItem[] = []
                if (evtRes.ok) {
                    const data = await evtRes.json()
                    fetchedEvents = (data.events || []).map((e: any) => ({ ...e, type: 'event' }))
                }

                if (!isMounted) return

                const allItems = [...fetchedSignals, ...fetchedEvents].sort(
                    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
                )

                setItems(allItems)

                if (fetchedSignals.length > 0) {
                    const now = new Date(fetchedSignals[0].timestamp).getTime()
                    const last60s = fetchedSignals.filter((s: StreamItem) => now - new Date(s.timestamp).getTime() <= 60000).length
                    const prev60s = fetchedSignals.filter((s: StreamItem) => {
                        const age = now - new Date(s.timestamp).getTime()
                        return age > 60000 && age <= 120000
                    }).length

                    const total2mins = fetchedSignals.filter((s: StreamItem) => now - new Date(s.timestamp).getTime() <= 120000).length

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

                const [sigRes, evtRes] = await Promise.all([
                    fetch(`/api/v2/signals?${params.toString()}`),
                    fetch(`/api/v2/events?${params.toString()}`)
                ])

                let newSignals: StreamItem[] = []
                let newVelocity = null
                if (sigRes.ok) {
                    const data = await sigRes.json()
                    newSignals = (data.signals || []).map((s: Signal) => ({ ...s, type: 'signal' }))
                    newVelocity = data.velocity || null
                }
                
                let newEvents: StreamItem[] = []
                if (evtRes.ok) {
                    const data = await evtRes.json()
                    newEvents = (data.events || []).map((e: any) => ({ ...e, type: 'event' }))
                }

                if (!isMounted) return

                if (newVelocity) setVelocity(newVelocity)

                const newItems = [...newSignals, ...newEvents]
                
                if (newItems.length > 0) {
                    newItems.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                    latestTimestampRef.current = newItems[0].timestamp
                    setItems(prev => {
                        const merged = [...newItems, ...prev]
                        // Unique by type + id
                        const unique = merged.filter((v, i, a) => a.findIndex(t => (t.type === v.type && t.id === v.id)) === i)
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
                        {velocity.signals_per_minute === 0 && items.length > 0 
                            ? `~${items.length} items in view` 
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
                {items.length === 0 ? (
                    <div className="empty-state">No signals or events found</div>
                ) : (
                    items
                        .filter(item => item.type === 'event' || isGeopoliticallyRelevant(item as Signal))
                        .sort((a, b) => {
                            // prioritize events and high-priority signals
                            const pA = a.type === 'event' ? 0 : getSignalPriority(a as Signal)
                            const pB = b.type === 'event' ? 0 : getSignalPriority(b as Signal)
                            if (pA !== pB) return pA - pB
                            return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
                        })
                        .map(item => {
                            if (item.type === 'event') {
                                const evt = item as GeopoliticalEvent
                                const quadColor = evt.action.quad_class === 1 || evt.action.quad_class === 2 ? '#4ade80' : '#ef4444'
                                const sourceDomain = evt.meta.source_url ? extractDomain(evt.meta.source_url) : ''
                                return (
                                    <div key={`evt-${evt.id}`} className="signal-row event-card">
                                        <div className="event-header">
                                            <span className="event-quad" style={{color: quadColor, fontWeight: 700, fontSize: '9px', letterSpacing: '0.04em'}}>
                                                {evt.action.quad_class === 1 ? 'COOP' : evt.action.quad_class === 2 ? 'VERBAL' : evt.action.quad_class === 3 ? 'DEMAND' : 'CONFLICT'}
                                            </span>
                                            <span className="event-label" style={{color: quadColor}}>{evt.action.label}</span>
                                            <span className="signal-time">{formatTime(evt.timestamp)}</span>
                                        </div>
                                        <div className="event-actors">
                                            {evt.actor1 && (
                                                <span className="event-actor source">
                                                    {cleanActorName(evt.actor1.name, evt.actor1.country_code)}
                                                </span>
                                            )}
                                            {evt.actor2 && (
                                                <>
                                                    <span className="event-arrow">→</span>
                                                    <span className="event-actor target">
                                                        {cleanActorName(evt.actor2.name, evt.actor2.country_code)}
                                                    </span>
                                                </>
                                            )}
                                        </div>
                                        <div className="event-meta">
                                            <span>{evt.location.country_code || 'GLO'}{evt.location.name ? ` · ${evt.location.name.split(',')[0]}` : ''}</span>
                                            {evt.action.goldstein_scale !== null && (
                                                <span className={evt.action.goldstein_scale >= 0 ? 'positive' : 'negative'}>
                                                    {evt.action.goldstein_scale > 0 ? '+' : ''}{evt.action.goldstein_scale}
                                                </span>
                                            )}
                                            {sourceDomain && (
                                                <a href={evt.meta.source_url} target="_blank" rel="noopener noreferrer" className="signal-link">{sourceDomain}</a>
                                            )}
                                        </div>
                                    </div>
                                )
                            }

                            // Render Signal
                            const sig = item as Signal & { type: 'signal' }
                            const isValid = isValidHeadline(sig.headline)
                            
                            if (!isValid) {
                                return (
                                    <div key={`sig-${sig.id}`} className={`signal-row compact-mode`}>
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
