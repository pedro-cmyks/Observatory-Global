import { useState, useEffect, useCallback, useRef } from 'react'
import { useSavedWatches, fetchWatchCount } from '../hooks/useSavedWatches'
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { ComposableMap, Geographies, Geography } from 'react-simple-maps'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { COUNTRY_OPTIONS, resolveCountryName } from '../lib/countryNames'
import { Flag } from '../components/Flag'
import { readBriefingCache, writeBriefingCache } from '../lib/briefingPrefetch'
import { resolveThreadThemeTarget } from '../lib/threadThemeTarget'
import { selectLeadThread } from '../lib/briefLead'
import { coverageChipTip, COVERAGE_CHIP_LABEL } from '../lib/countryChips'
import { track, trackOnce } from '../lib/telemetry'
import { TranslatableHeadline } from '../components/TranslatableHeadline'
import { addPin, createInvestigation, getActiveInvestigationId, getInvestigation, removePin } from '../lib/workbench'
import { OfflineBanner } from '../components/OfflineBanner'
import { LoadingMoment } from '../components/LoadingMoment'
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
    source_lang?: string | null
    url?: string
    timestamp?: string | null
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
    coverage_gaps?: {
        slug: string
        label: string
        raw_signals: number
        verified: number
        scored: number
        status: 'gate_pending' | 'none_verified'
    }[]
    category_counts?: { category: string; topics: number; signals: number }[]
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

// B1 (dataviz audit): changed_10h is RAW FEED VELOCITY (delta of raw assigned
// signals over 10h, whole feed) — a different lineage and denominator than the
// row's window count, so "34 ▼ −168/10h" read as broken math. Label the
// lineage instead of juxtaposing two unlabeled counts of different bases.
function trendArrow(trend?: string, changed10h?: number): { glyph: string; cls: string; label: string; tip: string } | null {
    const tip = changed10h
        ? `Raw feed velocity: ${changed10h > 0 ? '+' : ''}${changed10h} raw assigned signals over the last 10h across the whole feed — a different lineage than the row count, which is this window's signals.`
        : 'Trend over the last 10h of the raw feed.'
    if (trend === 'surging') return { glyph: '▲', cls: 'up', label: changed10h ? `+${changed10h}/10h raw` : 'surging', tip }
    if (trend === 'fading') return { glyph: '▼', cls: 'down', label: changed10h ? `${changed10h}/10h raw` : 'fading', tip }
    if (trend === 'stable') return { glyph: '—', cls: 'flat', label: 'stable', tip }
    return null
}

// Inline sparkline from a thread's hourly timeline. Graphic slot per the
// surfaces review (§3): degrades to null when the timeline is too short,
// the slot itself stays in the row markup.
// B2 (dataviz audit): each spark is max-normalized to its own row — a 3/h
// ripple draws the same amplitude as a 300/h spike. The peak annotation gives
// each spark the magnitude anchor cross-row comparison needs.
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
        <span className="brief-spark" data-tip={`Shape only — each sparkline is scaled to its own peak of ${max.toLocaleString()} signals/h; compare rows by the peak number, not the amplitude.`}>
            <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} preserveAspectRatio="none">
                <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.5" />
            </svg>
            <span className="brief-spark-peak">{max > 999 ? `${(max / 1000).toFixed(1)}k` : max}/h</span>
        </span>
    )
}

