import { useState, useEffect, useCallback, useRef } from 'react'
import { useSavedWatches, fetchWatchCount } from '../hooks/useSavedWatches'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ComposableMap, Geographies, Geography } from 'react-simple-maps'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { COUNTRY_OPTIONS, resolveCountryName } from '../lib/countryNames'
import { TIME_RANGE_OPTIONS, TIME_RANGE_LABELS, timeRangeToHours, type TimeRange } from '../lib/timeRanges'
import { readBriefingCache } from '../lib/briefingPrefetch'
import { resolveThreadThemeTarget } from '../lib/threadThemeTarget'
import { selectLeadThread } from '../lib/briefLead'
import { coverageChipTip, COVERAGE_CHIP_LABEL } from '../lib/countryChips'
import { track, trackOnce } from '../lib/telemetry'
import { OfflineBanner } from '../components/OfflineBanner'
import './BriefNewspaper.css'

// Natural Earth 110m with ISO_A2 country properties
const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

// world-atlas numeric IDs to ISO-2 for signal lookup
// Only top-coverage countries needed; unmapped = base color
const NUMERIC_TO_ISO2: Record<string, string> = {
    '4':'AF','8':'AL','12':'DZ','24':'AO','32':'AR','36':'AU','40':'AT','50':'BD',
    '56':'BE','64':'BT','68':'BO','76':'BR','100':'BG','116':'KH','120':'CM','124':'CA',
    '144':'LK','152':'CL','156':'CN','170':'CO','180':'CD','188':'CR','192':'CU','196':'CY',
    '203':'CZ','208':'DK','214':'DO','218':'EC','818':'EG','222':'SV','231':'ET','246':'FI',
    '250':'FR','276':'DE','288':'GH','300':'GR','320':'GT','324':'GN','332':'HT','340':'HN',
    '348':'HU','356':'IN','360':'ID','364':'IR','368':'IQ','372':'IE','376':'IL','380':'IT',
    '388':'JM','392':'JP','400':'JO','398':'KZ','404':'KE','408':'KP','410':'KR','414':'KW',
    '418':'LA','422':'LB','430':'LR','434':'LY','484':'MX','458':'MY','466':'ML','504':'MA',
    '508':'MZ','516':'NA','524':'NP','528':'NL','554':'NZ','558':'NI','566':'NG','578':'NO',
    '586':'PK','591':'PA','604':'PE','608':'PH','616':'PL','620':'PT','630':'PR','634':'QA',
    '642':'RO','643':'RU','646':'RW','682':'SA','686':'SN','694':'SL','706':'SO','710':'ZA',
    '724':'ES','729':'SD','752':'SE','756':'CH','760':'SY','158':'TW','762':'TJ','764':'TH',
    '768':'TG','788':'TN','792':'TR','800':'UG','804':'UA','784':'AE','826':'GB','840':'US',
    '858':'UY','860':'UZ','704':'VN','887':'YE','894':'ZM','716':'ZW',
}

function signalColor(intensity: number): string {
    const r = Math.round(26 + (29 - 26) * intensity)
    const g = Math.round(37 + (158 - 37) * intensity)
    const b = Math.round(53 + (117 - 53) * intensity)
    return `rgb(${r},${g},${b})`
}

interface ThreadEvidence {
    id?: string | number
    headline: string
    source?: string
    country_code?: string | null
    url?: string
}

interface TimelinePoint {
    hour: string
    count: number
    avg_sentiment: number
}

interface TopThread {
    thread_id: string
    label: string
    anchor_topics?: string[]
    signal_count: number
    lifetime_signal_count?: number
    source_count?: number
    country_count?: number
    changed_10h?: number
    trend?: string
    why_now?: string
    top_countries?: string[]
    top_country_names?: string[]
    evidence_samples?: ThreadEvidence[]
    hourly_timeline?: TimelinePoint[]
    confidence?: string
}

interface HeatCountry {
    code: string
    name: string
    volume: number
    heat: number
    components?: Record<string, number>
}

interface BriefingData {
    period_hours: number
    stats: {
        total_signals: number
        countries: number
        sources: number
        avg_sentiment: number
    }
    top_countries: { code: string; name: string; signals: number; sentiment: number; sentiment_source?: string; nlp_coverage?: number }[]
    negative_sentiment: { code: string; name: string; sentiment: number; signals: number; sentiment_source?: string; nlp_coverage?: number }[]
    positive_sentiment: { code: string; name: string; sentiment: number; signals: number; sentiment_source?: string; nlp_coverage?: number }[]
    top_themes: {
        theme: string
        count: number
        source_table?: string
        model_version?: string | null
        topic_coverage?: number | null
        sentiment_coverage?: number | null
    }[]
    top_threads?: TopThread[]
    heat_countries?: HeatCountry[]
    historical_coverage?: {
        source: 'hot' | 'historical_processed'
        sentimentCoverage?: number | null
        topicCoverage?: number | null
        modelVersion?: string | null
    }
    top_sources: { source: string; count: number }[]
}

