import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useSavedWatches, fetchWatchCount } from '../hooks/useSavedWatches'
import { enqueueUrls, useArticleStates } from '../lib/articleEnrichment'
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { ComposableMap, Geographies, Geography } from 'react-simple-maps'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { COUNTRY_OPTIONS, resolveCountryName } from '../lib/countryNames'
import { Flag } from '../components/Flag'
import { readBriefingCache, writeBriefingCache } from '../lib/briefingPrefetch'
import { resolveThreadThemeTarget } from '../lib/threadThemeTarget'
import { isLeadEligible, leadBlockReason, selectLiveLead, LEAD_CONFIDENCE_FLOOR } from '../lib/leadConfidence'
import { splitEditionThreads, buildShareCaption } from '../lib/briefEdition'
import { coverageChipTip, COVERAGE_CHIP_LABEL } from '../lib/countryChips'
import { LabelReviewChip } from '../lib/labelReviewChip'
import { track, trackOnce } from '../lib/telemetry'
import { TranslatableHeadline } from '../components/TranslatableHeadline'
import PinReceiptButton from '../components/PinReceiptButton'
import type { CitationGateStatus } from '../lib/workbench'
import { resolveOriginChip, resolveTierChip } from '../lib/sourceProvenance'
import { TranslatableText } from '../components/TranslatableText'
import { addPin, createInvestigation, getActiveInvestigationId, getInvestigation, removePin } from '../lib/workbench'
import { OfflineBanner } from '../components/OfflineBanner'
import { LoadingMoment } from '../components/LoadingMoment'
import { EclipseStrip } from '../components/EclipseStrip'
import { decodeEntities, type EclipseData } from '../lib/attentionEclipse'
import { formatSentimentPm1, formatTone10, measuredSentimentChip } from '../lib/sentimentScale'
import { reconcileSentimentProse } from '../lib/reconcileSentimentProse'
import { useReaderTheme, ReaderThemeToggle } from '../lib/readerTheme'
import {
    assessDailyPublication,
    publicationThreads,
    type DailyPublicationArtifact,
} from '../lib/dailyPublication'
import { buildStaleBanner } from '../lib/staleBanner'
import '../styles/readerTheme.css'
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

// Map density ramp lives on the reader palette now: paper-chip -> emerald,
// per theme (SVG fills need concrete colors, var() is unreliable in
// react-simple-maps attribute context).
function lerpHex(a: string, b: string, t: number): string {
    const pa = [1, 3, 5].map(i => parseInt(a.slice(i, i + 2), 16))
    const pb = [1, 3, 5].map(i => parseInt(b.slice(i, i + 2), 16))
    const c = pa.map((v, i) => Math.round(v + (pb[i] - v) * t))
    return `rgb(${c[0]},${c[1]},${c[2]})`
}

const MAP_RAMP = {
    light: { zero: '#e6ebe7', low: '#d9e3dc', high: '#0f7b5a', stroke: '#c9d2cb' },
    dark: { zero: '#131e19', low: '#1b2620', high: '#2fd0a0', stroke: '#243029' },
} as const

interface ThreadEvidence {
    id?: string | number
    headline: string
    source?: string
    /** Story SUBJECT/coverage country — never an origin assertion (N1). */
    country_code?: string | null
    /** OUTLET origin country (signals_v2.source_origin_country) — the only
     *  legal basis for the receipt's origin chip. */
    source_origin_country?: string | null
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
    category?: string | null
    parent_domain?: string | null
    top_countries?: string[]
    top_country_names?: string[]
    evidence_samples?: ThreadEvidence[]
    hourly_timeline?: TimelinePoint[]
    confidence?: string
    avg_confidence?: number | null
    confidence_measured?: boolean
    // Label Court (Lane B / #204): entailment of the label vs its own top-N
    // receipts. "failed" auto-demotes; label_proposed carries an advisory
    // neutral receipt-derived label. NULL until the nightly court runs.
    label_status?: 'entailed' | 'partial' | 'failed' | null
    label_proposed?: string | null
    edition_role?: string
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
        // measured 2026-07-16 (docs/research/gap-pool): top-K (<=3) receipts
        // above the topic's extended (~75%) threshold — the recoverable
        // newsworthy hits buried in the raw pool; gap-slice precision 29-43%,
        // so always rendered with the unverified-extended label.
        extended_receipts?: {
            headline: string
            source?: string | null
            url?: string | null
            gate_score: number
            tier: 'extended'
        }[]
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

// Union-safe extraction of the label-trust props for the shared LabelReviewChip.
// The lead can be a live TopThread OR a sealed DailyPublicationThread (already
// reconciled at assembly, no per-row confidence columns). This shape carries
// only the trust fields; a sealed row that lacks them all resolves to no chip.
interface LabelTrustRow {
    label_status?: string | null
    avg_confidence?: number | null
    confidence_measured?: boolean
    label_proposed?: string | null
}
function labelReviewChipProps(t: LabelTrustRow) {
    return {
        labelStatus: t.label_status ?? null,
        avgConfidence: typeof t.avg_confidence === 'number' ? t.avg_confidence : null,
        confidenceMeasured: t.confidence_measured === true,
        labelProposed: t.label_proposed ?? null,
    }
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

// Edition sections. Index is the tab order; accent slots come from the reader
// palette (emerald / ochre / plum) via the panel's --r-sec override in CSS.
const SECTIONS = [
    { id: 'world', label: 'The World', kicker: 'Serious geopolitics' },
    { id: 'radar', label: 'Under the Radar', kicker: 'The Atlas edge' },
    { id: 'culture', label: 'Culture, Sport & Life', kicker: 'Where the rest of us live' },
] as const

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
    const [dailyEdition, setDailyEdition] = useState<DailyPublicationArtifact | null>(null)
    const [eclipse, setEclipse] = useState<EclipseData | null>(null)

    // Reader identity: SCOPED theme on the page wrapper (never :root — the
    // keep-alive shell shares the document with the console's Intel-Noir).
    const { theme: readerTheme, toggle: toggleReaderTheme } = useReaderTheme()

    // Edition tabs (roving tabindex; panels stay mounted so translations and
    // scroll state survive tab flips).
    const [section, setSection] = useState(0)
    const tabRefs = useRef<(HTMLButtonElement | null)[]>([])
    const selectSection = (i: number, focus = false) => {
        setSection(i)
        track('brief_section_click', { section: `tab_${SECTIONS[i].id}` })
        if (focus) tabRefs.current[i]?.focus()
    }
    const onTabKeyDown = (e: React.KeyboardEvent, i: number) => {
        let n: number | null = null
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') n = (i + 1) % SECTIONS.length
        else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') n = (i - 1 + SECTIONS.length) % SECTIONS.length
        else if (e.key === 'Home') n = 0
        else if (e.key === 'End') n = SECTIONS.length - 1
        if (n !== null) {
            e.preventDefault()
            selectSection(n, true)
        }
    }

    // Share dialog (LinkedIn card + copy-caption).
    const shareDialogRef = useRef<HTMLDialogElement>(null)
    const shareFallbackRef = useRef<HTMLTextAreaElement>(null)
    const [shareCopied, setShareCopied] = useState('')
    const [shareFallbackOpen, setShareFallbackOpen] = useState(false)

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

    // Shared L1/L3 contract: fetch independently from the fast legacy Brief.
    // A degraded artifact is useful as an honest status receipt but cannot
    // replace the newspaper until its full-universe compatibility gate passes.
    useEffect(() => {
        const ctrl = new AbortController()
        const timer = setTimeout(() => ctrl.abort(), 12000)
        fetch('/api/v2/investigation/daily-publication', { signal: ctrl.signal })
            .then(response => response.ok ? response.json() : null)
            .then(edition => { if (edition) setDailyEdition(edition as DailyPublicationArtifact) })
            .catch(() => { /* legacy Brief remains the explicit fallback */ })
            .finally(() => clearTimeout(timer))
        return () => { clearTimeout(timer); ctrl.abort() }
    }, [])

    // Attention-eclipse: only surfaces when the day's coverage is concentrated on
    // one dominant event. Best-effort + silent-degrade (endpoint 404 before deploy,
    // or a diffuse day, simply renders no strip).
    useEffect(() => {
        const ctrl = new AbortController()
        const timer = setTimeout(() => ctrl.abort(), 12000)
        fetch(`/api/v2/attention/eclipse?hours=${hours}`, { signal: ctrl.signal })
            .then(response => response.ok ? response.json() : null)
            .then(payload => { if (payload) setEclipse(payload as EclipseData) })
            .catch(() => { /* no strip when unavailable */ })
            .finally(() => clearTimeout(timer))
        return () => { clearTimeout(timer); ctrl.abort() }
    }, [hours])

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
                    // N15: freeze the Label Court verdict with the pin so the
                    // dossier can mark a failed/partial label under review.
                    labelStatus: t.label_status ?? null,
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

    const goToAtlas = (params?: string, sectionName?: string) => {
        // B1 (2026-07-05): per-section engagement — answers whether the front
        // page satisfies at the surface or fails to invite depth (12.5% ramp).
        if (sectionName) track('brief_section_click', { section: sectionName })
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

    const weekday = now.toLocaleDateString('en-US', { weekday: 'long' })
    const dayLine = now.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })

