import { useState, useEffect, useRef } from 'react'
import { getThemeLabel, getThemeIcon, resolveThreadTitle } from '../lib/themeLabels'
import { decodeEntities } from '../lib/decodeEntities'
import { formatAttachSimilarity, laneTag, truncationNote } from '../lib/discussionHonesty'
import { buildThreadVoiceModel, canHaveThreadVoice, type ThreadVoiceModel } from '../lib/threadVoice'
import { CountQualifierChip, formatCountWindow } from '../lib/countQualifier'
import { resolveThemeCountMeta } from '../lib/themeDetailCount'
import { LabelReviewChip } from '../lib/labelReviewChip'
import { TemporalSignatureChip, type TemporalSignatureMeta } from '../lib/temporalSignatureChip'
import { CompareBar } from './CompareBar'
import { NarrativeDrift } from './NarrativeDrift'
import { NarrativeBiography } from './NarrativeBiography'
import { TranslatableHeadline } from './TranslatableHeadline'
import PinReceiptButton from './PinReceiptButton'
import { ShareThreadButton } from './ShareCard'
import { useIsMobile } from '../hooks/useIsMobile'
import { ExportMenu } from './ExportMenu'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { Pin, PinOff, X } from '../lib/icons'
import { getSourceFamilyMeta, type SourceFamily } from '../lib/sourceFamily'
import { TierChip } from './TierChip'
import { RelationshipChip } from './RelationshipChip'
import { fetchTopicRelationship, type TopicRelationship } from '../lib/topicRelationship'
import { EvidenceRoute } from './EvidenceRoute'
import { buildTopicEvidenceRoute } from '../lib/evidenceRoute'
import { buildKeySubjects, type SubjectType } from '../lib/countryBriefSubjects'

const SUBJECT_BADGE: Record<SubjectType, string> = {
    person: 'person', place: 'place', organization: 'org', group: 'group', event: 'event',
}
import { resolveCountryName } from '../lib/countryNames'
import { useFocusData } from '../contexts/FocusDataContext'
import { conflictsForCountry } from '../lib/conflictEvents'
import { PanelSkeleton, PanelSkeletonGrid } from './PanelSkeleton'
import { LoadingMoment } from './LoadingMoment'
import { CoverageBadge, type CoverageMeta } from './CoverageBadge'
import type { PublicAttentionOrigin } from '../lib/publicAttention'
import { buildThemeDetailEmptyState } from '../lib/themeDetailEmptyState'
import { Flag } from './Flag'
import { FocusTimeline } from './FocusTimeline'
import './ThemeDetail.css'


interface ThemeData {
    theme: string
    label?: string
    country: string | null
    /** null = NOT MEASURED (the count query timed out or failed — see
     *  `degraded`). Render "not measured", never 0: a timeout is not absence. */
    total: number | null
    // Atlas-topic threads resolve through gated signal_topic_assignments: `total`
    // is the precise (gate-kept) count once scored, while `rawTotal` is the raw
    // assigned count the Narrative Threads list shows. Surfacing both keeps the
    // panel number reconciled with the list instead of silently disagreeing.
    rawTotal?: number
    gated?: number
    /**
     * Council R4 N19 — what `total` actually IS. For dynamic threads `total` is
     * `agg_n_signals`, a LIFETIME aggregate, and the header used to stamp it
     * with the requested window ("3,659 signals · Last 24h") while the thread
     * row one click up read 88 for the same story.
     *
     * `countBasis: 'lifetime'` names the basis so the header never has to infer
     * it; `currentTotal` is the ROW'S OWN number (the latest snapshot's kept
     * count) so the two surfaces agree by construction; `countWindowHours` is
     * the MEASURED window that number was clustered over (168h in production —
     * never the hardcoded 24 either surface used to print).
     *
     * All optional and honestly absent: a caller/topic without a snapshot
     * serves undefined, never 0 (a 0 would read as "nothing in the window").
     */
    countBasis?: 'lifetime'
    currentTotal?: number | null
    countWindowHours?: number | null
    verified?: number
    extended?: number
    extendedThreshold?: number
    gatePending?: boolean
    gateCoverage?: number | null
    /** X2/S2 (time-as-dimension): topic lifetime start — AGE is first-class. */
    firstSeen?: string | null
    /** Temporal signature (mig 085): new/continuous/recurrent/resurrected;
     *  null below the census member floor or until the nightly classifier
     *  runs — the chip renders nothing then (absence over guess). */
    temporalSignature?: string | null
    signatureMeta?: TemporalSignatureMeta | null
    /** null when the payload is degraded (query timeout/error) — unmeasured. */
    avgSentiment: number | null
    /** Timeout-as-absence contract (mirrors /api/v2/stats): true when the
     *  backend's queries did not complete, with a reason code. Counts are
     *  null, arrays empty — nothing here is a measured zero. */
    degraded?: boolean
    degraded_reason?: 'db_timeout' | 'db_error' | string | null
    signals: Array<{
        id?: number
        timestamp: string
        country: string
        source: string
        url: string
        headline?: string | null
        source_lang?: string | null
        sentiment: number
        otherThemes: string[]
        persons: string[]
        /** mig 097 durable receipts: frozen snapshot whose live signal aged
         *  out of the 7-day hot window — rendered visibly archived. */
        archived?: boolean
    }>
    graphSignals?: Array<{
        id?: number
        timestamp: string
        country: string
        source: string
        url: string
        headline?: string | null
        source_lang?: string | null
        sentiment: number
        otherThemes: string[]
        persons: string[]
        archived?: boolean
    }>
    countryBreakdown: Array<{ code: string; count: number; sentiment: number }>
    relatedThemes: Array<{ theme: string; count: number }>
    topSources: Array<{
        name: string; count: number; sentiment: number;
        family?: SourceFamily | string | null;
        // #217 capability G: credibility tier — label with provenance, never a filter
        credibility?: { tier: number; label: string; provenance: string } | null;
    }>
    topPersons: Array<{ name: string; count: number }>
    timeline: Array<{ hour: string; count: number; sentiment: number }>
    source?: string
    query?: string
    coverage?: CoverageMeta
    coverageTier?: 'thin' | 'limited' | 'ok'
    warnings?: string[]
    /** #224 black-hole guard — measured thread coherence (avg member-to-centroid
     *  cosine). `warning` set when the thread likely conflates unrelated stories. */
    coherence?: {
        score: number
        tier: 'tight' | 'mixed' | 'loose'
        distinctCountries: number
        topCountryShare: number
        members: number
        warning: string | null
    } | null
    countryFraming?: Array<{
        country_code: string
        country_name: string
        signal_count: number
        avg_sentiment: number
        top_sub_themes: string[]
        sentiment_label: string
        volumeRank?: number
    }>
    relatedConcepts?: Array<{ slug: string; label: string; description: string }>
    /** R3 spine: the specific living stories under this atlas topic/category */
    memberStories?: Array<{ id: string; label: string; n: number; last_seen: string | null; crisis_relevant: boolean | null }>
}

interface ThemeDetailProps {
    theme: string
    originCountry?: string
    originCountryName?: string
    originAttention?: PublicAttentionOrigin
    threadContext?: { thread_id: string; label: string }
    /** When set, automatically applies a country filter to the theme data fetch (compound search) */
    initialDrillCountry?: string
    hours: number

    onClose: () => void
    onThemeSelect?: (theme: string, originAttention?: PublicAttentionOrigin) => void
    onCountryCardClick?: (code: string, name: string) => void
    onPersonClick?: (name: string) => void
    onSourceClick?: (domain: string) => void
    onCompareClick?: (theme: string) => void
    /** #232 UX slice: chip click opens the country (CountryBrief carries the
        conflict-events strip). Geography-join only — never a story match. */
    onConflictChipClick?: (code: string, name: string) => void
    /** Deep-link cold open: fires when the fetch lands a real thread label so
        surfaces OUTSIDE this panel (focus chip, stream header, universe
        orbit) can replace their generic placeholder with the real name. */
    onLabelResolved?: (themeId: string, label: string) => void
}

interface NarrativeNote {
    lede: string
    movement: string
    evidence: string
    caveat?: string | null
    quality: 'strong' | 'provisional' | 'thin'
    source: string
}

interface ThreadForumItem {
    signal_id: number
    headline: string
    subreddit?: string | null
    country_code?: string | null
    source_url?: string | null
    source_lang?: string | null
    similarity: number
}

interface AttentionSearchData {
    signal_matches?: Array<{
        id: number
        timestamp: string
        country: string
        source: string
        headline: string | null
        themes: string[]
    }>
    themes?: Array<{ theme: string; total_signals: number }>
}

function buildDynamicTopicInsight(data: ThemeData): string | null {
    // A degraded payload has no measured count or tone — a templated insight
    // over unmeasured numbers would be fabrication. Serve nothing.
    if (data.total == null || data.avgSentiment == null) return null
    const topCountries = data.countryBreakdown
        .slice(0, 3)
        .map(c => `${resolveCountryName(c.code)} (${c.count.toLocaleString()} signals)`)
        .join(', ')
    const topSources = data.topSources
        .slice(0, 3)
        .map(s => s.name)
        .join(', ')
    const tone = data.avgSentiment > 0.5
        ? 'positive'
        : data.avgSentiment < -0.5
            ? 'negative'
            : 'mixed'

    return [
        `This dynamic story is active in the selected window with ${data.total.toLocaleString()} signals${topCountries ? `, led by ${topCountries}` : ''}.`,
        `Coverage tone is ${tone} (${data.avgSentiment.toFixed(2)}), and the current evidence sample spans ${data.signals.length.toLocaleString()} recent items${topSources ? ` from sources including ${topSources}` : ''}.`,
    ].join('\n\n')
}