interface CountryBriefData {
    countryCode: string
    name: string
    totalSignals: number
    sentiment: number
    sources: number
}

// Heat components a reader can act on. geo_confidence and duplication are
// data-quality terms, not story terms — never surface them as "why hot".
const HEAT_STORY_COMPONENTS = ['velocity', 'surprise', 'diversity', 'voice', 'polyphony'] as const

function dominantHeatComponent(components?: Record<string, number>): string | null {
    if (!components) return null
    let best: string | null = null
    let bestVal = -Infinity
    for (const key of HEAT_STORY_COMPONENTS) {
        const v = components[key]
        if (typeof v === 'number' && v > bestVal) {
            best = key
            bestVal = v
        }
    }
    return best
}

// #183: sentiment numbers carry their provenance — NLP-weighted (RoBERTa)
// vs raw GDELT tone. Low NLP coverage tones the badge down so a glance
// reads as "less confident value".
function SentimentSourceBadge({ source, coverage }: { source?: string; coverage?: number }) {
    if (!source) return null
    const isNlp = source.startsWith('nlp')
    const lowCov = (coverage ?? 0) < 0.30
    return (
        <span
            className={`brief-sentsrc${isNlp && !lowCov ? '' : ' brief-sentsrc--weak'}`}
            data-tip={isNlp
                ? `Sentiment from multilingual NLP model, ${Math.round((coverage ?? 0) * 100)}% of signals covered${lowCov ? ' — low coverage, less confident' : ''}`
                : 'Sentiment from raw GDELT tone only — no NLP coverage'}
        >
            {isNlp ? `NLP ${Math.round((coverage ?? 0) * 100)}%` : 'GDELT'}
        </span>
    )
}

function trendArrow(trend?: string, changed10h?: number): { glyph: string; cls: string; label: string } | null {
    if (trend === 'surging') return { glyph: '▲', cls: 'up', label: changed10h ? `+${changed10h} / 10h` : 'surging' }
    if (trend === 'fading') return { glyph: '▼', cls: 'down', label: changed10h ? `${changed10h} / 10h` : 'fading' }
    if (trend === 'stable') return { glyph: '—', cls: 'flat', label: 'stable' }
    return null
}

// Inline sparkline from a thread's hourly timeline. Graphic slot per the
// surfaces review (§3): degrades to null when the timeline is too short,
// the slot itself stays in the row markup.
function Sparkline({ timeline }: { timeline?: TimelinePoint[] }) {
    if (!timeline || timeline.length < 2) return <span className="brief-spark brief-spark-empty" />
    const counts = timeline.map(p => p.count)
    const max = Math.max(...counts, 1)
    const w = 96
    const h = 24
    const step = w / (counts.length - 1)
    const points = counts
        .map((c, i) => `${(i * step).toFixed(1)},${(h - 2 - (c / max) * (h - 4)).toFixed(1)}`)
        .join(' ')
    return (
        <span className="brief-spark">
            <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} preserveAspectRatio="none">
                <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.5" />
            </svg>
        </span>
    )
}

