import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useSavedWatches, fetchWatchCount } from '../hooks/useSavedWatches'
import { enqueueUrls, useArticleStates } from '../lib/articleEnrichment'
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { ComposableMap, Geographies, Geography } from 'react-simple-maps'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { COUNTRY_OPTIONS, resolveCountryName } from '../lib/countryNames'
import { Flag } from '../components/Flag'
import {
    clearBriefingCache,
    readBriefingCache,
    updateCachedInsight,
    writeBriefingCache,
} from '../lib/briefingPrefetch'
import {
    deskEmptyCopy,
    furnitureNote,
    instrumentReading,
    laneState,
    mapDensityNote,
    type LaneEvidence,
} from '../lib/briefLanes'
import { ANALYSIS_BASIS, ANALYSIS_LABEL, ANALYSIS_NATURE, insightStaleness } from '../lib/editorAnalysis'
import { countryDoorCopy } from '../lib/countryDoor'
import { resolveThreadThemeTarget } from '../lib/threadThemeTarget'
import { isLeadEligible, leadBlockReason, selectLiveLead, LEAD_CONFIDENCE_FLOOR } from '../lib/leadConfidence'
import { confidenceBucketLabel, confidenceBucketTip, resolveConfidenceBucket } from '../lib/threadConfidence'
import { splitEditionThreads, buildShareCaption } from '../lib/briefEdition'
import {
    frontPageScope,
    deskCensusNote,
    CATEGORY_INDEX_BASIS,
    CONSOLE_LINK_LABEL,
    type CensusRow,
} from '../lib/briefCoherence'
import { coverageChipTip, COVERAGE_CHIP_LABEL } from '../lib/countryChips'
import { LabelReviewChip } from '../lib/labelReviewChip'
import { track, trackOnce } from '../lib/telemetry'
import { TranslatableHeadline, shouldTranslate as shouldTranslateSignal } from '../components/TranslatableHeadline'
import PinReceiptButton from '../components/PinReceiptButton'
import CopyCitationButton from '../components/CopyCitationButton'
import { looksLikeNaturalQuestion, askAtlasLabel } from '../lib/naturalQuery'
import type { CitationGateStatus } from '../lib/workbench'
import { resolveOriginChip, resolveTierChip } from '../lib/sourceProvenance'
import { TranslatableText } from '../components/TranslatableText'
import { addPin, createInvestigation, describePinTarget, getActiveInvestigationId, getInvestigation, movePin, removePin } from '../lib/workbench'
import { saveTargetTip, saveTargetToast } from '../lib/pinTarget'
import { flashPinToast } from '../lib/pinToast'
import { TranslatedSection } from '../components/TranslatedSection'
import { shouldTranslate as shouldTranslateFree } from '../lib/translatableText'
import { usePageLanguage } from '../lib/pageLanguage'
import { OfflineBanner } from '../components/OfflineBanner'
import { LoadingMoment } from '../components/LoadingMoment'
import { EclipseStrip } from '../components/EclipseStrip'
import { CoverageGapCard } from '../components/CoverageGapCard'
import type { CoverageGap } from '../lib/coverageGaps'
import { decodeEntities, eclipseTier, type EclipseData } from '../lib/attentionEclipse'
// PRINTER'S MARKS — design exploration 2026-08-13, gated behind ?marks= (page
// is byte-identical without the param). Nothing here ships without Pedro.
import {
    buildRegMarkData, buildVoiceMix, PMTrimWrap, RegistrationMark, VoiceMixStrip,
    type MixableReceipt,
} from '../components/PrintersMarks'
import { BriefWorldMarketsBand, BriefCountryMarketsCard } from '../components/BriefMarkets'
import {
    describePositiveColumn,
    describeToneBlend,
    formatSentimentPm1,
    formatTone10,
    measuredSentimentChip,
    toneBridgeNote,
    toneLineageNote,
    toneSaturationTip,
    toneScaleFooter,
} from '../lib/sentimentScale'
import type { SentimentScale } from '../lib/sentimentScale'
import { reconcileSentimentProse } from '../lib/reconcileSentimentProse'
import { useReaderTheme, ReaderThemeToggle } from '../lib/readerTheme'
import {
    publicationThreads,
    resolveEditionServing,
    type DailyPublicationArtifact,
} from '../lib/dailyPublication'
import { weaveVoices } from '../lib/briefVoices'
import {
    excludedAfterBarNote,
    gapConfidenceChip,
    gapEmptyCopy,
    risingEmptyCopy,
    sectionReceipts,
    whyNowParts,
    type GapSection,
    type RisingSection,
} from '../lib/briefSections'
// X4 (2026-08-13, blind college C5) — every stat on this page prints its plain
// companion beside it. The number stays; the words are what make it checkable
// by a reader who does not read statistics.
import { timesPhrase, baselinePhrase, selfVoicePhrase, heatComponentPhrase } from '../lib/statPhrases'
import { buildStaleBanner } from '../lib/staleBanner'
import {
    resolveSourceCount,
    sourceCountTip,
    logUnmeasuredSourceCount,
    UNMEASURED_SOURCES_LABEL,
} from '../lib/briefSourceCount'
import { AtlasMark } from '../components/AtlasMark'
import { useIsMobile } from '../hooks/useIsMobile'
import { bandStartsCollapsed, freshnessSummary, type BriefBand, type FreshnessFacts } from '../lib/briefMobileBands'
import {
    composeCountrySections,
    editionAgeNote,
    fetchCountryEdition,
    type CountryEdition,
    type CountrySection,
} from '../lib/countryEdition'
import { INGEST_NOTE, withBasisTip } from '../lib/ingestBasis'
import '../styles/readerTheme.css'
import './BriefNewspaper.css'

/**
 * How long the front page waits for its own data before showing the error card.
 *
 * Sized above the measured latency of /api/v2/briefing (17.5s and 16.9s on two
 * cold production curls, 2026-08-06), not chosen for feel. The two best-effort
 * fetches below — daily-publication and attention/eclipse — keep their own 12s,
 * because neither blocks the page and both measured under 2s.
 */
const BRIEF_FETCH_TIMEOUT_MS = 25000

/**
 * Mirror of the backend's BRIEFING_TOP_THREADS_LIMIT (briefing.py) — how many
 * ranked threads the front page asks for. Used ONLY to detect truncation: a
 * list served at exactly this size was cut, which is what entitles the page to
 * say the rank continues in the console (W5). If the backend default moves,
 * this becomes conservative (under-claiming), never a false claim.
 */
const BRIEF_STORY_CAP = 10

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
    /** Authoritative state-media flag (signals_v2.is_state_media) — forces the
     *  STATE tier chip so a state outlet is never shown neutral (R3 P0). */
    is_state_media?: boolean | null
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
    // Subject geography (#238): the countries the story is ABOUT, with the
    // status of that derivation. The lead's woven standfirst only makes an
    // own-press claim when this says `verified` — coverage volume is not
    // subjecthood, and a guessed subject would make the claim a lie.
    subject_countries?: string[]
    subject_country_names?: string[]
    subject_geography_status?: string | null
    // 2026-07-30 (gb5-blind-check "cron-safety item 2"): the court tried this
    // row (umbrella lane) and could not ground a verdict — a live TopThread
    // carries this from fetch_threads; a sealed DailyPublicationThread never
    // does (see LabelTrustRow below).
    court_withheld?: boolean
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
        sentiment_source?: string
        nlp_coverage?: number
    }
    // C2: the scale every `sentiment` field here is on, plus the ×10 bridge to
    // the tone panels and the range the fusion can actually serve (wider than
    // the panels' legend). Optional — a cached/older payload degrades to the
    // shipped defaults rather than to a blank scale.
    sentiment_scale?: SentimentScale
    top_countries: { code: string; name: string; signals: number; sentiment: number; sentiment_source?: string; nlp_coverage?: number }[]
    // Same shape the dedicated /api/v2/attention/coverage-gaps endpoint
    // serves (contract coverage-gaps-v0) — reuse lib/coverageGaps' CoverageGap
    // rather than hand-duplicating the shape here (was a stale near-copy: the
    // backend (gap_receipts.py) always sends source/url as present-but-nullable
    // keys, never omits them, matching CoverageGap exactly).
    coverage_gaps?: CoverageGap[]
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
    // The Brief's two measured sections (T3.2). The SAME shapes ride inside the
    // sealed package, so the front page reads one contract either way.
    rising?: RisingSection
    gap?: GapSection
    heat_countries?: HeatCountry[]
    historical_coverage?: {
        source: 'hot' | 'historical_processed'
        sentimentCoverage?: number | null
        topicCoverage?: number | null
        modelVersion?: string | null
    }
    top_sources: { source: string; count: number }[]
    /**
     * C1 — WHICH LANES ANSWERED. The backend has always shipped this
     * (`_fetch_section` appends a segment name on any exception; `top_threads`
     * has its own try/except doing the same), and the page has always thrown it
     * away and rendered the empty array as a measured zero. It is the only thing
     * that separates "the gate judged and found nothing" from "the gate never
     * ran", and the whole of §4.1/§4.7 of the blind judge's read is what happens
     * when a page cannot tell those apart. See lib/briefLanes.ts.
     */
    degraded?: boolean
    degraded_segments?: string[]
}

interface CountryBriefData {
    countryCode: string
    name: string
    totalSignals: number
    sentiment: number
    sources: number
}

/**
 * The "N sources" segment of a row's vitals — the ONE place the Brief prints an
 * outlet count.
 *
 * Cold-user probe 2026-08-12: a row served "116 SIGNALS · 0 sources" with no
 * receipts. The two numbers ride different lineages (see lib/briefSourceCount),
 * so a zero there is the receipt lane failing to answer, never a measured
 * "published by nobody". Zero now renders as the degraded state it is, and the
 * empty upstream field is logged once per thread.
 */