    const dailyGate = assessDailyPublication(dailyEdition)
    // Staleness truth: what edition is served, how old, and when the next seal is.
    // Honest sealed/live split — the sealed package is only "served" when the gate
    // passes; otherwise the always-current live view below is what the reader sees.
    const staleBanner = dailyEdition
        ? buildStaleBanner({
            sealedAt: dailyEdition.sealed_at ?? dailyEdition.completion?.generated_at as string | null ?? null,
            editionDate: dailyEdition.edition_date ?? null,
            servedFromSeal: dailyGate.useSharedPackage,
            reasonCodes: dailyGate.reasonCodes,
            now,
            // N10: honest next-attempt from the backend's schedule truth
            // (02:30 constant remains the no-schedule fallback inside).
            nextAttemptAt: dailyEdition.seal_schedule?.next_attempt_at ?? null,
            attemptWindowOpen: dailyEdition.seal_schedule?.attempt_window_open ?? false,
            nextSealLocal: dailyEdition.seal_schedule?.next_attempt_local,
        })
        : null
    const allThreads = dailyGate.useSharedPackage ? publicationThreads(dailyEdition) : (data?.top_threads ?? [])

    // Council Phase 1 (+ R2 N2, lead-eligibility v2): on the LIVE brief the front
    // page may only present a thread as an assembled story (label-as-fact: lead
    // or desk card) when we trust its label — measured confidence >= floor AND
    // the Label Court STAMPED it (entailed/partial). An unstamped (null) label
    // can no longer lead: new topics promote and serve before the court cycle,
    // so null was exactly the fold hole (31/37 served unstamped incl all leads).
    // Stamps land within ~30 min (court rides the classifier cron).
    // Everything else drops to the honest "Unassembled signals" tray with its raw
    // receipts. Nothing vanishes (no-silent-filtering) — a thread is either an
    // assembled card or a tray entry, exactly once.
    //
    // The gate is scoped to the legacy live path: the sealed daily package is a
    // separately-assembled, already-reconciled artifact whose rows may not carry
    // per-row confidence — re-gating it here would dump a curated edition into the
    // tray. When the package is active, trust its assembly (old behavior).
    // FOLLOW-UP (verified 2026-07-20): DailyPublicationThread carries NO
    // label_status, so the stamp rule cannot honestly apply there yet — when the
    // publication builder starts freezing label_status into the sealed graph,
    // enforce the same stamp requirement at SEAL time (not here). Never fake it.
    //
    // Lead = the TOP-RANKED *eligible* thread (see lib/leadConfidence.ts). Never
    // the first thread that merely carries evidence (broke after unified ranking
    // 2026-06-24), and never a below-floor blob (broke the front page's trust:
    // the 0.214 Greek "Teen Fall" led while real stories scored 0.9+).
    const gateActive = !countryFilter && !dailyGate.useSharedPackage
    // gateActive implies the legacy live path, so the gate operates on the
    // concrete TopThread rows (which carry avg_confidence/label_status) — the
    // sealed-package union type has no confidence columns to gate on.
    const liveThreads: TopThread[] = data?.top_threads ?? []
    // ONE source of truth for lead selection (lib/leadConfidence.selectLiveLead):
    // reads label_status/avg_confidence off the live payload, so a top thread
    // newly served as court-failed (dt-565) demotes automatically and the next
    // eligible thread wins; when none clears the bar, leadUnavailable fires.
    const liveLead = gateActive ? selectLiveLead(liveThreads) : null
    const eligiblePool = countryFilter ? [] : (gateActive ? liveLead!.eligible : allThreads)
    const unassembledThreads: TopThread[] = gateActive ? liveThreads.filter(t => !isLeadEligible(t)) : []
    const preferredLead = dailyGate.useSharedPackage
        ? allThreads.find(thread => thread.edition_role === 'lead') ?? null
        : null
    const leadThread = countryFilter ? null : (preferredLead ?? liveLead?.lead ?? eligiblePool[0] ?? null)
    // Honest empty-lead (live path only): threads exist but none cleared the bar.
    const leadUnavailable = gateActive && (liveLead?.leadUnavailable ?? false)
    // Timing vs quality: the empty lead is "awaiting verification" when at least
    // one thread would lead once the 30-min court cycle stamps it.
    const leadAwaiting = gateActive && (liveLead?.awaitingVerification ?? false)

    // Leak 2: the COUNTRY edition gets the SAME eligibility split as the global
    // path — below-bar / court-failed country threads never render as assembled
    // cards; they drop to the unassembled tray (or the honest empty-lead when
    // none clears the bar). Country threads share the /threads contract, so they
    // carry avg_confidence/label_status too.
    const countryPool: TopThread[] = countryThreads ?? []
    const countryEligible = countryFilter ? countryPool.filter(isLeadEligible) : []
    const countryUnassembled = countryFilter ? countryPool.filter(t => !isLeadEligible(t)) : []
    // Same timing/quality split for the country edition's empty state.
    const countryAwaiting = countryFilter
        ? countryEligible.length === 0 && countryPool.some(t => leadBlockReason(t) === 'awaiting-verification')
        : false
    const restThreads = leadThread
        ? eligiblePool.filter(t => t.thread_id !== leadThread.thread_id)
        : eligiblePool
    // Edition sections: culture/sport/lifestyle threads get their OWN section
    // (nothing dropped); the ranked lead stays the lead regardless of lane.
    const { world: worldRest, culture: cultureRest } = splitEditionThreads(restThreads)
    const worldCards = dailyGate.useSharedPackage ? worldRest : worldRest.slice(0, 8)
    const cultureCards = dailyGate.useSharedPackage ? cultureRest : cultureRest.slice(0, 6)

    const heatStrip = (data?.heat_countries ?? []).slice(0, 4)
    const coverageGaps = data?.coverage_gaps ?? []
    const maxGapRaw = Math.max(1, ...coverageGaps.map(g => g.raw_signals))

    // Honest standfirst: AI insight when the service produced one; otherwise a
    // single factual line. No template essay variants — an editorial that
    // pretends to judge is worse than no editorial (surfaces review §1.4).
    const displayInsight = dailyGate.useSharedPackage ? null : insight
    const standfirstFallback = dailyGate.useSharedPackage && dailyEdition
        ? `${dailyEdition.package.title}. ${allThreads.length} measured story nodes, ${dailyEdition.package.receipts.length} frozen receipts; no LLM selected or ranked the edition.`
        : data
        ? `${data.stats.total_signals.toLocaleString()} signals across ${data.stats.countries} countries from ${data.stats.sources} sources${leadThread ? ` · lead: ${decodeEntities(leadThread.label)}` : ''}.`
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
    const mapRamp = MAP_RAMP[readerTheme]

