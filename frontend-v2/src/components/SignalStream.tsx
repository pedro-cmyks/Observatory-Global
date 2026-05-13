import React, { useEffect, useMemo, useState, useRef } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { timeRangeToHours } from '../lib/timeRanges'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { mergeStreamItems, splitInitialStreamBatch } from '../lib/signalStreamQueue'
import { Pin, PinOff } from 'lucide-react'
import { SignalDetailPanel } from './SignalDetailPanel'
import type { Signal } from './SignalDetailPanel'
import './SignalStream.css'

type StreamItem = Signal & { type: 'signal' }

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

// Format timestamp as relative age: 1s, 2m, 15m, 2h
const formatRelativeAge = (ts: string): string => {
    const sec = Math.max(0, Math.floor((Date.now() - new Date(ts).getTime()) / 1000))
    if (sec < 60) return `${sec}s`
    const min = Math.floor(sec / 60)
    if (min < 60) return `${min}m`
    return `${Math.floor(min / 60)}h`
}

const CRITICAL_THEMES = ['TAX_TERROR', 'ARMEDCONFLICT', 'CRISISLEX_C03_DEAD_WOUNDED', 'KILL', 'MILITARY']
const ELEVATED_THEMES = ['SOC_PROTEST', 'EPU_POLICY', 'CRIME', 'ARREST', 'DISASTER']
const MARITIME_KEYWORDS = /suezmax|vessel|maritime|shipping|tanker|LNG|MMSI|strait|harbor|harbour|crude oil|container ship/i