function SourceCountSegment({ row, className, bold }: {
    row: { thread_id?: string; signal_count?: number; source_count?: number | null; evidence_samples?: readonly unknown[] | null }
    className?: string
    bold?: boolean
}) {
    const basis = resolveSourceCount(row)
    if (!basis) return null
    if (basis.kind === 'unmeasured') {
        logUnmeasuredSourceCount(row.thread_id ?? '(unknown thread)', basis)
        return (
            <span className={[className, 'brief-sources-unmeasured'].filter(Boolean).join(' ')} data-tip={sourceCountTip(basis)}>
                {UNMEASURED_SOURCES_LABEL}
            </span>
        )
    }
    return (
        <span className={className} data-tip={sourceCountTip(basis)}>
            {bold ? <b>{basis.count.toLocaleString()}</b> : basis.count.toLocaleString()} sources
        </span>
    )
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
    court_withheld?: boolean
}
function labelReviewChipProps(t: LabelTrustRow) {
    return {
        labelStatus: t.label_status ?? null,
        avgConfidence: typeof t.avg_confidence === 'number' ? t.avg_confidence : null,
        confidenceMeasured: t.confidence_measured === true,
        labelProposed: t.label_proposed ?? null,
        courtWithheld: t.court_withheld === true,
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
    // C3(iii): when the reading was written, so a held one can be LABELED stale
    // instead of silently disappearing between reloads.
    const [insightGeneratedAt, setInsightGeneratedAt] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)
    const [briefError, setBriefError] = useState<string | null>(null)
    const [showingStale, setShowingStale] = useState(false)
    const [countryFilter, setCountryFilter] = useState<string | null>(countryParam)
    const [countryDetail, setCountryDetail] = useState<CountryBriefData | null>(null)
    const [countryThreads, setCountryThreads] = useState<TopThread[] | null>(null)
    const [countryQuery, setCountryQuery] = useState('')
    const [showCountryDropdown, setShowCountryDropdown] = useState(false)
    const countryInputRef = useRef<HTMLInputElement>(null)
    const [now] = useState(new Date())
    const [dailyEdition, setDailyEdition] = useState<DailyPublicationArtifact | null>(null)
    const [eclipse, setEclipse] = useState<EclipseData | null>(null)

    // Task 5 (mobile IA #236): the Brief buried its news under ~1707px of
    // chrome — the freshness box and the markets band are honesty surfaces
    // (staleness truth / "not part of the sealed edition"), not chrome to
    // delete, so they collapse to an expandable one-line summary on a phone
    // instead. `userExpandedBands` tracks ONLY what the reader tapped open —
    // never a useState initializer keyed on isMobile, which would freeze the
    // wrong answer across a resize/orientation change (see bandStartsCollapsed).
    const isMobile = useIsMobile()
    const [userExpandedBands, setUserExpandedBands] = useState<Record<BriefBand, boolean>>({
        freshness: false,
        markets: false,
    })
    const isBandOpen = (band: BriefBand) => !bandStartsCollapsed(band, isMobile) || userExpandedBands[band]
    const expandBand = (band: BriefBand) => setUserExpandedBands(b => ({ ...b, [band]: true }))

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

    // C3(iii) — the analysis stops flickering.
    //
    // The insight is a background LLM call the front page deliberately never
    // waits on. It used to be written to React state ONLY, while the cache was
    // written the instant the brief landed (insight: null). Every reload inside
    // the 4-minute TTL then read that cache, short-circuited before requesting
    // the insight again, and rendered the bare fallback line where the analysis
    // had been — "present on two loads, absent on two others" (judge §4.10).
    //
    // One function, used on BOTH paths (cache hit and fresh fetch): if we do not
    // have a reading for this window, ask for one; when it lands, keep it in the
    // cache so the next load is deterministic. A failure never clears a reading
    // we already hold — a labeled-stale interpretation beats an empty slot.
    const fetchInsight = useCallback((h: number) => {
        const insightCtrl = new AbortController()
        const insightTimer = setTimeout(() => insightCtrl.abort(), 25000)
        fetch(`/api/v2/briefing/insight?hours=${h}`, { signal: insightCtrl.signal })
            .then(r => (r.ok ? r.json() : null))
            .then(d => {
                if (!d?.insight) return
                setInsight(d.insight)
                setInsightGeneratedAt(d.generated_at ?? null)
                updateCachedInsight(h, d.insight, d.generated_at ?? null)
            })
            .catch(() => { /* best-effort; a held reading stays on screen, labeled */ })
            .finally(() => clearTimeout(insightTimer))
    }, [])

    const fetchData = useCallback(async (h: number, options: { force?: boolean } = {}) => {
        setBriefError(null)
        if (options.force) clearBriefingCache()
        const cached = options.force ? null : readBriefingCache(h, { allowStale: true })
        if (cached) {
            setData(cached.briefing as BriefingData)
            setInsight(cached.insight)
            setInsightGeneratedAt(cached.insightGeneratedAt)
            setShowingStale(cached.isStale)
            setLoading(false)
            // A cached payload that never got a reading must ASK for one, or the
            // analysis stays missing for the rest of the TTL for no visible reason.
            if (!cached.insight) fetchInsight(h)
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
            //
            // #236: that timeout was 12s, and production /api/v2/briefing was
            // measured at 17.5s and 16.9s on two cold curls — so on a phone the
            // front page aborted before its own data could arrive and every cold
            // visit rendered the error card. SPA navigation hid it, because the
            // keep-alive shell holds the payload in memory; only a true reload
            // showed it. Raised above the measured latency so the honest failure
            // state is reserved for an actual failure.
            //
            // This is a floor over a symptom, not a fix. The endpoint's latency is
            // the defect and it is tracked separately; when it comes down, this
            // number should come down with it rather than quietly ratcheting up.
            const ctrl = new AbortController()
            const timer = setTimeout(() => ctrl.abort(), BRIEF_FETCH_TIMEOUT_MS)
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
            writeBriefingCache(h, briefing, cached?.insight ?? null, cached?.insightGeneratedAt ?? null)
            setLoading(false)
            // Background, non-blocking: the insight fills the standfirst later.
            fetchInsight(h)
        } catch (e) {
            console.error(e)
            setBriefError('Live briefing unavailable — retry when the data service recovers.')
            setLoading(false)
        }
    }, [fetchInsight])

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
            return
        }

        let cancelled = false

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
            .catch(() => {
                if (cancelled) return
                setCountryDetail(null)
                setCountryThreads(null)
            })

        return () => { cancelled = true }
    }, [countryFilter, hours])

    const [countryEdition, setCountryEdition] = useState<CountryEdition | null>(null)
    const [countryEditionFailed, setCountryEditionFailed] = useState(false)
    // C4: the door's failure state has to be re-openable. Bumping this re-runs
    // the fetch without navigating away or reloading the whole edition.
    const [countryEditionAttempt, setCountryEditionAttempt] = useState(0)
    const retryCountryEdition = () => setCountryEditionAttempt(n => n + 1)

    useEffect(() => {
        if (!countryFilter) { setCountryEdition(null); setCountryEditionFailed(false); return }
        let cancelled = false
        setCountryEdition(null); setCountryEditionFailed(false)
        fetchCountryEdition(countryFilter, hours).then(ed => {
            if (cancelled) return
            if (ed) setCountryEdition(ed); else setCountryEditionFailed(true)
        })
        return () => { cancelled = true }
    }, [countryFilter, hours, countryEditionAttempt])

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

    // N37 (council R4, NIVELES seat): ◇ Save used to append into whatever
    // investigation happened to be active — unrelated stories mixed with no
    // signal. The destination is now stated BEFORE the click (tooltip) and
    // NAMED after it, with a one-click correction. Recomputed per render via
    // wbTick so it tracks the active investigation.
    const pinTarget = (() => { void wbTick; return describePinTarget() })()

    const toggleSaveThread = (t: TopThread, e?: React.MouseEvent) => {
        e?.stopPropagation()
        const target = resolveThreadThemeTarget(t)
        if (!target) return
        const anchorId = `theme-${target.theme}`
        // Snapshot the destination BEFORE the save so the confirmation can name
        // the investigation the pin actually joined (and whether it existed).
        const before = describePinTarget()
        let invId = getActiveInvestigationId()
        if (!invId || !getInvestigation(invId)) invId = createInvestigation(t.label).id
        if (savedIds.has(anchorId)) {
            removePin(invId, anchorId)
            flashPinToast('Removed from investigation')
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
            // Name the destination, and offer the correction the guardrail
            // ("pins from unrelated sessions should not silently mix") asks
            // for: move this one pin into its own investigation. One click,
            // no modal — the friction stays proportional to the mistake.
            const landedIn = invId
            flashPinToast(
                saveTargetToast(before, t.label),
                before.kind === 'existing'
                    ? {
                        label: 'Move to its own',
                        run: () => {
                            const fresh = createInvestigation(t.label)
                            movePin(anchorId, landedIn, fresh.id)
                            setWbTick(x => x + 1)
                        },
                    }
                    : undefined,
            )
        }
        setWbTick(x => x + 1)
    }

    const goToAtlas = (params?: string, sectionName?: string) => {
        // B1 (2026-07-05): per-section engagement — answers whether the front
        // page satisfies at the surface or fails to invite depth (12.5% ramp).
        if (sectionName) track('brief_section_click', { section: sectionName })
        const next = new URLSearchParams(params)
        next.set('entry', sectionName === 'eclipse' ? 'eclipse' : 'brief')
        navigate(`/app?${next.toString()}`)
    }

    // X5 · the bridge out of silence (colegio ciego, USUARIO-PERDIDO):
    //   "I typed 'what is happening in israel,' pressed Enter — nothing, no
    //    message, no 'try a country name.' … Three tries, gave up."
    // He typed a question into a LEXICAL COUNTRY FILTER. Measured on prod:
    // `israel` returns 4 themes / 6 live stories, `what is happening in israel`
    // returns 0/0 — the question words dissolve the match. Atlas already has a
    // lane for that question (the cross-thread story, /app?q=), and this is the
    // only thing that was missing: the door being NAMED at the moment of the
    // miss. No new search machinery — one route into the lane that exists.
    const askAtlas = (raw: string) => {
        const q = raw.trim()
        if (q.length < 2) return
        track('brief_ask_atlas', { q_len: q.length })
        goToAtlas(`q=${encodeURIComponent(q)}`, 'ask-atlas')
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

    // Deep-link into a STORY folder from a row that is not a full thread object
    // (the rising items carry only an id + label). Same door as openThread —
    // resolveThreadThemeTarget → ?theme=, so the console's breadcrumb lands
    // `World ▸ Story` exactly as it does from the desk.
    const openStoryById = (threadId: string, label: string, sectionName: string) => {
        const target = resolveThreadThemeTarget({ thread_id: threadId, label })
        if (!target) return
        track('brief_thread_open', { thread: target.theme })
        trackOnce('first_value_moment', { kind: 'brief_thread' })
        goToAtlas(`theme=${encodeURIComponent(target.theme)}`, sectionName)
    }

    const moodLabel = (s: number) => s > 0.15 ? 'POSITIVE' : s < -0.15 ? 'NEGATIVE' : 'NEUTRAL'
    const moodClass = (s: number) => s > 0.15 ? 'mood-positive' : s < -0.15 ? 'mood-negative' : 'mood-neutral'

    const weekday = now.toLocaleDateString('en-US', { weekday: 'long' })
    const dayLine = now.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
    // Task 5 (mobile IA #236): the weekday-name dateline was one more masthead
    // row on a phone. Same fact (the date), shorter form — CSS swaps which
    // span renders at the mobile breakpoint, no lost information (share-card
    // copy below keeps the full weekday form; that is a modal, not the door).
    const dayLineShort = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

    // SERVING POLICY (T3.3, approved option b): FRESHNESS decides, not status.
    // A sealed edition under 26h old is served whatever it graded, with its
    // degradation rendered as visible labels; the live view is the fallback only
    // when no fresh seal exists (or the artifact is structurally unreadable).
    // The old all-or-nothing gate had, measured, become "never serve the
    // edition" — 25 of 25 consecutive seals graded degraded.
    const serving = resolveEditionServing(dailyEdition, now)
    const servedFromSeal = serving.serve === 'sealed'
    // Staleness truth: what edition is served, how old, and when the next seal is.
    const staleBanner = dailyEdition
        ? buildStaleBanner({
            sealedAt: dailyEdition.sealed_at ?? dailyEdition.completion?.generated_at as string | null ?? null,
            editionDate: dailyEdition.edition_date ?? null,
            servedFromSeal,
            reasonCodes: serving.reasonCodes,
            now,
            // N10: honest next-attempt from the backend's schedule truth
            // (02:30 constant remains the no-schedule fallback inside).
            nextAttemptAt: dailyEdition.seal_schedule?.next_attempt_at ?? null,
            attemptWindowOpen: dailyEdition.seal_schedule?.attempt_window_open ?? false,
            nextSealLocal: dailyEdition.seal_schedule?.next_attempt_local,
        })
        : null
    const allThreads = serving.serve === 'sealed' ? publicationThreads(dailyEdition) : (data?.top_threads ?? [])

    // PRINTER'S MARKS (shipped 2026-08-13, Pedro-approved — exploration doc
    // docs/superpowers/specs/2026-08-13-printers-marks-exploration.md). Every
    // mark renders data this block already computed — seal moment, grade,
    // degradation, receipts — never ornament. `?marks=off` is the kill switch.
    const marksOff = searchParams.get('marks') === 'off'
    const regMark = !marksOff
        ? buildRegMarkData(dailyEdition, serving, {
            ageLabel: staleBanner?.age ?? null,
            liveReason: staleBanner?.why ?? null,
            nextSeal: staleBanner?.nextAttempt ?? null,
        })
        : null
    const voiceMix = !marksOff
        ? buildVoiceMix(
            (allThreads as Array<{ evidence_samples?: MixableReceipt[] }>).flatMap(t => t.evidence_samples ?? []),
            servedFromSeal ? 'sealed' : 'live',
        )
        : null

    // Council Phase 1 (+ R2 N2, lead-eligibility v2): on the LIVE brief the front
    // page may only present a thread as an assembled story (label-as-fact: lead
    // or desk card) when we trust its label — measured confidence >= floor AND
    // the Label Court STAMPED it (entailed/partial). An unstamped (null) label
    // can no longer lead: new topics promote and serve before the court cycle,
    // so null was exactly the fold hole (31/37 served unstamped incl all leads).
    // Stamps normally land within ~30 min (court rides the classifier cron),
    // but the reader-facing copy no longer promises that timing (2026-07-27)
    // — the cron isn't always live, so a fixed ETA can go stale for days.
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
    const gateActive = !countryFilter && !servedFromSeal
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
    const preferredLead = servedFromSeal
        ? allThreads.find(thread => thread.edition_role === 'lead') ?? null
        : null
    const leadThread = countryFilter ? null : (preferredLead ?? liveLead?.lead ?? eligiblePool[0] ?? null)
    // Honest empty-lead (live path only): threads exist but none cleared the bar.
    const leadUnavailable = gateActive && (liveLead?.leadUnavailable ?? false)
    // Timing vs quality: the empty lead is "awaiting verification" when at least
    // one thread would lead once the 30-min court cycle stamps it.
    const leadAwaiting = gateActive && (liveLead?.awaitingVerification ?? false)

    const restThreads = leadThread
        ? eligiblePool.filter(t => t.thread_id !== leadThread.thread_id)
        : eligiblePool
    // Edition sections: culture/sport/lifestyle threads get their OWN section
    // (nothing dropped); the ranked lead stays the lead regardless of lane.
    const { world: worldRest, culture: cultureRest } = splitEditionThreads(restThreads)
    const worldCards = servedFromSeal ? worldRest : worldRest.slice(0, 8)
    const cultureCards = servedFromSeal ? cultureRest : cultureRest.slice(0, 6)

    // ---- W5: front page ↔ console coherence -----------------------------------
    // The judge opened the console and found "DR Congo Ebola Outbreak" and
    // "SpaceX Rocket Moon Crash" — stories that appear nowhere here — and
    // concluded the two views disagree about what today's stories are.
    //
    // MEASURED against prod: they do not. Both read the SAME fetch_threads →
    // rank_threads lane; the Brief asks it for BRIEFING_TOP_THREADS_LIMIT rows
    // and the console asks for more. Every Brief thread was inside the console's
    // rank. The order differs only because rank_threads min-max normalises
    // across the set it was handed.
    //
    // We do NOT force-unify them — a frozen sealed edition and a live rank are
    // different measurements on purpose. We make the relationship legible: this
    // page names its basis and, when its list came back AT the cap (which
    // proves it was cut), says the rank continues in the console.
    const editionScope = frontPageScope({
        servedFromSeal,
        shown: servedFromSeal ? allThreads.length : liveThreads.length,
        // A sealed edition is an assembled artifact, not a capped slice — pass
        // no cap so it never claims a truncation it did not suffer.
        cap: servedFromSeal ? 0 : BRIEF_STORY_CAP,
    })
    const censusRows: CensusRow[] = data?.category_counts ?? []
    // The second half of the same root cause: the category index at the foot of
    // the page counts the whole active-topic census while the desks above carry
    // only ranked front-page stories — so "Culture is honestly empty" and
    // "Sports 1,398" sat in one viewport reading as a contradiction.
    const cultureCensusNote = deskCensusNote({
        rows: censusRows,
        family: 'culture',
        deskName: 'this desk',
    })

    const heatStrip = (data?.heat_countries ?? []).slice(0, 4)
    const coverageGaps = data?.coverage_gaps ?? []
    const maxGapRaw = Math.max(1, ...coverageGaps.map(g => g.raw_signals))

    // ---- C1: which lanes answered (lib/briefLanes.ts) --------------------------
    // `briefUnavailable` covers the case the payload cannot report on itself:
    // there IS no payload, so every count on the page would be invented.
    //
    // Deliberately NOT keyed on `briefError`. A failed revalidation over a
    // cached payload is a staleness fact, not a lane fact: the cached brief
    // carries its own degraded_segments from the moment it was fetched, and the
    // stale banner already tells the reader which moment that is. Blanking its
    // tiles to "—" while the desks below render that same payload's stories
    // would be a second inconsistency, not a repair of the first.
    //
    // A sealed edition is its own assembled artifact — its emptiness is a real
    // editorial verdict frozen at seal time, not a live lane failure.
    const laneEvidence: LaneEvidence = {
        degradedSegments: servedFromSeal ? [] : (data?.degraded_segments ?? []),
        briefUnavailable: !servedFromSeal && !data,
    }
    const storiesUnanswered = laneState('stories', laneEvidence) === 'unanswered'
    // The retry a reader needs when a lane died: go past the cache, ask again.
    const retryLanes = () => { void fetchData(hours, { force: true }) }

    // Honest standfirst: AI insight when the service produced one; otherwise a
    // single factual line. No template essay variants — an editorial that
    // pretends to judge is worse than no editorial (surfaces review §1.4).
    const displayInsight = servedFromSeal ? null : insight
    // C3(iii): a held reading is LABELED with the hour it was written rather
    // than dropped — the empty slot is what read as random flicker.
    const analysisAge = insightStaleness(insightGeneratedAt, now)
    const standfirstFallback = servedFromSeal && dailyEdition
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
    const dailyEditionArticles = dailyEdition?.package?.article_enrichment?.articles ?? null
    const editionYield = dailyEdition?.package?.article_enrichment?.yield ?? null
    const coverageCheck = dailyEdition?.package?.coverage_check ?? null

    // ---- the coverage diary's two measured sections (T3.2 → T3.3) ----
    //
    // ONE contract, two carriers: the sealed package holds the copies computed
    // inside the seal, the live briefing holds today's. Serve the sealed ones
    // when the sealed edition is what the page is built from, so the sections and
    // the stories around them describe the same moment; a seal built before T3.2
    // carries neither, and falls back to the live copies rather than to silence.
    const risingSection = (servedFromSeal
        ? (dailyEdition?.package?.rising as RisingSection | undefined) ?? data?.rising
        : data?.rising) ?? null
    const gapSection = (servedFromSeal
        ? (dailyEdition?.package?.gap as GapSection | undefined) ?? data?.gap
        : data?.gap) ?? null
    const risingItems = risingSection?.items ?? []
    const risingEmpty = risingEmptyCopy(risingSection)
    const risingExcluded = excludedAfterBarNote(risingSection?.excluded_after_bar)
    const gapEmpty = gapEmptyCopy(gapSection)
    const gapCountry = gapSection?.country ?? null
    const gapMeasured = gapSection?.measured ?? null
    const gapConfidence = gapConfidenceChip(gapSection)
    const gapReceipts = sectionReceipts(gapSection?.receipts)

    // THE LEAD'S VOICES, as prose (spec §3b.1). Every clause is measured or
    // absent — see lib/briefVoices.ts. The subject-country clause is gated on
    // VERIFIED subject geography: coverage volume is not subjecthood, and an
    // own-press sentence built on a guessed subject would be a false claim.
    const leadSourceBasis = leadThread ? resolveSourceCount(leadThread) : null
    const leadSubjectVerified = (leadThread as TopThread | null)?.subject_geography_status === 'verified'
    const leadVoices = leadThread
        ? weaveVoices({
            outlets: leadSourceBasis?.kind === 'measured' ? leadSourceBasis.count : null,
            receipts: leadThread.evidence_samples ?? [],
            subjectCountries: leadSubjectVerified ? (leadThread as TopThread).subject_countries : null,
            subjectCountryNames: leadSubjectVerified ? (leadThread as TopThread).subject_country_names : null,
            // V2's tension guard already attributes the divergence backend-side;
            // the standfirst re-states it, the coverage-check block below keeps
            // both verbatim quotes.
            tension: coverageCheck?.findings?.find(f => f.kind === 'tension') ?? null,
        })
        : null

    // Collapsed-band summary for the freshness box (Task 5, mobile IA #236).
    // Derived from data the full markup already renders (staleBanner/editionYield
    // above) — no new fetch. The freshnessSummary() line stays exactly the honest
    // "sealed <age> · full text X/Y" fact; the degraded-lane reason and the next
    // seal attempt are appended when present so collapsing never drops a fact the
    // expanded box would have shown (the freshness box is an honesty rail, not
    // chrome — never a bare label).
    //
    // Follow-up review: this used to recompute the age itself
    // (Math.floor(ms / 3600000)), which printed "sealed 0h ago" at 20 minutes
    // and "sealed 87h ago" at 3 days — a second, cruder phrasing of the exact
    // fact staleBanner.age already states correctly ("sealed just now" /
    // "sealed 3 days ago") in the expanded box below. Reuse that string
    // (stripping its own "sealed " prefix, since freshnessSummary adds it
    // back) instead of a parallel computation, so the two never diverge.
    const freshnessFacts: FreshnessFacts = (() => {
        const sealedAge = staleBanner?.age
            ? staleBanner.age.replace(/^sealed\s+/, '')
            : null
        const hasYield = !!editionYield && editionYield.attempted > 0
        return {
            sealedAge,
            fullTextOk: hasYield ? editionYield!.ok : null,
            fullTextTotal: hasYield ? editionYield!.attempted : null,
        }
    })()
    const freshnessCollapsedLine = [
        freshnessSummary(freshnessFacts),
        staleBanner && staleBanner.tone === 'stale' ? staleBanner.why : null,
        // T3.3: a degraded edition is now PUBLISHED, so how it is incomplete has
        // to travel with it — including into the collapsed phone line, which is
        // all a mobile reader sees until they tap.
        ...serving.degradation,
        staleBanner?.nextAttempt ?? null,
    ].filter(Boolean).join(' · ')

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
    const globalLiveArticleStates = useArticleStates(liveReceiptUrls)

    // Country excerpt sources: warm map from the endpoint + a live poll on the
    // still-pending receipt URLs (progressive fill — same machinery as the seal).
    const countryEditionArticles = countryEdition?.article_enrichment?.articles ?? null
    const countryPendingUrls = useMemo(
        () => countryEdition?.article_enrichment?.pending_urls ?? [],
        [countryEdition],
    )
    useEffect(() => { enqueueUrls(countryPendingUrls) }, [countryPendingUrls])
    const countryLiveStates = useArticleStates(countryPendingUrls)

    // renderReceipt reads these two names; select country sources when a country
    // is open (the two views are mutually exclusive via countryFilter).
    const editionArticles = countryFilter ? countryEditionArticles : dailyEditionArticles
    const liveArticleStates = countryFilter ? countryLiveStates : globalLiveArticleStates

    // Page language (translation target, Settings → Page Language). Only used
    // here to GATE the section Translate-all control — the translatable
    // children subscribe to the store on their own.
    const pageLang = usePageLanguage()

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
                    const tc = resolveTierChip(ev.source, ev.source_origin_country, ev.is_state_media)
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
                {/* X5 (estudiante): the receipts already carry outlet + original
                    language + date + link — this copies that row as ONE citable
                    line. Formats what is shown; measures nothing new. */}
                <CopyCitationButton
                    receipt={{
                        headline,
                        source: ev.source,
                        url: ev.url,
                        sourceLang: ev.source_lang,
                        publishedDate: ev.timestamp,
                    }}
                />
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
        // source). A READY seed (sealed excerpt) wins; otherwise the live poll
        // fills the gap. The seed can arrive `pending` (the country edition's
        // endpoint never blocks, so its seed carries not-yet-fetched rows) — a
        // plain `seed ?? live` would short-circuit on that truthy pending object
        // and the poll's later `ok` would never render. Clamped; link = full read.
        const seed = ev.url ? (editionArticles?.[ev.url] ?? null) : null
        const live = ev.url ? (liveArticleStates.get(ev.url) ?? null) : null
        const enriched = seed?.status === 'ok' ? seed : (live ?? seed)
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

    // Gate for the section Translate-all control: does this thread block hold
    // ANYTHING the translate lanes could act on (label, receipt headline, or a
    // fetched excerpt)? All-native sections render no dead button. Checks the
    // full evidence list, not the rendered slice — a cheap over-approximation.
    const threadHasTranslatable = (t: { label: string; evidence_samples?: ThreadEvidence[] | null }): boolean => {
        if (shouldTranslateFree(decodeEntities(t.label), pageLang)) return true
        for (const ev of t.evidence_samples ?? []) {
            if (shouldTranslateSignal(ev.source_lang, decodeEntities(ev.headline), pageLang)) return true
            if (ev.url) {
                const seed = editionArticles?.[ev.url] ?? null
                const live = liveArticleStates.get(ev.url) ?? null
                const enriched = seed?.status === 'ok' ? seed : (live ?? seed)
                if (enriched?.status === 'ok' && enriched.excerpt
                    && shouldTranslateFree(enriched.excerpt, pageLang)) return true
            }
        }
        return false
    }

    const renderSaveChip = (t: TopThread) => {
        const theme = resolveThreadThemeTarget(t)?.theme
        const saved = savedIds.has(`theme-${theme}`)
        return (
            <span
                role="button"
                tabIndex={0}
                className={`brief-save-btn ${saved ? 'saved' : ''}`}
                // N37: the destination is legible BEFORE the click.
                data-tip={saved ? 'Remove from investigation' : saveTargetTip(pinTarget)}
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
            <TranslatedSection key={t.thread_id} active={threadHasTranslatable(t)}>
                {(translateControl) => (
            <article className={`brief-card${opts?.wide ? ' wide' : ''}`}>
                <div className="reader-kicker">
                    <span>{category || 'Story'}</span>
                    <span className="cat">{t.signal_count.toLocaleString()} signals</span>
                </div>
                <h3 className="brief-card-headline">
                    <button className="brief-headline-btn" onClick={() => openThread(t, opts?.country)}>
                        <TranslatableText text={decodeEntities(t.label)} />
                    </button>
                    <LabelReviewChip {...labelReviewChipProps(t)} />
                </h3>
                {translateControl && <div className="brief-translate-row">{translateControl}</div>}
                <div className="brief-vitals-line">
                    <SourceCountSegment row={t} bold />
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
                        <button className="brief-theme-link" onClick={() => openThread(t, opts?.country)}>Open story →</button>
                    </span>
                </div>
            </article>
                )}
            </TranslatedSection>
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
        // N14 (council R4): the desk row prints the served BAND, never the raw
        // number — top_threads buckets correctly, the render was ignoring it.
        const confBucket = resolveConfidenceBucket({ band: t.confidence ?? null, avgConfidence: conf })
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
            <TranslatedSection key={t.thread_id} active={threadHasTranslatable(t)}>
                {(translateControl) => (
            <div className="brief-unassembled-cell">
                <div className="brief-unassembled-head">
                    <span
                        className="brief-unassembled-label"
                        data-tip={reason === 'awaiting-verification'
                            ? 'This cluster is queued for its label check — it can front the page once verified. Meanwhile, read the raw sources below.'
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
                {translateControl && <div className="brief-translate-row">{translateControl}</div>}
                {t.label_proposed && (
                    <div className="brief-unassembled-proposed">
                        <span className="lab">receipt-derived</span>
                        <span>{decodeEntities(t.label_proposed)}</span>
                    </div>
                )}
                <div className="brief-unassembled-meta">
                    {confBucket.bucket != null && (
                        <span data-tip={confidenceBucketTip(confBucket.bucket, confBucket.source)}>
                            {confidenceBucketLabel(confBucket.bucket)}
                        </span>
                    )}
                    <span>{t.signal_count.toLocaleString()} raw signals</span>
                    <SourceCountSegment row={t} />
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
                )}
            </TranslatedSection>
        )
    }

    const renderCountryGaps = (gaps: CountrySection<TopThread>['gaps']) => (
        <ul className="brief-coverage-gaps">
            {gaps.map(g => (
                <li key={g.slug} className="brief-coverage-gap">
                    <span className="brief-gap-label">{g.label}</span>
                    {/* The gap is Atlas's gate on Atlas's ingest — not a claim
                        that the country's press left the subject alone (X1). */}
                    <span className="brief-gap-meta" data-tip={INGEST_NOTE}>
                        {g.raw_signals} signals ingested · 0 cleared the gate
                    </span>
                </li>
            ))}
        </ul>
    )

    const COUNTRY_SECTION_META: Record<
        CountrySection<TopThread>['kind'],
        { title: string; kicker: string }
    > = {
        country_today: { title: 'Today', kicker: 'The country now' },
        under_radar: { title: 'Under the Radar', kicker: 'Domestic signal, not yet surfacing' },
        culture_sport_life: { title: 'Culture, Sport & Life', kicker: 'Where the rest of us live' },
    }

    const renderCountrySection = (
        sec: CountrySection<TopThread>,
        country: string,
    ) => {
        const meta = COUNTRY_SECTION_META[sec.kind]
        return (
            <section key={sec.kind} className={`brief-country-section brief-country-section-${sec.kind}`}>
                <span className="reader-section-kicker">{meta.kicker}</span>
                <h3 className="brief-section-title">{meta.title}</h3>
                {!sec.present ? (
                    <p className="brief-empty-note">{sec.empty_reason}</p>
                ) : sec.kind === 'under_radar' ? (
                    renderCountryGaps(sec.gaps)
                ) : (
                    <div className="brief-cards">
                        {sec.threads.map((t, i) => renderThreadCard(t, { country, wide: i === 0 }))}
                    </div>
                )}
            </section>
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
                data-tip="Clusters Atlas is tracking but has not assembled into a trustworthy story: their machine label is below the front-page confidence bar, the Label Court could not entail it against its own receipts, or it is still awaiting its label check. The receipts are real. Nothing is deleted."
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
                        <p className="reader-eyebrow"><AtlasMark size={13} />The Daily Instrument · Global Edition</p>
                        <h1 className="reader-wordmark">ATLAS<span className="dot">.</span></h1>
                        <p className="reader-tagline">Narrative intelligence — measured from coverage, not editorialized.</p>
                    </div>
                    <div className="brief-masthead-right">
                        {regMark && <RegistrationMark data={regMark} />}
                        <div className="reader-dateline">
                            <span className="brief-dateline-full">{weekday}, <b>{dayLine}</b></span>
                            <span className="brief-dateline-short"><b>{dayLineShort}</b></span>
                        </div>
                        <span
                            className="reader-chip"
                            data-tip="The Brief is the day's edition — always the last 24 hours. For other time windows, open the console."
                        >
                            <span className="live" />Measured · Last 24 hours
                        </span>
                        {eclipse?.eclipse && eclipseTier(eclipse) === 'total' && (
                            <button
                                className="brief-eclipse-mark"
                                onClick={() => goToAtlas(undefined, 'eclipse')}
                                data-tip="A total attention eclipse is active — enter the console"
                                aria-label="Enter the eclipse"
                            >◑</button>
                        )}
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

                        {voiceMix && <VoiceMixStrip mix={voiceMix} />}

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
                            !isBandOpen('freshness') ? (
                                <button
                                    type="button"
                                    className="brief-band-summary"
                                    aria-label="Daily edition freshness — tap to expand"
                                    onClick={() => expandBand('freshness')}
                                >
                                    {freshnessCollapsedLine} ▸
                                </button>
                            ) : (
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
                                    {/* T3.3 serving policy: the edition is served
                                        even when it graded degraded, so every way
                                        it is incomplete is stated ON it — the
                                        degradation is a label, never a silent
                                        fallback to a different newspaper. */}
                                    {serving.degradation.length > 0 && (
                                        <span
                                            className="brief-publication-degraded"
                                            data-tip="This edition sealed incomplete and is served anyway, labelled. Nothing here was invented to fill the gaps."
                                        >
                                            {serving.degradation.map(label => (
                                                <span key={label} className="brief-degrade-chip">{label}</span>
                                            ))}
                                        </span>
                                    )}
                                </section>
                            )
                        )}

                        {servedFromSeal && dailyEdition && (
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
                                {/* Task 5 follow-up (#236): the "sub" caption below states this
                                    tile's scale (±1) — the ONLY other place on the page that
                                    restates it is measuredSentimentChip, which renders only when
                                    the AI insight is present (this project's insight lane has a
                                    documented multi-day-outage history). Hiding "sub" on mobile
                                    (below) would leave a bare signed number with no scale
                                    anywhere on the page, breaking sentimentScale.ts's own rule
                                    ("every printed value states its scale"). The mobile-only
                                    label swap keeps that promise without the vertical cost of
                                    keeping "sub" visible — desktop's RENDERED label is unchanged
                                    (the .k rule itself is never edited by mobile CSS; its child
                                    is two spans now, one per viewport, not a bare text node). */}
                                <div className="k">
                                    <span className="brief-vital-k-full">Avg sentiment</span>
                                    {/* C2: mobile hides ".sub", which is where the desktop
                                        bridge lives — so the short label carries the
                                        conversion too, or the phone shows −0.49 above panels
                                        reading −10.0 with nothing linking them. */}
                                    <span className="brief-vital-k-mobile">Sentiment · ±1 · ×10 below</span>
                                </div>
                                <div className="v">
                                    {formatSentimentPm1(data.stats.avg_sentiment)}
                                    <SentimentSourceBadge
                                        source={data.stats.sentiment_source}
                                        coverage={data.stats.nlp_coverage}
                                    />
                                </div>
                                {/* C2 (blind judge §4.8): this tile and the tone panels below
                                    print the SAME fused aggregate — the strip on ±1, the panels
                                    at ×10 — and the page offered no bridge, so "−0.49" and
                                    "−10.0" read as two unrelated measurements. State the
                                    conversion with this window's own number. */}
                                <div className="sub">{toneBridgeNote(data.stats.avg_sentiment, data.sentiment_scale)}</div>
                            </div>
                            {/* C1 — A TILE IS THE LOUDEST PLACE TO INVENT A NUMBER. It carries
                                no prose to qualify itself, so "Tracked stories 0" and "Coverage
                                gaps 0" read as measured findings even on a window where neither
                                lane ran (judge §4.1/§4.7: the second contradicted the section
                                right below it, which admitted the lane never answered). Both now
                                print an em dash with the reason in the tip when their lane is
                                down — unknown, never zero. */}
                            {(() => {
                                const reading = instrumentReading(
                                    allThreads.length, 'stories', laneEvidence,
                                    'Ranked stories served this window.',
                                )
                                return (
                                    <div className="brief-vital">
                                        <div className="k">Tracked stories</div>
                                        <div className={`v${reading.unmeasured ? ' brief-vital-unmeasured' : ''}`} data-tip={reading.tip}>
                                            {reading.value}
                                        </div>
                                        <div className="sub">
                                            {reading.unmeasured ? 'unknown — the story lane did not answer' : 'ranked stories served this window'}
                                        </div>
                                    </div>
                                )
                            })()}
                            {(() => {
                                const reading = instrumentReading(
                                    coverageGaps.length, 'gaps', laneEvidence,
                                    'Categories with attention but zero verified rows.',
                                )
                                return (
                                    <div className="brief-vital">
                                        {/* Same rationale as the sentiment tile above: "Coverage gaps"
                                            alone is cryptic and its definition ("categories with
                                            attention but zero verified rows") is only reachable via the
                                            Under-the-Radar tab. */}
                                        <div className="k">
                                            <span className="brief-vital-k-full">Coverage gaps</span>
                                            <span className="brief-vital-k-mobile">Gaps · unverified</span>
                                        </div>
                                        <div className={`v${reading.unmeasured ? ' brief-vital-unmeasured' : ''}`} data-tip={reading.tip}>
                                            {reading.value}
                                        </div>
                                        <div className="sub">
                                            {reading.unmeasured
                                                ? 'unknown — the coverage-gap lane did not answer'
                                                : 'categories with attention but zero verified rows'}
                                        </div>
                                    </div>
                                )
                            })()}
                        </section>

                        {/* ============ WORLD MARKETS BAND (full-width franja, top) ============
                            Global bellwethers — NOT the country's data, so it never swaps on
                            country focus; the country's own instruments live in the country
                            edition below (BriefCountryMarketsCard). Collapses to a one-line
                            summary on mobile (Task 5). Follow-up review: "descriptive" alone
                            only let the reader INFER not-sealed (the instrument strip above is
                            equally "descriptive" and IS part of the measured edition) — the
                            honesty rule here is the disclaimer may never be hidden OR weakened,
                            so the line now STATES it, echoing BriefMarkets.tsx's own "Live
                            overlay — not part of the sealed edition" rather than paraphrasing
                            around it (same fix already applied to the freshness band below). */}
                        {!isBandOpen('markets') ? (
                            <button
                                type="button"
                                className="brief-band-summary"
                                aria-label="World markets — live overlay, not part of the sealed edition — tap to expand"
                                onClick={() => expandBand('markets')}
                            >
                                World markets · live overlay, not sealed ▸
                            </button>
                        ) : (
                            <BriefWorldMarketsBand />
                        )}

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
                                                // X5: Enter used to do literally nothing. It now
                                                // carries a QUESTION to the lane that can read it;
                                                // a country-shaped query still belongs to the list
                                                // below, so Enter stays inert for those.
                                                onKeyDown={e => {
                                                    if (e.key !== 'Enter') return
                                                    if (suggestions.length > 0 || !looksLikeNaturalQuestion(countryQuery)) return
                                                    e.preventDefault()
                                                    askAtlas(countryQuery)
                                                }}
                                            />
                                            {showCountryDropdown && suggestions.length > 0 && (
                                                <div className="brief-country-dropdown">
                                                    {/* C4: this door does NOT eject — it opens the
                                                        country's edition inside this newspaper. The
                                                        judge could not tell which of the page's two
                                                        country doors did which, so each one says. */}
                                                    {suggestions.slice(0, 10).map(c => {
                                                        const name = resolveCountryName(c.code, c.name)
                                                        return (
                                                            <button
                                                                key={c.code}
                                                                className={`brief-country-option${c.signals === 0 ? ' empty' : ''}`}
                                                                onMouseDown={e => e.preventDefault()}
                                                                onClick={() => selectCountry(c.code)}
                                                                data-tip={`Opens ${name}'s edition inside this newspaper — the chip beside "Country:" clears it.`}
                                                                aria-label={`Open ${name}'s edition in this newspaper`}
                                                            >
                                                                <span><Flag code={c.code} /> {name}</span>
                                                                <span className="brief-country-option-count">{c.signals > 0 ? c.signals.toLocaleString() : 'not in top countries'}</span>
                                                            </button>
                                                        )
                                                    })}
                                                </div>
                                            )}
                                            {/* X5: a zero-match lexical box must SAY so, and when
                                                what was typed reads like a question it must name
                                                the lane that can answer it. Silence was the whole
                                                defect — "no message, no 'try a country name'". */}
                                            {showCountryDropdown && q.length > 0 && suggestions.length === 0 && (
                                                <div className="brief-country-dropdown brief-country-dropdown--empty">
                                                    <p className="brief-country-empty">
                                                        No country matches “{countryQuery.trim()}”.
                                                    </p>
                                                    {looksLikeNaturalQuestion(countryQuery) ? (
                                                        <button
                                                            className="brief-country-ask"
                                                            onMouseDown={e => e.preventDefault()}
                                                            onClick={() => askAtlas(countryQuery)}
                                                            data-tip="Reads your question across the live stories — matching threads, who says what, and where coverage is missing."
                                                            aria-label={`Ask Atlas: ${countryQuery.trim()}`}
                                                        >
                                                            <span className="brief-country-ask-label">{askAtlasLabel(countryQuery)}</span>
                                                            <span className="brief-country-ask-hint">reads it across the live stories →</span>
                                                        </button>
                                                    ) : (
                                                        <p className="brief-country-empty-hint">
                                                            This box searches country names. Try one — or ask a full question and Atlas will read it across the stories.
                                                        </p>
                                                    )}
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
                            <PMTrimWrap
                                mode={!regMark ? 'off' : (regMark.state === 'live' ? 'live' : 'frame')}
                                sealTime={regMark?.sealTime ?? null}
                                gradeLine={regMark
                                    ? (regMark.state === 'full'
                                        ? 'FULL'
                                        : `PARTIAL ${regMark.answered ?? '·'}/${regMark.total ?? '·'}`)
                                    : null}
                                reason={regMark?.reason ?? null}
                                nextSeal={regMark?.nextSeal ?? null}
                            >
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
                                        <TranslatedSection active={threadHasTranslatable(leadThread)}>
                                            {(translateControl) => (
                                        <article className="brief-lead">
                                            <div className="reader-kicker">
                                                <span>Lead{(leadThread.category ?? leadThread.parent_domain) ? ` · ${leadThread.category ?? leadThread.parent_domain}` : ''}</span>
                                                <span className="cat" data-tip="Top-ranked story in this window (movement, volume and coherence). Sample evidence headlines shown when available.">
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
                                            {translateControl && <div className="brief-translate-row">{translateControl}</div>}
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
                                                <SourceCountSegment row={leadThread} className="reader-pill" />
                                            </div>
                                            {/* THE VOICES, AS PROSE (spec §3b.1) — who is telling
                                                this story and who is not. The absorbed voice-bar
                                                design lives here as a sentence rather than a chart;
                                                every clause is measured or absent (lib/briefVoices),
                                                and the basis line names which lineage each number
                                                came from. */}
                                            {leadVoices && (
                                                <p className="brief-lead-voices">
                                                    <span className="lab">Who is telling it</span>
                                                    <span className="brief-voices-sentence">{leadVoices.sentence}</span>
                                                    <span className="brief-voices-basis">{leadVoices.basis}</span>
                                                </p>
                                            )}
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
                                                    <button className="brief-theme-link" onClick={() => openThread(leadThread)}>Open story →</button>
                                                </span>
                                            </div>
                                        </article>
                                            )}
                                        </TranslatedSection>
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
                                                    have not yet been checked against their own receipts. Rather
                                                    than lead with an unverified label, see the unassembled desk
                                                    below for the raw receipts.
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
                                        // C1 — THE LAST N23 DEN. This slot printed a GATE VERDICT
                                        // ("no story cleared…") from an empty array, whatever
                                        // emptied it. On the day the judge read the page, the
                                        // story lane was down and the console one click away was
                                        // full of ranked stories: the honesty voice narrating an
                                        // outage as an editorial finding. Which sentence appears
                                        // is now decided by whether the lane ANSWERED, and the
                                        // failure branch offers the only useful action — ask again.
                                        <article className={`brief-lead brief-lead-empty${storiesUnanswered ? ' brief-lead-unanswered' : ''}`}>
                                            <div className="reader-kicker">
                                                <span>Lead</span>
                                                {storiesUnanswered && <span className="cat">lane did not answer</span>}
                                            </div>
                                            <p>{deskEmptyCopy('world', laneState('stories', laneEvidence))}</p>
                                            {storiesUnanswered && (
                                                <button className="brief-theme-link" onClick={retryLanes}>
                                                    Ask the story lane again ↻
                                                </button>
                                            )}
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
                                                        {ANALYSIS_LABEL}
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
                                                    {/* C3(i)+(ii) — the page's ONLY interpretation, saying so.
                                                        The judge read this paragraph to the end, believed it was
                                                        the one claim about the world on the page, and then found
                                                        its numbers apparently contradicting the tone table four
                                                        inches below. Both were true of DIFFERENT populations on
                                                        DIFFERENT scales; nothing said so. This line is computed by
                                                        the surface, not promised by the model, so it stays true
                                                        when the prose is stale, drifts, or changes provider. */}
                                                    <p className="brief-analysis-nature">
                                                        {ANALYSIS_NATURE} <span className="brief-analysis-basis">{ANALYSIS_BASIS}</span>
                                                    </p>
                                                    {analysisAge.note && (
                                                        <p className="brief-analysis-stale">{analysisAge.note}</p>
                                                    )}
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
                                                        // The verdict is over the handful of lead
                                                        // articles Atlas fetched and read, never
                                                        // over "the outlets" at large (X1).
                                                        f.kind === 'tension' ? '⚠ the outlets read here diverge'
                                                            : f.kind === 'shared_source' ? '⊘ same wire source'
                                                            : '✓ the outlets read here agree'
                                                    }</span>
                                                    <p className="brief-cc-note">{f.note}</p>
                                                    <blockquote dir="auto">“{f.a.quote}”{f.a.outlet ? <span className="brief-cc-src"> — {f.a.outlet}</span> : null}</blockquote>
                                                    <blockquote dir="auto">“{f.b.quote}”{f.b.outlet ? <span className="brief-cc-src"> — {f.b.outlet}</span> : null}</blockquote>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {/* ============ EL VACÍO · THE GAP ============
                                        The day's best blindspot, written as a story (spec §3b.2):
                                        the country whose coverage diverged furthest from its own
                                        press. Bar and prose are the backend's (brief-gap-v1) —
                                        this renders them, adds nothing, and when the day has no
                                        finding it SAYS which of the two silences it is
                                        (G-VACÍO-HONESTO). */}
                                    {gapSection && (
                                        <section className="brief-gap-section" aria-label="The Gap — today's measured blindspot">
                                            {/* X1 (2026-08-13): "The coverage nobody wrote"
                                                asserted a fact about the world from a hole
                                                in Atlas's feed set. What is measurable is
                                                the coverage Atlas did not see. */}
                                            <span className="reader-section-kicker brief-sub-kicker" data-tip={INGEST_NOTE}>The coverage Atlas did not see</span>
                                            <h3 className="brief-section-subtitle">The Gap</h3>
                                            {gapCountry && gapMeasured ? (
                                                <>
                                                    <div className="reader-kicker">
                                                        <span>
                                                            <Flag code={gapCountry.code} /> {gapCountry.name}
                                                        </span>
                                                        {gapConfidence && (
                                                            <span className="cat brief-gap-confidence" data-tip={gapConfidence.tip}>
                                                                {gapConfidence.label}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="brief-gap-prose">{gapSection.prose}</p>
                                                    {/* Load-bearing honesty: the caveat is served
                                                        verbatim, never trimmed or paraphrased. */}
                                                    {gapSection.caveat && (
                                                        <p className="brief-gap-caveat">{gapSection.caveat}</p>
                                                    )}
                                                    <div className="brief-metarow">
                                                        {/* X4 (blind college C5): every pill in this row
                                                            was a bare statistic. Each keeps its number and
                                                            gains the plain reading beside it — the pills
                                                            are the reader's only summary when the prose
                                                            above scrolls past. */}
                                                        {typeof gapMeasured.multiplier === 'number' && (
                                                            <span
                                                                className="reader-pill measured"
                                                                data-tip="Today's volume against the mean of this country's other retained days — its OWN baseline, not the field's."
                                                            >
                                                                {gapMeasured.multiplier}×
                                                                <span className="reader-pill-plain">
                                                                    {timesPhrase(gapMeasured.multiplier, { of: 'its usual day' })
                                                                        ?? 'against its own usual day'}
                                                                </span>
                                                            </span>
                                                        )}
                                                        {typeof gapMeasured.volume === 'number' && (
                                                            <span className="reader-pill">{gapMeasured.volume.toLocaleString()} signals today</span>
                                                        )}
                                                        {typeof gapMeasured.baseline === 'number' && (
                                                            <span className="reader-pill">
                                                                {gapMeasured.baseline}/day
                                                                <span className="reader-pill-plain">
                                                                    {baselinePhrase(gapMeasured.baseline, gapMeasured.baseline_days)}
                                                                </span>
                                                            </span>
                                                        )}
                                                        {/* The 0.5 sentinel never becomes a fact: an
                                                            unjudgeable country prints its ignorance. */}
                                                        {gapMeasured.self_voice_status === 'measured'
                                                            && typeof gapMeasured.self_voice_ratio === 'number' ? (
                                                            <span
                                                                className="reader-pill"
                                                                data-tip={withBasisTip(`Outlet OWNERSHIP, not language: ${gapMeasured.domestic_n ?? 0} of the ${gapMeasured.known_origin_n ?? 0} signals whose outlet home country is known are domestic${typeof gapMeasured.unattributed_n === 'number' ? `; ${gapMeasured.unattributed_n} carry no known origin` : ''}.`)}
                                                            >
                                                                own press {Math.round(gapMeasured.self_voice_ratio * 100)}% of ingest
                                                                {/* X4: "% of ingest" is two abstractions
                                                                    stacked. The share stays; "N in every
                                                                    100" is the same fact a reader can
                                                                    picture. X1's base is already on the
                                                                    tip above and in the prose. */}
                                                                <span className="reader-pill-plain">
                                                                    {selfVoicePhrase(gapMeasured.self_voice_ratio)}
                                                                </span>
                                                            </span>
                                                        ) : (
                                                            <span
                                                                className="reader-pill brief-sources-unmeasured"
                                                                data-tip={withBasisTip("Too few signals carry an attributable outlet home country to judge this country's own voice.")}
                                                            >
                                                                own press not measurable
                                                            </span>
                                                        )}
                                                    </div>
                                                    {gapSection.day_complete === false && (
                                                        <p className="brief-footref">
                                                            Measured on a UTC day that is not finished yet — against full-day
                                                            baselines, this multiplier is a floor.
                                                        </p>
                                                    )}
                                                    {gapReceipts.length > 0 && (
                                                        <>
                                                            <div className="brief-rc-lab">Receipts — real source · outlet origin when known</div>
                                                            <div className="brief-receipts">
                                                                {gapReceipts.map((ev, i) => renderReceipt(ev, i, { contextLabel: gapCountry.name }))}
                                                            </div>
                                                        </>
                                                    )}
                                                    <div className="brief-card-foot">
                                                        <span className="brief-card-actions">
                                                            <button
                                                                className="brief-theme-link"
                                                                onClick={() => goToAtlas(`country=${gapCountry.code}`, 'gap')}
                                                            >
                                                                Open {gapCountry.name} →
                                                            </button>
                                                        </span>
                                                    </div>
                                                </>
                                            ) : (
                                                <p className="brief-empty-note">{gapEmpty}</p>
                                            )}
                                        </section>
                                    )}

                                    {/* ============ LO QUE SUBE · WHAT IS RISING ============
                                        Measured acceleration over each story's OWN Kalman baseline
                                        (brief-rising-v1), with its why-now. Nothing here is a
                                        forecast, and a story that cleared the bar but could not be
                                        printed is COUNTED below rather than dropped. */}
                                    {risingSection && (
                                        <section className="brief-rising-section" aria-label="What is rising — measured acceleration">
                                            <span className="reader-section-kicker brief-sub-kicker">Measured acceleration</span>
                                            <h3 className="brief-section-subtitle">What Is Rising</h3>
                                            {risingItems.length > 0 ? (
                                                <div className="brief-rising-list">
                                                    {risingItems.map(item => {
                                                        const receipts = sectionReceipts(item.receipts)
                                                        return (
                                                            <article key={item.thread_id} className="brief-rising-item">
                                                                <h4 className="brief-rising-headline">
                                                                    <button
                                                                        className="brief-headline-btn"
                                                                        onClick={() => openStoryById(item.thread_id, item.label, 'rising')}
                                                                    >
                                                                        <TranslatableText text={decodeEntities(item.label)} />
                                                                    </button>
                                                                    {/* failed / partial / too_broad are MARKED, not hidden
                                                                        — the backend passes the court's verdict through
                                                                        for exactly this chip. */}
                                                                    <LabelReviewChip labelStatus={item.label_status ?? null} confidenceMeasured={false} />
                                                                </h4>
                                                                {/* X4: the plain reading LEADS, in reader
                                                                    type; the statistics follow as a stat
                                                                    line, so the analyst keeps every number
                                                                    and the non-analyst still learns what
                                                                    happened. A seal frozen before X4 carries
                                                                    only the old joined string, and
                                                                    whyNowParts renders that verbatim rather
                                                                    than guessing a clause out of it. */}
                                                                {(() => {
                                                                    const why = whyNowParts(item)
                                                                    if (!why.plain && !why.measured) return null
                                                                    return (
                                                                        <p className="brief-whynow">
                                                                            <span className="lab">Why now</span>
                                                                            {why.plain && (
                                                                                <span className="brief-whynow-plain">{why.plain}</span>
                                                                            )}
                                                                            {why.measured && (
                                                                                <span
                                                                                    className="brief-whynow-measured"
                                                                                    data-tip="Measured against this story's OWN history, never against the field: how far above its normal pace it ran, which way it is moving, and how many signals that rests on."
                                                                                >
                                                                                    {why.measured}
                                                                                </span>
                                                                            )}
                                                                        </p>
                                                                    )
                                                                })()}
                                                                {receipts.length > 0 ? (
                                                                    <div className="brief-receipts">
                                                                        {receipts.map((ev, i) => renderReceipt(ev, i, { contextLabel: item.label }))}
                                                                    </div>
                                                                ) : (
                                                                    <p className="brief-footref">
                                                                        No receipt resolved for this story — the acceleration is measured,
                                                                        the evidence lane came back empty.
                                                                    </p>
                                                                )}
                                                                <div className="brief-card-foot">
                                                                    <span className="brief-card-actions">
                                                                        <button
                                                                            className="brief-theme-link"
                                                                            onClick={() => openStoryById(item.thread_id, item.label, 'rising')}
                                                                        >
                                                                            Open story →
                                                                        </button>
                                                                    </span>
                                                                </div>
                                                            </article>
                                                        )
                                                    })}
                                                </div>
                                            ) : (
                                                <p className="brief-empty-note">{risingEmpty}</p>
                                            )}
                                            {risingSection.status === 'partial' && risingItems.length > 0 && (
                                                <p className="brief-footref">
                                                    Only {risingItems.length === 1 ? 'one story' : `${risingItems.length} stories`} cleared
                                                    the bar in this window.
                                                </p>
                                            )}
                                            {risingExcluded && (
                                                <p className="brief-footref">{risingExcluded}</p>
                                            )}
                                        </section>
                                    )}

                                    {/* THE REST OF THE DESK */}
                                    {worldCards.length > 0 && (
                                        <div className="brief-cards">
                                            {worldCards.map((t, i) => renderThreadCard(t, { wide: i === 0 }))}
                                        </div>
                                    )}

                                    {/* W5 — WHERE THE FRONT PAGE ENDS AND THE RANK DOES NOT.
                                        The judge found console stories missing from here and read
                                        it as the two views disagreeing. They do not: this page is
                                        the top slice of the SAME rank. Say so, and say where the
                                        rest is — rather than letting the reader discover the gap
                                        and conclude one of the two is lying. */}
                                    {worldCards.length > 0 && (
                                        <p className="brief-coherence-note">
                                            <span>{editionScope.sentence} {editionScope.consoleNote}</span>
                                            <button
                                                className="brief-theme-link"
                                                onClick={() => goToAtlas('', 'coherence_console')}
                                            >
                                                {CONSOLE_LINK_LABEL}
                                            </button>
                                        </p>
                                    )}

                                    {/* UNASSEMBLED SIGNALS — clusters below the confidence bar or
                                        failed by the Label Court. Additive (no thread vanishes): the
                                        label is struck under review and the raw receipts, grouped by
                                        source country, are the content. */}
                                    {unassembledThreads.length > 0 && renderUnassembledSection(unassembledThreads)}
                                    {/* Markets moved to the top full-width band (BriefMarketsBand).
                                        HEATING UP moved below the trim (printer's-marks ship,
                                        2026-08-13): it reads live heat_countries, so inside the
                                        sealed edition's crop marks it made the trim over-claim. */}
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
                                                    <CoverageGapCard
                                                        key={g.slug}
                                                        gap={g}
                                                        maxRaw={maxGapRaw}
                                                        onOpen={(slug) => goToAtlas(`theme=${encodeURIComponent(slug)}`, 'gap_box')}
                                                    />
                                                ))}
                                            </div>
                                            <p className="brief-footref">
                                                Gap bars: track length ∝ raw signals on a shared scale; the admitted fill is drawn
                                                from the verified count — 0% clearance is an empty bar, not a sliver.
                                            </p>
                                        </>
                                    ) : (
                                        // C1: "no gaps" is a finding only when the lane ran.
                                        <p className="brief-empty-note">
                                            {deskEmptyCopy('gaps', laneState('gaps', laneEvidence))}
                                        </p>
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
                                        // C1: the culture desk is the SAME `top_threads` fetch as
                                        // The World, so when that lane dies both desks are unknown
                                        // — and neither may claim a gate ruled on them.
                                        <>
                                            <p className="brief-empty-note">
                                                {deskEmptyCopy('culture', laneState('stories', laneEvidence))}
                                            </p>
                                            {/* W5 — THE CONTRADICTION THAT WAS NOT ONE. This desk
                                                said "nothing cleared the gate" while the category
                                                index in the same viewport said "Sports 1,398". Two
                                                different bases: the index counts every ACTIVE topic
                                                Atlas tracks; this desk carries only threads that
                                                reached the ranked front page. Reconciled here, from
                                                the same numbers the reader can see below — and only
                                                when the lane actually answered, so we never explain
                                                away an emptiness we failed to measure. */}
                                            {!storiesUnanswered && cultureCensusNote && (
                                                <p className="brief-footref">{cultureCensusNote}</p>
                                            )}
                                            {storiesUnanswered && (
                                                <button className="brief-theme-link" onClick={retryLanes}>
                                                    Ask the story lane again ↻
                                                </button>
                                            )}
                                        </>
                                    )}
                                </section>
                            </PMTrimWrap>

                            {/* HEATING UP — live anomaly heat. Lives OUTSIDE the sealed
                                edition's trim (it re-measures every load), beside the other
                                live instrumentation, and no longer only on the World tab —
                                it was never World-specific data. */}
                            {heatStrip.length > 0 && (
                                <section className="brief-heat-strip">
                                    <h3
                                        className="brief-bottom-heading"
                                        data-tip="Countries with the strongest anomaly heat right now. The tag names the dominant component: velocity (volume acceleration), surprise (off-baseline), diversity (many themes), voice (source spread), polyphony (many actors). Live measurement — outside the sealed edition."
                                    >
                                        Heating Up
                                    </h3>
                                    {/* C4 — THE DOOR SAYS IT IS A DOOR. A bare tile with a
                                        country and a number teleported the judge into the
                                        analyst console with "no warning, no way back"
                                        (§4.2). The destination is right — `?country=` sets
                                        the scope, the console renders `World ▸ COUNTRY X`
                                        and opens that country's panel — so the fix is to
                                        announce the jump and NAME the way back, which is
                                        the first crumb. Same voice as The Gap's already-
                                        correct "Open Colombia →". */}
                                    <div className="brief-heat-row">
                                        {heatStrip.map(h => {
                                            const comp = dominantHeatComponent(h.components)
                                            const name = resolveCountryName(h.code, h.name)
                                            const door = countryDoorCopy(name, 'where this heat is measured')
                                            return (
                                                <button
                                                    key={h.code}
                                                    className="brief-heat-card"
                                                    onClick={() => goToAtlas(`country=${h.code}`, 'heating_up')}
                                                    data-tip={door.tip}
                                                    aria-label={door.ariaLabel}
                                                >
                                                    <span className="brief-heat-name"><Flag code={h.code} /> {name}</span>
                                                    <span className="brief-heat-val">{Math.round(h.heat * 100)}</span>
                                                    {/* X4 (2026-08-13, blind college C5): this chip
                                                        printed the raw metric column name — "Malta 67
                                                        SURPRISE" — on the front page. It is a REASON
                                                        label, not a number, so translating it whole
                                                        costs the analyst nothing while the tip keeps
                                                        the engine's own term. An unknown component
                                                        falls back to the raw name: at least true. */}
                                                    {comp && (
                                                        <span
                                                            className="brief-heat-comp"
                                                            data-tip={`Strongest ingredient of this country's heat score: the "${comp}" component.`}
                                                        >
                                                            {heatComponentPhrase(comp) ?? comp}
                                                        </span>
                                                    )}
                                                    <span className="brief-heat-door">{door.cue}</span>
                                                </button>
                                            )
                                        })}
                                    </div>
                                </section>
                            )}
                            </>
                        )}

                        {/* ===== COUNTRY EDITION ===== */}
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
                                            <div className="k">Stories</div>
                                            <div className="v">{countryEdition?.threads.length ?? countryThreads?.length ?? 0}</div>
                                            <div className="sub">country-scoped stories</div>
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
                                {/* COUNTRY MARKETS — this country's OWN instruments (its data),
                                    below the country edition header. Renders nothing when the
                                    country has no tracked instrument (honest absence). */}
                                <BriefCountryMarketsCard countryCode={countryFilter} />

                                {/* N26: this door is served from the nightly artifact when one
                                    is fresh, so it can legitimately be hours old — while the
                                    vitals right above it ("in the last 24h") are live. Say the
                                    age rather than let the two read as one moment. Renders
                                    nothing for a live build. */}
                                {(() => {
                                    const note = editionAgeNote(countryEdition?.artifact)
                                    return note ? (
                                        <p className="brief-country-enrich">{note}</p>
                                    ) : null
                                })()}

                                {(() => {
                                    const enr = countryEdition?.article_enrichment
                                    if (!enr?.yield || enr.yield.attempted === 0) return null
                                    const stillPending = (enr.pending_urls ?? []).filter(u => {
                                        const s = countryLiveStates.get(u)
                                        return !s || s.status === 'pending' || s.status === 'queued'
                                    }).length
                                    return (
                                        <p className="brief-country-enrich" aria-live="polite">
                                            {`full text ${enr.yield.ok}/${enr.yield.attempted} receipts`}
                                            {stillPending > 0 ? ` · enriching ${stillPending} more…` : ''}
                                        </p>
                                    )
                                })()}

                                {countryEditionFailed ? (
                                    <div className="brief-country-note">
                                        {/* C4: the wait is bounded now (COUNTRY_EDITION_TIMEOUT_MS)
                                            — "Assembling…" can no longer run forever (judge §4.3:
                                            30+ seconds, twice, never resolved). A dead end becomes
                                            a state with two ways out. */}
                                        <p>Atlas could not assemble this country's edition right now — the door did not answer, so nothing about this country's coverage is claimed either way.</p>
                                        <button className="brief-theme-link" onClick={() => retryCountryEdition()}>
                                            Try this country again ↻
                                        </button>
                                        <button
                                            className="brief-theme-link"
                                            onClick={() => goToAtlas(`country=${countryFilter}`, 'country_edition_failed')}
                                            data-tip={countryDoorCopy(resolveCountryName(countryFilter, countryDetail?.name)).tip}
                                        >
                                            {countryDoorCopy(resolveCountryName(countryFilter, countryDetail?.name)).cue}
                                        </button>
                                    </div>
                                ) : !countryEdition ? (
                                    <p className="brief-country-note">
                                        Assembling this country's edition for the last {hours}h…
                                    </p>
                                ) : countryEdition.threads.length === 0 && countryEdition.coverage_gaps.length === 0 ? (
                                    <div className="brief-country-note">
                                        {/* C1, one door deeper: a DEGRADED build reached no verdict
                                            about this country — only a build that ran may say the
                                            gate found nothing. */}
                                        <p>{deskEmptyCopy('country', countryEdition.artifact?.degraded ? 'unanswered' : 'served')}</p>
                                        <button className="brief-theme-link" onClick={() => goToAtlas(`country=${countryFilter}`)}>
                                            Open country in Atlas →
                                        </button>
                                    </div>
                                ) : (
                                    composeCountrySections<TopThread>(
                                        (countryEdition.threads as unknown as TopThread[]),
                                        countryEdition.coverage_gaps,
                                    ).map(sec => renderCountrySection(sec, countryFilter))
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
                                {/* Task 5 (mobile IA #236): skip the choropleth on a phone — it
                                    was the 4th-heaviest block on the page and react-simple-maps
                                    fetches the world GeoJSON (GEO_URL) as soon as ComposableMap
                                    mounts, so this must be a conditional RENDER, not just CSS
                                    display:none, or the download still happens. The "Most Active"
                                    list beside it (a sibling column, not inside .brief-minimap)
                                    stays — it is real content, not a map render. */}
                                {/* C1 (judge §4.5): the density map rendering as "a flat grey
                                    landmass with no density shading at all" is the map's version
                                    of empty furniture — indistinguishable from a world where
                                    nothing happened. Say which it is BEFORE the shapes. */}
                                {(() => {
                                    const note = mapDensityNote(laneEvidence, signalMap.size)
                                    return note ? <p className="brief-empty-note brief-map-note">{note}</p> : null
                                })()}
                                {!isMobile && (
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
                                )}
                            </div>
                            <div className="brief-bottom-col brief-map-side">
                                <h3 className="brief-bottom-heading">Most Active</h3>
                                {data.top_countries.slice(0, 8).map(c => {
                                    const name = resolveCountryName(c.code, c.name)
                                    const door = countryDoorCopy(name, 'where its coverage is counted')
                                    return (
                                        <button
                                            key={c.code}
                                            className="brief-bottom-country"
                                            onClick={() => goToAtlas(`country=${c.code}`, 'most_active')}
                                            data-tip={door.tip}
                                            aria-label={door.ariaLabel}
                                        >
                                            <span><Flag code={c.code} /> {name}</span>
                                            <span className="brief-bottom-num">{c.signals.toLocaleString()}</span>
                                        </button>
                                    )
                                })}
                                {/* C1 §4.5: a heading over a void. */}
                                {(() => {
                                    const note = furnitureNote('countries', laneEvidence, data.top_countries.length)
                                    return note ? <p className="brief-empty-note">{note}</p> : null
                                })()}
                            </div>
                        </section>

                        <div className="brief-rule" />

                        <section className="brief-bottom-row">
                            {/* B3 (dataviz audit): ONE user-facing tone scale everywhere — ±10,
                                the scale ThemeDetail already explains. The API serves the ±1
                                value; multiply back for display and label the unit.
                                C2 (blind judge §4.9): the unit is NOT the lineage. These columns
                                said "GDELT tone" in the footer while every row carried an "NLP
                                nn%" chip — and the chip was the honest one (measured: 10/10 rows
                                nlp_weighted). Source is chosen PER ROW by the fusion, so the
                                footer states the measured mix instead of one source it can't
                                claim, and a value clamped to the legend edge says so on its face
                                rather than only in a hover. */}
                            {(() => {
                                const scale = data.sentiment_scale
                                const negRows = data.negative_sentiment.slice(0, 4)
                                const posRows = data.positive_sentiment.slice(0, 4)
                                const posNote = describePositiveColumn(posRows.map(c => c.sentiment))
                                const toneRow = (
                                    c: { code: string; name: string; sentiment: number; signals: number; sentiment_source?: string; nlp_coverage?: number },
                                    lane: 'negative' | 'positive',
                                ) => {
                                    // Council P1-4: never print a value outside the legend
                                    // ("Gaza −10.3" under −10…+10) — clamp for display, keep
                                    // the raw figure honest in the hover AND mark the clamp.
                                    const tone = formatTone10(c.sentiment, scale)
                                    const satTip = toneSaturationTip(tone, scale)
                                    const blend = describeToneBlend([c.sentiment_source]).label
                                    return (
                                        <button
                                            key={c.code}
                                            className="brief-bottom-country"
                                            onClick={() => goToAtlas(`country=${c.code}`, lane === 'negative' ? 'most_negative' : 'most_positive')}
                                            // C4: the row's NUMBER carries its own tone tip, so the
                                            // door's promise rides on the accessible name (a visible
                                            // second tip here would fight the tone hover).
                                            aria-label={countryDoorCopy(resolveCountryName(c.code, c.name), 'where this tone is measured').ariaLabel}
                                        >
                                            <span><Flag code={c.code} /> {resolveCountryName(c.code, c.name)}</span>
                                            <span
                                                className={`brief-bottom-num ${lane}`}
                                                data-tip={`${blend} ${tone.display} on the tone scale (${c.signals.toLocaleString()} signals). ${satTip ?? 'Same fused aggregate as the strip above, ×10.'}`}
                                            >
                                                {tone.marker && (
                                                    <span className="brief-tone-marker" aria-label="saturated at the legend edge">{tone.marker}</span>
                                                )}
                                                {tone.display}
                                                <SentimentSourceBadge source={c.sentiment_source} coverage={c.nlp_coverage} />
                                            </span>
                                        </button>
                                    )
                                }
                                return (
                                    <>
                                        <div className="brief-bottom-col">
                                            <h3 className="brief-bottom-heading" data-tip={`Avg tone, −10 (critical/conflict) to +10 (supportive) — the same scale as the console's story detail, and the instrument strip's ±1 number ×10. Source per row: ${toneLineageNote(scale)}.`}>Most Negative</h3>
                                            {negRows.map(c => toneRow(c, 'negative'))}
                                            <div className="brief-scale-note">{toneScaleFooter(negRows.map(c => c.sentiment_source), scale)}</div>
                                        </div>
                                        <div className="brief-bottom-col">
                                            <h3 className="brief-bottom-heading" data-tip={`Top of the tone distribution, −10 (critical/conflict) to +10 (supportive) — the same scale as the console's story detail. A ranking, not a promise that the rows are positive. Source per row: ${toneLineageNote(scale)}.`}>Most Positive</h3>
                                            {posRows.map(c => toneRow(c, 'positive'))}
                                            {posNote && <div className="brief-scale-note brief-scale-note--caveat">{posNote}</div>}
                                            <div className="brief-scale-note">{toneScaleFooter(posRows.map(c => c.sentiment_source), scale)}</div>
                                        </div>
                                    </>
                                )
                            })()}
                            <div className="brief-bottom-col">
                                <h3 className="brief-bottom-heading">Sources</h3>
                                {data.top_sources.slice(0, 5).map(s => (
                                    <div key={s.source} className="brief-source-row">
                                        <span className="brief-source-name">{s.source}</span>
                                        <span className="brief-source-count">{s.count}</span>
                                    </div>
                                ))}
                                {/* C1 §4.5 — the live witness for this fix: on 2026-08-13 the
                                    briefing payload carried degraded_segments ["top_sources",
                                    "theme_country"] and this column rendered as a heading over
                                    nothing, with the page's 27,812-source vital right above it. */}
                                {(() => {
                                    const note = furnitureNote('sources', laneEvidence, data.top_sources.length)
                                    return note ? <p className="brief-empty-note">{note}</p> : null
                                })()}
                            </div>
                            <div className="brief-bottom-col">
                                {(data.category_counts?.length ?? 0) > 0 ? (
                                    /* #249: Atlas's OWN R3.1 categories — the GDELT
                                       taxonomy index retired once every story carries
                                       a category. Search opens the category term. */
                                    <>
                                        <h3 className="brief-bottom-heading" data-tip="Atlas category index — every live story is typed into an open category (crisis anchors + emergent).">By Category</h3>
                                        {/* W5: the index declares its base. Its numbers count the
                                            whole active-topic census, NOT the desks above — which
                                            is why a desk can be honestly empty while a row here
                                            reads in the thousands. */}
                                        <p className="brief-footref brief-bottom-basis">{CATEGORY_INDEX_BASIS}</p>
                                        {data.category_counts!.slice(0, 6).map(c => (
                                            <button
                                                key={c.category}
                                                className="brief-bottom-country"
                                                onClick={() => goToAtlas(`q=${encodeURIComponent(c.category)}`, 'by_category')}
                                                data-tip={`${c.topics.toLocaleString()} tracked ${c.topics === 1 ? 'story' : 'stories'} · ${c.signals.toLocaleString()} raw signals. Tracked, not necessarily on this page.`}
                                            >
                                                <span>{c.category}</span>
                                                {/* Both numbers, so the big one is never read alone
                                                    as "stories on the front page". */}
                                                <span className="brief-bottom-num">
                                                    <span className="brief-bottom-topics">{c.topics.toLocaleString()} tracked</span>
                                                    <span className="brief-bottom-signals">{c.signals.toLocaleString()} raw</span>
                                                </span>
                                            </button>
                                        ))}
                                    </>
                                ) : (
                                    <>
                                        <h3 className="brief-bottom-heading" data-tip="Taxonomy index — themes are a navigation aid, not the story model. Stories above are the editorial unit.">By Theme</h3>
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
                                        {/* C1 §4.5: BY THEME headed a void when the theme lane died. */}
                                        {(() => {
                                            const note = furnitureNote('themes', laneEvidence, data.top_themes.length)
                                            return note ? <p className="brief-empty-note">{note}</p> : null
                                        })()}
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
