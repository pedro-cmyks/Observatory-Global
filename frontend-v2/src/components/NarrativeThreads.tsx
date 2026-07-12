import React, { useEffect, useState, useCallback } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { timeRangeToHours } from '../lib/timeRanges'
import { resolveCountryName } from '../lib/countryNames'
import { Flag } from './Flag'
import { buildCountryThreadEmptyState, getNarrativeFetchLimit, getNarrativesForDisplay } from '../lib/narrativeThreadLimits'
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
    // #214 / T4 (dataviz audit): gate lineage for the count label. Atlas topics
    // carry both; dynamic/emergent threads may not (undefined → plain count).
    gated_signal_count?: number
    gate_scored_count?: number
    discussion_count?: number
    forum_sentiment?: number | null
    country_count: number
    source_count: number
    top_sources: string[]
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

// Sparkline SVG component.
// T3 (dataviz audit): every row is max-normalized to itself — 20 mini-charts,
// 20 private y-scales. The peak annotation anchors the magnitude so rows can
// be compared by number even though the amplitudes can't.
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
        <span className="narrative-sparkline-wrap" data-tip={`Shape only — this sparkline is scaled to its own peak of ${max.toLocaleString()} signals/h; compare rows by the peak number, not the amplitude.`}>
            <svg className="narrative-sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
                <polygon points={areaPoints} fill={strokeColor} />
                <polyline points={points} stroke={strokeColor} />
            </svg>
            <span className="narrative-spark-peak">peak {max > 999 ? `${(max / 1000).toFixed(1)}k` : max}/h</span>
        </span>
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

const stripCountrySuffix = (label: string): string =>
    label.replace(/\s+in\s+.+$/i, '').trim()

const normalizeTrend = (trend: string): Narrative['trend'] => {
    if (trend === 'surging') return 'accelerating'
    if (trend === 'fading') return 'fading'
    return 'stable'
}

const normalizeThread = (thread: any): Narrative => ({
    thread_id: thread.thread_id,
    label: stripCountrySuffix(thread.label || thread.summary || thread.thread_id),
    anchor_topics: thread.anchor_topics || [],
    parent_domain: thread.parent_domain || null,
    signal_count: thread.signal_count || 0,
    gated_signal_count: thread.gated_signal_count,
    gate_scored_count: thread.gate_scored_count,
    discussion_count: thread.discussion_count || 0,
    forum_sentiment: thread.forum_sentiment ?? null,
    country_count: thread.country_count || 0,
    source_count: thread.source_count || 0,
    top_sources: thread.top_sources || thread.source_mix?.top_sources || [],
    first_seen: thread.first_seen || null,
    changed_10h: thread.changed_10h || 0,
    trend: normalizeTrend(thread.trend),
    // Whole percent only: avg assignment confidence does not support a
    // decimal of precision ("59.15%" is false precision on a model average).
    confidence_pct: Math.round((thread.avg_confidence || 0) * 100),
    sentiment_swing_10h: thread.sentiment_swing_10h ?? null,
    top_entities: thread.top_entities || thread.top_people || [],
    hourly_timeline: thread.hourly_timeline || [],
    top_countries: thread.top_countries || [],
    top_country_names: thread.top_country_names || [],
})

interface NarrativeThreadsProps {
    onCountrySelect?: (code: string) => void
    onThreadSelect?: (thread: Narrative) => void
    activeThreadId?: string | null
}

export type LivingThreadSelection = Narrative