    // ---- share dialog ----
    const shareCaption = data
        ? buildShareCaption({
            leadLabel: leadThread ? decodeEntities(leadThread.label) : null,
            signals: data.stats.total_signals,
            countries: data.stats.countries,
            sources: data.stats.sources,
        })
        : ''

    const openShare = () => {
        track('brief_section_click', { section: 'share_open' })
        setShareCopied('')
        setShareFallbackOpen(false)
        const dlg = shareDialogRef.current
        if (!dlg) return
        if (typeof dlg.showModal === 'function') dlg.showModal()
        else dlg.setAttribute('open', '')
    }
    const closeShare = () => {
        const dlg = shareDialogRef.current
        if (!dlg) return
        if (typeof dlg.close === 'function') dlg.close()
        else dlg.removeAttribute('open')
        setShareCopied('')
    }
    const showShareFallback = () => {
        setShareFallbackOpen(true)
        setTimeout(() => {
            shareFallbackRef.current?.focus()
            shareFallbackRef.current?.select()
        }, 0)
    }
    const copyShareCaption = () => {
        if (navigator.clipboard?.writeText) {
            navigator.clipboard.writeText(shareCaption).then(
                () => setShareCopied('Caption copied ✓'),
                showShareFallback,
            )
        } else {
            showShareFallback()
        }
    }

    // ---- render helpers ----

    // Enrichment bridge (spec 2026-07-20): the sealed edition may carry
    // server-fetched excerpts per receipt URL + a lead coverage check. Absent
    // on pre-bridge editions — everything below degrades to exactly the old
    // render. All three sections share renderReceipt, so one join enriches them.
    const editionArticles = dailyEdition?.package?.article_enrichment?.articles ?? null
    const editionYield = dailyEdition?.package?.article_enrichment?.yield ?? null
    const coverageCheck = dailyEdition?.package?.coverage_check ?? null

    // LIVE-view enrichment: when the sealed edition is degraded the Brief
    // serves live threads whose receipt URLs differ from the sealed set — so
    // the live receipts go through the SAME shared server cache the Workbench
    // uses (enqueue is a no-op for already-fetched URLs). Sealed excerpts win;
    // live states fill the gaps. Best-effort, offline-silent.
    const liveReceiptUrls = useMemo(
        () => Array.from(new Set(
            allThreads.flatMap(t => (t.evidence_samples ?? []).slice(0, 3)
                .map(ev => (ev.url ?? '').trim())
                .filter(u => u.startsWith('http'))),
        )).slice(0, 48),
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [allThreads.map(t => t.thread_id).join('|')],
    )
    useEffect(() => { enqueueUrls(liveReceiptUrls) }, [liveReceiptUrls])
    const liveArticleStates = useArticleStates(liveReceiptUrls)