export function BriefNewspaper() {
    const navigate = useNavigate()
    const [searchParams, setSearchParams] = useSearchParams()
    const countryParam = searchParams.get('country')?.toUpperCase() ?? null
    const { watches, remove: removeWatch, markSeen } = useSavedWatches()
    const [watchCounts, setWatchCounts] = useState<Record<string, number | null>>({})
    const [data, setData] = useState<BriefingData | null>(null)
    const [insight, setInsight] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)
    const [briefError, setBriefError] = useState<string | null>(null)
    const [showingStale, setShowingStale] = useState(false)
    const [countryFilter, setCountryFilter] = useState<string | null>(countryParam)
    const [countryDetail, setCountryDetail] = useState<CountryBriefData | null>(null)
    const [countryThreads, setCountryThreads] = useState<TopThread[] | null>(null)
    const [countryLoading, setCountryLoading] = useState(false)
    const [countryError, setCountryError] = useState<string | null>(null)
    const [countryQuery, setCountryQuery] = useState('')
    const [showCountryDropdown, setShowCountryDropdown] = useState(false)
    const countryInputRef = useRef<HTMLInputElement>(null)
    const [now] = useState(new Date())

    // #239 keep-alive: the Brief stays mounted across App↔Brief switches, so
    // URL params must keep driving state after mount (the useState initializers
    // above run once). Internal changes write the same params back via
    // setSearchParams, so this sync is loop-safe. pathname-guarded: /app's
    // params must never drive the hidden Brief.
    const location = useLocation()
    useEffect(() => {
        if (location.pathname !== '/brief') return
        setCountryFilter(countryParam)
    }, [location.pathname, countryParam])

    // Pedro (2026-07-05): the Brief is the DAY's edition — always 24h. Other
    // windows live in the console; time-as-dimension belongs to L2 scrubbers.
    const hours = 24

    const fetchData = useCallback(async (h: number) => {
        setBriefError(null)
        const cached = readBriefingCache(h, { allowStale: true })
        if (cached) {
            setData(cached.briefing as BriefingData)
            setInsight(cached.insight)
            setShowingStale(cached.isStale)
            setLoading(false)
            if (!cached.isStale) return
        } else {
            setLoading(true)
            setData(null)
            setInsight(null)
            setShowingStale(false)
        }
        try {
            // The Brief (fast pre-agg query) is the critical path — paint it as
            // soon as it lands. The AI "Editor's Analysis" insight is an LLM call
            // (Anthropic→DeepSeek) that can take seconds or hang on dry credits;
            // NEVER block the front page on it. Fetch it in the background and
            // fill in the standfirst when it arrives. A hard timeout on the brief
            // fetch turns a hang into a visible error instead of an endless spinner.
            const ctrl = new AbortController()
            const timer = setTimeout(() => ctrl.abort(), 12000)
            let briefRes: Response
            try {
                briefRes = await fetch(`/api/v2/briefing?hours=${h}`, { signal: ctrl.signal })
            } finally {
                clearTimeout(timer)
            }
            if (!briefRes.ok) throw new Error(`Briefing request failed: ${briefRes.status}`)
            const briefing = await briefRes.json()
            setData(briefing)
            setShowingStale(false)
            writeBriefingCache(h, briefing, cached?.insight ?? null)
            setLoading(false)
            // Background, non-blocking: the insight fills the standfirst later.
            const insightCtrl = new AbortController()
            const insightTimer = setTimeout(() => insightCtrl.abort(), 25000)
            fetch(`/api/v2/briefing/insight?hours=${h}`, { signal: insightCtrl.signal })
                .then(r => (r.ok ? r.json() : null))
                .then(d => { if (d?.insight) setInsight(d.insight) })
                .catch(() => { /* insight is best-effort; standfirst has a factual fallback */ })
                .finally(() => clearTimeout(insightTimer))
        } catch (e) {
            console.error(e)
            setBriefError('Live briefing unavailable — retry when the data service recovers.')
            setLoading(false)
        }
    }, [])

    // T5.1: /brief had ZERO telemetry (app_open only fires on /app) — the
    // consumer front door was invisible to the value-moment funnel.
    useEffect(() => { track('brief_open') }, [])

    // B1: one-shot scroll-depth signal — did the reader get past the fold?
    useEffect(() => {
        const onScroll = () => {
            const el = document.documentElement
            if ((el.scrollTop + window.innerHeight) / el.scrollHeight > 0.6) {
                trackOnce('brief_scroll_depth', { pct: 60 })
                window.removeEventListener('scroll', onScroll)
            }
        }
        window.addEventListener('scroll', onScroll, { passive: true })
        return () => window.removeEventListener('scroll', onScroll)
    }, [])

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

    const selectCountry = (code: string | null) => {
        setCountryFilter(code)
        setCountryQuery('')
        setShowCountryDropdown(false)
        setSearchParams(code ? { country: code } : {})
    }

    // B4 (2026-07-05, L1→L3 bridge): save a Brief thread into the active
    // investigation (workbench lib directly — the Brief route mounts no
    // WorkspaceProvider). Snapshot frozen from the payload's own evidence.
    const [wbTick, setWbTick] = useState(0)
    const savedIds = (() => {
        void wbTick
        const id = getActiveInvestigationId()
        const inv = id ? getInvestigation(id) : null
        return new Set((inv?.pins ?? []).map(pin => pin.anchorId))
    })()

    const toggleSaveThread = (t: TopThread, e?: React.MouseEvent) => {
        e?.stopPropagation()
        const target = resolveThreadThemeTarget(t)
        if (!target) return
        const anchorId = `theme-${target.theme}`
        let invId = getActiveInvestigationId()
        if (!invId || !getInvestigation(invId)) invId = createInvestigation(t.label).id
        if (savedIds.has(anchorId)) {
            removePin(invId, anchorId)
        } else {
            track('brief_section_click', { section: 'save_thread' })
            addPin(invId, {
                anchorId,
                anchorType: 'theme',
                label: t.label,
                open: {
                    surface: 'l2_params',
                    params: { urlParams: `?theme=${encodeURIComponent(target.theme)}${target.originCountry ? `&country=${target.originCountry}` : ''}` },
                },
                snapshot: {
                    capturedAt: new Date().toISOString(),
                    summary: `${t.label} · ${t.signal_count.toLocaleString()} signals · 24h brief`,
                    metrics: { signals: t.signal_count, changed_10h: t.changed_10h ?? 0 },
                    evidence: (t.evidence_samples ?? []).slice(0, 3).map(ev => ({
                        headline: ev.headline, source: ev.source, url: ev.url,
                        date: typeof ev.timestamp === 'string' && ev.timestamp.length >= 10
                            ? ev.timestamp.slice(0, 10) : undefined,
                    })),
                },
            })
        }
        setWbTick(x => x + 1)
    }

    const goToAtlas = (params?: string, section?: string) => {
        // B1 (2026-07-05): per-section engagement — answers whether the front
        // page satisfies at the surface or fails to invite depth (12.5% ramp).
        if (section) track('brief_section_click', { section })
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
        const evidence = t.evidence_samples?.[0]
        return (
            <button
                key={t.thread_id}
                className="brief-thread-row"
                onClick={() => openThread(t, country)}
            >
                <span className="brief-thread-main">
                    <span className="brief-thread-label">{t.label}</span>
                    {evidence?.headline && (
                        <span className="brief-thread-headline">
                            {evidence.id != null
                                ? <TranslatableHeadline signalId={Number(evidence.id)} original={evidence.headline} sourceLang={evidence.source_lang} />
                                : evidence.headline}
                        </span>
                    )}
                </span>
                <span className="brief-thread-meta">
                    <span
                        role="button"
                        tabIndex={0}
                        className={`brief-save-btn ${savedIds.has(`theme-${resolveThreadThemeTarget(t)?.theme}`) ? 'saved' : ''}`}
                        data-tip={savedIds.has(`theme-${resolveThreadThemeTarget(t)?.theme}`) ? 'Remove from investigation' : 'Save to investigation'}
                        onClick={e => toggleSaveThread(t, e)}
                        onKeyDown={e => { if (e.key === 'Enter') { e.stopPropagation(); toggleSaveThread(t) } }}
                    >
                        {savedIds.has(`theme-${resolveThreadThemeTarget(t)?.theme}`) ? '◆' : '◇'}
                    </span>
                    <Sparkline timeline={t.hourly_timeline} />
                    <span className="brief-thread-count">{t.signal_count.toLocaleString()}</span>
                    {arrow && (
                        <span className={`brief-thread-trend brief-thread-trend-${arrow.cls}`} data-tip={arrow.tip}>
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
                    <button className="brief-back brief-back-primary" onClick={() => goToAtlas(countryFilter ? `country=${countryFilter}` : undefined, 'masthead_console')}>Open Console</button>
                </div>
                <div className="brief-masthead-center">
                    <div className="brief-edition-flag">INTELLIGENCE BRIEF</div>
                    <h1 className="brief-title">ATLAS</h1>
                    <div className="brief-dateline">{dateStr}</div>
                </div>
                <div className="brief-range-selector">
                    <span className="brief-range-fixed" data-tip="The Brief is the day's edition — always the last 24 hours. For other time windows, open the console.">
                        LAST 24 HOURS
                    </span>
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
                    <LoadingMoment compact />
                </div>
            ) : data ? (
                <main className="brief-content">

                    {(showingStale || briefError) && (
                        <div className="brief-cache-note" role="status">
                            <span>
                                {showingStale
                                    ? 'Showing cached brief while Atlas refreshes live data.'
                                    : briefError}
                            </span>
                            <button onClick={() => fetchData(hours)}>Retry live refresh</button>
                        </div>
                    )}

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
                                                        <span><Flag code={c.code} /> {resolveCountryName(c.code, c.name)}</span>
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
                                                <span className={`brief-thread-trend brief-thread-trend-${arrow.cls}`} data-tip={arrow.tip}>
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
                                                    <span className="brief-headline-text">
                                                        {s.id != null
                                                            ? <TranslatableHeadline signalId={Number(s.id)} original={s.headline} sourceLang={s.source_lang} />
                                                            : s.headline}
                                                    </span>
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
                                    <span className="brief-lead-actions">
                                        <span className="brief-theme-link">Open thread →</span>
                                        <span
                                            role="button"
                                            tabIndex={0}
                                            className={`brief-save-btn ${leadThread && savedIds.has(`theme-${resolveThreadThemeTarget(leadThread)?.theme}`) ? 'saved' : ''}`}
                                            data-tip="Save this story into your investigation (Workbench)"
                                            onClick={e => { e.stopPropagation(); toggleSaveThread(leadThread) }}
                                            onKeyDown={e => { if (e.key === 'Enter') { e.stopPropagation(); toggleSaveThread(leadThread) } }}
                                        >
                                            {leadThread && savedIds.has(`theme-${resolveThreadThemeTarget(leadThread)?.theme}`) ? '◆ Saved' : '◇ Save'}
                                        </span>
                                    </span>
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
                                                        onClick={() => goToAtlas(`country=${h.code}`, 'heating_up')}
                                                    >
                                                        <span className="brief-heat-name"><Flag code={h.code} /> {resolveCountryName(h.code, h.name)}</span>
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

                            {/* B3 GAP BOX (#225 reserved slot, fed 2026-07-05): attention
                                without verified coverage — the wedge's "what is missing". */}
                            {(data.coverage_gaps ?? []).length > 0 && (
                                <>
                                    <section className="brief-gapbox">
                                        <h3
                                            className="brief-bottom-heading"
                                            data-tip="Categories with real coverage in the last 24h where NOTHING cleared the quality gate — attention without verified evidence. 'gate pending' means not yet scored, not rejected."
                                        >
                                            Coverage Gaps — unverified attention
                                        </h3>
                                        {data.coverage_gaps!.map(g => (
                                            <button
                                                key={g.slug}
                                                className="brief-gap-row"
                                                onClick={() => goToAtlas(`theme=${encodeURIComponent(g.slug)}`, 'gap_box')}
                                            >
                                                <span className="brief-gap-label">{g.label}</span>
                                                <span className="brief-gap-meta">
                                                    {g.raw_signals.toLocaleString()} signals · 0 verified ·{' '}
                                                    <span className={`brief-gap-status brief-gap-status--${g.status}`}>
                                                        {g.status === 'gate_pending' ? 'gate pending' : 'none cleared the gate'}
                                                    </span>
                                                </span>
                                            </button>
                                        ))}
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
                                        Signal density — last 24h
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
                                                    // B6 (dataviz audit): linear normalize over a heavy-tailed
                                                    // distribution saturated the US and left ~90% of countries in
                                                    // the bottom 10% of the ramp reading as "no data" — sqrt spreads
                                                    // the mid-range without lying about rank order.
                                                    const intensity = Math.sqrt(count / maxSignals)
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
                                            onClick={() => goToAtlas(`country=${c.code}`, 'most_active')}
                                        >
                                            <span><Flag code={c.code} /> {resolveCountryName(c.code, c.name)}</span>
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
                                    Narrative Threads — <Flag code={countryFilter} /> {resolveCountryName(countryFilter, countryDetail?.name)}
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
                        {/* B3 (dataviz audit): ONE user-facing tone scale everywhere — raw
                            GDELT ±10 (the scale ThemeDetail already explains). The API serves
                            ÷10 values for the internal ±0.1 thresholds; multiply back for
                            display and label the unit. */}
                        <div className="brief-bottom-col">
                            <h3 className="brief-bottom-heading" data-tip="Avg GDELT tone, −10 (critical/conflict) to +10 (supportive). Scores rarely exceed ±3 in normal news — the same scale as the console's thread detail.">Most Negative</h3>
                            {data.negative_sentiment.slice(0, 4).map(c => (
                                <button
                                    key={c.code}
                                    className="brief-bottom-country"
                                    onClick={() => goToAtlas(`country=${c.code}`, 'most_negative')}
                                >
                                    <span><Flag code={c.code} /> {resolveCountryName(c.code, c.name)}</span>
                                    <span className="brief-bottom-num negative" data-tip={`Avg tone ${(c.sentiment * 10).toFixed(1)} on the GDELT −10…+10 scale (${c.signals.toLocaleString()} signals)`}>
                                        {(c.sentiment * 10).toFixed(1)}
                                        <SentimentSourceBadge source={c.sentiment_source} coverage={c.nlp_coverage} />
                                    </span>
                                </button>
                            ))}
                            <div className="brief-scale-note">GDELT tone · −10…+10</div>
                        </div>
                        <div className="brief-bottom-col">
                            <h3 className="brief-bottom-heading" data-tip="Avg GDELT tone, −10 (critical/conflict) to +10 (supportive). Scores rarely exceed ±3 in normal news — the same scale as the console's thread detail.">Most Positive</h3>
                            {data.positive_sentiment.slice(0, 4).map(c => (
                                <button
                                    key={c.code}
                                    className="brief-bottom-country"
                                    onClick={() => goToAtlas(`country=${c.code}`, 'most_positive')}
                                >
                                    <span><Flag code={c.code} /> {resolveCountryName(c.code, c.name)}</span>
                                    <span className="brief-bottom-num positive" data-tip={`Avg tone +${(c.sentiment * 10).toFixed(1)} on the GDELT −10…+10 scale (${c.signals.toLocaleString()} signals)`}>
                                        +{(c.sentiment * 10).toFixed(1)}
                                        <SentimentSourceBadge source={c.sentiment_source} coverage={c.nlp_coverage} />
                                    </span>
                                </button>
                            ))}
                            <div className="brief-scale-note">GDELT tone · −10…+10</div>
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
                            {(data.category_counts?.length ?? 0) > 0 ? (
                                /* #249: Atlas's OWN R3.1 categories — the GDELT
                                   taxonomy index retired once every story carries
                                   a category. Search opens the category term. */
                                <>
                                    <h3 className="brief-bottom-heading" data-tip="Atlas category index — every live story is typed into an open category (crisis anchors + emergent).">By Category</h3>
                                    {data.category_counts!.slice(0, 6).map(c => (
                                        <button
                                            key={c.category}
                                            className="brief-bottom-country"
                                            onClick={() => goToAtlas(`q=${encodeURIComponent(c.category)}`, 'by_category')}
                                        >
                                            <span>{c.category}</span>
                                            <span className="brief-bottom-num">{c.signals.toLocaleString()}</span>
                                        </button>
                                    ))}
                                </>
                            ) : (
                                <>
                                    <h3 className="brief-bottom-heading" data-tip="Taxonomy index — themes are a navigation aid, not the story model. Narrative Threads above are the editorial unit.">By Theme</h3>
                                    {data.top_themes.slice(0, 6).map(t => (
                                        <button
                                            key={t.theme}
                                            className="brief-bottom-country"
                                            onClick={() => goToAtlas(`theme=${encodeURIComponent(t.theme)}${countryFilter ? `&country=${countryFilter}` : ''}`, 'by_theme')}
                                        >
                                            <span>{getThemeIcon(t.theme)} {getThemeLabel(t.theme)}</span>
                                            <span className="brief-bottom-num">{t.count.toLocaleString()}</span>
                                        </button>
                                    ))}
                                </>
                            )}
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
                        <button className="brief-cta-btn" onClick={() => goToAtlas(countryFilter ? `country=${countryFilter}` : undefined, 'final_cta')}>
                            Enter Atlas →
                        </button>
                    </section>

                </main>
            ) : (
                <div className="brief-error">
                    <p>{briefError ?? 'Failed to load briefing data.'}</p>
                    <button onClick={() => fetchData(hours)}>Retry briefing</button>
                </div>
            )}
        </div>
    )
}