// Filter out malformed GDELT document IDs and garbage headlines
const isValidHeadline = (title: string | null): boolean => {
    if (!title) return false
    // Filter out GDELT document ID prefix pattern like "26061264.Title Here"
    if (/^\d{6,}\./.test(title)) return false
    // Filter out hex-looking strings (GDELT document IDs)
    if (/^[A-Fa-f0-9\s-]{20,}$/.test(title)) return false
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

const INITIAL_VISIBLE_ITEMS = 18
const MAX_STREAM_ITEMS = 120

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
    const [streamFilter, setStreamFilter] = useState<'all' | 'critical' | 'elevated' | 'notable' | 'trend' | 'person' | 'maritime'>('notable')
    const [newItemIds, setNewItemIds] = useState<Set<string>>(new Set())
    const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
    const listRef = useRef<HTMLDivElement>(null)
    const latestTimestampRef = useRef<string | null>(null)
    const dripQueueRef = useRef<StreamItem[]>([])
    const seenIdsRef = useRef<Set<number>>(new Set())
    const { pinItem, unpinItem, isPinned } = useWorkspace()

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

                const sigRes = await fetch(`/api/v2/signals?${params.toString()}`)

                let fetchedSignals: StreamItem[] = []
                if (sigRes.ok) {
                    const data = await sigRes.json()
                    fetchedSignals = (data.signals || [])
                        .filter((s: Signal) => isValidHeadline(s.headline))
                        .map((s: Signal) => ({ ...s, type: 'signal' as const }))
                }

                if (!isMounted) return

                seenIdsRef.current = new Set(fetchedSignals.map(s => s.id))

                const allItems = fetchedSignals.sort(
                    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
                )

                const { visible, queue } = splitInitialStreamBatch(allItems, INITIAL_VISIBLE_ITEMS)
                setItems(visible)
                dripQueueRef.current = queue

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
        dripQueueRef.current = []
        seenIdsRef.current = new Set()
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

                const sigRes = await fetch(`/api/v2/signals?${params.toString()}`)

                let newSignals: StreamItem[] = []
                let newVelocity = null
                if (sigRes.ok) {
                    const data = await sigRes.json()
                    newSignals = (data.signals || [])
                        .filter((s: Signal) => isValidHeadline(s.headline) && !seenIdsRef.current.has(s.id))
                        .map((s: Signal) => ({ ...s, type: 'signal' as const }))
                    newVelocity = data.velocity || null
                }

                if (!isMounted) return

                if (newVelocity) setVelocity(newVelocity)

                if (newSignals.length > 0) {
                    newSignals.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                    latestTimestampRef.current = newSignals[0].timestamp
                    newSignals.forEach(s => seenIdsRef.current.add(s.id))
                    dripQueueRef.current = mergeStreamItems(dripQueueRef.current, newSignals, 200)
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

    // Drip-reveal: pop one queued signal every ~1 second for a live-stream feel
    useEffect(() => {
        const drip = setInterval(() => {
            if (dripQueueRef.current.length === 0) return
            // Drip faster when a batch is waiting so the stream stays alive between 15-min ingests.
            const batch = dripQueueRef.current.length > 30 ? 3 : dripQueueRef.current.length > 12 ? 2 : 1
            for (let i = 0; i < batch; i++) {
                if (dripQueueRef.current.length === 0) break
                const next = dripQueueRef.current.shift()!
                const itemKey = `${next.type}-${next.id}`
                setNewItemIds(prev => new Set([...prev, itemKey]))
                setTimeout(() => setNewItemIds(prev => { const s = new Set(prev); s.delete(itemKey); return s }), 700)
                setItems(prev => mergeStreamItems([next], prev, MAX_STREAM_ITEMS))
            }
        }, 1800)
        return () => clearInterval(drip)
    }, [])

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

    const filteredItems = useMemo(() => items.filter(sig => {
        if (streamFilter === 'all') return true
        if (streamFilter === 'person') return sig.persons?.length > 0
        if (streamFilter === 'maritime') return MARITIME_KEYWORDS.test(sig.headline || '') || sig.themes.some(t => t.includes('MARITIME') || t.includes('VESSEL'))
        if (streamFilter === 'trend') return sig.themes.some(t => HIGH_PRIORITY_THEMES.some(h => t.includes(h)))
        if (streamFilter === 'critical') return sig.themes.some(t => CRITICAL_THEMES.some(c => t.includes(c)))
        if (streamFilter === 'elevated') return sig.themes.some(t => ELEVATED_THEMES.some(e => t.includes(e)))
        if (streamFilter === 'notable') {
            return getSignalPriority(sig) === 1 ||
                sig.themes.some(t => CRITICAL_THEMES.some(c => t.includes(c))) ||
                sig.themes.some(t => ELEVATED_THEMES.some(e => t.includes(e))) ||
                sig.persons?.length > 0
        }
        return true
    }), [items, streamFilter])

    const visibleItems = useMemo(() => filteredItems.filter(sig => isGeopoliticallyRelevant(sig)), [filteredItems])

    return (
        <>
        <div className="signal-stream-container">
            {/* Stream Header: live status + filter tabs */}
            <div className="stream-header">
                <div className="stream-status-bar">
                    <span className={`stream-live-dot${isHovered ? ' paused' : ''}`} />
                    <span className="stream-status-text">
                        {isHovered ? 'paused · last 15 min' : '● LIVE'}
                    </span>
                    {velocity && velocity.signals_per_minute !== '--' && !isHovered && (
                        <span className="stream-velocity">
                            {velocity.signals_per_minute} sig/min
                            {velocity.delta !== '--' && Number(velocity.delta) !== 0 && (
                                <span className={`stream-vel-delta ${Number(velocity.delta) >= 0 ? 'up' : 'down'}`}>
                                    {Number(velocity.delta) >= 0 ? ' ▲' : ' ▼'}{Math.abs(Number(velocity.percentage_change)).toFixed(0)}%
                                </span>
                            )}
                        </span>
                    )}
                </div>
                <div className="stream-filter-bar">
                    {(['all', 'critical', 'elevated', 'notable'] as const).map(f => (
                        <button
                            key={f}
                            className={`stream-filter-tab${streamFilter === f ? ' active' : ''}`}
                            onClick={() => setStreamFilter(f)}
                        >
                            {f.toUpperCase()}
                        </button>
                    ))}
                    <span className="stream-filter-sep" />
                    {(['trend', 'person', 'maritime'] as const).map(f => (
                        <button
                            key={f}
                            className={`stream-filter-tab${streamFilter === f ? ' active' : ''}`}
                            onClick={() => setStreamFilter(f)}
                        >
                            {f.toUpperCase()}
                        </button>
                    ))}
                </div>
            </div>

            {/* Stream List */}
            <div
                className="signal-list"
                ref={listRef}
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
            >
                {visibleItems.length === 0 ? (
                    <div className="empty-state">No signals found</div>
                ) : (
                    visibleItems
                        .map(sig => {
                            const itemKey = `signal-${sig.id}`
                            const isNew = newItemIds.has(itemKey)
                            return (
                                <div key={sig.id} className={`signal-row priority-${getSignalPriority(sig)}${isNew ? ' new-entry' : ''}`}>
                                    <div className="signal-meta">
                                        <span className="time">{formatRelativeAge(sig.timestamp)}</span>
                                        <span 
                                            className="country-chip clickable" 
                                            onClick={(e) => handleCountryClick(e, sig.country || '')}
                                        >
                                            {sig.country || 'GLO'}
                                        </span>
                                        <span className={`sentiment-indicator ${getSentimentClass(sig.sentiment)}`} />
                                    </div>
                                    
                                    <div className="signal-main">
                                        <div className="headline" style={{ display: 'flex', gap: '6px', alignItems: 'flex-start' }}>
                                            <span
                                                style={{ flex: 1, cursor: 'pointer' }}
                                                onClick={(e) => { e.stopPropagation(); setSelectedSignal(sig); }}
                                            >
                                                {sig.headline || `Signal from ${sig.source}`}
                                            </span>
                                            <button
                                                className="pin-btn"
                                                onClick={() => {
                                                    const pinnedId = `signal-${sig.id}`
                                                    if (isPinned(pinnedId)) {
                                                        unpinItem(pinnedId)
                                                    } else {
                                                        pinItem({
                                                            id: pinnedId,
                                                            type: 'signal',
                                                            title: sig.headline || `Signal from ${sig.source}`,
                                                            urlParams: `?${new URLSearchParams(window.location.search).toString()}`
                                                        })
                                                    }
                                                }}
                                                data-tip={isPinned(`signal-${sig.id}`) ? "Unpin Signal" : "Pin Signal to Workspace"}
                                                style={{ background: 'transparent', border: 'none', color: isPinned(`signal-${sig.id}`) ? '#10b981' : '#64748b', cursor: 'pointer', padding: '2px' }}
                                            >
                                                {isPinned(`signal-${sig.id}`) ? <PinOff size={12} /> : <Pin size={12} />}
                                            </button>
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

        {selectedSignal && (
            <SignalDetailPanel
                signal={selectedSignal}
                onClose={() => setSelectedSignal(null)}
                onThemeClick={(t) => setTheme(t, 'stream')}
                onCountryClick={(c) => setCountry(c, 'stream')}
                onPersonClick={(p) => setPerson(p)}
                allowlist={allowlist}
                relatedSignals={
                    items
                        .filter(s => s.id !== selectedSignal.id && s.themes.some(t => selectedSignal.themes.includes(t)))
                        .slice(0, 3)
                }
                onPin={() => {
                    const pinnedId = `signal-${selectedSignal.id}`
                    if (isPinned(pinnedId)) unpinItem(pinnedId)
                    else pinItem({ id: pinnedId, type: 'signal', title: selectedSignal.headline || `Signal from ${selectedSignal.source}`, urlParams: '' })
                }}
                isPinned={isPinned(`signal-${selectedSignal.id}`)}
            />
        )}
        </>
    )
}
