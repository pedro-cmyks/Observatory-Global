import React, { useEffect, useMemo, useState, useRef } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { TranslatableHeadline } from './TranslatableHeadline'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { decodeEntities } from '../lib/decodeEntities'
import { mergeStreamItems, splitInitialStreamBatch } from '../lib/signalStreamQueue'
import { useEclipseMode } from '../contexts/EclipseModeContext'
import {
    type StreamTab, eclipseTopicParam, resolveStreamTab, streamRowEclipseClass,
    streamTabModel, STREAM_DEFAULT_TAB,
} from '../lib/streamTabs'
import { useStoryLens } from '../contexts/StoryLensContext'
import { hasLensContent, lensTopicParam } from '../lib/storyLens'
import type { StreamLevel } from '../contexts/FocusContext'
import { Pin, PinOff } from '../lib/icons'
import PinReceiptButton from './PinReceiptButton'
import { SignalDetailPanel } from './SignalDetailPanel'
import type { Signal } from './SignalDetailPanel'
import { resolveTierChip } from '../lib/sourceProvenance'
import './SignalStream.css'

type StreamItem = Signal & { type: 'signal'; addedAt?: number }

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

// Age since the item ENTERED the stream (its render moment = zero), not its
// publication time. A live feed counts up from when each item appeared: the
// item just added shows 0s, the one added a second earlier shows 1s, etc.
const formatRelativeAge = (addedAt: number, now: number): string => {
    const sec = Math.max(0, Math.floor((now - addedAt) / 1000))
    if (sec < 60) return `${sec}s`
    const min = Math.floor(sec / 60)
    if (min < 60) return `${min}m`
    return `${Math.floor(min / 60)}h`
}

const CRITICAL_THEMES = ['TAX_TERROR', 'ARMEDCONFLICT', 'CRISISLEX_C03_DEAD_WOUNDED', 'KILL', 'MILITARY']
const ELEVATED_THEMES = ['SOC_PROTEST', 'EPU_POLICY', 'CRIME', 'ARREST', 'DISASTER']
const MARITIME_KEYWORDS = /suezmax|vessel|maritime|shipping|tanker|LNG|MMSI|strait|harbor|harbour|crude oil|container ship/i
// L12: content classes Pedro asked for — filter by WHAT the signal is about,
// not only how urgent it is. Conflict/disaster mirror the map layers.
const CONFLICT_THEMES = ['ARMEDCONFLICT', 'TAX_TERROR', 'MILITARY', 'KILL', 'REBELLION', 'CEASEFIRE', 'PEACEKEEP']
const DISASTER_THEMES = ['NATURAL_DISASTER', 'DISASTER', 'EARTHQUAKE', 'FLOOD', 'WILDFIRE', 'HURRICANE', 'CYCLONE', 'DROUGHT', 'VOLCANO']
const DISASTER_KEYWORDS = /earthquake|sismo|terremoto|flood|inundaci|wildfire|incendio forestal|hurricane|hurac[aá]n|cyclone|cicl[oó]n|tsunami|volcan|erupci|landslide|deslizamiento/i

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

// Interleave non-English native-voice signals ~1-in-3 so GDELT's English
// firehose doesn't fill every recency slot. Order otherwise preserved.
const isOwnVoiceSignal = (s: Signal): boolean => {
    const l = (s.source_lang || '').toLowerCase()
    return !!l && !['en', 'xx', 'un', 'und'].includes(l)
}
function interleaveOwnVoice<T extends Signal>(items: T[]): T[] {
    const own = items.filter(isOwnVoiceSignal)
    if (own.length === 0) return items
    const eng = items.filter(s => !isOwnVoiceSignal(s))
    const out: T[] = []
    let ei = 0, oi = 0
    while (ei < eng.length || oi < own.length) {
        if (ei < eng.length) out.push(eng[ei++])
        if (ei < eng.length) out.push(eng[ei++])
        if (oi < own.length) out.push(own[oi++])
    }
    return out
}