export const NarrativeThreads: React.FC<NarrativeThreadsProps> = ({ onCountrySelect, onThreadSelect, activeThreadId }) => {
    const [narratives, setNarratives] = useState<Narrative[]>([])
    // #234: precise person→thread set from the backend (full persons array),
    // replacing the capped top_entities heuristic for the focus highlight.
    const [personMatchIds, setPersonMatchIds] = useState<Set<string> | null>(null)
    const [effectiveHours, setEffectiveHours] = useState<number | null>(null)
    const [loading, setLoading] = useState(true)
    // G5: a failed fetch (503 db_busy / 500 / network) must not read as an
    // honest "no active narratives" empty. Track it so the empty branch can
    // say "unavailable — retrying" instead.
    const [feedError, setFeedError] = useState(false)
    const { filter, setCountry, setMapFlyCountry, setPerson } = useFocus()
    const { timeRange } = useFocusData()
    // W4 (2026-07-05): thread rows are pinnable into the active investigation.
    const { pinItem, unpinItem, isPinned } = useWorkspace()

    // Cap to 24h when browsing globally (spread_pct becomes meaningless at wider windows);
    // when a country is selected, use the full range so client-side filtering has real data.
    const rawHours = timeRangeToHours(timeRange)
    const cappedHours = filter.country ? rawHours : Math.min(rawHours, 24)
    const isCapped = !filter.country && rawHours > 24

    // Fetch enough rows for the panel to use the available vertical space.
    const fetchLimit = getNarrativeFetchLimit(!!filter.country)

    const fetchNarratives = useCallback(async () => {
        try {
            const params = new URLSearchParams({
                hours: String(cappedHours),
                limit: String(fetchLimit),
            })
            if (filter.country) params.set('country_code', filter.country)
            let res = await fetch(`/api/v2/threads?${params.toString()}`)
            if (!res.ok) {
                // One quick retry: a cold country-scoped query can 500 once,
                // which silently left the GLOBAL list under a "Scoped to X"
                // strip until the 5-min interval (capture-doc §B, live-seen).
                await new Promise(r => setTimeout(r, 2500))
                res = await fetch(`/api/v2/threads?${params.toString()}`)
                if (!res.ok) { setFeedError(true); return }   // service failure, not empty
            }
            const data = await res.json()
            setNarratives((data.threads || []).map(normalizeThread))
            setEffectiveHours(data.hours ?? null)
            setFeedError(false)
        } catch (e) {
            console.error('[NarrativeThreads] Fetch error', e)
            setFeedError(true)   // network throw = unavailable, not empty
        } finally {
            setLoading(false)
        }
    }, [cappedHours, fetchLimit, filter.country])

    // Initial fetch + 5-minute interval; re-fetch when country changes
    useEffect(() => {
        setLoading(true)
        fetchNarratives()
        const interval = setInterval(fetchNarratives, 5 * 60 * 1000)
        return () => clearInterval(interval)
    }, [fetchNarratives])

    // #234: when a person is focused, fetch the PRECISE set of threads that
    // mention them (backend ?person=, full persons array) for the highlight —
    // more accurate than the capped top_entities. Cleared when no person.
    useEffect(() => {
        const person = filter.person?.trim()
        if (!person) { setPersonMatchIds(null); return }
        let cancelled = false
        fetch(`/api/v2/threads?hours=${cappedHours}&person=${encodeURIComponent(person)}`)
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                if (cancelled || !d) return
                setPersonMatchIds(new Set((d.threads || []).map((t: { thread_id: string }) => t.thread_id)))
            })
            .catch(() => { if (!cancelled) setPersonMatchIds(null) })
        return () => { cancelled = true }
    }, [filter.person, cappedHours])

    // When country is active, show only threads that include that country
    const displayedNarratives = getNarrativesForDisplay(narratives, filter.country ?? undefined)

    // #234: when a person is focused, surface the threads that mention them
    // (the person appears in top_entities) and dim the rest — mirroring the
    // map's relation re-scope. top_entities is capped and noisy, so if NOTHING
    // matches we keep the global list rather than dimming everything.
    const focusPerson = filter.person?.toLowerCase().trim() || null
    const threadMatchesPerson = (n: Narrative): boolean => {
        if (!focusPerson) return false
        // Precise: the backend ?person= set (full persons array). Until it
        // arrives, fall back to the capped top_entities heuristic.
        if (personMatchIds) return personMatchIds.has(n.thread_id)
        return (n.top_entities || []).some(e => e.toLowerCase().includes(focusPerson))
    }
    const anyPersonMatch = !!focusPerson && displayedNarratives.some(threadMatchesPerson)

    // #234: when a thread is open, surface its SIBLING threads — those sharing a
    // top country with it — and dim the rest. No focus-model change (thread-open
    // clears focus by design); reuses the activeThreadId prop. Guarded: only
    // when the open thread is in this list, has countries, and at least one
    // OTHER thread relates — otherwise the list stays as-is.
    const activeThread = activeThreadId
        ? displayedNarratives.find(n => n.thread_id === activeThreadId)
        : null
    // Relate by the open thread's PRIMARY geography (top-2 countries), not all 5:
    // sharing the dominant country (often US) is too broad to be a real sibling.
    const activeCountries = new Set((activeThread?.top_countries || []).slice(0, 2))
    // #234 upgrade: ALSO relate by shared DISTINCTIVE ENTITY (rarity-weighted) —
    // sharper than geography alone. Naive entity overlap is HARMFUL: a single
    // common GDELT entity (measured: "donald trump" in 14/30 threads) links every
    // unrelated thread. So only entities shared by FEW threads count — a common
    // actor is noise, a rare shared actor is a real sibling signal (e.g. opening a
    // Russia–Ukraine thread surfaces another thread sharing Zelensky, not every
    // US thread sharing Trump). Cap = min(3, 25% of the list).
    const norm = (e: string) => e.toLowerCase().trim()
    const entityDF = new Map<string, number>()
    for (const n of displayedNarratives)
        for (const e of new Set((n.top_entities || []).map(norm).filter(Boolean)))
            entityDF.set(e, (entityDF.get(e) || 0) + 1)
    const distinctiveCap = Math.max(2, Math.min(3, Math.floor(displayedNarratives.length * 0.25)))
    const isDistinctive = (e: string) => (entityDF.get(e) || 0) <= distinctiveCap
    const activeEntities = new Set(
        (activeThread?.top_entities || []).map(norm).filter(e => e && isDistinctive(e))
    )
    const threadRelated = (n: Narrative): boolean =>
        !!activeThread && (
            n.thread_id === activeThreadId ||
            n.top_countries.some(c => activeCountries.has(c)) ||
            (n.top_entities || []).some(e => activeEntities.has(norm(e)))
        )
    const anyThreadRelation = !!activeThread && (activeCountries.size > 0 || activeEntities.size > 0) &&
        displayedNarratives.some(n => n.thread_id !== activeThreadId && threadRelated(n))

    // #234 legibility (Paper 7 / reason-codes guardrail): expose WHY a sibling
    // relates — the shared distinctive entity (preferred, more specific) or the
    // shared primary country — so the re-scope is never a silent dim.
    const relationReason = (n: Narrative): string | null => {
        if (!activeThread || n.thread_id === activeThreadId) return null
        const sharedEntity = (n.top_entities || []).find(e => activeEntities.has(norm(e)))
        if (sharedEntity) return sharedEntity
        const sharedCountry = n.top_countries.find(c => activeCountries.has(c))
        return sharedCountry ? resolveCountryName(sharedCountry) : null
    }

    // person focus takes precedence; else thread-sibling relation
    const relate = anyPersonMatch ? threadMatchesPerson : (anyThreadRelation ? threadRelated : null)
    const orderedNarratives = relate
        ? [...displayedNarratives].sort((a, b) => Number(relate(b)) - Number(relate(a)))
        : displayedNarratives

    const handleClick = (n: Narrative) => {
        onThreadSelect?.(n)
        if (n.top_countries.length > 0) {
            setMapFlyCountry(n.top_countries[0])
        }
    }

    const handleCountryPipClick = (e: React.MouseEvent, code: string) => {
        e.stopPropagation()
        setCountry(code)
        setMapFlyCountry(code)
        onCountrySelect?.(code)
    }

    const clearCountryFilter = () => {
        setCountry(null)
        setMapFlyCountry(null)
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
                {feedError ? (
                    <div className="narrative-empty narrative-empty--error" role="status" aria-live="polite">
                        Narrative feed unavailable — retrying…
                    </div>
                ) : (
                    <div className="narrative-empty">No active narratives in this time range</div>
                )}
            </div>
        )
    }

    if (displayedNarratives.length === 0 && filter.country) {
        const emptyState = buildCountryThreadEmptyState(filter.country, resolveCountryName(filter.country))
        return (
            <div className="narrative-threads-container">
                <div className="narrative-empty narrative-empty--actionable">
                    <div className="narrative-empty-title">{emptyState.title}</div>
                    <p>{emptyState.body}</p>
                    <button type="button" className="narrative-empty-action" onClick={clearCountryFilter}>
                        {emptyState.actionLabel}
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="narrative-threads-container">
            {(filter.country || (anyPersonMatch && focusPerson)) && (() => {
                // A3 scope strip: make silent re-scopes legible + reversible.
                const scopedToCountry = !!filter.country
                const scopeName = scopedToCountry
                    ? resolveCountryName(filter.country!)
                    : (filter.person || '')
                const clearScope = scopedToCountry ? clearCountryFilter : () => setPerson(null)
                return (
                    <div className="narrative-scope-strip" data-tip={scopedToCountry ? 'Threads filtered to this country by backend quality gates' : 'Threads that mention this person'}>
                        <span className="narrative-scope-label">
                            Scoped to <strong>{scopeName}</strong>
                        </span>
                        <button type="button" className="narrative-scope-clear" onClick={clearScope} data-tip="Clear scope" aria-label="Clear scope">✕</button>
                    </div>
                )
            })()}
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
            {orderedNarratives.map(n => {
                const isFocused = activeThreadId === n.thread_id
                // Dim conditions:
                //  - a country is locked AND this thread doesn't cover it -> dim
                //  - a person is focused, some thread mentions them, this one doesn't -> dim (#234)
                const dimByCountry = !!filter.country && !n.top_countries.includes(filter.country)
                const dimByPerson = anyPersonMatch && !threadMatchesPerson(n)
                const dimByThread = !anyPersonMatch && anyThreadRelation && !threadRelated(n)
                const isDimmed = dimByCountry || dimByPerson || dimByThread
                // #234 legibility: show the relation reason on surfaced siblings.
                const siblingReason = (anyThreadRelation && !anyPersonMatch && !filter.country
                    && !isFocused && !isDimmed) ? relationReason(n) : null
                const trendArrow = n.trend === 'accelerating' ? '▲' : n.trend === 'fading' ? '▼' : '→'
                // Plain-language hover hint; falls back to label when no description is available.
                const rowHint = `${n.label}: ${n.signal_count.toLocaleString()} signals across ${n.country_count} countries from ${n.source_count} sources. Click to open the unified thread detail.`
                const domainLabel = (n.parent_domain || 'narrative thread').replace(/-/g, ' ')
                // Unified threads (Pedro 2026-06-24): no living/aggregate source
                // tier — every row is a narrative thread, ranked by movement +
                // volume + coherence. The trend arrow carries the movement; the
                // count its weight. No source-origin badge.

                const colorIdx = orderedNarratives.indexOf(n) % THREAD_COLORS.length
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
                                <span className="narrative-label-text" data-tip={n.label}>
                                    {n.label}
                                    <span className="narrative-cluster-label">
                                        {domainLabel}
                                        {siblingReason && (
                                            <span className="narrative-sibling-reason" data-tip={`Related to the open thread via ${siblingReason}`}>
                                                ↔ {siblingReason}
                                            </span>
                                        )}
                                    </span>
                                </span>
                            </div>
                            {/* T4 (dataviz audit): count-lineage label. The row count is the RAW
                                assigned count; the opened detail shows the gate-verified count —
                                unlabeled they read as a bug. Convention: raw · sourced · verified. */}
                            <span
                                className="narrative-count"
                                data-tip={n.gate_scored_count && n.gated_signal_count !== n.signal_count
                                    ? `${n.signal_count.toLocaleString()} raw assigned signals · ${(n.gated_signal_count ?? 0).toLocaleString()} verified by the relevance gate. The detail view shows the verified set.`
                                    : `${n.signal_count.toLocaleString()} media signals in the selected window`}
                            >
                                {n.signal_count > 999 ? `${(n.signal_count / 1000).toFixed(1)}k` : n.signal_count}
                                {!!n.gate_scored_count && n.gated_signal_count != null && n.gated_signal_count !== n.signal_count && (
                                    <span className="narrative-count-lineage">
                                        {n.gated_signal_count.toLocaleString()} verified
                                    </span>
                                )}
                                {n.signal_count < 10 && (
                                    <span className="coverage-badge coverage-badge--thin" data-tip={`Only ${n.signal_count} signals — treat as indicative only`}>thin</span>
                                )}
                                {n.signal_count >= 10 && n.signal_count < 50 && (
                                    <span className="coverage-badge coverage-badge--limited" data-tip={`${n.signal_count} signals — limited coverage`}>~</span>
                                )}
                            </span>
                            <button
                                className={`narrative-pin ${isPinned(`theme-${n.thread_id}`) ? 'narrative-pin--active' : ''}`}
                                data-tip={isPinned(`theme-${n.thread_id}`) ? 'Unpin from investigation' : 'Pin thread to investigation'}
                                onClick={e => {
                                    e.stopPropagation()
                                    const id = `theme-${n.thread_id}`
                                    if (isPinned(id)) unpinItem(id)
                                    else pinItem({ id, type: 'theme', title: n.label, urlParams: `?theme=${encodeURIComponent(n.thread_id)}` })
                                }}
                            >◆</button>
                        </div>

                        {/* Row 2: Countries, Persons, attention badges + age */}
                        <div className="narrative-detail">
                            <div className="narrative-entities">
                                {n.top_countries.map(c => (
                                    <button key={c} className={`country-pip country-pip--btn${filter.country === c ? ' country-pip--active' : ''}`} onClick={e => handleCountryPipClick(e, c)} data-tip={`Focus on ${c}`}><Flag code={c} /> {c}</button>
                                ))}
                                {n.top_entities.slice(0, 4).map(p => (
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
                                {n.discussion_count != null && n.discussion_count > 0 && (
                                    <span className="attention-badge forum" data-tip={`${n.discussion_count} forum post(s) discussing this — people-side, not evidence.${n.forum_sentiment != null ? ` Public mood ${n.forum_sentiment > 0.1 ? 'positive' : n.forum_sentiment < -0.1 ? 'negative' : 'neutral'} (${n.forum_sentiment.toFixed(1)}).` : ''}`}>
                                        FORUM {n.discussion_count}{n.forum_sentiment != null ? ` · ${n.forum_sentiment > 0.1 ? '▲' : n.forum_sentiment < -0.1 ? '▼' : '–'}` : ''}
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
                            <span className="spread-label spread-label--confidence" data-tip="Atlas confidence for this living thread">{n.confidence_pct}% confidence</span>
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