export function BriefNewspaper() {
    const navigate = useNavigate()
    const [searchParams, setSearchParams] = useSearchParams()
    const rangeParam = searchParams.get('range')
    const countryParam = searchParams.get('country')?.toUpperCase() ?? null
    const initialRange = TIME_RANGE_OPTIONS.includes(rangeParam as TimeRange)
        ? (rangeParam as TimeRange)
        : '24h'

    const [timeRange, setTimeRange] = useState<TimeRange>(initialRange)
    const { watches, remove: removeWatch, markSeen } = useSavedWatches()
    const [watchCounts, setWatchCounts] = useState<Record<string, number | null>>({})
    const [data, setData] = useState<BriefingData | null>(null)
    const [insight, setInsight] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)
    const [countryFilter, setCountryFilter] = useState<string | null>(countryParam)
    const [countryDetail, setCountryDetail] = useState<CountryBriefData | null>(null)
    const [countryThreads, setCountryThreads] = useState<TopThread[] | null>(null)
    const [countryLoading, setCountryLoading] = useState(false)
    const [countryError, setCountryError] = useState<string | null>(null)
    const [countryQuery, setCountryQuery] = useState('')
    const [showCountryDropdown, setShowCountryDropdown] = useState(false)
    const countryInputRef = useRef<HTMLInputElement>(null)
    const [now] = useState(new Date())

    const hours = timeRangeToHours(timeRange)

    const fetchData = useCallback(async (h: number) => {
        setLoading(true)
        setData(null)
        setInsight(null)
        try {
            // Use Landing prefetch cache when available — eliminates visible loading delay
            const cached = readBriefingCache(h)
            if (cached) {
                setData(cached.briefing as BriefingData)
                if (cached.insight) setInsight(cached.insight)
            } else {
                const [briefRes, insightRes] = await Promise.all([
                    fetch(`/api/v2/briefing?hours=${h}`),
                    fetch(`/api/v2/briefing/insight?hours=${h}`)
                ])
                if (!briefRes.ok) throw new Error(`Briefing request failed: ${briefRes.status}`)
                setData(await briefRes.json())
                if (insightRes.ok) {
                    const insightData = await insightRes.json()
                    if (insightData.insight) setInsight(insightData.insight)
                }
            }
        } catch (e) {
            console.error(e)
        } finally {
            setLoading(false)
        }
    }, [])

    // T5.1: /brief had ZERO telemetry (app_open only fires on /app) — the
    // consumer front door was invisible to the value-moment funnel.
    useEffect(() => { track('brief_open') }, [])

    useEffect(() => {
        fetchData(hours)
    }, [hours, fetchData])

    useEffect(() => {
        if (!countryFilter) {
            setCountryDetail(null)
            setCountryThreads(null)
            setCountryError(null)
            return
        }

        let cancelled = false
        setCountryLoading(true)
        setCountryError(null)

        Promise.all([
            fetch(`/api/v2/nodes?focus_type=country&focus_value=${countryFilter}&hours=${hours}&limit=5`)
                .then(async r => {
                    if (!r.ok) throw new Error(`Country summary request failed: ${r.status}`)
                    return r.json()
                }),
            // Country body is country-scoped Narrative Threads — same contract
            // CountryBrief (L2) uses, so L1 and L2 agree on what a country shows.
            fetch(`/api/v2/threads?hours=${hours}&limit=6&country_code=${countryFilter}`)
                .then(async r => {
                    if (!r.ok) throw new Error(`Country threads request failed: ${r.status}`)
                    return r.json()
                })
        ])
            .then(([nodeData, threadData]) => {
                if (cancelled) return
                const node = nodeData.nodes?.[0]
                const threads: TopThread[] = threadData.threads ?? []
                setCountryDetail({
                    countryCode: countryFilter,
                    name: node?.name ?? resolveCountryName(countryFilter),
                    totalSignals: node?.signalCount ?? 0,
                    sentiment: node?.sentiment ?? 0,
                    sources: node?.sourceCount ?? 0,
                })
                setCountryThreads(threads)
            })
            .catch(e => {
                if (cancelled) return
                setCountryDetail(null)
                setCountryThreads(null)
                setCountryError(e instanceof Error ? e.message : 'Country data unavailable')
            })
            .finally(() => {
                if (!cancelled) setCountryLoading(false)
            })

        return () => { cancelled = true }
    }, [countryFilter, hours])

    useEffect(() => {
        if (watches.length === 0) return
        let cancelled = false
        void (async () => {
            const entries = await Promise.all(
                watches.map(async w => [w.id, await fetchWatchCount(w.filter)] as [string, number])
            )
            if (!cancelled) setWatchCounts(Object.fromEntries(entries))
        })()
        return () => { cancelled = true }
    }, [watches])

    const handleRangeChange = (range: TimeRange) => {
        setTimeRange(range)
        setSearchParams(countryFilter ? { range, country: countryFilter } : { range })
    }

    const selectCountry = (code: string | null) => {
        setCountryFilter(code)
        setCountryQuery('')
        setShowCountryDropdown(false)
        setSearchParams(code ? { range: timeRange, country: code } : { range: timeRange })
    }

    const goToAtlas = (params?: string) => {
        const next = new URLSearchParams(params)
        next.set('entry', 'brief')
        navigate(`/app?${next.toString()}`)
    }

    const openThread = (thread: TopThread, country?: string | null) => {
        const target = resolveThreadThemeTarget(thread)
        if (!target) return
        // T5.1: opening a story from the Brief IS the consumer value moment.
        // Distinct event (not thread_open — the console fires that on the
        // deep-link mount, this avoids double-counting the same open).
        track('brief_thread_open', { thread: target.theme })
        trackOnce('first_value_moment', { kind: 'brief_thread' })
        const params = new URLSearchParams()
        params.set('theme', target.theme)
        const cc = country ?? target.originCountry
        if (cc) params.set('country', cc)
        goToAtlas(params.toString())
    }

    const moodLabel = (s: number) => s > 0.15 ? 'POSITIVE' : s < -0.15 ? 'NEGATIVE' : 'NEUTRAL'
    const moodClass = (s: number) => s > 0.15 ? 'mood-positive' : s < -0.15 ? 'mood-negative' : 'mood-neutral'

    const dateStr = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })

    const allThreads = data?.top_threads ?? []
    // Lead story = the TOP-RANKED thread (see lib/briefLead.ts). Never the
    // first thread that merely *carries* evidence — that broke after ranking
    // was unified (2026-06-24). The lead renders evidence headlines when
    // present and degrades gracefully when absent.
    const leadThread = selectLeadThread(allThreads, countryFilter)
    const watchlistThreads = leadThread
        ? allThreads.filter(t => t.thread_id !== leadThread.thread_id).slice(0, 8)
        : allThreads.slice(0, 8)

    const heatStrip = (data?.heat_countries ?? []).slice(0, 4)

    // Honest standfirst: AI insight when the service produced one; otherwise a
    // single factual line. No template essay variants — an editorial that
    // pretends to judge is worse than no editorial (surfaces review §1.4).
    const standfirstFallback = data
        ? `${data.stats.total_signals.toLocaleString()} signals across ${data.stats.countries} countries from ${data.stats.sources} sources${leadThread ? ` · lead: ${leadThread.label}` : ''}.`
        : null

    const historicalCoverage = data?.historical_coverage

    const signalMap = data
        ? new Map([
            ...data.top_countries.map(c => [c.code, c.signals] as const),
            ...(countryFilter && countryDetail ? [[countryFilter, countryDetail.totalSignals] as const] : [])
        ])
        : new Map<string, number>()
    const maxSignals = data
        ? Math.max(1, ...data.top_countries.map(c => c.signals), countryDetail?.totalSignals ?? 0)
        : 1

    const renderThreadRow = (t: TopThread, country?: string | null) => {
        const arrow = trendArrow(t.trend, t.changed_10h)
        // In country view every thread is already scoped — repeating the
        // country chip on each row is noise.
        const chips = (t.top_countries ?? []).filter(cc => cc !== country).slice(0, 2)
        const headline = t.evidence_samples?.[0]?.headline
        return (
            <button
                key={t.thread_id}
                className="brief-thread-row"
                onClick={() => openThread(t, country)}
            >
                <span className="brief-thread-main">
                    <span className="brief-thread-label">{t.label}</span>
                    {headline && <span className="brief-thread-headline">{headline}</span>}
                </span>
                <span className="brief-thread-meta">
                    <Sparkline timeline={t.hourly_timeline} />
                    <span className="brief-thread-count">{t.signal_count.toLocaleString()}</span>
                    {arrow && (
                        <span className={`brief-thread-trend brief-thread-trend-${arrow.cls}`}>
                            {arrow.glyph} {arrow.label}
                        </span>
                    )}
                    {chips.map(cc => {
                        const name = resolveCountryName(cc, cc)
                        return (
                            <span key={cc} className="brief-thread-chip" data-tip={coverageChipTip(name)}>{name}</span>
                        )
                    })}
                </span>
            </button>
        )
    }

    return (
        <div className="brief-page">
            <OfflineBanner />
            <header className="brief-masthead">
                <div className="brief-nav-actions">
                    <button className="brief-back" onClick={() => navigate('/')}>← Home</button>
                    <button className="brief-back brief-back-primary" onClick={() => goToAtlas(countryFilter ? `country=${countryFilter}` : undefined)}>Open Console</button>
                </div>
                <div className="brief-masthead-center">
                    <div className="brief-edition-flag">INTELLIGENCE BRIEF</div>
                    <h1 className="brief-title">ATLAS</h1>
                    <div className="brief-dateline">{dateStr}</div>
                </div>
                <div className="brief-range-selector">
                    {TIME_RANGE_OPTIONS.slice(0, 5).map(r => (
                        <button
                            key={r}
                            className={`brief-range-btn ${timeRange === r ? 'active' : ''}`}
                            onClick={() => handleRangeChange(r)}
                        >
                            {TIME_RANGE_LABELS[r]}
                        </button>
                    ))}
                </div>
            </header>

            <div className="brief-rule" />

            {loading ? (
                <div className="brief-loading">
                    <div className="brief-loading-lines">
                        {[90, 75, 60, 80, 45].map((w, i) => (
                            <div key={i} className="brief-loading-line" style={{ width: `${w}%` }} />
                        ))}
                    </div>
                    <p>Loading brief…</p>
                </div>
            ) : data ? (
                <main className="brief-content">

                    {historicalCoverage?.source === 'historical_processed' && (
                        <div
                            className="brief-coverage-note"
                            data-tip="This long-window brief is served from compact processed historical aggregates synced from the local archive, not from raw historical rows."
                        >
                            <span>Historical processed</span>
                            {typeof historicalCoverage.topicCoverage === 'number' && (
                                <span>{Math.round(historicalCoverage.topicCoverage * 100)}% topic coverage</span>
                            )}
                            {typeof historicalCoverage.sentimentCoverage === 'number' && (
                                <span>{Math.round(historicalCoverage.sentimentCoverage * 100)}% NLP sentiment</span>
                            )}
                        </div>
                    )}

                    {/* COUNTRY FILTER */}
                    {(() => {
                        const signalCounts = new Map(data.top_countries.map(c => [c.code, c.signals]))
                        if (countryFilter && countryDetail) {
                            signalCounts.set(countryFilter, countryDetail.totalSignals)
                        }
                        const apiNames = new Map(data.top_countries.map(c => [c.code, c.name]))
                        if (countryFilter && countryDetail) {
                            apiNames.set(countryFilter, countryDetail.name)
                        }
                        const allCountries = COUNTRY_OPTIONS.map(c => ({
                            code: c.code,
                            name: resolveCountryName(c.code, apiNames.get(c.code) ?? c.name),
                            signals: signalCounts.get(c.code) ?? 0,
                        }))
                        const q = countryQuery.toLowerCase().trim()
                        const suggestions = q
                            ? allCountries.filter(c =>
                                resolveCountryName(c.code, c.name).toLowerCase().includes(q) ||
                                c.code.toLowerCase().includes(q)
                              )
                            : allCountries
                        suggestions.sort((a, b) => {
                            if (b.signals !== a.signals) return b.signals - a.signals
                            return a.name.localeCompare(b.name)
                        })
                        const activeCountry = countryFilter
                            ? allCountries.find(c => c.code === countryFilter)
                            : null

                        return (
                            <section className="brief-filter-row">
                                <span className="brief-filter-label">Country:</span>
                                {activeCountry ? (
                                    <div className="brief-filter-active">
                                        <span className="brief-filter-chip active">
                                            {resolveCountryName(activeCountry.code, activeCountry.name)}
                                        </span>
                                        <button
                                            className="brief-filter-clear"
                                            onClick={() => selectCountry(null)}
                                        >
                                            x
                                        </button>
                                    </div>
                                ) : (
                                    <div className="brief-filter-search-wrap">
                                        <input
                                            ref={countryInputRef}
                                            className="brief-filter-input"
                                            placeholder="Search country…"
                                            value={countryQuery}
                                            onChange={e => { setCountryQuery(e.target.value); setShowCountryDropdown(true) }}
                                            onFocus={() => setShowCountryDropdown(true)}
                                            onBlur={() => setTimeout(() => setShowCountryDropdown(false), 150)}
                                        />
                                        {showCountryDropdown && suggestions.length > 0 && (
                                            <div className="brief-country-dropdown">
                                                {suggestions.slice(0, 10).map(c => (
                                                    <button
                                                        key={c.code}
                                                        className={`brief-country-option${c.signals === 0 ? ' empty' : ''}`}
                                                        onMouseDown={e => e.preventDefault()}
                                                        onClick={() => selectCountry(c.code)}
                                                    >
                                                        <span>{resolveCountryName(c.code, c.name)}</span>
                                                        <span className="brief-country-option-count">{c.signals > 0 ? c.signals.toLocaleString() : 'not in top countries'}</span>
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </section>
                        )
                    })()}

                    {/* ===== GLOBAL FRONT PAGE ===== */}
                    {!countryFilter && (
                        <>
                            {/* LEAD STORY — top thread with evidence */}
                            {leadThread ? (
                                <section
                                    className="brief-lead-story"
                                    role="button"
                                    tabIndex={0}
                                    onClick={() => openThread(leadThread)}
                                    onKeyDown={event => {
                                        if (event.key === 'Enter' || event.key === ' ') {
                                            event.preventDefault()
                                            openThread(leadThread)
                                        }
                                    }}
                                >
                                    <div className="brief-section-tag" data-tip="Top-ranked narrative thread in this window (movement, volume and coherence). Sample evidence headlines shown when available.">LEAD STORY</div>
                                    <h2 className="brief-lead-headline">{leadThread.label}</h2>
                                    <div className="brief-lead-meta">
                                        <span className="brief-lead-count">{leadThread.signal_count.toLocaleString()} signals</span>
                                        {leadThread.source_count != null && (
                                            <span className="brief-lead-sub">{leadThread.source_count} sources</span>
                                        )}
                                        {(() => {
                                            const arrow = trendArrow(leadThread.trend, leadThread.changed_10h)
                                            return arrow ? (
                                                <span className={`brief-thread-trend brief-thread-trend-${arrow.cls}`}>
                                                    {arrow.glyph} {arrow.label}
                                                </span>
                                            ) : null
                                        })()}
                                        <Sparkline timeline={leadThread.hourly_timeline} />
                                    </div>
                                    {leadThread.why_now && (
                                        <p className="brief-lead-whynow">{leadThread.why_now}</p>
                                    )}
                                    {(leadThread.evidence_samples ?? []).slice(0, 3).length > 0 && (
                                        <ul className="brief-headlines">
                                            {(leadThread.evidence_samples ?? []).slice(0, 3).map((s, i) => (
                                                <li key={s.id ?? i} className="brief-headline-item">
                                                    <span className="brief-headline-text">{s.headline}</span>
                                                    <span className="brief-headline-meta">
                                                        {s.country_code && (
                                                            <span className="brief-headline-country">{resolveCountryName(s.country_code, s.country_code)}</span>
                                                        )}
                                                        {s.source && <span className="brief-headline-source">{s.source}</span>}
                                                    </span>
                                                </li>
                                            ))}
                                        </ul>
                                    )}
                                    {(leadThread.top_countries ?? []).length > 0 && (
                                        <div className="brief-article-countries">
                                            <span className="brief-chip-caption">{COVERAGE_CHIP_LABEL}:</span>
                                            {(leadThread.top_countries ?? []).slice(0, 4).map(cc => {
                                                const name = resolveCountryName(cc, cc)
                                                return (
                                                    <span key={cc} className="brief-thread-chip" data-tip={coverageChipTip(name)}>{name}</span>
                                                )
                                            })}
                                        </div>
                                    )}
                                    <span className="brief-theme-link">Open thread →</span>
                                </section>
                            ) : (
                                <section className="brief-lead-story brief-lead-empty">
                                    <div className="brief-section-tag">LEAD STORY</div>
                                    <p>No narrative thread cleared the quality gate in this window. Open the console to inspect raw coverage.</p>
                                </section>
                            )}

                            <div className="brief-rule thin" />

                            {/* WATCHLIST — remaining threads */}
                            {watchlistThreads.length > 0 && (
                                <>
                                    <section className="brief-watchlist">
                                        <h3 className="brief-bottom-heading">Watchlist</h3>
                                        <div className="brief-thread-list">
                                            {watchlistThreads.map(t => renderThreadRow(t))}
                                        </div>
                                    </section>
                                    <div className="brief-rule thin" />
                                </>
                            )}

                            {/* STANDFIRST — AI insight when real, one factual line otherwise */}
                            {(insight || standfirstFallback) && (
                                <>
                                    <section className="brief-lead">
                                        {insight ? (
                                            <>
                                                <div
                                                    className="brief-section-tag"
                                                    data-tip="AI-generated pattern reading based on signal volume, sentiment shifts, and narrative spread. Describes observable coverage patterns — does not reflect Atlas editorial opinion."
                                                >
                                                    EDITOR'S ANALYSIS
                                                </div>
                                                <p className="brief-lead-text">{insight}</p>
                                            </>
                                        ) : (
                                            <p className="brief-standfirst">{standfirstFallback}</p>
                                        )}
                                    </section>
                                    <div className="brief-rule thin" />
                                </>
                            )}

                            {/* HEATING UP — country heat strip */}
                            {heatStrip.length > 0 && (
                                <>
                                    <section className="brief-heat-strip">
                                        <h3
                                            className="brief-bottom-heading"
                                            data-tip="Countries with the strongest anomaly heat right now. The tag names the dominant component: velocity (volume acceleration), surprise (off-baseline), diversity (many themes), voice (source spread), polyphony (many actors)."
                                        >
                                            Heating Up
                                        </h3>
                                        <div className="brief-heat-row">
                                            {heatStrip.map(h => {
                                                const comp = dominantHeatComponent(h.components)
                                                return (
                                                    <button
                                                        key={h.code}
                                                        className="brief-heat-card"
                                                        onClick={() => goToAtlas(`country=${h.code}`)}
                                                    >
                                                        <span className="brief-heat-name">{resolveCountryName(h.code, h.name)}</span>
                                                        <span className="brief-heat-val">{Math.round(h.heat * 100)}</span>
                                                        {comp && <span className="brief-heat-comp">{comp}</span>}
                                                    </button>
                                                )
                                            })}
                                        </div>
                                    </section>
                                    <div className="brief-rule thin" />
                                </>
                            )}

                            {/* MAP — demoted to half-width beside Most Active (surfaces review §4.7) */}
                            <section className="brief-map-row">
                                <div className="brief-minimap brief-minimap-demoted">
                                    <div
                                        className="brief-minimap-label"
                                        data-tip="Signal density: how many media signals Atlas captured per country in this window. Darker = more coverage. Coverage volume reflects media attention, not geopolitical importance."
                                    >
                                        Signal density — {TIME_RANGE_LABELS[timeRange]}
                                    </div>
                                    <ComposableMap
                                        projection="geoEqualEarth"
                                        projectionConfig={{ scale: 150, center: [0, 5] }}
                                        width={800}
                                        height={400}
                                    >
                                        <Geographies geography={GEO_URL}>
                                            {({ geographies }) =>
                                                geographies.map(geo => {
                                                    const iso2 = NUMERIC_TO_ISO2[String(geo.id)]
                                                    const count = iso2 ? (signalMap.get(iso2) ?? 0) : 0
                                                    const intensity = count / maxSignals
                                                    return (
                                                        <Geography
                                                            key={geo.rsmKey}
                                                            geography={geo}
                                                            fill={count > 0 ? signalColor(intensity) : '#12202e'}
                                                            stroke="#0c1017"
                                                            strokeWidth={0.5}
                                                            onClick={() => iso2 && selectCountry(iso2)}
                                                            style={{
                                                                default: { outline: 'none' },
                                                                hover: { outline: 'none' },
                                                                pressed: { outline: 'none' },
                                                            }}
                                                        />
                                                    )
                                                })
                                            }
                                        </Geographies>
                                    </ComposableMap>
                                </div>
                                <div className="brief-bottom-col brief-map-side">
                                    <h3 className="brief-bottom-heading">Most Active</h3>
                                    {data.top_countries.slice(0, 8).map(c => (
                                        <button
                                            key={c.code}
                                            className="brief-bottom-country"
                                            onClick={() => goToAtlas(`country=${c.code}`)}
                                        >
                                            <span>{resolveCountryName(c.code, c.name)}</span>
                                            <span className="brief-bottom-num">{c.signals.toLocaleString()}</span>
                                        </button>
                                    ))}
                                </div>
                            </section>
                        </>
                    )}

                    {/* ===== COUNTRY VIEW ===== */}
                    {countryFilter && (
                        <>
                            {countryDetail && (
                                <section className="brief-stats-bar">
                                    <div className="brief-stat">
                                        <span className="brief-stat-value">{countryDetail.totalSignals.toLocaleString()}</span>
                                        <span className="brief-stat-label">signals</span>
                                    </div>
                                    <div className="brief-stat-divider" />
                                    <div className="brief-stat">
                                        <span className="brief-stat-value">{countryThreads?.length ?? 0}</span>
                                        <span className="brief-stat-label">threads</span>
                                    </div>
                                    <div className="brief-stat-divider" />
                                    <div
                                        className={`brief-stat ${moodClass(countryDetail.sentiment)}`}
                                        data-tip="Aggregate sentiment across this country's signals in the window."
                                    >
                                        <span className="brief-stat-value">{moodLabel(countryDetail.sentiment)}</span>
                                        <span className="brief-stat-label">country mood</span>
                                    </div>
                                </section>
                            )}

                            <div className="brief-rule thin" />

                            <section className="brief-watchlist">
                                <h3 className="brief-bottom-heading">
                                    Narrative Threads — {resolveCountryName(countryFilter, countryDetail?.name)}
                                </h3>
                                {countryLoading ? (
                                    <p className="brief-country-note">Checking this country's narrative threads for the selected window…</p>
                                ) : (countryThreads?.length ?? 0) > 0 ? (
                                    <div className="brief-thread-list">
                                        {countryThreads!.map(t => renderThreadRow(t, countryFilter))}
                                    </div>
                                ) : (
                                    <div className="brief-country-note">
                                        <p>
                                            {countryError
                                                ? 'Atlas could not load this country brief right now. Open the console to inspect broader context or expand the time range.'
                                                : 'No coherent narrative thread cleared the quality gate for this country in the current window.'}
                                        </p>
                                        <button
                                            className="brief-theme-link"
                                            onClick={() => goToAtlas(`country=${countryFilter}`)}
                                        >
                                            Open country in Atlas →
                                        </button>
                                    </div>
                                )}
                            </section>
                        </>
                    )}

                    <div className="brief-rule" />

                    {/* BACK-MATTER — sentiment + sources + theme index */}
                    <section className="brief-bottom-row">
                        <div className="brief-bottom-col">
                            <h3 className="brief-bottom-heading">Most Negative</h3>
                            {data.negative_sentiment.slice(0, 4).map(c => (
                                <button
                                    key={c.code}
                                    className="brief-bottom-country"
                                    onClick={() => goToAtlas(`country=${c.code}`)}
                                >
                                    <span>{resolveCountryName(c.code, c.name)}</span>
                                    <span className="brief-bottom-num negative">
                                        {c.sentiment.toFixed(2)}
                                        <SentimentSourceBadge source={c.sentiment_source} coverage={c.nlp_coverage} />
                                    </span>
                                </button>
                            ))}
                        </div>
                        <div className="brief-bottom-col">
                            <h3 className="brief-bottom-heading">Most Positive</h3>
                            {data.positive_sentiment.slice(0, 4).map(c => (
                                <button
                                    key={c.code}
                                    className="brief-bottom-country"
                                    onClick={() => goToAtlas(`country=${c.code}`)}
                                >
                                    <span>{resolveCountryName(c.code, c.name)}</span>
                                    <span className="brief-bottom-num positive">
                                        +{c.sentiment.toFixed(2)}
                                        <SentimentSourceBadge source={c.sentiment_source} coverage={c.nlp_coverage} />
                                    </span>
                                </button>
                            ))}
                        </div>
                        <div className="brief-bottom-col">
                            <h3 className="brief-bottom-heading">Sources</h3>
                            {data.top_sources.slice(0, 5).map(s => (
                                <div key={s.source} className="brief-source-row">
                                    <span className="brief-source-name">{s.source}</span>
                                    <span className="brief-source-count">{s.count}</span>
                                </div>
                            ))}
                        </div>
                        <div className="brief-bottom-col">
                            <h3 className="brief-bottom-heading" data-tip="Taxonomy index — themes are a navigation aid, not the story model. Narrative Threads above are the editorial unit.">By Theme</h3>
                            {data.top_themes.slice(0, 6).map(t => (
                                <button
                                    key={t.theme}
                                    className="brief-bottom-country"
                                    onClick={() => goToAtlas(`theme=${encodeURIComponent(t.theme)}${countryFilter ? `&country=${countryFilter}` : ''}`)}
                                >
                                    <span>{getThemeIcon(t.theme)} {getThemeLabel(t.theme)}</span>
                                    <span className="brief-bottom-num">{t.count.toLocaleString()}</span>
                                </button>
                            ))}
                        </div>
                    </section>

                    {watches.length > 0 && (
                        <>
                            <div className="brief-rule" />
                            <section className="brief-watches">
                                <div className="brief-section-tag">SAVED WATCHES</div>
                                <div className="brief-watches-grid">
                                    {watches.map(w => {
                                        const parts: string[] = []
                                        if (w.filter.country) parts.push(resolveCountryName(w.filter.country))
                                        if (w.filter.concept) parts.push(w.filter.concept.label)
                                        else if (w.filter.theme) parts.push(getThemeLabel(w.filter.theme))
                                        if (w.filter.person) parts.push(w.filter.person)
                                        if (w.filter.region) parts.push(w.filter.region.label)
                                        const atlasParams = [
                                            w.filter.country ? `country=${w.filter.country}` : null,
                                            w.filter.theme ? `theme=${encodeURIComponent(w.filter.theme)}` : null,
                                            w.filter.person ? `person=${encodeURIComponent(w.filter.person)}` : null,
                                        ].filter(Boolean).join('&')
                                        const currentCount = watchCounts[w.id] ?? null
                                        const prevCount = w.lastSeenCount ?? null
                                        const delta = currentCount !== null && prevCount !== null ? currentCount - prevCount : null
                                        return (
                                            <div key={w.id} className="brief-watch-card">
                                                <div className="brief-watch-name">{w.name}</div>
                                                <div className="brief-watch-scope">{parts.join(' · ') || 'Global'}</div>
                                                <div className="brief-watch-stats">
                                                    {currentCount === null ? (
                                                        <span className="brief-watch-count loading">—</span>
                                                    ) : (
                                                        <span className="brief-watch-count">{currentCount.toLocaleString()} signals today</span>
                                                    )}
                                                    {delta !== null && delta !== 0 && (
                                                        <span className={`brief-watch-delta ${delta > 0 ? 'up' : 'down'}`}>
                                                            {delta > 0 ? '↑' : '↓'}{Math.abs(delta)} vs last check
                                                        </span>
                                                    )}
                                                    {delta === 0 && prevCount !== null && (
                                                        <span className="brief-watch-delta neutral">no change</span>
                                                    )}
                                                </div>
                                                <div className="brief-watch-date">
                                                    Saved {new Date(w.createdAt).toLocaleDateString()}
                                                    {w.lastSeenAt && ` · checked ${new Date(w.lastSeenAt).toLocaleDateString()}`}
                                                </div>
                                                <div className="brief-watch-actions">
                                                    <button
                                                        className="brief-watch-open"
                                                        onClick={() => {
                                                            if (currentCount !== null) markSeen(w.id, currentCount)
                                                            goToAtlas(atlasParams || undefined)
                                                        }}
                                                    >Open in Atlas →</button>
                                                    <button className="brief-watch-remove" onClick={() => removeWatch(w.id)} data-tip="Remove watch">×</button>
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            </section>
                        </>
                    )}

                    <div className="brief-rule" />

                    {/* CTA — enter Atlas */}
                    <section className="brief-cta">
                        <p className="brief-cta-label">Full intelligence terminal</p>
                        <button className="brief-cta-btn" onClick={() => goToAtlas(countryFilter ? `country=${countryFilter}` : undefined)}>
                            Enter Atlas →
                        </button>
                    </section>

                </main>
            ) : (
                <div className="brief-error">Failed to load briefing data.</div>
            )}
        </div>
    )
}