    // Receipts: REAL LINKS. Evidence urls render as <a href> (the whole point
    // of a receipt); rows without a url degrade to a plain row.
    const renderReceipt = (
        ev: ThreadEvidence, i: number,
        ctx?: { gateStatus?: CitationGateStatus; contextLabel?: string },
    ) => {
        // Entities decoded before any render/translate path (council P0-3);
        // id-less receipts (e.g. the sealed daily package) still translate via
        // the free-text lane instead of rendering a foreign headline plain
        // (council wish 6 — the lead's Greek receipts never translated).
        const headline = decodeEntities(ev.headline)
        const head = (
            <span className="brief-receipt-head" dir="auto">
                {ev.id != null
                    ? <TranslatableHeadline signalId={Number(ev.id)} original={headline} sourceLang={ev.source_lang} />
                    : <TranslatableText text={headline} />}
            </span>
        )
        const meta = (
            <span className="brief-receipt-meta">
                {ev.source && <span className="brief-receipt-src">{ev.source}</span>}
                {/* N1: tier + origin chips ENTAIL source_origin_country. The
                    tier chip is name-classified but LOCAL only renders with a
                    known origin; the country chip is the OUTLET's origin —
                    never the story's subject country — and simply does not
                    render when the origin is unknown (absence over guess). */}
                {ev.source && (() => {
                    const tc = resolveTierChip(ev.source, ev.source_origin_country)
                    return (
                        <span className={`brief-receipt-tier brief-receipt-tier--${tc.tier}`} data-tip={tc.tip}>
                            {tc.label}
                        </span>
                    )
                })()}
                {(() => {
                    const oc = resolveOriginChip(ev.source_origin_country)
                    return oc ? (
                        <span className="brief-receipt-cc" data-tip={oc.tip}>
                            {oc.countryCode}
                        </span>
                    ) : null
                })()}
                {ev.url && <span className="brief-receipt-ext" aria-hidden="true">↗</span>}
                <PinReceiptButton
                    contextLabel={ctx?.contextLabel || headline}
                    citation={{
                        headline,
                        source: ev.source || undefined,
                        url: ev.url || undefined,
                        originCountry: ev.source_origin_country || undefined,
                        sourceLang: ev.source_lang || undefined,
                        gateStatus: ctx?.gateStatus ?? 'unknown',
                        publishedDate: ev.timestamp && ev.timestamp.length >= 10 ? ev.timestamp.slice(0, 10) : undefined,
                    }}
                />
            </span>
        )
        const receiptEl = ev.url ? (
            <a
                key={ev.id ?? i}
                className="brief-receipt"
                href={ev.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={e => e.stopPropagation()}
            >
                {head}
                {meta}
            </a>
        ) : (
            <div key={ev.id ?? i} className="brief-receipt">
                {head}
                {meta}
            </div>
        )
        // Excerpt under its receipt (same [receipt] identity — never a new
        // source). Sealed-edition excerpt wins; live shared-cache state fills
        // the gap when the edition is degraded. Clamped; the link is the full read.
        const enriched = ev.url
            ? (editionArticles?.[ev.url] ?? liveArticleStates.get(ev.url) ?? null)
            : null
        if (enriched?.status === 'ok' && enriched.excerpt) {
            return (
                <div key={ev.id ?? i} className="brief-receipt-block">
                    {receiptEl}
                    <blockquote className="brief-receipt-excerpt" dir="auto">
                        “<TranslatableText text={enriched.excerpt} />”
                        <span className="brief-receipt-excerpt-meta">
                            FROM THE SOURCE · fetched {enriched.fetched_at ? enriched.fetched_at.slice(0, 10) : 'at seal'}{enriched.via === 'wayback' ? ' · via Wayback Machine' : ''}
                        </span>
                    </blockquote>
                </div>
            )
        }
        return receiptEl
    }

    const renderSaveChip = (t: TopThread) => {
        const theme = resolveThreadThemeTarget(t)?.theme
        const saved = savedIds.has(`theme-${theme}`)
        return (
            <span
                role="button"
                tabIndex={0}
                className={`brief-save-btn ${saved ? 'saved' : ''}`}
                data-tip={saved ? 'Remove from investigation' : 'Save to investigation (Workbench)'}
                onClick={e => toggleSaveThread(t, e)}
                onKeyDown={e => { if (e.key === 'Enter') { e.stopPropagation(); toggleSaveThread(t) } }}
            >
                {saved ? '◆ Saved' : '◇ Save'}
            </span>
        )
    }

    const renderCoverageChips = (t: TopThread, country?: string | null, max = 3) => {
        // In country view every thread is already scoped — repeating the
        // country chip on each row is noise.
        const chips = (t.top_countries ?? []).filter(cc => cc !== country).slice(0, max)
        if (chips.length === 0) return null
        return (
            <span className="brief-chiprow">
                <span className="brief-chip-caption">{COVERAGE_CHIP_LABEL}:</span>
                {chips.map(cc => {
                    const name = resolveCountryName(cc, cc)
                    return <span key={cc} className="brief-thread-chip" data-tip={coverageChipTip(name)}>{name}</span>
                })}
            </span>
        )
    }

    const renderThreadCard = (t: TopThread, opts?: { country?: string | null; wide?: boolean }) => {
        const arrow = trendArrow(t.trend, t.changed_10h)
        const receipts = (t.evidence_samples ?? []).slice(0, opts?.wide ? 3 : 2)
        const category = t.category ?? t.parent_domain
        return (
            <article key={t.thread_id} className={`brief-card${opts?.wide ? ' wide' : ''}`}>
                <div className="reader-kicker">
                    <span>{category || 'Narrative thread'}</span>
                    <span className="cat">{t.signal_count.toLocaleString()} signals</span>
                </div>
                <h3 className="brief-card-headline">
                    <button className="brief-headline-btn" onClick={() => openThread(t, opts?.country)}>
                        <TranslatableText text={decodeEntities(t.label)} />
                    </button>
                    <LabelReviewChip {...labelReviewChipProps(t)} />
                </h3>
                <div className="brief-vitals-line">
                    {t.source_count != null && <span><b>{t.source_count}</b> sources</span>}
                    {arrow && (
                        <span className={`brief-thread-trend brief-thread-trend-${arrow.cls}`} data-tip={arrow.tip}>
                            {arrow.glyph} {arrow.label}
                        </span>
                    )}
                    <Sparkline timeline={t.hourly_timeline} />
                </div>
                {receipts.length > 0 && (
                    <>
                        <div className="brief-rc-lab">Receipts</div>
                        <div className="brief-receipts">{receipts.map((ev, i) => renderReceipt(ev, i, { contextLabel: t.label }))}</div>
                    </>
                )}
                <div className="brief-card-foot">
                    {renderCoverageChips(t, opts?.country, 2)}
                    <span className="brief-card-actions">
                        {renderSaveChip(t)}
                        <button className="brief-theme-link" onClick={() => openThread(t, opts?.country)}>Open thread →</button>
                    </span>
                </div>
            </article>
        )
    }

    // UNASSEMBLED SIGNALS TRAY entry. A cluster whose machine label we don't
    // trust for the front page (below the confidence floor OR failed the Label
    // Court). We NEVER present its label as a headline/fact — it renders struck
    // with a "label under review" chip, and the raw receipts (grouped by the
    // country each source is filed from) are the real content. Reuses the loved
    // Under-the-Radar receipt shape.
    const renderUnassembledEntry = (t: TopThread) => {
        const reason = leadBlockReason(t)
        const conf = typeof t.avg_confidence === 'number' ? t.avg_confidence : null
        const receipts = t.evidence_samples ?? []
        const groups = new Map<string, ThreadEvidence[]>()
        for (const ev of receipts) {
            const cc = ev.country_code || '—'
            const arr = groups.get(cc) ?? []
            arr.push(ev)
            groups.set(cc, arr)
        }
        const groupList = [...groups.entries()]
        return (
            <div key={t.thread_id} className="brief-unassembled-cell">
                <div className="brief-unassembled-head">
                    <span
                        className="brief-unassembled-label"
                        data-tip={reason === 'awaiting-verification'
                            ? 'This cluster is queued for its label check (stamps land within ~30 min) — it can front the page once verified. Meanwhile, read the raw sources below.'
                            : "This cluster's machine label was not trusted for the front page. Read the raw sources below — not the label."}
                    >
                        {decodeEntities(t.label)}
                    </span>
                    {/* ONE chip everywhere (leak 3): the shared LabelReviewChip, not a
                        bespoke span. `reason` is passed explicitly because the tray's
                        membership was decided by the band-aware leadBlockReason — the
                        override guarantees the chip renders even for a band-only row. */}
                    <LabelReviewChip
                        reason={reason}
                        labelStatus={t.label_status ?? null}
                        avgConfidence={conf}
                        labelProposed={t.label_proposed ?? null}
                    />
                </div>
                {t.label_proposed && (
                    <div className="brief-unassembled-proposed">
                        <span className="lab">receipt-derived</span>
                        <span>{decodeEntities(t.label_proposed)}</span>
                    </div>
                )}
                <div className="brief-unassembled-meta">
                    {conf != null && <span>{Math.round(conf * 100)}% confidence</span>}
                    <span>{t.signal_count.toLocaleString()} raw signals</span>
                    {t.source_count != null && <span>{t.source_count} sources</span>}
                </div>
                {groupList.length > 0 ? (
                    <div className="brief-unassembled-groups">
                        {groupList.map(([cc, evs]) => (
                            <div key={cc} className="brief-unassembled-group">
                                <div className="brief-unassembled-cc">
                                    {cc !== '—'
                                        ? <><Flag code={cc} /> {resolveCountryName(cc, cc)}</>
                                        : <span>Unattributed</span>}
                                </div>
                                <div className="brief-receipts">{evs.slice(0, 3).map((ev, i) => renderReceipt(ev, i, { gateStatus: 'below_gate', contextLabel: t.label }))}</div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="brief-unassembled-noreceipts">No sample receipts carried for this cluster this window.</p>
                )}
            </div>
        )
    }

    // Shared "Unassembled signals" section — ONE markup for the global AND
    // country editions (leak 2), so both surfaces demote below-bar/court-failed
    // clusters identically. Receipts are grouped by source country and, per the
    // lede, translated into the viewer's language (now honestly true — the
    // GDELT-unknown Greek receipts translate via TranslatableHeadline).
    const renderUnassembledSection = (threads: TopThread[]) => (
        <section className="brief-unassembled" aria-label="Unassembled signals">
            <span className="reader-section-kicker brief-sub-kicker">The unassembled desk</span>
            <h3
                className="brief-section-title brief-unassembled-title"
                data-tip="Clusters Atlas is tracking but has not assembled into a trustworthy story: their machine label is below the front-page confidence bar, the Label Court could not entail it against its own receipts, or it is still awaiting its label check (stamps land within ~30 min). The receipts are real. Nothing is deleted."
            >
                Below the confidence bar
            </h3>
            <p className="brief-section-lede">
                {threads.length} tracked cluster{threads.length === 1 ? '' : 's'}{' '}
                whose label did not clear the {Math.round(LEAD_CONFIDENCE_FLOOR * 100)}% bar or is still
                awaiting its receipt check. Read the sources, not the label — grouped by the country each
                source is filed from, translated into your language.
            </p>
            <div className="brief-unassembled-grid">
                {threads.map(renderUnassembledEntry)}
            </div>
        </section>
    )

    return (
        <div className={`atlas-reader brief-page${countryFilter ? '' : ` brief-sec-${SECTIONS[section].id}`}`} data-rtheme={readerTheme}>
            <OfflineBanner />
            <div className="brief-wrap">
                <div className="brief-topbar" aria-hidden="true" />

                {/* ============ MASTHEAD ============ */}
                <header className="reader-masthead brief-masthead">
                    <div className="brief-brand">
                        <p className="reader-eyebrow">The Daily Instrument · Global Edition</p>
                        <h1 className="reader-wordmark">ATLAS<span className="dot">.</span></h1>
                        <p className="reader-tagline">Narrative intelligence — measured from coverage, not editorialized.</p>
                    </div>
                    <div className="brief-masthead-right">
                        <div className="reader-dateline">{weekday}, <b>{dayLine}</b></div>
                        <span
                            className="reader-chip"
                            data-tip="The Brief is the day's edition — always the last 24 hours. For other time windows, open the console."
                        >
                            <span className="live" />Measured · Last 24 hours
                        </span>
                        <div className="brief-masthead-actions">
                            <button className="reader-chip" onClick={() => navigate('/')}>← Home</button>
                            <button
                                className="reader-chip"
                                onClick={() => goToAtlas(countryFilter ? `country=${countryFilter}` : undefined, 'masthead_console')}
                            >
                                Open Console
                            </button>
                            <button
                                className="reader-chip"
                                onClick={openShare}
                                aria-haspopup="dialog"
                            >
                                ↑ Share
                            </button>
                            <ReaderThemeToggle theme={readerTheme} onToggle={toggleReaderTheme} />
                        </div>
                    </div>
                </header>

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

                        {dailyEdition && staleBanner && (
                            <section
                                className={`brief-publication-state ${staleBanner.served === 'sealed' ? 'is-ready' : 'is-rebuilding'}`}
                                aria-label="Daily edition freshness"
                                data-tone={staleBanner.tone}
                            >
                                <div>
                                    <span className="brief-publication-kicker">
                                        {staleBanner.served === 'sealed' ? 'SEALED DAILY EDITION' : 'LIVE VIEW'}
                                    </span>
                                    <strong>{staleBanner.edition}</strong>
                                </div>
                                <span className="brief-publication-cutoff">
                                    {[
                                        staleBanner.age,
                                        staleBanner.tone === 'stale' ? staleBanner.why : null,
                                        staleBanner.served === 'live' ? staleBanner.liveNote : null,
                                        staleBanner.nextAttempt,
                                        editionYield && editionYield.attempted > 0
                                            ? `full text ${editionYield.ok}/${editionYield.attempted} receipts`
                                            : null,
                                    ].filter(Boolean).join(' · ')}
                                </span>
                            </section>
                        )}

                        {dailyGate.useSharedPackage && dailyEdition && (
                            <section className="brief-readiness-rail" aria-label="Editorial readiness">
                                {(['who', 'what', 'when', 'where', 'how', 'why'] as const).map(key => {
                                    const item = dailyEdition.package.readiness[key]
                                    return (
                                        <div key={key} className={`brief-readiness-cell is-${item.status}`}>
                                            <span>{key}</span>
                                            <strong>{item.status}</strong>
                                            <small>{item.values.slice(0, 2).join(' · ') || item.reason_codes.join(' · ').replaceAll('_', ' ')}</small>
                                        </div>
                                    )
                                })}
                            </section>
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

                        {/* ============ INSTRUMENT STRIP — real vitals ============ */}
                        <section className="brief-instrument" aria-label="Today's measured vitals">
                            <div className="brief-vital">
                                <div className="k">Signals</div>
                                <div className="v">{data.stats.total_signals.toLocaleString()}</div>
                                <div className="sub">ingested in the last 24h</div>
                            </div>
                            <div className="brief-vital">
                                <div className="k">Countries</div>
                                <div className="v">{data.stats.countries}</div>
                                <div className="sub">with coverage in-window</div>
                            </div>
                            <div className="brief-vital">
                                <div className="k">Sources</div>
                                <div className="v">{data.stats.sources.toLocaleString()}</div>
                                <div className="sub">outlet domains · raw 24h feed</div>
                            </div>
                            <div className="brief-vital">
                                <div className="k">Avg sentiment</div>
                                <div className="v">{formatSentimentPm1(data.stats.avg_sentiment)}</div>
                                <div className="sub">normalized ±1 scale · window aggregate</div>
                            </div>
                            <div className="brief-vital">
                                <div className="k">Tracked stories</div>
                                <div className="v">{allThreads.length}</div>
                                <div className="sub">ranked narrative threads served this window</div>
                            </div>
                            <div className="brief-vital">
                                <div className="k">Coverage gaps</div>
                                <div className="v">{coverageGaps.length}</div>
                                <div className="sub">categories with attention but zero verified rows</div>
                            </div>
                        </section>

                        {/* ============ COUNTRY FILTER ============ */}
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
                                            <span className="reader-chip brief-filter-chip">
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

                        {/* ===== GLOBAL EDITION — three color-coded sections ===== */}
                        {!countryFilter && (
                            <>
                                <div className="brief-tablist" role="tablist" aria-label="Sections of today's edition">
                                    {SECTIONS.map((s, i) => (
                                        <button
                                            key={s.id}
                                            ref={el => { tabRefs.current[i] = el }}
                                            className={`brief-tab brief-tab-${s.id}`}
                                            id={`brief-tab-${s.id}`}
                                            role="tab"
                                            aria-selected={section === i}
                                            aria-controls={`brief-panel-${s.id}`}
                                            tabIndex={section === i ? 0 : -1}
                                            onClick={() => selectSection(i)}
                                            onKeyDown={e => onTabKeyDown(e, i)}
                                        >
                                            <span className="swatch" aria-hidden="true" />
                                            <span>{s.label}</span>
                                            <span className="num">{String(i + 1).padStart(2, '0')}</span>
                                        </button>
                                    ))}
                                </div>

                                {/* ---------- PANEL 1 · THE WORLD ---------- */}
                                <section
                                    className="brief-panel brief-panel-world"
                                    id="brief-panel-world"
                                    role="tabpanel"
                                    aria-labelledby="brief-tab-world"
                                    tabIndex={0}
                                    hidden={section !== 0}
                                >
                                    <span className="reader-section-kicker">{SECTIONS[0].kicker}</span>
                                    <h2 className="brief-section-title">The World</h2>
                                    <p className="brief-section-lede">
                                        The day's hardest news, ranked by measured coverage. One lead, then the rest of
                                        the desk — each with its own receipts. Coverage counts are the volume of press,
                                        not a judgement of importance.
                                    </p>

                                    {/* LEAD */}
                                    {leadThread ? (
                                        <article className="brief-lead">
                                            <div className="reader-kicker">
                                                <span>Lead{(leadThread.category ?? leadThread.parent_domain) ? ` · ${leadThread.category ?? leadThread.parent_domain}` : ''}</span>
                                                <span className="cat" data-tip="Top-ranked narrative thread in this window (movement, volume and coherence). Sample evidence headlines shown when available.">
                                                    top-ranked thread · 24h window
                                                </span>
                                            </div>
                                            <h3 className="brief-lead-headline">
                                                <button className="brief-headline-btn" onClick={() => openThread(leadThread)}>
                                                    <TranslatableText text={decodeEntities(leadThread.label)} />
                                                </button>
                                                {/* leadThread is TopThread | sealed DailyPublicationThread; the
                                                    sealed row carries no trust columns, so read through the
                                                    LabelTrustRow shape (missing fields → no chip). */}
                                                <LabelReviewChip {...labelReviewChipProps(leadThread as LabelTrustRow)} />
                                            </h3>
                                            <div className="brief-metarow">
                                                {(() => {
                                                    const arrow = trendArrow(leadThread.trend, leadThread.changed_10h)
                                                    return arrow ? (
                                                        <span className={`reader-pill brief-pill-trend brief-thread-trend-${arrow.cls}`} data-tip={arrow.tip}>
                                                            {arrow.glyph} {arrow.label}
                                                        </span>
                                                    ) : null
                                                })()}
                                                <span className="reader-pill measured">Measured · last 24h</span>
                                                <span className="reader-pill">{leadThread.signal_count.toLocaleString()} signals</span>
                                                {leadThread.source_count != null && (
                                                    <span className="reader-pill">{leadThread.source_count} sources</span>
                                                )}
                                            </div>
                                            {leadThread.why_now && (
                                                <p className="brief-whynow">
                                                    <span className="lab">Why now</span>
                                                    {decodeEntities(leadThread.why_now)}
                                                </p>
                                            )}
                                            <div className="brief-vitals-line">
                                                <Sparkline timeline={leadThread.hourly_timeline} />
                                                {renderCoverageChips(leadThread, null, 4)}
                                            </div>
                                            {(leadThread.evidence_samples ?? []).length > 0 && (
                                                <>
                                                    {/* N1: the receipt country chip is now the OUTLET's
                                                        recorded origin (absent when unknown) — the caption
                                                        matches what actually renders. */}
                                                    <div className="brief-rc-lab">Receipts — real source · outlet origin when known</div>
                                                    <div className="brief-receipts">
                                                        {(leadThread.evidence_samples ?? []).slice(0, 3).map((ev, i) => renderReceipt(ev, i, { contextLabel: leadThread.label }))}
                                                    </div>
                                                </>
                                            )}
                                            <div className="brief-card-foot">
                                                <span className="brief-card-actions">
                                                    {renderSaveChip(leadThread)}
                                                    <button className="brief-theme-link" onClick={() => openThread(leadThread)}>Open thread →</button>
                                                </span>
                                            </div>
                                        </article>
                                    ) : leadUnavailable ? (
                                        // Two DIFFERENT truths (lead-eligibility v2): "awaiting
                                        // verification" = timing (stories would lead once the 30-min
                                        // court cycle stamps them); "no story clears the bar" =
                                        // quality (nothing would lead even after stamping).
                                        leadAwaiting ? (
                                            <article className="brief-lead brief-lead-empty brief-lead-belowbar">
                                                <div className="reader-kicker">
                                                    <span>Lead</span>
                                                    <span className="cat">awaiting verification</span>
                                                </div>
                                                <p>
                                                    Today's top stories are awaiting verification — their labels
                                                    have not yet been checked against their own receipts (stamps
                                                    land within ~30 minutes). Rather than lead with an unverified
                                                    label, see the unassembled desk below for the raw receipts.
                                                </p>
                                            </article>
                                        ) : (
                                            <article className="brief-lead brief-lead-empty brief-lead-belowbar">
                                                <div className="reader-kicker">
                                                    <span>Lead</span>
                                                    <span className="cat">no story clears the bar</span>
                                                </div>
                                                <p>
                                                    No assembled story clears the {Math.round(LEAD_CONFIDENCE_FLOOR * 100)}% confidence
                                                    bar this window — {allThreads.length} tracked cluster{allThreads.length === 1 ? '' : 's'}{' '}
                                                    sit{allThreads.length === 1 ? 's' : ''} below it. Rather than lead with a label we
                                                    don't trust, see the unassembled desk below for the raw receipts.
                                                </p>
                                            </article>
                                        )
                                    ) : (
                                        <article className="brief-lead brief-lead-empty">
                                            <div className="reader-kicker"><span>Lead</span></div>
                                            <p>No narrative thread cleared the quality gate in this window. Open the console to inspect raw coverage.</p>
                                        </article>
                                    )}

                                    {/* STANDFIRST — AI insight when real, one factual line otherwise */}
                                    {(displayInsight || standfirstFallback) && (
                                        <div className="brief-standfirst-box">
                                            {displayInsight ? (
                                                <>
                                                    <span
                                                        className="lab"
                                                        data-tip="AI-generated pattern reading based on signal volume, sentiment shifts, and narrative spread. Describes observable coverage patterns — does not reflect Atlas editorial opinion."
                                                    >
                                                        Editor's analysis
                                                        {/* Council P1-4: the prose can be stale/generated — the chip
                                                            carries the SAME measured number the instrument strip
                                                            shows, so any sentiment figure inside the prose is
                                                            anchored to the current measurement and its scale. */}
                                                        <span
                                                            className="brief-measured-chip"
                                                            data-tip="The window's measured average sentiment — identical to the instrument strip above. If the prose cites a different figure, trust this one: the prose may be older than the measurement."
                                                        >
                                                            {measuredSentimentChip(data.stats.avg_sentiment)}
                                                        </span>
                                                    </span>
                                                    {/* Fix round item 3: the chip anchors, but a STALE figure
                                                        inside the prose still co-rendered ("-0.1" under the
                                                        -0.53 strip). Numeric sentiment claims that disagree
                                                        with the measurement beyond 0.05 are replaced inline
                                                        with the measured value — marked, never silent. */}
                                                    <p>
                                                        {reconcileSentimentProse(displayInsight, data.stats.avg_sentiment).map((seg, i) =>
                                                            seg.corrected ? (
                                                                <span
                                                                    key={i}
                                                                    className="brief-corrected-figure"
                                                                    data-tip={`Corrected against the measured strip — the generated prose cited ${seg.corrected.original}, the measured window average is ${seg.text}.`}
                                                                >
                                                                    {seg.text}
                                                                </span>
                                                            ) : (
                                                                <span key={i}>{seg.text}</span>
                                                            ),
                                                        )}
                                                    </p>
                                                </>
                                            ) : (
                                                <p className="brief-standfirst">{standfirstFallback}</p>
                                            )}
                                        </div>
                                    )}

                                    {/* COVERAGE CHECK (spec 2026-07-20): cross-read over the
                                        lead's fetched bodies — where outlets corroborate and
                                        where their numbers/claims diverge, with both verbatim
                                        quotes. Possible findings, never asserted. */}
                                    {coverageCheck && (coverageCheck.findings?.length ?? 0) > 0 && (
                                        <div className="brief-coverage-check">
                                            <span
                                                className="lab"
                                                data-tip={coverageCheck.note ?? 'AI-read comparison of the lead story\'s fetched source texts — only quote-backed claims are compared; verify the quotes.'}
                                            >
                                                Coverage check
                                                <span className="brief-coverage-check-meta">
                                                    AI READ{coverageCheck.model ? ` · ${coverageCheck.model}` : ''} · {coverageCheck.articles_with_claims ?? '?'} sources compared · verify quotes
                                                </span>
                                            </span>
                                            {coverageCheck.findings!.map((f, i) => (
                                                <div key={i} className={`brief-cc-finding brief-cc-finding--${f.kind}`}>
                                                    <span className="brief-cc-kind">{
                                                        f.kind === 'tension' ? '⚠ outlets diverge'
                                                            : f.kind === 'shared_source' ? '⊘ same wire source'
                                                            : '✓ independent outlets agree'
                                                    }</span>
                                                    <p className="brief-cc-note">{f.note}</p>
                                                    <blockquote dir="auto">“{f.a.quote}”{f.a.outlet ? <span className="brief-cc-src"> — {f.a.outlet}</span> : null}</blockquote>
                                                    <blockquote dir="auto">“{f.b.quote}”{f.b.outlet ? <span className="brief-cc-src"> — {f.b.outlet}</span> : null}</blockquote>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {/* THE REST OF THE DESK */}
                                    {worldCards.length > 0 && (
                                        <div className="brief-cards">
                                            {worldCards.map((t, i) => renderThreadCard(t, { wide: i === 0 }))}
                                        </div>
                                    )}

                                    {/* UNASSEMBLED SIGNALS — clusters below the confidence bar or
                                        failed by the Label Court. Additive (no thread vanishes): the
                                        label is struck under review and the raw receipts, grouped by
                                        source country, are the content. */}
                                    {unassembledThreads.length > 0 && renderUnassembledSection(unassembledThreads)}

                                    {/* HEATING UP — country heat strip */}
                                    {heatStrip.length > 0 && (
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
                                    )}
                                </section>

                                {/* ---------- PANEL 2 · UNDER THE RADAR ---------- */}
                                <section
                                    className="brief-panel brief-panel-radar"
                                    id="brief-panel-radar"
                                    role="tabpanel"
                                    aria-labelledby="brief-tab-radar"
                                    tabIndex={0}
                                    hidden={section !== 1}
                                >
                                    <span className="reader-section-kicker">{SECTIONS[1].kicker}</span>
                                    <h2 className="brief-section-title">Under the Radar</h2>
                                    <p className="brief-section-lede">
                                        What the ranked front page leaves out: stories the pipeline <em>sees</em> but has
                                        not verified, and stories eclipsed by the day's dominant coverage. Nothing is
                                        deleted — it is surfaced with its honest status.
                                    </p>

                                    {coverageGaps.length > 0 ? (
                                        <>
                                            <span className="reader-section-kicker brief-sub-kicker">What is missing</span>
                                            <div className="brief-gapgrid">
                                                {coverageGaps.map(g => (
                                                    <div key={g.slug} className="brief-gap-cell">
                                                        <button
                                                            className="brief-gap"
                                                            onClick={() => goToAtlas(`theme=${encodeURIComponent(g.slug)}`, 'gap_box')}
                                                            data-tip="Category with real coverage in the last 24h where NOTHING cleared the quality gate — attention without verified evidence. 'gate pending' means not yet scored, not rejected."
                                                        >
                                                            <span className="brief-gap-label">{decodeEntities(g.label)}</span>
                                                            <span className="brief-gap-cat">Coverage gap</span>
                                                            <span className="brief-gauge">
                                                                <span><span className="num raw">{g.raw_signals.toLocaleString()}</span><span className="lbl">raw signals</span></span>
                                                                <span><span className="num ver">{g.verified}</span><span className="lbl">verified</span></span>
                                                            </span>
                                                            <span className="brief-gbar" aria-hidden="true" style={{ width: `${Math.max(8, Math.round((g.raw_signals / maxGapRaw) * 100))}%` }}>
                                                                <i style={{ width: g.raw_signals > 0 ? `${Math.round((g.verified / g.raw_signals) * 100)}%` : '0%' }} />
                                                            </span>
                                                            <span className={`brief-gap-status brief-gap-status--${g.status}`}>
                                                                <span className="d" />
                                                                {g.status === 'gate_pending' ? 'gate pending — not yet scored' : `${g.verified} of ${g.raw_signals.toLocaleString()} admitted — none cleared the quality gate`}
                                                            </span>
                                                        </button>
                                                        {(g.extended_receipts?.length ?? 0) > 0 && (
                                                            <div className="brief-gap-receipts">
                                                                <span className="brief-gap-receipts-label" data-tip="The strongest rows the ~75%-precision extended model recovers from this gap's raw pool (measured slice precision 29-43% — read as leads, not verified evidence).">
                                                                    UNVERIFIED · EXTENDED (~75% MODEL)
                                                                </span>
                                                                {g.extended_receipts!.map(r => (
                                                                    <a
                                                                        key={r.headline}
                                                                        className="brief-gap-receipt"
                                                                        href={r.url ?? undefined}
                                                                        target="_blank"
                                                                        rel="noopener noreferrer"
                                                                    >
                                                                        <span className="brief-gap-receipt-headline">{decodeEntities(r.headline)}</span>
                                                                        <span className="brief-gap-receipt-meta">{r.source ?? 'source unknown'} · score {r.gate_score.toFixed(2)} ↗</span>
                                                                    </a>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                            <p className="brief-footref">
                                                Gap bars: track length ∝ raw signals on a shared scale; the admitted fill is drawn
                                                from the verified count — 0% clearance is an empty bar, not a sliver.
                                            </p>
                                        </>
                                    ) : (
                                        <p className="brief-empty-note">No coverage gaps in this window — every scored category cleared at least one verified row.</p>
                                    )}

                                    {/* MEANWHILE, OFF THE FRONT PAGE — consequential stories
                                        eclipsed by a dominant event (renders only under an eclipse) */}
                                    <EclipseStrip
                                        data={eclipse}
                                        onOpenTopic={(id) => goToAtlas(`theme=${encodeURIComponent(id)}`, 'eclipse')}
                                    />
                                </section>

                                {/* ---------- PANEL 3 · CULTURE, SPORT & LIFE ---------- */}
                                <section
                                    className="brief-panel brief-panel-culture"
                                    id="brief-panel-culture"
                                    role="tabpanel"
                                    aria-labelledby="brief-tab-culture"
                                    tabIndex={0}
                                    hidden={section !== 2}
                                >
                                    <span className="reader-section-kicker">{SECTIONS[2].kicker}</span>
                                    <h2 className="brief-section-title">Culture, Sport &amp; Life</h2>
                                    <p className="brief-section-lede">
                                        A celebrity obituary or a World Cup semifinal is not noise — someone is reading
                                        it, and a soft label can hide a hard story folded inside it. Nothing here was
                                        judged unimportant by a machine; it simply has its own section instead of
                                        crowding out the front page. You decide what matters.
                                    </p>
                                    {cultureCards.length > 0 ? (
                                        <div className="brief-cards">
                                            {cultureCards.map((t, i) => renderThreadCard(t, { wide: i === 0 }))}
                                        </div>
                                    ) : (
                                        <p className="brief-empty-note">
                                            No culture, sport or lifestyle thread cleared the quality gate in this window —
                                            the section stays honestly empty rather than filled.
                                        </p>
                                    )}
                                </section>
                            </>
                        )}

                        {/* ===== COUNTRY VIEW ===== */}
                        {countryFilter && (
                            <section className="brief-panel brief-panel-country">
                                {countryDetail && (
                                    <div className="brief-instrument brief-instrument-country">
                                        <div className="brief-vital">
                                            <div className="k">Signals</div>
                                            <div className="v">{countryDetail.totalSignals.toLocaleString()}</div>
                                            <div className="sub">in the last 24h</div>
                                        </div>
                                        <div className="brief-vital">
                                            <div className="k">Threads</div>
                                            <div className="v">{countryThreads?.length ?? 0}</div>
                                            <div className="sub">country-scoped narrative threads</div>
                                        </div>
                                        <div className={`brief-vital ${moodClass(countryDetail.sentiment)}`}>
                                            <div className="k">Country mood</div>
                                            <div className="v" data-tip="Aggregate sentiment across this country's signals in the window.">{moodLabel(countryDetail.sentiment)}</div>
                                            <div className="sub">window aggregate</div>
                                        </div>
                                    </div>
                                )}

                                <span className="reader-section-kicker brief-sub-kicker">Country edition</span>
                                <h2 className="brief-section-title">
                                    <Flag code={countryFilter} /> {resolveCountryName(countryFilter, countryDetail?.name)}
                                </h2>
                                {countryLoading ? (
                                    <p className="brief-country-note">Checking this country's narrative threads for the selected window…</p>
                                ) : countryPool.length === 0 ? (
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
                                ) : (
                                    <>
                                        {/* Leak 2: only threads that clear the confidence bar AND the
                                            Label Court render as assembled cards. */}
                                        {countryEligible.length > 0 ? (
                                            <div className="brief-cards">
                                                {countryEligible.map((t, i) => renderThreadCard(t, { country: countryFilter, wide: i === 0 }))}
                                            </div>
                                        ) : (
                                            // Threads exist but none clears the bar (e.g. GR: the 0.214
                                            // "British Teen Fall" blob) — honest empty-lead, never an
                                            // assembled card. The raw receipts live in the tray below.
                                            // Timing vs quality split mirrors the global edition.
                                            <article className="brief-lead brief-lead-empty brief-lead-belowbar">
                                                <div className="reader-kicker">
                                                    <span>Lead</span>
                                                    <span className="cat">{countryAwaiting ? 'awaiting verification' : 'no story clears the bar'}</span>
                                                </div>
                                                {countryAwaiting ? (
                                                    <p>
                                                        Today's stories for {resolveCountryName(countryFilter, countryDetail?.name)} are
                                                        awaiting verification — their labels have not yet been checked against their own
                                                        receipts (stamps land within ~30 minutes). The raw receipts are in the
                                                        unassembled desk below.
                                                    </p>
                                                ) : (
                                                    <p>
                                                        No assembled story clears the {Math.round(LEAD_CONFIDENCE_FLOOR * 100)}% confidence
                                                        bar for {resolveCountryName(countryFilter, countryDetail?.name)} this window —{' '}
                                                        {countryUnassembled.length} tracked cluster{countryUnassembled.length === 1 ? '' : 's'}{' '}
                                                        sit{countryUnassembled.length === 1 ? 's' : ''} below it. Read the unassembled desk
                                                        below for the raw receipts rather than a label we don't trust.
                                                    </p>
                                                )}
                                            </article>
                                        )}

                                        {/* Same unassembled tray as the global edition. */}
                                        {countryUnassembled.length > 0 && renderUnassembledSection(countryUnassembled)}
                                    </>
                                )}
                            </section>
                        )}

                        <div className="brief-rule" />

                        {/* BACK-MATTER — map + most active + sentiment + sources + index */}
                        <section className="brief-map-row">
                            <div className="brief-minimap">
                                <div
                                    className="brief-bottom-heading"
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
                                                        fill={count > 0 ? lerpHex(mapRamp.low, mapRamp.high, intensity) : mapRamp.zero}
                                                        stroke={mapRamp.stroke}
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

                        <div className="brief-rule" />

                        <section className="brief-bottom-row">
                            {/* B3 (dataviz audit): ONE user-facing tone scale everywhere — raw
                                GDELT ±10 (the scale ThemeDetail already explains). The API serves
                                ÷10 values for the internal ±0.1 thresholds; multiply back for
                                display and label the unit. */}
                            <div className="brief-bottom-col">
                                <h3 className="brief-bottom-heading" data-tip="Avg GDELT tone, −10 (critical/conflict) to +10 (supportive). Scores rarely exceed ±3 in normal news — the same scale as the console's thread detail.">Most Negative</h3>
                                {data.negative_sentiment.slice(0, 4).map(c => {
                                    // Council P1-4: never print a value outside the legend
                                    // ("Gaza −10.3" under −10…+10) — clamp for display, keep
                                    // the raw figure honest in the hover.
                                    const tone = formatTone10(c.sentiment)
                                    return (
                                        <button
                                            key={c.code}
                                            className="brief-bottom-country"
                                            onClick={() => goToAtlas(`country=${c.code}`, 'most_negative')}
                                        >
                                            <span><Flag code={c.code} /> {resolveCountryName(c.code, c.name)}</span>
                                            <span className="brief-bottom-num negative" data-tip={`Avg tone ${tone.display} on the GDELT −10…+10 scale (${c.signals.toLocaleString()} signals)${tone.clamped ? ` — raw value ${tone.raw} clamped to the printed scale` : ''}`}>
                                                {tone.display}
                                                <SentimentSourceBadge source={c.sentiment_source} coverage={c.nlp_coverage} />
                                            </span>
                                        </button>
                                    )
                                })}
                                <div className="brief-scale-note">GDELT tone · −10…+10</div>
                            </div>
                            <div className="brief-bottom-col">
                                <h3 className="brief-bottom-heading" data-tip="Avg GDELT tone, −10 (critical/conflict) to +10 (supportive). Scores rarely exceed ±3 in normal news — the same scale as the console's thread detail.">Most Positive</h3>
                                {data.positive_sentiment.slice(0, 4).map(c => {
                                    const tone = formatTone10(c.sentiment)
                                    return (
                                        <button
                                            key={c.code}
                                            className="brief-bottom-country"
                                            onClick={() => goToAtlas(`country=${c.code}`, 'most_positive')}
                                        >
                                            <span><Flag code={c.code} /> {resolveCountryName(c.code, c.name)}</span>
                                            <span className="brief-bottom-num positive" data-tip={`Avg tone ${tone.display} on the GDELT −10…+10 scale (${c.signals.toLocaleString()} signals)${tone.clamped ? ` — raw value ${tone.raw} clamped to the printed scale` : ''}`}>
                                                {tone.display}
                                                <SentimentSourceBadge source={c.sentiment_source} coverage={c.nlp_coverage} />
                                            </span>
                                        </button>
                                    )
                                })}
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
                                    <span className="reader-section-kicker brief-sub-kicker">Saved watches</span>
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

                        {/* METHOD FOOTER + CTA */}
                        <footer className="brief-method">
                            <div className="brief-method-text">
                                <p>
                                    <b>Positions and prominence are measured from coverage volume, languages and countries.</b>{' '}
                                    Nothing is hidden — every story has a section. "Surging / fading" is the change in
                                    signals versus the prior 10 hours of the raw feed; coverage-country is where an
                                    outlet's row is geo-tagged, not necessarily the story's subject. Receipts link to
                                    the source. Where a verification gate found no admissible row, we say so plainly
                                    rather than fill the space.
                                </p>
                                <button className="brief-cta-btn" onClick={() => goToAtlas(countryFilter ? `country=${countryFilter}` : undefined, 'final_cta')}>
                                    Enter Atlas — full intelligence terminal →
                                </button>
                            </div>
                            <div className="brief-method-meta">
                                <div className="brief-wordmark-sm">ATLAS<span className="dot">.</span></div>
                                <div>The Atlas Edition · L1</div>
                                <div>Generated {dayLine}</div>
                                <div>Measured · last 24 hours</div>
                            </div>
                        </footer>

                    </main>
                ) : (
                    <div className="brief-error">
                        <p>{briefError ?? 'Failed to load briefing data.'}</p>
                        <button onClick={() => fetchData(hours)}>Retry briefing</button>
                    </div>
                )}

                {/* ============ SHARE DIALOG ============ */}
                <dialog
                    ref={shareDialogRef}
                    className="brief-share-dialog"
                    aria-labelledby="brief-share-title"
                    onClick={e => { if (e.target === shareDialogRef.current) closeShare() }}
                    onClose={() => setShareCopied('')}
                >
                    <div className="brief-share-shell">
                        <div className="brief-share-top">
                            <h2 className="brief-share-title" id="brief-share-title">Share today's edition</h2>
                            <button className="brief-share-close" type="button" onClick={closeShare} aria-label="Close share panel">
                                ✕ Close
                            </button>
                        </div>

                        <div className="brief-share-cardwrap">
                            <div
                                className="brief-share-card"
                                role="img"
                                aria-label={`Shareable preview card: ATLAS, ${weekday} ${dayLine}.${leadThread ? ` Lead — ${decodeEntities(leadThread.label)}.` : ''} The Atlas Edition — the news of the world, measured.`}
                            >
                                <div className="sc-head">
                                    <span className="sc-mark">ATLAS<span className="dot">.</span></span>
                                    <span className="sc-date">{weekday} · {dayLine}</span>
                                </div>
                                <p className="sc-kicker">
                                    {leadThread
                                        ? `Lead${(leadThread.category ?? leadThread.parent_domain) ? ` · ${leadThread.category ?? leadThread.parent_domain}` : ''}`
                                        : 'No lead sealed'}
                                </p>
                                {/* The share card refuses to freeze a lead we don't trust: when no
                                    thread clears the confidence bar there is no headline to publish. */}
                                <p className="sc-headline">{leadThread ? decodeEntities(leadThread.label) : 'Story under assembly — check back'}</p>
                                {leadThread?.why_now && <p className="sc-stand">{decodeEntities(leadThread.why_now)}</p>}
                                {worldCards.length > 0 && (
                                    <div className="sc-secondaries">
                                        <p className="sc-lab">Also in today's edition</p>
                                        {worldCards.slice(0, 2).map(t => (
                                            <p key={t.thread_id}>{decodeEntities(t.label)}</p>
                                        ))}
                                    </div>
                                )}
                                <div className="sc-bottom">
                                    {data && (
                                        <div className="sc-vitals">
                                            <span><b>{data.stats.total_signals.toLocaleString()}</b> signals</span>
                                            <span><b>{data.stats.countries}</b> countries</span>
                                            <span><b>{data.stats.sources.toLocaleString()}</b> sources</span>
                                            <span>measured · last 24h</span>
                                        </div>
                                    )}
                                    <div className="sc-foot">The Atlas Edition<span className="dot"> — </span>the news of the world, measured</div>
                                </div>
                            </div>
                        </div>

                        <p className="brief-share-hint">
                            <b>Screenshot the card</b>, or copy the caption — then paste both into your LinkedIn post.
                            Replace <span className="mono">&lt;your link&gt;</span> with the link to the full edition.
                        </p>
                        <div className="brief-share-actions">
                            <button className="brief-share-copy" type="button" onClick={copyShareCaption}>
                                ⧉ Copy caption
                            </button>
                            <span className="brief-share-copied" role="status" aria-live="polite">{shareCopied}</span>
                        </div>
                        {shareFallbackOpen && (
                            <>
                                <p className="brief-share-fallback-lab">Clipboard blocked — select and copy the caption below</p>
                                <textarea
                                    ref={shareFallbackRef}
                                    className="brief-share-fallback"
                                    readOnly
                                    rows={6}
                                    value={shareCaption}
                                    aria-label="LinkedIn caption text, select all and copy"
                                    onFocus={e => e.currentTarget.select()}
                                />
                            </>
                        )}
                    </div>
                </dialog>
            </div>
        </div>
    )
}