const getSignalPriority = (signal: Signal): number => {
    // Priority 1 (highest): Has high priority geopolitical themes
    if (signal.themes.some(t => HIGH_PRIORITY_THEMES.some(hpt => t.includes(hpt)))) return 1
    // Priority 2: Normal news
    return 2
}

// Backend relevance lanes (#177): sports/entertainment are noise for analyst
// workflows and must not sit beside crisis/conflict items in the default tabs.
const isNoiseLane = (signal: Signal): boolean =>
    signal.lane === 'sports' || signal.lane === 'entertainment'

export const SignalStream: React.FC = () => {
    const { filter, setTheme, setCountry, setPerson, setStreamLevel } = useFocus()
    // The stream is ambient — the live day (VIEW selector retired 2026-07-15).
    const STREAM_HOURS = 24
    const [items, setItems] = useState<StreamItem[]>([])
    const [nowTs, setNowTs] = useState(() => Date.now())
    const [velocity, setVelocity] = useState<Velocity | null>(null)
    const [allowlist, setAllowlist] = useState<string[]>([])
    const [isHovered, setIsHovered] = useState(false)
    const [streamFilter, setStreamFilter] = useState<StreamTab>(STREAM_DEFAULT_TAB)
    const [newItemIds, setNewItemIds] = useState<Set<string>>(new Set())
    const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
    // G5 (dataviz audit): distinguish a SERVICE FAILURE (fetch threw / non-2xx,
    // e.g. the 503 db_busy the API now returns when the shared DB is contended)
    // from an honest empty-200. A 500/503 must NOT read as "No signals found".
    const [feedError, setFeedError] = useState(false)
    const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const retryAttemptRef = useRef(0)
    const isHoveredRef = useRef(false)
    const listRef = useRef<HTMLDivElement>(null)
    const latestTimestampRef = useRef<string | null>(null)
    const dripQueueRef = useRef<StreamItem[]>([])
    const seenIdsRef = useRef<Set<number>>(new Set())
    const { pinItem, unpinItem, isPinned } = useWorkspace()

    /* ECLIPSE LENS (spec §6.4, Phase 4): inside the lens the category tabs
       collapse to ECLIPSE / SHADOW / ALL and stop being a theme filter — they
       become a TOPIC scope resolved server-side via `/api/v2/signals?topic=`
       (a signal row carries no topic linkage, which is why this phase waited on
       the backend filter). Outside the lens `tabModel.eclipse` is false,
       `topicParam` is null, and every path below is byte-identical to before. */
    const { mode: eclipseMode, data: eclipseData } = useEclipseMode()
    const eclipseActive = eclipseMode === 'ambient' && !!eclipseData

    /* STORY LENS (Task 6): a deliberate, per-story narrowing — Story|All over
       the same server-side `topic=` scope, built from the anchor + its
       siblings. Eclipse is the ambient, un-chosen condition and wins the tab
       bar when both are active; hasLensContent guards against claiming a scope
       with no anchor/siblings to back it (an honest-empty payload must not
       flip the tab bar to a lens with nothing in it). */
    const storyLens = useStoryLens()
    const lensActive = storyLens.state.active && hasLensContent(storyLens.data)

    const tabModel = useMemo(() => streamTabModel(eclipseActive, lensActive), [eclipseActive, lensActive])

    // Entering/leaving a lens invalidates the selected tab (a category tab
    // means nothing in a lens and vice versa) — land on the model's default
    // rather than render a bar with nothing selected. 'all' survives every flip.
    useEffect(() => {
        setStreamFilter(prev => resolveStreamTab(prev, tabModel))
    }, [tabModel])

    const topicParam = useMemo(() => {
        if (eclipseActive) return eclipseTopicParam(streamFilter, eclipseData)
        if (tabModel.lens && streamFilter === 'story') return lensTopicParam(storyLens.data)
        return null
    }, [eclipseActive, tabModel.lens, streamFilter, eclipseData, storyLens.data])

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

    // Fetch initial signals when the filter changes
    useEffect(() => {
        let isMounted = true

        const scheduleRetry = () => {
            if (!isMounted) return
            // Exponential backoff, capped: 3s → 6s → 12s → 24s → 30s.
            const attempt = retryAttemptRef.current++
            const delay = Math.min(3000 * 2 ** attempt, 30000)
            if (retryTimerRef.current) clearTimeout(retryTimerRef.current)
            retryTimerRef.current = setTimeout(() => { void fetchInitial() }, delay)
        }

        const fetchInitial = async () => {
            try {
                const params = new URLSearchParams()
                params.append('limit', '50')
                params.append('hours', String(STREAM_HOURS))
                params.append('sort', 'relevance')  // analyst-grade ranking (#177)
                if (filter.country) params.append('country_code', filter.country)
                if (filter.theme) params.append('theme', filter.theme)
                if (filter.person) params.append('person', filter.person)
                if (topicParam) params.append('topic', topicParam)

                const sigRes = await fetch(`/api/v2/signals?${params.toString()}`)

                // A non-2xx (500 bug, 503 db_busy, 429 throttle) is a service
                // failure, not an empty result. Keep the last-good items on
                // screen, flag the feed as unavailable, and retry with backoff.
                if (!sigRes.ok) {
                    if (!isMounted) return
                    setFeedError(true)
                    scheduleRetry()
                    return
                }

                const data = await sigRes.json()
                const fetchedSignals: StreamItem[] = (data.signals || [])
                    .filter((s: Signal) => isValidHeadline(s.headline))
                    .map((s: Signal) => ({ ...s, type: 'signal' as const }))

                if (!isMounted) return

                // Recovered: clear the error and reset the backoff.
                setFeedError(false)
                retryAttemptRef.current = 0
                if (retryTimerRef.current) { clearTimeout(retryTimerRef.current); retryTimerRef.current = null }

                seenIdsRef.current = new Set(fetchedSignals.map(s => s.id))

                const sorted = fetchedSignals.sort(
                    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
                )
                // Guarantee the world's OWN voice in the initial view. Sorting by
                // recency alone lets GDELT's English firehose fill every top slot;
                // interleave non-English native-voice signals ~1-in-3 so they are
                // actually seen (and translated by default downstream).
                const allItems = interleaveOwnVoice(sorted)

                const { visible, queue } = splitInitialStreamBatch(allItems, INITIAL_VISIBLE_ITEMS)
                const stampNow = Date.now()
                setItems(visible.map(it => ({ ...it, addedAt: stampNow })))
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
                if (!isMounted) return
                setFeedError(true)   // network throw = service unavailable, not empty
                scheduleRetry()
            }
        }

        latestTimestampRef.current = null
        dripQueueRef.current = []
        seenIdsRef.current = new Set()
        retryAttemptRef.current = 0
        void fetchInitial()

        return () => {
            isMounted = false
            if (retryTimerRef.current) { clearTimeout(retryTimerRef.current); retryTimerRef.current = null }
        }
        // topicParam re-runs this effect on a lens tab switch: the scope is a
        // server-side query, so switching Eclipse↔Shadow refetches rather than
        // re-filtering the pool in the client. No new POLLING is added — the
        // 15s interval below is the same one, just carrying the scope.
    }, [filter.country, filter.theme, filter.person, topicParam])

    // Poll for new signals
    useEffect(() => {
        let isMounted = true

        const pollSignals = async () => {
            if (isHovered) return // Pause on hover

            try {
                const params = new URLSearchParams()
                params.append('limit', '50')
                params.append('hours', String(STREAM_HOURS))
                if (filter.country) params.append('country_code', filter.country)
                if (filter.theme) params.append('theme', filter.theme)
                if (filter.person) params.append('person', filter.person)
                if (topicParam) params.append('topic', topicParam)
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
                    if (isMounted) setFeedError(false)   // a live poll recovered the feed
                } else if (isMounted) {
                    // 503 db_busy / 500 during a poll: surface unavailable but
                    // keep the current items; the init effect owns backoff retry.
                    setFeedError(true)
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
                if (isMounted) setFeedError(true)   // next poll (15s) re-checks
            }
        }

        const interval = setInterval(pollSignals, 15000)
        return () => {
            isMounted = false
            clearInterval(interval)
        }
    }, [filter.country, filter.theme, filter.person, isHovered, topicParam])

    // Drip-reveal: pop one queued signal every ~1 second for a live-stream feel
    useEffect(() => {
        const drip = setInterval(() => {
            if (isHoveredRef.current) return // F2: pause the VISIBLE flow too
            if (dripQueueRef.current.length === 0) return
            // L6 (Pedro): news must feel like a CONSTANT one-by-one arrival —
            // never a burst that drains the buffer and leaves the stream dead
            // until the next poll. One item per tick; the tick itself is fixed,
            // so a 50-item batch lasts ~2.5 min instead of dumping in 30s.
            const batch = 1
            for (let i = 0; i < batch; i++) {
                if (dripQueueRef.current.length === 0) break
                const next = dripQueueRef.current.shift()!
                const itemKey = `${next.type}-${next.id}`
                setNewItemIds(prev => new Set([...prev, itemKey]))
                setTimeout(() => setNewItemIds(prev => { const s = new Set(prev); s.delete(itemKey); return s }), 900)
                // Stamp the moment it appears so its age counts up from zero.
                const stamped = { ...next, addedAt: next.addedAt ?? Date.now() }
                setItems(prev => mergeStreamItems([stamped], prev, MAX_STREAM_ITEMS))
            }
        }, 3000)
        return () => clearInterval(drip)
    }, [])

    // Tick once a second so each item's "age since it appeared" counts up.
    useEffect(() => {
        const t = setInterval(() => setNowTs(Date.now()), 1000)
        return () => clearInterval(t)
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
        // Lens tabs are a SERVER-side topic scope, already applied to what we
        // fetched. Re-filtering here by theme keywords would silently drop
        // members of the very stories the lens exists to surface.
        if ((tabModel.eclipse || tabModel.lens) && streamFilter !== 'all') return true
        if (streamFilter === 'all') return true
        if (streamFilter === 'person') return sig.persons?.length > 0
        if (streamFilter === 'maritime') return MARITIME_KEYWORDS.test(sig.headline || '') || sig.themes.some(t => t.includes('MARITIME') || t.includes('VESSEL'))
        if (streamFilter === 'conflict') return sig.themes.some(t => CONFLICT_THEMES.some(c2 => t.includes(c2)))
        if (streamFilter === 'disaster') return sig.themes.some(t => DISASTER_THEMES.some(d => t.includes(d))) || DISASTER_KEYWORDS.test(sig.headline || '')
        // Analyst-grade tabs: never surface sports/entertainment noise lanes.
        if (isNoiseLane(sig)) return false
        if (streamFilter === 'trend') return sig.themes.some(t => HIGH_PRIORITY_THEMES.some(h => t.includes(h)))
        if (streamFilter === 'critical') return sig.themes.some(t => CRITICAL_THEMES.some(c => t.includes(c)))
        if (streamFilter === 'elevated') return sig.themes.some(t => ELEVATED_THEMES.some(e => t.includes(e)))
        if (streamFilter === 'notable') {
            return sig.lane === 'analyst' ||
                getSignalPriority(sig) === 1 ||
                sig.themes.some(t => CRITICAL_THEMES.some(c => t.includes(c))) ||
                sig.themes.some(t => ELEVATED_THEMES.some(e => t.includes(e))) ||
                sig.persons?.length > 0 ||
                // The world's own-language press is notable by definition: RSS
                // native-voice signals carry no GDELT themes/persons yet, so they
                // would otherwise be filtered out of the default view entirely.
                isOwnVoiceSignal(sig)
        }
        return true
    }), [items, streamFilter, tabModel.eclipse, tabModel.lens])

    // The noise-headline regex is a heuristic for an UNSCOPED stream. On a
    // topic-scoped tab the scope is the measured selector, so applying the
    // regex on top would be silent filtering of an explicitly-requested set.
    const visibleItems = useMemo(
        () => (topicParam ? filteredItems : filteredItems.filter(sig => isGeopoliticallyRelevant(sig))),
        [filteredItems, topicParam])
    const rowEclipseClass = (tabModel.eclipse || tabModel.lens) ? streamRowEclipseClass(streamFilter) : ''

    return (
        <>
        <div className="signal-stream-container">
            {/* Stream Header: live status + filter tabs */}
            <div className="stream-header">
                <div className="stream-status-bar">
                    <span className={`stream-live-dot${feedError ? ' feed-error' : ''}${isHovered ? ' paused' : ''}`} />
                    <span className="stream-status-text">
                        {feedError ? 'feed unavailable · retrying' : isHovered ? 'paused · last 15 min' : '● LIVE'}
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
                <div className={`stream-filter-bar${tabModel.eclipse ? ' stream-filter-bar--eclipse' : ''}${tabModel.lens ? ' stream-filter-bar--lens' : ''}`}>
                    {tabModel.primary.map(f => (
                        <button
                            key={f}
                            className={`stream-filter-tab${streamFilter === f ? ' active' : ''}${
                                tabModel.eclipse && f !== 'all' ? ` ecl-tab-${f}` : ''}${
                                tabModel.lens && f !== 'all' ? ` sl-tab-${f}` : ''}`}
                            // Lens tabs are a topic scope, not a stream LEVEL — leave
                            // the shared focus streamLevel alone so exiting the lens
                            // restores the category the reader had chosen.
                            onClick={() => {
                                setStreamFilter(f)
                                if (!tabModel.eclipse && !tabModel.lens) setStreamLevel(f as StreamLevel)
                            }}
                            data-tip={
                                f === 'eclipse' ? 'Signals inside the eclipsing story — the coverage everyone is already seeing.'
                                : f === 'shadow' ? 'Signals from the consequential stories the eclipse is drowning out. Ranked by coverage-volume share — a proxy for attention, not audience eyeballs.'
                                : f === 'story' ? 'Signals from this story and its measured siblings — the walked neighborhood, not the whole stream.'
                                : f === 'notable' ? 'Analyst-grade ranking: crisis/conflict, security, economy and political signals first. Sports and entertainment are filtered out.'
                                : f === 'all' ? (tabModel.eclipse
                                    ? 'The whole stream, unscoped — step out of the eclipse lens.'
                                    : tabModel.lens
                                    ? 'The whole stream, unscoped — step out of this story’s neighborhood.'
                                    : 'Everything, including sports and entertainment (lane-tagged).')
                                : undefined}
                        >
                            {f.toUpperCase()}
                        </button>
                    ))}
                    {tabModel.secondary.length > 0 && <span className="stream-filter-sep" />}
                    {tabModel.secondary.map(f => (
                        <button
                            key={f}
                            className={`stream-filter-tab${streamFilter === f ? ' active' : ''}`}
                            onClick={() => { setStreamFilter(f); setStreamLevel(f as StreamLevel) }}
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
                onMouseEnter={() => { isHoveredRef.current = true; setIsHovered(true) }}
                onMouseLeave={() => { isHoveredRef.current = false; setIsHovered(false) }}
            >
                {visibleItems.length === 0 ? (
                    feedError ? (
                        <div className="empty-state stream-feed-error" role="status" aria-live="polite">
                            <span className="stream-feed-error-dot" />
                            Signal feed unavailable — retrying…
                        </div>
                    ) : topicParam ? (
                        // Honest empty for a scoped tab: the stories exist (the
                        // eclipse endpoint or the story-siblings walk measured
                        // them) but none of their member signals landed in this
                        // window. Say which, and never let it read as "nothing
                        // is happening".
                        <div className="empty-state">
                            No signals yet from {
                                streamFilter === 'eclipse' ? 'the eclipsing story'
                                : streamFilter === 'story' ? "this story's scope"
                                : 'the shadow stories'
                            } in the last 24 h
                            <span className="stream-empty-note">
                                Stories are measured on classified coverage; membership lags ingest by up to one classifier pass.
                            </span>
                        </div>
                    ) : (
                        <div className="empty-state">No signals found</div>
                    )
                ) : (
                    visibleItems
                        .map(sig => {
                            const itemKey = `signal-${sig.id}`
                            const isNew = newItemIds.has(itemKey)
                            return (
                                <div
                                    key={sig.id}
                                    className={`signal-row priority-${getSignalPriority(sig)}${isNew ? ' new-entry' : ''}${rowEclipseClass ? ` ${rowEclipseClass}` : ''}`}
                                    onClick={(e) => {
                                        // F2: the WHOLE banner opens the story — not just
                                        // the headline letters. Inner pills keep their own
                                        // actions (they stopPropagation or match below).
                                        const t = e.target as HTMLElement
                                        if (t.closest('a, button, .country-chip, .person-tag, .theme-tag, .pin-btn')) return
                                        setSelectedSignal(sig)
                                    }}
                                    style={{ cursor: 'pointer' }}
                                >
                                    <div className="signal-meta">
                                        <span className="time">{formatRelativeAge(sig.addedAt ?? new Date(sig.timestamp).getTime(), nowTs)}</span>
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
                                                {sig.headline
                                                    ? <TranslatableHeadline signalId={sig.id} original={decodeEntities(sig.headline)} sourceLang={sig.source_lang} />
                                                    : `Signal from ${sig.source}`}
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
                                                            title: sig.headline ? decodeEntities(sig.headline) : `Signal from ${sig.source}`,
                                                            urlParams: `?${new URLSearchParams(window.location.search).toString()}`
                                                        })
                                                    }
                                                }}
                                                data-tip={isPinned(`signal-${sig.id}`) ? "Unpin Signal" : "Pin Signal to Workspace"}
                                                style={{ background: 'transparent', border: 'none', color: isPinned(`signal-${sig.id}`) ? '#10b981' : '#64748b', cursor: 'pointer', padding: '2px' }}
                                            >
                                                {isPinned(`signal-${sig.id}`) ? <PinOff size={12} /> : <Pin size={12} />}
                                            </button>
                                            <PinReceiptButton
                                                contextLabel={sig.headline ? decodeEntities(sig.headline) : `Signal from ${sig.source}`}
                                                citation={{
                                                    headline: sig.headline ? decodeEntities(sig.headline) : `Signal from ${sig.source}`,
                                                    source: sig.source || undefined,
                                                    url: sig.url || undefined,
                                                    // N1: sig.country = SUBJECT country, never an
                                                    // origin assertion; no origin in this payload.
                                                    sourceLang: sig.source_lang || undefined,
                                                    gateStatus: 'unknown',
                                                    publishedDate: sig.timestamp ? new Date(sig.timestamp).toISOString().slice(0, 10) : undefined,
                                                }}
                                            />
                                        </div>
                                        <div className="signal-footer">
                                            <span className={`source ${getSourceClass(sig.source)}`}>{sig.source}</span>
                                            {(() => {
                                                // Gold-eval defect: this row carried no tier reference —
                                                // no origin/is_state_media in this payload, so 'unknown' is
                                                // suppressed rather than guessed (absence over noise).
                                                const tc = resolveTierChip(sig.source, undefined)
                                                return tc.tier !== 'unknown' ? (
                                                    <span className={`l2-tier-chip l2-tier-chip--${tc.tier}`} data-tip={tc.tip}>{tc.label}</span>
                                                ) : null
                                            })()}
                                            {(sig.lane === 'sports' || sig.lane === 'entertainment') && (
                                                <span className={`stream-lane-badge stream-lane-badge--${sig.lane}`}
                                                    data-tip={`${sig.lane === 'sports' ? 'Sports' : 'Entertainment'} — separated from analyst workflows`}>
                                                    {sig.lane === 'sports' ? 'SPORT' : 'CULTURE'}
                                                </span>
                                            )}
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
                // Task 5.5 — open a semantic neighbor in-app: re-point this same
                // panel at the neighbor (its context re-fetches on signal.id).
                onSignalOpen={(sig) => setSelectedSignal(sig)}
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