function formatAttentionCount(n?: number): string {
    if (!n) return '0'
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}m`
    if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
    return String(n)
}

export function ThemeDetail({ theme, originCountry, originCountryName, originAttention, threadContext, initialDrillCountry, hours, onClose, onThemeSelect, onCountryCardClick, onPersonClick, onSourceClick, onConflictChipClick, onLabelResolved }: ThemeDetailProps) {
    const [data, setData] = useState<ThemeData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [insight, setInsight] = useState<string | null>(null)
    const [insightLoading, setInsightLoading] = useState(false)
    const [insightFailed, setInsightFailed] = useState(false)
    const isMobile = useIsMobile()
    const [selectedSource, setSelectedSource] = useState<string | null>(null)
    const [showAllCoverage, setShowAllCoverage] = useState(false)
    const [showDrift, setShowDrift] = useState(false)
    // Deep history (time-as-dimension, thread level): archive-era series
    // back to May-03 + click-a-day receipts. Fetched on-demand (toggle).
    const [deepHistory, setDeepHistory] = useState<
        null | 'loading' | {
            available: boolean; reason?: string; matched_units?: number;
            series?: Array<{ day: string; units: number; signals: number }>;
            day?: { date: string; items: Array<Record<string, unknown>>; empty_reason?: string | null };
        }>(null)
    const [deepDay, setDeepDay] = useState<string | null>(null)

    const fetchDeepHistory = async (day?: string) => {
        if (!day) setDeepHistory('loading')
        try {
            const q = day ? `?date=${day}` : ''
            const r = await fetch(`/api/v2/theme/${encodeURIComponent(theme)}/deep-history${q}`)
            const j = await r.json()
            setDeepHistory(j)
            if (day) setDeepDay(day)
        } catch {
            setDeepHistory({ available: false, reason: 'request failed' })
        }
    }

    // #237 community discussion: the forum/social posts behind the thread,
    // as a non-evidence claim-origin layer. Auto-loads with the detail.
    const [discussion, setDiscussion] = useState<
        null | { count: number; noise_count?: number; items: Array<{ headline: string; platform: string; url: string; origin: string; lang: string; similarity?: number; lane?: string }> }>(null)
    useEffect(() => {
        let alive = true
        fetch(`/api/v2/topic/${encodeURIComponent(theme)}/discussion`)
            .then(r => r.json())
            .then(d => { if (alive && d?.items) setDiscussion(d) })
            .catch(() => { /* section absent */ })
        return () => { alive = false }
    }, [theme])

    // #168: press-vs-public relationship for this thread — full mode (all 5
    // types render, media-led included; the list rows only badge the
    // exceptions). Same topic-backed gate as thread voice: only topics with
    // typed membership rows can carry the measurement. Failure -> absent.
    const [relationship, setRelationship] = useState<TopicRelationship | null>(null)
    useEffect(() => {
        setRelationship(null)
        if (!canHaveThreadVoice(theme)) return
        let alive = true
        fetchTopicRelationship(theme).then(rel => { if (alive) setRelationship(rel) })
        return () => { alive = false }
    }, [theme])

    // Voice Mix · who speaks (council wish 18): language + outlet-origin
    // distribution over this thread's typed evidence members + self-voice
    // relation. Only topic-backed threads can have member rows; network
    // failure -> section absent, backend available:false -> honest reason.
    const [threadVoice, setThreadVoice] = useState<ThreadVoiceModel | null>(null)
    useEffect(() => {
        setThreadVoice(null)
        if (!canHaveThreadVoice(theme)) return
        let alive = true
        fetch(`/api/v2/topic/${encodeURIComponent(theme)}/voice?hours=${hours}`)
            .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
            .then(d => { if (alive && typeof d?.available === 'boolean') setThreadVoice(buildThreadVoiceModel(d)) })
            .catch(() => { /* section absent on network failure */ })
        return () => { alive = false }
    }, [theme, hours])

    // #161 external-depth lane: on-demand DOC 2.0 enrichment for THIN topics.
    // null = not fetched; 'loading'; {available:false,...} = honest gap.
    const [externalDepth, setExternalDepth] = useState<
        null | 'loading' | {
            available: boolean; reason?: string; query?: string;
            items?: Array<{ title: string; url: string; domain: string;
                language: string | null; verified: boolean;
                credibility?: { tier: number; label: string; provenance: string } }>
        }>(null)

    const fetchExternalDepth = async () => {
        setExternalDepth('loading')
        try {
            const r = await fetch(`/api/v2/theme/${encodeURIComponent(theme)}/external-depth`)
            setExternalDepth(await r.json())
        } catch {
            setExternalDepth({ available: false, reason: 'request failed — retry later' })
        }
    }

    // On phones the thread read is a full-screen overlay; lock the cockpit
    // behind it so background scroll doesn't bleed through.
    useEffect(() => {
        if (!isMobile) return
        const prev = document.body.style.overflow
        document.body.style.overflow = 'hidden'
        return () => { document.body.style.overflow = prev }
    }, [isMobile])
    // E3: how-covered cards expand IN PLACE (mini coverage peek) instead of
    // jumping straight to the big country panel.
    const [expandedFraming, setExpandedFraming] = useState<string | null>(null)
    const [drillCountry, setDrillCountry] = useState<string | null>(initialDrillCountry || null)
    const [drillCountryName, setDrillCountryName] = useState<string | null>(
        initialDrillCountry ? (originCountryName || initialDrillCountry) : null
    )
    const detailRef = useRef<HTMLDivElement>(null)
    const { pinItem, unpinItem, isPinned } = useWorkspace()
    // #232 UX slice: when this thread is country-scoped, surface how many
    // conflict events sit in that country this window. GEOGRAPHY-JOIN ONLY —
    // no semantic event→story matching in this slice.
    const { acledConflicts } = useFocusData()
    const conflictScopeCountry = drillCountry || originCountry || null
    const scopedConflicts = conflictsForCountry(acledConflicts, conflictScopeCountry)
    const isDynamicTopic = theme.toLowerCase().startsWith('dynamic-topic-')
    // Custom query thread: token shape is `query-thread::<raw user query>`.
    // The raw text is preserved (accents/spaces) for the /search/thread builder.
    const isQueryThread = theme.startsWith('query-thread::')
    const queryThreadText = isQueryThread ? theme.slice('query-thread::'.length) : ''

    // Public attention signals
    const [trendMatch, setTrendMatch] = useState<{ has_public_interest: boolean; matches: Array<{ keyword: string; country_code: string }> } | null>(null)
    const [wikiMatch, setWikiMatch] = useState<{ has_wiki_activity: boolean; matches: Array<{ title: string; views: number }>, total_views: number } | null>(null)
    const [attentionSearchData, setAttentionSearchData] = useState<AttentionSearchData | null>(null)
    const [threadNote, setThreadNote] = useState<NarrativeNote | null>(null)
    // Label trust for the header chip (council Phase 1): captured from the same
    // thread fetch as the narrative note. Only set when opened from a thread.
    const [threadLabelTrust, setThreadLabelTrust] = useState<{
        label_status: string | null
        avg_confidence: number | null
        confidence_measured: boolean
        label_proposed: string | null
        // 2026-07-30 (gb5-blind-check "cron-safety item 2"): court-attempted-
        // but-ungrounded (umbrella lane) — see labelReviewChip.tsx.
        court_withheld: boolean
    } | null>(null)
    // Per-thread forum discussion (L2 C3): semantic neighbors of the thread
    // centroid from the social lane. Discussion only — never gated evidence.
    const [threadForum, setThreadForum] = useState<ThreadForumItem[]>([])

    // Reset drill state when theme changes, preserving country-scoped pivots from Brief/CountryBrief.
    useEffect(() => {
        setDrillCountry(initialDrillCountry || null)
        setDrillCountryName(initialDrillCountry ? (originCountryName || initialDrillCountry) : null)
    }, [theme, initialDrillCountry, originCountryName])

    // Deep-link cold open (council STILL-BROKEN): when the fetch lands a real
    // label, hand it up — the focus chip / stream header / universe orbit
    // otherwise keep their generic placeholder forever. The parent guards
    // against no-op updates, so re-fires are harmless.
    useEffect(() => {
        const resolved = data?.label ? decodeEntities(data.label) : ''
        if (resolved.trim()) onLabelResolved?.(theme, resolved)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [data?.label, theme])

    useEffect(() => {
        setShowDrift(false)
        if (loading || !data) return
        const timer = window.setTimeout(() => setShowDrift(true), 900)
        return () => window.clearTimeout(timer)
    }, [theme, hours, drillCountry, loading, data])

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true)
            setError(null)
            setInsight(null)
            setSelectedSource(null)
            try {
                const params = new URLSearchParams({ hours: hours.toString() })
                if (drillCountry) params.append('country_code', drillCountry)
                const url = isQueryThread
                    ? `/api/v2/search/thread?q=${encodeURIComponent(queryThreadText)}&${params.toString()}`
                    : `/api/v2/theme/${encodeURIComponent(theme)}?${params.toString()}`

                const res = await fetch(url)
                if (!res.ok) throw new Error(`HTTP ${res.status}`)

                const json = await res.json()
                setData(json)
            } catch (e) {
                setError(e instanceof Error ? e.message : 'Failed to load')
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [theme, hours, drillCountry])

    // Fetch public attention signals (trends + wiki)
    useEffect(() => {
        if (!theme) return
        if (isQueryThread) return  // theme-code match is meaningless for free-text threads
        const encoded = encodeURIComponent(theme)
        fetch(`/api/v2/trends/match?theme=${encoded}&hours=${hours}`)
            .then(r => r.json().catch(() => null))
            .then(d => { if (d) setTrendMatch(d) })
            .catch(() => { })
        fetch(`/api/v2/wiki/match?theme=${encoded}&days=1`)
            .then(r => r.json().catch(() => null))
            .then(d => { if (d) setWikiMatch(d) })
            .catch(() => { })
    }, [theme, hours])

    // Per-thread forum discussion (L2 C3). Only dynamic-topic threads carry a
    // centroid the backend can match the social lane against; others get [].
    useEffect(() => {
        if (!isDynamicTopic) { setThreadForum([]); return }
        const controller = new AbortController()
        fetch(`/api/v2/public-attention?thread=${encodeURIComponent(theme)}&hours=${hours}`, { signal: controller.signal })
            .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
            .then(d => { if (!controller.signal.aborted) setThreadForum(d?.forum?.items ?? []) })
            .catch(() => { if (!controller.signal.aborted) setThreadForum([]) })
        return () => controller.abort()
    }, [theme, hours, isDynamicTopic])

    useEffect(() => {
        if (!originAttention?.title) {
            setAttentionSearchData(null)
            return
        }
        const controller = new AbortController()
        const query = originAttention.query || originAttention.title
        fetch(`/api/v2/search/unified?q=${encodeURIComponent(query)}&hours=${hours}`, { signal: controller.signal })
            .then(r => r.json().catch(() => null))
            .then(d => { if (!controller.signal.aborted) setAttentionSearchData(d) })
            .catch(() => { if (!controller.signal.aborted) setAttentionSearchData(null) })
        return () => controller.abort()
    }, [originAttention?.title, originAttention?.query, hours])

    useEffect(() => {
        if (!threadContext?.thread_id) {
            setThreadNote(null)
            setThreadLabelTrust(null)
            return
        }
        const controller = new AbortController()
        fetch(`/api/v2/threads/${encodeURIComponent(threadContext.thread_id)}?hours=${hours}&llm=1`, { signal: controller.signal })
            .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
            .then(payload => {
                if (!controller.signal.aborted) {
                    const t = payload?.thread
                    setThreadNote(t?.narrative_note ?? null)
                    setThreadLabelTrust(t ? {
                        label_status: t.label_status ?? null,
                        avg_confidence: typeof t.avg_confidence === 'number' ? t.avg_confidence : null,
                        confidence_measured: t.confidence_measured === true,
                        label_proposed: t.label_proposed ?? null,
                        court_withheld: t.court_withheld === true,
                    } : null)
                }
            })
            .catch(() => {
                if (!controller.signal.aborted) { setThreadNote(null); setThreadLabelTrust(null) }
            })
        return () => controller.abort()
    }, [threadContext?.thread_id, hours])

    const [insightError, setInsightError] = useState<string | null>(null)

    // Fetch AI insight async after main data loads
    useEffect(() => {
        if (!theme) return
        if (isDynamicTopic || isQueryThread) return
        setInsightLoading(true)
        setInsightFailed(false)
        setInsightError(null)
        setInsight(null)
        const params = new URLSearchParams({ hours: hours.toString() })
        fetch(`/api/v2/theme/${encodeURIComponent(theme)}/insight?${params}`)
            .then(r => r.json().catch(() => null))
            .then(json => {
                if (json?.insight) {
                    setInsight(json.insight)
                } else {
                    setInsightFailed(true)
                    setInsightError(json?.error ?? null)
                }
            })
            .catch(() => { setInsightFailed(true); setInsightError(null) })
            .finally(() => setInsightLoading(false))
    }, [theme, hours, isDynamicTopic, isQueryThread])

    useEffect(() => {
        if (!isDynamicTopic && !isQueryThread) return
        setInsightLoading(false)
        setInsightFailed(false)
        setInsightError(null)
        setInsight(isDynamicTopic && data ? buildDynamicTopicInsight(data) : null)
    }, [isDynamicTopic, isQueryThread, data])

    // R3c defect 7: theme vars, not dark literals — noir's var values ARE
    // these literals (#4ade80 / #f87171 / #fbbf24), so noir is byte-identical.
    const getSentimentColor = (s: number) =>
        s > 0.1 ? 'var(--color-sentiment-positive)' : s < -0.1 ? 'var(--color-sentiment-negative)' : 'var(--color-severity-notable)'

    const sentimentWord = (s: number): string => {
        if (s > 2) return 'Very positive'
        if (s > 0.5) return 'Slightly positive'
        if (s > -0.5) return 'Neutral'
        if (s > -2) return 'Mostly negative'
        return 'Very negative'
    }

    const formatTime = (iso: string) => {
        const d = new Date(iso)
        return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    }

    // One coverage article: the HEADLINE is the primary, clickable line so a
    // reader can actually read the story and open the original (sister
    // feedback 2026-06-25 — the old list showed only metadata + a "View
    // Source" link, never the headline).
    const renderArticle = (
        sig: { id?: number; timestamp: string; country: string; source: string; url: string; headline?: string | null; source_lang?: string | null; sentiment: number; persons: string[]; archived?: boolean },
        opts: { showSource?: boolean } = {},
    ) => {
        // Evidence headlines can arrive HTML-entity-encoded — decode for display.
        const title = sig.headline ? decodeEntities(sig.headline) : 'Untitled report'
        return (
            <div className="coverage-article">
                <div className="coverage-article-headline" style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                    <span style={{ flex: 1, minWidth: 0 }}>
                        {sig.id != null && sig.headline
                            ? <TranslatableHeadline signalId={sig.id} original={title} sourceLang={sig.source_lang} />
                            : <span className="coverage-article-headline--nolink">{title}</span>}
                    </span>
                    <PinReceiptButton
                        contextLabel={displayLabel}
                        citation={{
                            headline: title,
                            source: sig.source || undefined,
                            url: sig.url || undefined,
                            // N1: sig.country is the story's SUBJECT country, not the
                            // outlet's origin — never stored as an origin assertion.
                            // This payload carries no source_origin_country yet, so the
                            // pin records no origin (absence over guess).
                            sourceLang: sig.source_lang || undefined,
                            gateStatus: 'unknown',
                            publishedDate: sig.timestamp ? sig.timestamp.slice(0, 10) : undefined,
                        }}
                    />
                </div>
                <div className="coverage-article-meta">
                    {sig.url && (
                        <a href={sig.url} target="_blank" rel="noopener noreferrer" className="coverage-article-open">
                            open original ↗
                        </a>
                    )}
                    {opts.showSource && <span className="coverage-article-source">{sig.source || 'Unknown'}</span>}
                    {opts.showSource && sig.source && <TierChip source={sig.source} />}
                    {/* mig 097 durable receipt — frozen snapshot, visibly
                        archived (mirrors DayEvidencePanel's FROM THE ARCHIVE
                        tier). Sentiment was not frozen, so none is shown. */}
                    {sig.archived && (
                        <span
                            className="badge coverage-badge coverage-badge--archived"
                            data-tip="Frozen receipt captured when this story was clustered — the live signal has aged out of the 7-day hot window. Headline and link are real; live stats no longer include it."
                        >
                            FROM THE ARCHIVE
                        </span>
                    )}
                    {sig.timestamp && <span>{formatTime(sig.timestamp)}</span>}
                    {sig.country && <span>{sig.country}</span>}
                    {!sig.archived && (
                        <span style={{ color: getSentimentColor(sig.sentiment) }}>
                            {sig.sentiment > 0 ? '+' : ''}{sig.sentiment.toFixed(2)}
                        </span>
                    )}
                </div>
            </div>
        )
    }

    // Sentiment bar color for framing cards
    const getFramingSentimentColor = (s: number): string => {
        if (s > 0.5) return 'var(--color-sentiment-positive)'
        if (s > -0.5) return 'var(--color-sentiment-neutral)'
        if (s > -2.0) return '#f59e0b'
        return '#ef4444'
    }

    // Sentiment bar width (normalized to 0-100 from -10 to +10 scale)
    const getSentimentBarWidth = (s: number): number => {
        return Math.min(100, Math.max(5, ((s + 10) / 20) * 100))
    }

    const pinnedId = `theme-${theme}${originCountry ? '-' + originCountry : ''}`
    const pinned = isPinned(pinnedId)
    // Never serve a placeholder title — ON THE LOADING PATH TOO (council P1-7:
    // "Dynamic Topic 49 — 0 signals" flashed ~3s before resolve). Preference:
    // resolved payload label → the label carried by the list row that opened
    // this thread (threadContext) → resolveThreadTitle: while the FIRST fetch
    // of an opaque id is in flight, an honest "Loading thread…" (deep-link
    // cold open, council STILL-BROKEN) — never the raw id, and never the
    // resolved-looking "Narrative Thread" generic (that remains the
    // post-failure fallback inside). Labels can arrive HTML-entity-encoded —
    // decode for display.
    const displayLabel = decodeEntities(
        data?.label
        || threadContext?.label
        || (isQueryThread ? queryThreadText : resolveThreadTitle(theme, null, loading && !data)))
    // While the first fetch is in flight there is no honest count yet — print
    // an ellipsis, never a false "0 signals" next to a skeleton, and never a
    // window word ("Last 24h") over a count that doesn't exist yet. A degraded
    // payload (total: null — the query timed out/failed) renders "not
    // measured", never 0: a timeout is not absence (cc0bf804 class).
    const countMeta = resolveThemeCountMeta({
        loading,
        hasData: !!data,
        total: data?.total,
        degraded: data?.degraded,
        degradedReason: data?.degraded_reason,
        hours,
    })
    const totalDisplay = countMeta.countText
    // N19: does this payload declare `total` to be a lifetime aggregate AND
    // carry the row's current-window number to show beside it? Both are
    // required — a lifetime basis with no current number would leave the header
    // with nothing windowed to print.
    const lifetimeBasis = data?.countBasis === 'lifetime' && data?.currentTotal != null
    // The measured window, or null. Never defaulted to '24h' — printing an
    // assumed window over a number counted across another one is the bug.
    const currentWindowLabel = formatCountWindow(data?.countWindowHours)
    // total counts VERIFIED (gate-kept) evidence; with the below-gate
    // fallback (#214) the backend can return raw signals labeled unverified
    // even when total is 0 — only show the empty state when there is truly
    // nothing to inspect.
    const emptyState = data && data.total === 0 && (data.signals?.length ?? 0) === 0
        ? buildThemeDetailEmptyState({
            label: displayLabel,
            countryName: drillCountryName || (drillCountry ? resolveCountryName(drillCountry) : null),
            hours,
            openedFrom: threadContext ? 'thread' : originAttention ? 'public_attention' : 'topic',
        })
        : null
    const countryFramingRows = data
        ? (data.countryFraming && data.countryFraming.length > 0
            ? data.countryFraming
            : data.countryBreakdown.map(c => ({
                country_code: c.code,
                country_name: resolveCountryName(c.code),
                signal_count: c.count,
                avg_sentiment: c.sentiment,
                top_sub_themes: [],
                sentiment_label: c.sentiment > 0.1 ? 'positive' : c.sentiment < -0.1 ? 'negative' : 'neutral',
            })))
        : []

    const handlePin = () => {
        if (pinned) {
            unpinItem(pinnedId)
        } else {
            const params = new URLSearchParams(window.location.search)
            params.set('theme', theme)
            if (originCountry) params.set('country', originCountry)
            pinItem({
                id: pinnedId,
                type: 'theme',
                title: `${displayLabel}${originCountryName ? ` in ${originCountryName}` : ''}`,
                urlParams: `?${params.toString()}`,
                // Council R4 N25 (the wedge-killer): freeze the evidence THIS
                // PANEL IS SHOWING. The pin used to carry metadata only and
                // wait on an async re-fetch at a different window/scope — when
                // that missed, the dossier reported an evidence gap on a thread
                // that had its receipts on screen. These rows are the ones the
                // analyst saw (display order; capped in freezeVisibleEvidence).
                evidence: data?.signals ?? [],
            })
        }
    }

    return (
        <div className="theme-detail-overlay" ref={detailRef}>
            <div className="theme-detail-panel">
                <div style={{ position: 'absolute', top: '16px', right: '16px', display: 'flex', gap: '8px', alignItems: 'center', zIndex: 100 }}>
                    <button
                        onClick={handlePin}
                        data-tip={pinned ? "Unpin Theme" : "Pin Theme to Workspace"}
                        style={{ background: 'rgba(var(--color-ink-rgb),0.05)', border: '1px solid rgba(var(--color-ink-rgb),0.1)', color: pinned ? '#10b981' : 'var(--color-sentiment-neutral)', width: '28px', height: '28px', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', transition: 'all 0.2s' }}
                    >
                        {pinned ? <PinOff size={14} /> : <Pin size={14} />}
                    </button>
                    {!loading && data && (
                        <>
                            <ShareThreadButton
                                input={{
                                    label: displayLabel,
                                    whyNow: countMeta.unmeasured
                                        ? 'signal count not measured'
                                        : `${(data.total ?? data.signals.length).toLocaleString()} signals`,
                                    url: `${window.location.origin}/app?theme=${encodeURIComponent(theme)}`,
                                }}
                                evidence={data.signals.map(s => s.headline).filter((h): h is string => !!h)}
                            />
                            <ExportMenu
                                themeName={displayLabel}
                                data={data}
                                insight={insight}
                                captureRef={detailRef}
                            />
                        </>
                    )}
                    <button className="theme-detail-close" onClick={onClose} style={{ position: 'relative', top: 'auto', right: 'auto' }}>
                        <X size={16} />
                    </button>
                </div>


                <div className="theme-detail-header" id="td-header">
                    <span className="theme-detail-icon">{getThemeIcon(theme)}</span>
                    <div style={{ flex: 1 }}>
                        <h2>
                            {displayLabel}
                            {threadLabelTrust && (
                                <LabelReviewChip
                                    labelStatus={threadLabelTrust.label_status}
                                    avgConfidence={threadLabelTrust.avg_confidence}
                                    confidenceMeasured={threadLabelTrust.confidence_measured}
                                    labelProposed={threadLabelTrust.label_proposed}
                                    courtWithheld={threadLabelTrust.court_withheld}
                                />
                            )}
                            <TemporalSignatureChip
                                signature={data?.temporalSignature}
                                meta={data?.signatureMeta}
                            />
                        </h2>
                        {isQueryThread && (
                            <p className="theme-detail-meta">
                                <span className="query-thread-tag">Custom story</span>
                                {data?.coverageTier === 'thin' && (
                                    <span className="badge coverage-badge coverage-badge--thin" data-tip="Few matching signals — this story is built from thin coverage">THIN</span>
                                )}
                                {data?.coverageTier === 'limited' && (
                                    <span className="badge coverage-badge coverage-badge--limited" data-tip="Limited matching signals for this query">LIMITED</span>
                                )}
                                {' '}Built from your search · {countMeta.unmeasured ? 'matching signals not measured' : `${totalDisplay} matching signals`}
                            </p>
                        )}
                        {drillCountry ? (
                            <p className="theme-detail-meta">
                                <button
                                    className="drill-back-btn"
                                    onClick={() => { setDrillCountry(null); setDrillCountryName(null) }}
                                >
                                    ← Global
                                </button>
                                {' · '}<Flag code={drillCountry} title={drillCountryName} /> {drillCountryName} · {countMeta.unmeasured ? 'signal count not measured' : `${totalDisplay} signals`}
                            </p>
                        ) : (
                            <p className="theme-detail-meta">
                                {/* T4 (dataviz audit): count lineage at the seam — the list row,
                                    this header and "Show all coverage (N)" each carry a different
                                    count; unlabeled they read as bugs. Convention: raw · sourced ·
                                    verified. */}
                                {data?.rawTotal && data.rawTotal !== data.total ? (
                                    <span data-tip={`${data.rawTotal.toLocaleString()} raw signals assigned to this story · ${(data.signals?.length ?? 0).toLocaleString()} sourced (fetched with headline + outlet in this view) · ${(data.total || 0).toLocaleString()} verified by the relevance gate`}>
                                        Global · {data.rawTotal.toLocaleString()} raw · {(data.signals?.length ?? 0).toLocaleString()} sourced · {(data.total || 0).toLocaleString()} verified · Last {hours}h
                                    </span>
                                ) : lifetimeBasis ? (
                                    /* N19: `total` is a LIFETIME aggregate. Print the
                                       current-window number the thread row shows (same
                                       source, so they cannot contradict) with the window
                                       it was really counted over, and name the lifetime
                                       total as lifetime instead of stamping it "Last
                                       24h". When the window is unknown we say so rather
                                       than inventing one. */
                                    <span data-tip={`${(data!.currentTotal ?? 0).toLocaleString()} signals in this story's serving membership${currentWindowLabel ? ` over the last ${currentWindowLabel}` : ''} — the number the Stories row shows. ${(data!.total || 0).toLocaleString()} is this story's all-time total since it first appeared, not a count for the current window.`}>
                                        Global · {(data!.currentTotal ?? 0).toLocaleString()} signals
                                        {currentWindowLabel
                                            ? <> · last {currentWindowLabel}</>
                                            : <> · window not reported</>}
                                        {' · '}{(data!.total || 0).toLocaleString()} lifetime
                                    </span>
                                ) : countMeta.unmeasured ? (
                                    /* Degraded payload: the count query did not
                                       complete. "not measured" is the claim —
                                       never 0, and no window word over a number
                                       that doesn't exist. */
                                    <span data-tip={countMeta.notice ?? undefined}>
                                        Global · signal count not measured
                                    </span>
                                ) : (
                                    /* While the first fetch is in flight
                                       windowLabel is null — the old branch
                                       stamped "Last 24h" beside "…" (N19: never
                                       print an assumed window). */
                                    <>Global · {totalDisplay} signals{countMeta.windowLabel ? <> · {countMeta.windowLabel}</> : null}</>
                                )}
                                {data?.firstSeen && (
                                    <span className="origin-country-hint" data-tip="Topic lifetime — when this story identity first appeared (not the current window)">
                                        {' · '}active since {new Date(data.firstSeen).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                    </span>
                                )}
                                {originCountryName && (
                                    <span className="origin-country-hint"> · opened from <Flag code={originCountry!} title={originCountryName} /> {originCountryName}</span>
                                )}
                                {originAttention?.title && (
                                    <span className="origin-country-hint"> · opened from Public Attention: {originAttention.title}</span>
                                )}
                            </p>
                        )}
                        {data && (
                            <div className="theme-detail-coverage-row">
                                <CoverageBadge
                                    coverage={data.coverage}
                                    source={data.source}
                                    warnings={data.warnings}
                                />
                                <RelationshipChip rel={relationship} />
                            </div>
                        )}
                        {conflictScopeCountry && scopedConflicts.length > 0 && (
                            <button
                                className="td-conflict-chip"
                                data-tip="GDELT CAMEO machine-coded events in this story's country — related by country, not by story. Click to open the country brief with the full list."
                                onClick={() => onConflictChipClick?.(conflictScopeCountry, resolveCountryName(conflictScopeCountry, drillCountryName || originCountryName))}
                            >
                                ⚑ {scopedConflicts.length} conflict event{scopedConflicts.length === 1 ? '' : 's'} in {resolveCountryName(conflictScopeCountry, drillCountryName || originCountryName)} this window
                                <span className="td-conflict-chip-note">related by country, not by story</span>
                            </button>
                        )}
                        {data?.coherence?.warning && (
                            <div
                                className={`theme-coherence-warn theme-coherence-warn--${data.coherence.tier}`}
                                data-tip="Measured coherence = average similarity of this story's coverage to its own centre. A low score means the story mixes unrelated stories under one label — pinning it can pollute an investigation."
                            >
                                <span className="theme-coherence-glyph">⚠</span>
                                <span>{data.coherence.warning}</span>
                                <span className="theme-coherence-score">coherence {data.coherence.score.toFixed(2)}</span>
                            </div>
                        )}
                        {/* #173 Evidence Route — the topic funnel, each chip its real
                            count, clickable to scroll to the section it names. Query
                            threads skip it: raw/gate lineage does not apply to them. */}
                        {data && !isQueryThread && (
                            <EvidenceRoute
                                steps={buildTopicEvidenceRoute({
                                    topicLabel: displayLabel,
                                    rawAssignedCount: data.rawTotal ?? data.total,
                                    verifiedCount: data.total,
                                    countryCount: data.countryBreakdown.length,
                                    outletCount: data.topSources.length,
                                    sourcedEvidenceCount: data.signals.length,
                                })}
                                onStepClick={id => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                            />
                        )}
                    </div>
                </div>

                {loading && !data && (
                    <div className="theme-detail-loading">
                        <LoadingMoment compact />
                        <PanelSkeletonGrid cols={2} rows={2} />
                        <PanelSkeleton rows={4} />
                    </div>
                )}
                {loading && data && <div className="panel-reloading" aria-label="Refreshing" />}
                {error && <div className="theme-detail-error">Error: {error}</div>}
                {countMeta.notice && (
                    /* Degraded payload (query timeout/error under DB load):
                       name the state instead of rendering fabricated zeros. */
                    <div className="theme-detail-error" data-tip="The backend served a degraded payload — its database queries did not complete. Counts and evidence below are unmeasured, not empty.">
                        {countMeta.notice}
                    </div>
                )}

                {data && emptyState && (
                    <div className="theme-detail-empty-state">
                        <div className="theme-detail-empty-kicker">Coverage gate</div>
                        <h3>{emptyState.title}</h3>
                        <p>{emptyState.body}</p>
                        <p className="theme-detail-empty-note">{emptyState.secondaryNote}</p>
                        <div className="theme-detail-empty-actions">
                            {drillCountry ? (
                                <button
                                    type="button"
                                    className="theme-detail-empty-action"
                                    onClick={() => { setDrillCountry(null); setDrillCountryName(null) }}
                                >
                                    {emptyState.primaryAction}
                                </button>
                            ) : (
                                <button
                                    type="button"
                                    className="theme-detail-empty-action"
                                    onClick={onClose}
                                >
                                    {emptyState.primaryAction}
                                </button>
                            )}
                        </div>
                    </div>
                )}

                {data && !emptyState && (
                    <>
                        {threadNote && (
                            <div className={`theme-thread-note theme-thread-note-${threadNote.quality}`}>
                                <p className="theme-thread-note-lede">{threadNote.lede}</p>
                                <p>{threadNote.movement}</p>
                                <p>{threadNote.evidence}</p>
                                {threadNote.caveat && (
                                    <p className="theme-thread-note-caveat">{threadNote.caveat}</p>
                                )}
                            </div>
                        )}

                        {/* AI Coverage Insight */}
                        <div className="theme-insight-block">
                            {insightLoading && !insight && (
                                <div className="theme-insight-loading">
                                    <span className="insight-pulse" />
                                    Analyzing coverage patterns…
                                </div>
                            )}
                            {insight && (() => {
                                const paragraphs = insight
                                    .split('\n')
                                    .map(l => l.replace(/^#{1,3}\s*/, '').trim())
                                    .join('\n')
                                    .split(/\n{2,}/)
                                    .map(p => p.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim())
                                    .filter(p => p.length > 0)
                                return paragraphs.map((p, i) => (
                                    <p key={i} className="theme-insight-text">{p}</p>
                                ))
                            })()}
                            {insightFailed && !insightLoading && !insight && (
                                <p className="theme-insight-unavailable">
                                    {insightError === 'insight_no_credits'
                                        ? 'AI analysis unavailable — Anthropic account has no credits.'
                                        : data && data.total != null && data.avgSentiment != null
                                            ? (() => {
                                                const top = data.countryBreakdown[0]
                                                const topName = top ? resolveCountryName(top.code) : null
                                                const tone = data.avgSentiment! > 0.1 ? 'positive' : data.avgSentiment! < -0.1 ? 'negative' : 'neutral'
                                                return [
                                                    topName ? `Top coverage: ${topName} (${top!.count} signals).` : null,
                                                    `Overall tone: ${tone} (${data.avgSentiment!.toFixed(2)}).`,
                                                    `${data.total!.toLocaleString()} total signals. AI summary unavailable.`,
                                                ].filter(Boolean).join(' ')
                                            })()
                                            : 'AI summary unavailable.'
                                    }
                                </p>
                            )}
                        </div>

                        {data.warnings?.includes('below_gate_evidence') && (
                            <div
                                className="theme-below-gate-banner"
                                style={{
                                    fontSize: 10, lineHeight: 1.5, padding: '6px 10px', margin: '0 0 8px',
                                    borderRadius: 6, border: '1px solid rgba(251,191,36,0.35)',
                                    background: 'rgba(251,191,36,0.07)', color: 'rgba(252,211,77,0.9)',
                                }}
                                data-tip="Gates decide what Atlas volunteers, not what it can find when asked"
                            >
                                0 signals cleared the quality gate for this slice — showing the{' '}
                                {data.rawTotal?.toLocaleString()} assigned signals as UNVERIFIED evidence.
                                Treat headlines below as candidate material, not confirmed coverage.
                            </div>
                        )}

                        {data.warnings?.includes('extended_coverage') && (data.extended ?? 0) > 0 && (
                            <div
                                className="theme-extended-banner"
                                style={{
                                    fontSize: 10, lineHeight: 1.5, padding: '6px 10px', margin: '0 0 8px',
                                    borderRadius: 6, border: '1px solid rgba(96,165,250,0.35)',
                                    background: 'rgba(96,165,250,0.07)', color: 'rgba(147,197,253,0.95)',
                                }}
                                data-tip="Verified = kept by the 90%-precision gate. Extended = cleared a lower ~75%-precision bar — likely on-topic, shown so honest coverage isn't dropped, but weigh it lighter."
                            >
                                <strong>{(data.verified ?? 0).toLocaleString()} verified</strong> ·{' '}
                                <strong>+{(data.extended ?? 0).toLocaleString()} extended coverage</strong>{' '}
                                (~75% confidence). Extended rows likely on-topic — weighed lighter than verified.
                            </div>
                        )}

                        {/* Summary Stats */}
                        <div className="theme-stats-row">
                            <div className="theme-stat" data-tip={lifetimeBasis
                                ? `${(data.total ?? 0).toLocaleString()} signals over this story's whole lifetime — an all-time total, not a count for the current window. ${(data.currentTotal ?? 0).toLocaleString()} are in the current serving membership${currentWindowLabel ? ` (last ${currentWindowLabel})` : ''}.`
                                : data.rawTotal && data.rawTotal !== data.total
                                ? `${data.total} precise signals kept by the relevance gate, of ${data.rawTotal} assigned to this story. The Stories list shows the assigned count.`
                                : countMeta.unmeasured
                                ? (countMeta.notice ?? 'Count not measured — the data query did not complete.')
                                : "Total media signals (articles, posts) mentioning this topic in the selected time window"}>
                                <span className="theme-stat-value">
                                    {/* Degraded: null total is NOT MEASURED — never
                                        render it as 0 or stamp a window chip on it. */}
                                    {countMeta.unmeasured ? '—' : data.total}
                                    {/* N19: a lifetime total takes the 'lifetime' base, which
                                        suppresses the window segment entirely — the old chip
                                        stamped `${hours}h` on an all-time number. */}
                                    {data.total != null && (
                                        <CountQualifierChip
                                            count={data.total}
                                            windowLabel={lifetimeBasis ? null : `${hours}h`}
                                            base={lifetimeBasis
                                                ? 'lifetime'
                                                : data.rawTotal && data.rawTotal !== data.total ? 'verified' : 'raw'}
                                        />
                                    )}
                                </span>
                                <span className="theme-stat-label">Signals</span>
                                {countMeta.unmeasured && (
                                    <span className="theme-stat-subnote">not measured</span>
                                )}
                                {lifetimeBasis ? (
                                    <span className="theme-stat-subnote">
                                        {(data.currentTotal ?? 0).toLocaleString()} in the last {currentWindowLabel ?? 'reported window'}
                                    </span>
                                ) : data.rawTotal && data.rawTotal !== data.total ? (
                                    <span className="theme-stat-subnote">of {data.rawTotal.toLocaleString()} assigned</span>
                                ) : null}
                            </div>
                            <div className="theme-stat" data-tip={data.avgSentiment == null
                                ? 'Not measured — the data query did not complete.'
                                : "Avg GDELT tone: −10 to +10. Negative = topic framed critically or with conflict, positive = framed supportively. Scores rarely exceed ±3 in normal news."}>
                                <span className="theme-stat-value" style={data.avgSentiment != null ? { color: getSentimentColor(data.avgSentiment) } : undefined}>
                                    {data.avgSentiment == null
                                        ? '—'
                                        : `${data.avgSentiment > 0 ? '+' : ''}${data.avgSentiment.toFixed(2)}`}
                                </span>
                                <span className="theme-stat-label">Avg Sentiment</span>
                            </div>
                            {/* Degraded: these arrays are empty because the
                                queries failed — their length is not a measured
                                0 either. */}
                            <div className="theme-stat" data-tip={countMeta.unmeasured ? 'Not measured — the data query did not complete.' : "Number of distinct countries where media sources are covering this topic"}>
                                <span className="theme-stat-value">{countMeta.unmeasured ? '—' : data.countryBreakdown.length}</span>
                                <span className="theme-stat-label">Countries</span>
                            </div>
                            <div className="theme-stat" data-tip={countMeta.unmeasured ? 'Not measured — the data query did not complete.' : "Number of distinct media outlets (news sites, blogs, feeds) contributing signals"}>
                                <span className="theme-stat-value">{countMeta.unmeasured ? '—' : data.topSources.length}</span>
                                <span className="theme-stat-label">Sources</span>
                            </div>
                        </div>

                        {/* Period comparison: volume & sentiment vs previous period */}
                        <CompareBar entityType="theme" entityValue={theme} hours={hours} />

                        {originAttention?.title && (
                            <div className="theme-section public-attention-origin">
                                <div className="section-label theme-section-title">OPENED FROM PUBLIC ATTENTION</div>
                                <div className="public-attention-origin-card">
                                    <div>
                                        <span className="attention-signal-icon">PUBLIC</span>
                                        <h3>{originAttention.title}</h3>
                                        <p>
                                            This story was opened from a people-side attention item, so Atlas is reading {displayLabel}
                                            {' '}through that context instead of as a generic global topic.
                                        </p>
                                    </div>
                                    <div className="public-attention-origin-metrics">
                                        <span><strong>{formatAttentionCount(originAttention.views)}</strong> wiki views</span>
                                        <span><strong>{originAttention.country_count ?? attentionSearchData?.signal_matches?.filter(s => s.country).length ?? 0}</strong> countries</span>
                                        <span><strong>{attentionSearchData?.signal_matches?.length ?? 0}</strong> media matches</span>
                                    </div>
                                </div>
                                {attentionSearchData?.signal_matches && attentionSearchData.signal_matches.length > 0 && (
                                    <div className="public-attention-evidence">
                                        {attentionSearchData.signal_matches.slice(0, 3).map(signal => (
                                            <div key={signal.id} className="public-attention-evidence-row">
                                                <span>
                                                    {signal.country || 'GLO'} · {signal.source}
                                                    <TierChip source={signal.source} />
                                                </span>
                                                <p>{signal.headline ? decodeEntities(signal.headline) : 'Untitled signal'}</p>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* STORY SYSTEM lives in the map panel's UNIVERSE tab
                            (spec 2026-07-02-universe-view.md §7.3): opening a
                            thread travels to its orbit THERE — same information,
                            one home. The legacy evolution graph was retired with
                            the move (component kept: TemporalNarrativeGraph). */}

                        {/* Narrative Drift timeline — deferred so AEIL explanation
                            renders first. NarrativeDrift renders null when there is
                            no real trend (most threads), so the section collapses
                            entirely instead of showing an empty placeholder. */}
                        {showDrift && (
                            <NarrativeDrift themeCode={theme} countryCode={drillCountry || originCountry} days={14} />
                        )}

                        {/* NARRATIVE BIOGRAPHY (2026-07-18): the weekly lineage
                            spine — how this story evolved across the hot/archive
                            seam. Renders ONLY when the lineage endpoint returns
                            >=2 weeks; absence is honest (no placeholder). */}
                        <NarrativeBiography
                            theme={theme}
                            temporalSignature={data?.temporalSignature}
                            signatureMeta={data?.signatureMeta}
                        />


                        {/* Combined activity timeline (Track C4b — spec §3): diverging
                            volume bars (tone by position) + rarity-normalized key-subject
                            trend lines + voice-mix band + edge-diff overlay. Replaces the
                            old red/green sentiment bars; the legacy hourly series is passed
                            as a fallback so atlas-category threads (which don't resolve to a
                            dynamic topic in the timeline endpoint) never regress. */}
                        {(data.timeline.length > 0 || theme.startsWith('dynamic-topic-')) && (
                            <div className="theme-section">
                                <FocusTimeline
                                    focusRef={theme}
                                    hours={hours}
                                    granularity="day"
                                    label={data.label || getThemeLabel(theme)}
                                    fallbackTimeline={data.timeline}
                                />
                            </div>
                        )}


                        {/* Related Topics (GDELT co-occurring themes) removed: raw GDELT
                            theme codes are not the user-facing topic model (product
                            guardrail) and the click resolved to an unroutable code.
                            Narrative threads + semantic neighbors are the related model. */}

                        {/* Key Subjects — typed: person is one type (#176) */}
                        {data.topPersons.length > 0 && (() => {
                            const keySubjects = buildKeySubjects(
                                data.topPersons.map(p => ({ name: p.name, count: p.count })), 8,
                            )
                            if (keySubjects.length === 0) return null
                            return (
                                <div className="theme-section">
                                    <h3 className="section-label">Key Subjects</h3>
                                    <div className="person-pills">
                                        {keySubjects.map(s => {
                                            const clickable = s.type === 'person'
                                            return (
                                                <span
                                                    key={`${s.type}:${s.name}`}
                                                    className={`person-pill${clickable ? '' : ' person-pill--static'}`}
                                                    data-tip={clickable
                                                        ? `${s.count} mentions — click to filter signals`
                                                        : `${s.type} · ${s.count} mentions`}
                                                    onClick={clickable ? () => onPersonClick?.(s.name) : undefined}
                                                >
                                                    <span className="subject-badge" data-type={s.type}>{SUBJECT_BADGE[s.type]}</span>
                                                    {s.name}
                                                    <span className="person-pill-count">{s.count}</span>
                                                </span>
                                            )
                                        })}
                                    </div>
                                </div>
                            )
                        })()}


                        {/* All coverage — collapsed by default. Replaces the old
                            always-on "Recent Coverage" list (metadata-only, no
                            headlines). Now shows real headlines linking to the
                            original article. Per-source coverage lives in the
                            expand under each Top Source above. */}
                        {data.signals.length > 0 && (
                            <div className="theme-section" id="td-signals">
                                <button
                                    className="all-coverage-toggle"
                                    onClick={() => setShowAllCoverage(v => !v)}
                                    data-tip="Every recent article in this story, newest first"
                                >
                                    {showAllCoverage ? '▴ Hide' : '▾ Show'} all coverage ({data.signals.length})
                                </button>
                                {showAllCoverage && (
                                    <div className="coverage-articles coverage-articles--all">
                                        {data.signals.slice(0, 30).map((sig, i) => (
                                            <div key={i}>{renderArticle(sig, { showSource: true })}</div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}


                        {/* #161 external-depth lane — offered when the topic is THIN
                            (few gate-verified receipts). On-demand, never automatic:
                            latency is 15-30s and the source is external/unverified. */}
                        {((data.verified ?? data.total ?? 0) < 10) && (
                            <div className="theme-section external-depth-section">
                                <div className="section-label theme-section-title">EXTERNAL DEPTH</div>
                                {externalDepth === null && (
                                    <button
                                        className="external-depth-btn"
                                        onClick={fetchExternalDepth}
                                        data-tip="Search GDELT DOC 2.0 full-text index for additional coverage of this thin topic. External source — results are unverified and carry credibility tiers. Takes 15-30s."
                                    >
                                        ⊕ Search external coverage (GDELT DOC 2.0)
                                    </button>
                                )}
                                {externalDepth === 'loading' && (
                                    <p className="external-depth-status">Querying external index… (15-30s, external source)</p>
                                )}
                                {externalDepth && externalDepth !== 'loading' && !externalDepth.available && (
                                    <p className="external-depth-status">
                                        External lane unavailable: {externalDepth.reason}
                                    </p>
                                )}
                                {externalDepth && externalDepth !== 'loading' && externalDepth.available && (
                                    <div className="external-depth-results">
                                        <p className="external-depth-caveat">
                                            EXTERNAL · UNVERIFIED — {externalDepth.items?.length ?? 0} articles from the DOC 2.0 index
                                            (query: {externalDepth.query}). Not Atlas evidence; tiers shown per source.
                                        </p>
                                        {(externalDepth.items ?? []).slice(0, 12).map((it, i) => (
                                            <div key={i} className="external-depth-item">
                                                <a href={it.url} target="_blank" rel="noopener noreferrer">{decodeEntities(it.title)}</a>
                                                <span className="external-depth-meta">
                                                    {it.domain}{it.language ? ` · ${it.language}` : ''}
                                                    {it.credibility && !['unknown', 'mainstream'].includes(it.credibility.label) && (
                                                        <span
                                                            className={`source-tier-badge source-tier-${it.credibility.label}`}
                                                            data-tip={`Credibility tier: ${it.credibility.label} — ${it.credibility.provenance}`}
                                                        >
                                                            {it.credibility.label}
                                                        </span>
                                                    )}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* HOW IT'S COVERED — Framing Analysis (hidden when drilled into a country) */}
                        {!drillCountry && countryFramingRows.length > 0 && (() => {
                            // Assign ranks by volume BEFORE reordering
                            const withRank = countryFramingRows.map((cf, idx) => ({ ...cf, volumeRank: idx + 1 }))
                            let framing = withRank

                            if (originCountry) {
                                const originIdx = framing.findIndex(c => c.country_code === originCountry)
                                if (originIdx > 0) {
                                    const [originEntry] = framing.splice(originIdx, 1)
                                    framing = [originEntry, ...framing]
                                } else if (originIdx === -1) {
                                    const fallback = data.countryBreakdown.find(c => c.code === originCountry)
                                    if (fallback) {
                                        // Find rank by comparing to countryBreakdown order
                                        const breakdownRank = data.countryBreakdown.findIndex(c => c.code === originCountry) + 1
                                        framing = [{
                                            country_code: originCountry,
                                            country_name: originCountryName || originCountry,
                                            signal_count: fallback.count,
                                            avg_sentiment: fallback.sentiment,
                                            top_sub_themes: [],
                                            sentiment_label: fallback.sentiment > 0 ? 'positive' : 'negative',
                                            volumeRank: breakdownRank || framing.length + 1
                                        }, ...framing]
                                    }
                                }
                            }
                            const totalFramingSignals = framing.reduce((s, c) => s + c.signal_count, 0)
                            const extraCountries = data.countryBreakdown.length - countryFramingRows.length
                            return (
                                <div className="theme-section framing-section" id="td-coverage">
                                    <div className="framing-header-row">
                                        <h3 className="section-label" data-help="Each card shows how a country's media frames this topic. Tone ranges from −10 (critical) to +10 (supportive). Click any card to see country-specific signals.">How It's Covered</h3>
                                        <span className="framing-scope">
                                            top {countryFramingRows.length} of {data.countryBreakdown.length} countries by volume
                                        </span>
                                        <span className="framing-info-btn" data-tip="Each card shows how a country's media covers this topic. Tone −10 to +10: negative = framed critically, positive = framed supportively. Sub-themes co-occur most in that country's coverage. Click any card to see that country's signals.">?</span>
                                    </div>
                                    {/* D2 (dataviz audit): the cards sum to fewer signals than the
                                        header because only geo-attributed signals get a country —
                                        say so instead of letting the numbers silently disagree. */}
                                    {(() => {
                                        const geoSum = data.countryBreakdown.reduce((s, c) => s + (c.count || 0), 0)
                                        const denom = data.total || 0
                                        return geoSum > 0 && denom > geoSum ? (
                                            <div className="framing-geo-note" data-tip="Signals without a resolvable subject country don't appear in any country card — the gap is attribution coverage, not missing data.">
                                                {geoSum.toLocaleString()} of {denom.toLocaleString()} signals are geo-attributed — cards cover only those
                                            </div>
                                        ) : null
                                    })()}
                                    <div className="framing-grid">
                                        {framing.map((cf, idx) => {
                                            const sharePct = totalFramingSignals > 0
                                                ? Math.round((cf.signal_count / totalFramingSignals) * 100)
                                                : 0
                                            const isOrigin = cf.country_code === originCountry
                                            // D1 (dataviz audit): an n=1 country must not get the same
                                            // confident card as n=31 — dim thin cards, and below 3
                                            // signals a tone average is noise, not a number.
                                            const isThin = cf.signal_count < 5
                                            const toneMeaningful = cf.signal_count >= 3
                                            return (
                                                <div
                                                    key={cf.country_code}
                                                    className={`framing-card${isOrigin ? ' framing-card-origin' : ''}${isThin ? ' framing-card--thin' : ''}`}
                                                    onClick={() => setExpandedFraming(prev =>
                                                        prev === cf.country_code ? null : cf.country_code)}
                                                    data-tip={`Peek ${cf.country_name}'s coverage`}
                                                >
                                                    <div className="framing-card-header">
                                                        <span className="framing-rank">#{cf.volumeRank ?? idx + 1}</span>
                                                        <span className="framing-flag"><Flag code={cf.country_code} title={cf.country_name} /></span>
                                                        <span className="framing-country-name">{cf.country_name}</span>
                                                    </div>
                                                    <div className="framing-stats">
                                                        <span className="framing-signal-count" data-tip="Signals from this country · share of total global coverage for this topic">
                                                            {cf.signal_count.toLocaleString()} sig
                                                            <span className="framing-share"> · {sharePct}%</span>
                                                            {isThin && (
                                                                <span className="badge coverage-badge coverage-badge--thin" data-tip={`Only ${cf.signal_count} signal${cf.signal_count === 1 ? '' : 's'} from this country — treat as indicative only`}>thin</span>
                                                            )}
                                                        </span>
                                                        {toneMeaningful ? (
                                                            <span className="framing-tone" data-tip="Avg GDELT tone: how this country's media frames the topic. −10 = very critical, 0 = neutral, +10 = very supportive." style={{ color: getFramingSentimentColor(cf.avg_sentiment) }}>
                                                                {cf.avg_sentiment > 0 ? '+' : ''}{cf.avg_sentiment.toFixed(1)} tone
                                                            </span>
                                                        ) : (
                                                            <span className="framing-tone framing-tone--na" data-tip={`Tone average over ${cf.signal_count} signal${cf.signal_count === 1 ? '' : 's'} is noise, not a measurement — needs at least 3.`}>
                                                                — tone
                                                            </span>
                                                        )}
                                                    </div>
                                                    {toneMeaningful && (
                                                        <div className="framing-sentiment-bar" data-tip="Tone bar: left = negative, center = neutral, right = positive">
                                                            <div
                                                                className="framing-sentiment-fill"
                                                                style={{
                                                                    width: `${getSentimentBarWidth(cf.avg_sentiment)}%`,
                                                                    backgroundColor: getFramingSentimentColor(cf.avg_sentiment)
                                                                }}
                                                            />
                                                        </div>
                                                    )}
                                                    <div className="framing-sub-themes">
                                                        {cf.top_sub_themes
                                                            .filter(st => !st.startsWith('WORLDLANGUAGES_') && !st.startsWith('TAX_WORLDLANGUAGES_'))
                                                            .map(st => (
                                                                <span key={st} className="framing-chip">
                                                                    {getThemeIcon(st)} {getThemeLabel(st)}
                                                                </span>
                                                            ))}
                                                    </div>
                                                    {expandedFraming === cf.country_code && (() => {
                                                        const peek = data.signals
                                                            .filter(sig => sig.country === cf.country_code && sig.headline)
                                                            .slice(0, 4)
                                                        return (
                                                            <div className="framing-peek" onClick={e => e.stopPropagation()}>
                                                                {peek.length > 0 ? peek.map((sig, j) => (
                                                                    <a key={j} href={sig.url} target="_blank" rel="noopener noreferrer" className="framing-peek-row">
                                                                        {typeof sig.id === 'number'
                                                                            ? <TranslatableHeadline signalId={sig.id} original={decodeEntities(sig.headline!)} sourceLang={sig.source_lang} />
                                                                            : decodeEntities(sig.headline!)}
                                                                    </a>
                                                                )) : (
                                                                    <p className="framing-peek-empty">
                                                                        No {cf.country_name} headlines in the fetched sample — open the full view.
                                                                    </p>
                                                                )}
                                                                <button
                                                                    type="button"
                                                                    className="framing-peek-full"
                                                                    onClick={() => onCountryCardClick
                                                                        ? onCountryCardClick(cf.country_code, cf.country_name)
                                                                        : (setDrillCountry(cf.country_code), setDrillCountryName(cf.country_name))}
                                                                >
                                                                    Full {cf.country_name} coverage ↗
                                                                </button>
                                                            </div>
                                                        )
                                                    })()}
                                                </div>
                                            )
                                        })}
                                    </div>
                                    {extraCountries > 0 && (
                                        <p className="framing-more-note">
                                            + {extraCountries} {extraCountries === 1 ? 'country' : 'countries'} with lower volume
                                        </p>
                                    )}
                                </div>
                            )
                        })()}


                        {/* R3 spine drill-down: the SPECIFIC living stories under
                            this atlas topic (category) — big topics open into their
                            small stories (Pedro 2026-07-02). */}
                        {data.memberStories && data.memberStories.length > 0 && (
                            <div className="theme-section">
                                <div className="section-label theme-section-title">
                                    STORIES INSIDE THIS TOPIC · {data.memberStories.length}
                                </div>
                                <div className="member-stories">
                                    {data.memberStories.map(story => (
                                        <button
                                            key={story.id}
                                            className="member-story-row"
                                            onClick={() => onThemeSelect?.(story.id)}
                                            data-tip={`Open this specific story (${story.n} signals)`}
                                        >
                                            <span className="member-story-label">
                                                {story.crisis_relevant ? <span className="member-story-crisis">●</span> : null}
                                                {decodeEntities(story.label)}
                                            </span>
                                            <span className="member-story-meta">{story.n} sig</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}


                        {/* RELATED INVESTIGATIONS (Concepts) */}
                        {data.relatedConcepts && data.relatedConcepts.length > 0 && (
                            <div className="theme-section">
                                <div className="section-label theme-section-title">RELATED INVESTIGATIONS</div>
                                <div className="concepts-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '8px', marginTop: '12px' }}>
                                    {data.relatedConcepts.map(c => (
                                        <button 
                                            key={c.slug}
                                            className="concept-card"
                                            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onThemeSelect?.(c.slug, originAttention) }}
                                            style={{ textAlign: 'left', background: 'rgba(16, 185, 129, 0.05)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '12px', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s' }}
                                            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(16, 185, 129, 0.1)'}
                                            onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(16, 185, 129, 0.05)'}
                                        >
                                            <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#10b981', marginBottom: '4px' }}>{c.label}</div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--color-sentiment-neutral)', lineHeight: 1.4 }}>{c.description}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}


                        {/* PUBLIC ATTENTION — Trends & Wiki cross-reference */}
                        {(trendMatch?.has_public_interest || wikiMatch?.has_wiki_activity) && (
                            <div className="theme-section">
                                <div className="section-label theme-section-title">PUBLIC ATTENTION</div>
                                <div className="attention-signals-row">
                                    {trendMatch?.has_public_interest && (
                                        <div className="attention-signal-card">
                                            <span className="attention-signal-icon">SEARCH</span>
                                            <div>
                                                <div className="attention-signal-label">People are searching for this</div>
                                                <div className="attention-signal-detail">
                                                    {trendMatch.matches.slice(0, 3).map((m, i) => (
                                                        <span key={i} className="trending-keyword">{m.keyword}</span>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                    {wikiMatch?.has_wiki_activity && (
                                        <div className="attention-signal-card">
                                            <span className="attention-signal-icon">WIKI</span>
                                            <div>
                                                <div className="attention-signal-label">
                                                    Wikipedia spike — {(wikiMatch.total_views || 0).toLocaleString()} views
                                                </div>
                                                <div className="attention-signal-detail">
                                                    {wikiMatch.matches.slice(0, 3).map((m, i) => (
                                                        <span key={i} className="wiki-article">{m.title}</span>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}


                        {/* PUBLIC ATTENTION FOR THIS THREAD — forum discussion (L2 C3) */}
                        {threadForum.length > 0 && (
                            <div className="theme-section">
                                <div className="section-label theme-section-title">
                                    PUBLIC ATTENTION · THIS THREAD
                                    <span className="forum-lane-badge" data-tip="Forum discussion semantically related to this story. Discussion only — never counted as verified evidence.">DISCUSSION · UNVERIFIED</span>
                                </div>
                                <div className="thread-forum-list">
                                    {threadForum.slice(0, 6).map(item => (
                                        <a
                                            key={item.signal_id}
                                            className="thread-forum-row"
                                            href={item.source_url || undefined}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                        >
                                            <span className="thread-forum-meta">
                                                {item.subreddit && <span className="thread-forum-sub">{item.subreddit}</span>}
                                                <span className="thread-forum-sim" data-tip="Semantic similarity to this story">{Math.round(item.similarity * 100)}%</span>
                                            </span>
                                            <span className="thread-forum-headline">
                                                <TranslatableHeadline signalId={item.signal_id} original={decodeEntities(item.headline)} sourceLang={item.source_lang} />
                                            </span>
                                        </a>
                                    ))}
                                </div>
                            </div>
                        )}


                        {/* #237 community discussion — the forum/social posts behind
                            the thread. PUBLIC DISCUSSION, never evidence: the
                            claim-origin layer, verified=false always. */}
                        {discussion && discussion.count > 0 && (
                            <div className="theme-section community-discussion-section">
                                <div className="section-label theme-section-title">PUBLIC DISCUSSION · UNVERIFIED</div>
                                <p className="external-depth-caveat" data-tip="Non-traditional / forum / social sources (Bluesky, Lemmy). Shows emergence and claim origin — never evidence, never corroboration.">
                                    {discussion.count} posts from forum/social — claim-origin layer, not evidence
                                    {truncationNote(Math.min(discussion.items.length, 10), discussion.count) && (
                                        <> · {truncationNote(Math.min(discussion.items.length, 10), discussion.count)}</>
                                    )}
                                </p>
                                {discussion.items.slice(0, 10).map((it, i) => (
                                    <div key={i} className="community-discussion-item">
                                        <span className="cd-platform">
                                            {it.platform?.replace(/^lemmy\//, '')}{it.origin ? ` · ${it.origin}` : ''}
                                            {/* #248 relevance honesty: MEASURED attach similarity —
                                                absent when the engine recorded none (never faked). */}
                                            {formatAttachSimilarity(it.similarity) && (
                                                <span className="thread-forum-sim" data-tip="Measured semantic similarity between this post and the story — how confidently it was attached. Not verification.">
                                                    {formatAttachSimilarity(it.similarity)}
                                                </span>
                                            )}
                                            {laneTag(it.lane) && (
                                                <span className="cd-noise-lane" data-tip="This post reads as hobby/sports/entertainment/lifestyle rather than news discussion. It sorts below news-y posts but is never hidden.">
                                                    {laneTag(it.lane)}
                                                </span>
                                            )}
                                        </span>
                                        <a href={it.url} target="_blank" rel="noopener noreferrer">{decodeEntities(it.headline)}</a>
                                    </div>
                                ))}
                            </div>
                        )}


                        {/* Top Sources */}
                        {data.topSources.length > 0 && (
                            <div className="theme-section" id="td-sources">
                                <h3 className="section-label">Top Sources</h3>
                                <div className="source-list">
                                    {data.topSources.map(s => {
                                        const family = getSourceFamilyMeta(s.family)
                                        const isOpen = selectedSource === s.name
                                        const srcSigs = isOpen ? data.signals.filter(sig => sig.source === s.name) : []
                                        return (
                                            <div key={s.name} className="source-group">
                                                <div
                                                    className={`source-item ${isOpen ? 'source-active' : ''}`}
                                                    onClick={() => setSelectedSource(isOpen ? null : s.name)}
                                                    data-tip={`Avg tone ${s.sentiment > 0 ? '+' : ''}${s.sentiment.toFixed(2)} · ${family.tip} · click to read this source's coverage`}
                                                >
                                                    <span className="source-name">{s.name}</span>
                                                    <span className={`source-family-badge ${family.className}`} data-tip={family.tip}>
                                                        {family.label}
                                                    </span>
                                                    {s.credibility && !['unknown', 'mainstream'].includes(s.credibility.label) && (
                                                        <span
                                                            className={`source-tier-badge source-tier-${s.credibility.label}`}
                                                            data-tip={`Credibility tier: ${s.credibility.label} — ${s.credibility.provenance}`}
                                                        >
                                                            {s.credibility.label === 'reference' ? '◆ ref' :
                                                             s.credibility.label === 'wire' ? '◆ wire' :
                                                             s.credibility.label === 'state' ? '⚑ state' :
                                                             s.credibility.label === 'flagged' ? '⚠ flagged' :
                                                             s.credibility.label}
                                                        </span>
                                                    )}
                                                    <span className="source-count">{s.count}</span>
                                                    <span className="source-sentiment" style={{ color: getSentimentColor(s.sentiment) }}>
                                                        {sentimentWord(s.sentiment)}
                                                    </span>
                                                    <span className="source-see-articles">{isOpen ? '▴' : '▾'}</span>
                                                </div>
                                                {isOpen && (
                                                    <div className="source-coverage">
                                                        {onSourceClick && (
                                                            <button
                                                                className="source-full-profile-btn"
                                                                onClick={(e) => { e.stopPropagation(); onSourceClick(s.name) }}
                                                            >
                                                                Full source profile ↗
                                                            </button>
                                                        )}
                                                        {srcSigs.length === 0 ? (
                                                            <p className="coverage-source-empty">
                                                                No recent articles from {s.name} in the last {data.signals.length} fetched —
                                                                this source has {s.count} total over the period. Try a longer time window.
                                                            </p>
                                                        ) : (
                                                            <div className="coverage-articles">
                                                                {srcSigs.slice(0, 12).map((sig, i) => (
                                                                    <div key={i}>{renderArticle(sig)}</div>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>
                        )}


                        {/* VOICE MIX · WHO SPEAKS (council wish 18) — language +
                            outlet-origin distribution over this thread's typed
                            evidence members + self-voice vs the dominant subject
                            country (ownership, not language — same definition as
                            the country Voice Mix). */}
                        {threadVoice?.kind === 'unavailable' && (
                            <div className="theme-section thread-voice-section">
                                <div className="section-label theme-section-title">VOICE MIX · WHO SPEAKS</div>
                                <p className="external-depth-status">Voice mix unavailable: {threadVoice.reason}</p>
                            </div>
                        )}
                        {threadVoice?.kind === 'mix' && (() => {
                            const m = threadVoice
                            const sv = m.selfVoice
                            const barColor = sv && (sv.pct >= 50 ? 'var(--accent-green, #34d399)'
                                : sv.pct >= 20 ? 'var(--accent-amber, #fbbf24)'
                                : 'var(--accent-red, #f87171)')
                            return (
                                <div className="theme-section thread-voice-section">
                                    <div className="section-label theme-section-title">
                                        VOICE MIX · WHO SPEAKS
                                        <span className="sentiment-info-icon" data-tip="Who carries this story: languages and outlet home countries over the story's typed evidence members (a projection of the engine's member record, not all coverage). Self-voice is outlet OWNERSHIP, not language — a foreign outlet in the local language counts as soft power, never as a local voice.">?</span>
                                    </div>
                                    <div className="thread-voice-langs">
                                        {m.languages.slice(0, 6).map(l => (
                                            <span key={l.lang} className="thread-voice-chip">{l.lang} <strong>{l.n}</strong></span>
                                        ))}
                                        {m.languageUnknown > 0 && (
                                            <span className="thread-voice-chip thread-voice-chip--unknown" data-tip="Signals with no language metadata (mostly GDELT). Reported, never guessed.">
                                                unknown <strong>{m.languageUnknown}</strong>
                                            </span>
                                        )}
                                    </div>
                                    {sv && (
                                        <div className="thread-voice-self">
                                            <div className="thread-voice-self-head" style={{ color: barColor || undefined }}>
                                                {sv.pct}%
                                                <span className="thread-voice-self-sub">
                                                    of attributable voices are {resolveCountryName(sv.subject, sv.subject)}&apos;s own press
                                                </span>
                                                {sv.thin && (
                                                    <span className="badge coverage-badge coverage-badge--thin" data-tip={`Only ${sv.attributable} voices carry a known outlet origin — treat this ratio as indicative only`}>
                                                        thin
                                                    </span>
                                                )}
                                            </div>
                                            <div className="thread-voice-bar">
                                                <div style={{ width: `${sv.pct}%`, background: barColor || undefined }} />
                                            </div>
                                            <div className="thread-voice-detail">
                                                {sv.selfN} of {sv.attributable} attributable voices are domestic.
                                                {sv.dominantOutsider && (
                                                    <> Loudest outsider: <strong>{resolveCountryName(sv.dominantOutsider.origin, sv.dominantOutsider.origin)}</strong> ({sv.dominantOutsider.n}).</>
                                                )}
                                                {sv.softPct > 0 && (
                                                    <> {sv.softPct}% is foreign media in the local language (soft power, not self-coverage).</>
                                                )}
                                                {sv.unattributed > 0 && (
                                                    <> {sv.unattributed} of {m.voicesTotal} voices carry no outlet origin — excluded from these ratios, never assumed.</>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                    {!sv && (
                                        <p className="thread-voice-detail">
                                            {m.voicesTotal} voices measured — no dominant subject country or no attributable outlet origins, so a self-voice ratio is not computed.
                                        </p>
                                    )}
                                </div>
                            )
                        })()}


                        {/* Deep history (time-as-dimension, thread level): the story's
                            archive-era series back to May-03 + click-a-day receipts.
                            On-demand — embeds the label + scans archive units. */}
                        <div className="theme-section deep-history-section">
                            <div className="section-label theme-section-title">DEEP HISTORY</div>
                            {deepHistory === null && (
                                <button
                                    className="external-depth-btn"
                                    onClick={() => fetchDeepHistory()}
                                    data-tip="This story's full history back to May 3 from the processed archive. Click a day in the sparkline for that day's receipts. Archive units are matched by meaning (approximate) — tier-labeled."
                                >
                                    ⧗ Load full history (back to May 3)
                                </button>
                            )}
                            {deepHistory === 'loading' && (
                                <p className="external-depth-status">Matching archive units…</p>
                            )}
                            {deepHistory && deepHistory !== 'loading' && !deepHistory.available && (
                                <p className="external-depth-status">Deep history unavailable: {deepHistory.reason}</p>
                            )}
                            {deepHistory && deepHistory !== 'loading' && deepHistory.available && (deepHistory.series?.length ?? 0) > 0 && (
                                <div className="deep-history-body">
                                    <p className="external-depth-caveat">
                                        {deepHistory.matched_units} archive story-units matched by meaning
                                        (approximate · {deepHistory.series!.length} days) — click a bar for that day's receipts.
                                    </p>
                                    <div className="deep-history-spark">
                                        {(() => {
                                            const series = deepHistory.series!
                                            const max = Math.max(...series.map(p => p.signals), 1)
                                            return series.map(p => (
                                                <div
                                                    key={p.day}
                                                    className={`dh-bar ${deepDay === p.day ? 'dh-bar-active' : ''}`}
                                                    style={{ height: `${Math.max(3, (p.signals / max) * 44)}px` }}
                                                    data-tip={`${p.day}: ${p.signals} signals · ${p.units} clusters`}
                                                    onClick={() => fetchDeepHistory(p.day)}
                                                />
                                            ))
                                        })()}
                                    </div>
                                    {deepDay && deepHistory.day && (
                                        <div className="deep-history-day">
                                            <div className="deep-history-day-head">
                                                {deepDay} — {(deepHistory.day.items?.length ?? 0)} receipts
                                            </div>
                                            {(deepHistory.day.items ?? []).length === 0 ? (
                                                <p className="external-depth-status">{deepHistory.day.empty_reason}</p>
                                            ) : (deepHistory.day.items ?? []).map((it, i) => {
                                                const tier = it.tier as string
                                                const heads = (it.headlines as string[]) || []
                                                return (
                                                    <div key={i} className="deep-history-item">
                                                        <span className={`source-tier-badge source-tier-${tier === 'hot' ? 'reference' : 'state'}`}>
                                                            {tier === 'hot' ? '● live' : 'archive'}
                                                        </span>
                                                        {tier === 'hot'
                                                            ? <a href={it.url as string} target="_blank" rel="noopener noreferrer">{decodeEntities(it.headline as string)}</a>
                                                            : <span className="dh-cluster">{decodeEntities(it.cluster_label as string)}{heads.length ? ` — ${heads.slice(0, 2).map(h => decodeEntities(h)).join(' · ')}` : ''}</span>}
                                                    </div>
                                                )
                                            })}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>


                    </>
                )}
            </div>
        </div>
    )
}
