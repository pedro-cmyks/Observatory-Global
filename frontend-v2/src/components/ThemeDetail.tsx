import { useState, useEffect, useRef } from 'react'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { CompareBar } from './CompareBar'
import { NarrativeDrift } from './NarrativeDrift'
import { TranslatableHeadline } from './TranslatableHeadline'
import { ShareThreadButton } from './ShareCard'
import { useIsMobile } from '../hooks/useIsMobile'
import { ExportMenu } from './ExportMenu'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { Pin, PinOff, X } from '../lib/icons'
import { getSourceFamilyMeta, type SourceFamily } from '../lib/sourceFamily'
import { buildKeySubjects, type SubjectType } from '../lib/countryBriefSubjects'

const SUBJECT_BADGE: Record<SubjectType, string> = {
    person: 'person', place: 'place', organization: 'org', group: 'group', event: 'event',
}
import { resolveCountryName } from '../lib/countryNames'
import { PanelSkeleton, PanelSkeletonGrid } from './PanelSkeleton'
import { CoverageBadge, type CoverageMeta } from './CoverageBadge'
import type { PublicAttentionOrigin } from '../lib/publicAttention'
import { buildThemeDetailEmptyState } from '../lib/themeDetailEmptyState'
import './ThemeDetail.css'


interface ThemeData {
    theme: string
    label?: string
    country: string | null
    total: number
    // Atlas-topic threads resolve through gated signal_topic_assignments: `total`
    // is the precise (gate-kept) count once scored, while `rawTotal` is the raw
    // assigned count the Narrative Threads list shows. Surfacing both keeps the
    // panel number reconciled with the list instead of silently disagreeing.
    rawTotal?: number
    gated?: number
    gatePending?: boolean
    gateCoverage?: number | null
    avgSentiment: number
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
    }>
    countryBreakdown: Array<{ code: string; count: number; sentiment: number }>
    relatedThemes: Array<{ theme: string; count: number }>
    topSources: Array<{ name: string; count: number; sentiment: number; family?: SourceFamily | string | null }>
    topPersons: Array<{ name: string; count: number }>
    timeline: Array<{ hour: string; count: number; sentiment: number }>
    source?: string
    query?: string
    coverage?: CoverageMeta
    coverageTier?: 'thin' | 'limited' | 'ok'
    warnings?: string[]
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

function buildDynamicTopicInsight(data: ThemeData): string {
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
        `This dynamic narrative thread is active in the selected window with ${data.total.toLocaleString()} signals${topCountries ? `, led by ${topCountries}` : ''}.`,
        `Coverage tone is ${tone} (${data.avgSentiment.toFixed(2)}), and the current evidence sample spans ${data.signals.length.toLocaleString()} recent items${topSources ? ` from sources including ${topSources}` : ''}.`,
    ].join('\n\n')
}

function formatAttentionCount(n?: number): string {
    if (!n) return '0'
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}m`
    if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
    return String(n)
}

export function ThemeDetail({ theme, originCountry, originCountryName, originAttention, threadContext, initialDrillCountry, hours, onClose, onThemeSelect, onCountryCardClick, onPersonClick, onSourceClick }: ThemeDetailProps) {
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
    // Per-thread forum discussion (L2 C3): semantic neighbors of the thread
    // centroid from the social lane. Discussion only — never gated evidence.
    const [threadForum, setThreadForum] = useState<ThreadForumItem[]>([])

    // Reset drill state when theme changes, preserving country-scoped pivots from Brief/CountryBrief.
    useEffect(() => {
        setDrillCountry(initialDrillCountry || null)
        setDrillCountryName(initialDrillCountry ? (originCountryName || initialDrillCountry) : null)
    }, [theme, initialDrillCountry, originCountryName])

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
            return
        }
        const controller = new AbortController()
        fetch(`/api/v2/threads/${encodeURIComponent(threadContext.thread_id)}?hours=${hours}&llm=1`, { signal: controller.signal })
            .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
            .then(payload => {
                if (!controller.signal.aborted) {
                    setThreadNote(payload?.thread?.narrative_note ?? null)
                }
            })
            .catch(() => {
                if (!controller.signal.aborted) setThreadNote(null)
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

    const getSentimentColor = (s: number) =>
        s > 0.1 ? '#4ade80' : s < -0.1 ? '#f87171' : '#fbbf24'

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
        sig: { id?: number; timestamp: string; country: string; source: string; url: string; headline?: string | null; source_lang?: string | null; sentiment: number; persons: string[] },
        opts: { showSource?: boolean } = {},
    ) => {
        const title = sig.headline || 'Untitled report'
        return (
            <div className="coverage-article">
                <div className="coverage-article-headline">
                    {sig.id != null && sig.headline
                        ? <TranslatableHeadline signalId={sig.id} original={sig.headline} sourceLang={sig.source_lang} />
                        : <span className="coverage-article-headline--nolink">{title}</span>}
                </div>
                <div className="coverage-article-meta">
                    {sig.url && (
                        <a href={sig.url} target="_blank" rel="noopener noreferrer" className="coverage-article-open">
                            open original ↗
                        </a>
                    )}
                    {opts.showSource && <span className="coverage-article-source">{sig.source || 'Unknown'}</span>}
                    <span>{formatTime(sig.timestamp)}</span>
                    {sig.country && <span>{sig.country}</span>}
                    <span style={{ color: getSentimentColor(sig.sentiment) }}>
                        {sig.sentiment > 0 ? '+' : ''}{sig.sentiment.toFixed(2)}
                    </span>
                </div>
            </div>
        )
    }

    // Country code to flag emoji
    const getFlag = (code: string): string => {
        if (!code || code.length !== 2) return '🌐'
        const codePoints = code.toUpperCase().split('').map(c => 0x1F1E6 + c.charCodeAt(0) - 65)
        return String.fromCodePoint(...codePoints)
    }

    // Sentiment bar color for framing cards
    const getFramingSentimentColor = (s: number): string => {
        if (s > 0.5) return '#4ade80'
        if (s > -0.5) return '#94a3b8'
        if (s > -2.0) return '#f59e0b'
        return '#ef4444'
    }

    // Sentiment bar width (normalized to 0-100 from -10 to +10 scale)
    const getSentimentBarWidth = (s: number): number => {
        return Math.min(100, Math.max(5, ((s + 10) / 20) * 100))
    }

    const pinnedId = `theme-${theme}${originCountry ? '-' + originCountry : ''}`
    const pinned = isPinned(pinnedId)
    const displayLabel = data?.label || (isQueryThread ? queryThreadText : getThemeLabel(theme))
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
                urlParams: `?${params.toString()}`
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
                        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: pinned ? '#10b981' : '#94a3b8', width: '28px', height: '28px', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', transition: 'all 0.2s' }}
                    >
                        {pinned ? <PinOff size={14} /> : <Pin size={14} />}
                    </button>
                    {!loading && data && (
                        <>
                            <ShareThreadButton
                                input={{
                                    label: displayLabel,
                                    whyNow: `${(data.total ?? data.signals.length).toLocaleString()} signals`,
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


                <div className="theme-detail-header">
                    <span className="theme-detail-icon">{getThemeIcon(theme)}</span>
                    <div style={{ flex: 1 }}>
                        <h2>{displayLabel}</h2>
                        {isQueryThread && (
                            <p className="theme-detail-meta">
                                <span className="query-thread-tag">Custom thread</span>
                                {data?.coverageTier === 'thin' && (
                                    <span className="coverage-badge coverage-badge--thin" data-tip="Few matching signals — this thread is built from thin coverage">THIN</span>
                                )}
                                {data?.coverageTier === 'limited' && (
                                    <span className="coverage-badge coverage-badge--limited" data-tip="Limited matching signals for this query">LIMITED</span>
                                )}
                                {' '}Built from your search · {data?.total || 0} matching signals
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
                                {' · '}{getFlag(drillCountry)} {drillCountryName} · {data?.total || 0} signals
                            </p>
                        ) : (
                            <p className="theme-detail-meta">
                                Global · {data?.total || 0} signals · Last {hours}h
                                {originCountryName && (
                                    <span className="origin-country-hint"> · opened from {getFlag(originCountry!)} {originCountryName}</span>
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
                            </div>
                        )}
                    </div>
                </div>

                {loading && !data && (
                    <div className="theme-detail-loading">
                        <PanelSkeletonGrid cols={2} rows={2} />
                        <PanelSkeleton rows={4} />
                    </div>
                )}
                {loading && data && <div className="panel-reloading" aria-label="Refreshing" />}
                {error && <div className="theme-detail-error">Error: {error}</div>}

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
                                        : data
                                            ? (() => {
                                                const top = data.countryBreakdown[0]
                                                const topName = top ? resolveCountryName(top.code) : null
                                                const tone = data.avgSentiment > 0.1 ? 'positive' : data.avgSentiment < -0.1 ? 'negative' : 'neutral'
                                                return [
                                                    topName ? `Top coverage: ${topName} (${top!.count} signals).` : null,
                                                    `Overall tone: ${tone} (${data.avgSentiment.toFixed(2)}).`,
                                                    `${data.total.toLocaleString()} total signals. AI summary unavailable.`,
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

                        {/* Summary Stats */}
                        <div className="theme-stats-row">
                            <div className="theme-stat" data-tip={data.rawTotal && data.rawTotal !== data.total
                                ? `${data.total} precise signals kept by the relevance gate, of ${data.rawTotal} assigned to this thread. The Narrative Threads list shows the assigned count.`
                                : "Total media signals (articles, posts) mentioning this topic in the selected time window"}>
                                <span className="theme-stat-value">{data.total}</span>
                                <span className="theme-stat-label">Signals</span>
                                {data.rawTotal && data.rawTotal !== data.total ? (
                                    <span className="theme-stat-subnote">of {data.rawTotal.toLocaleString()} assigned</span>
                                ) : null}
                            </div>
                            <div className="theme-stat" data-tip="Avg GDELT tone: −10 to +10. Negative = topic framed critically or with conflict, positive = framed supportively. Scores rarely exceed ±3 in normal news.">
                                <span className="theme-stat-value" style={{ color: getSentimentColor(data.avgSentiment) }}>
                                    {data.avgSentiment > 0 ? '+' : ''}{data.avgSentiment.toFixed(2)}
                                </span>
                                <span className="theme-stat-label">Avg Sentiment</span>
                            </div>
                            <div className="theme-stat" data-tip="Number of distinct countries where media sources are covering this topic">
                                <span className="theme-stat-value">{data.countryBreakdown.length}</span>
                                <span className="theme-stat-label">Countries</span>
                            </div>
                            <div className="theme-stat" data-tip="Number of distinct media outlets (news sites, blogs, feeds) contributing signals">
                                <span className="theme-stat-value">{data.topSources.length}</span>
                                <span className="theme-stat-label">Sources</span>
                            </div>
                        </div>

                        {/* Period comparison: volume & sentiment vs previous period */}
                        <CompareBar entityType="theme" entityValue={theme} hours={hours} />

                        {originAttention?.title && (
                            <div className="theme-section public-attention-origin">
                                <div className="theme-section-title">PUBLIC ATTENTION CONTEXT</div>
                                <div className="public-attention-origin-card">
                                    <div>
                                        <span className="attention-signal-icon">PUBLIC</span>
                                        <h3>{originAttention.title}</h3>
                                        <p>
                                            This thread was opened from a people-side attention item, so Atlas is reading {displayLabel}
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
                                                <span>{signal.country || 'GLO'} · {signal.source}</span>
                                                <p>{signal.headline || 'Untitled signal'}</p>
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

                        {/* RELATED INVESTIGATIONS (Concepts) */}
                        {data.relatedConcepts && data.relatedConcepts.length > 0 && (
                            <div className="theme-section">
                                <div className="theme-section-title" style={{ color: '#10b981' }}>RELATED INVESTIGATIONS</div>
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
                                            <div style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.4 }}>{c.description}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* PUBLIC ATTENTION — Trends & Wiki cross-reference */}
                        {(trendMatch?.has_public_interest || wikiMatch?.has_wiki_activity) && (
                            <div className="theme-section">
                                <div className="theme-section-title">PUBLIC ATTENTION</div>
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
                                <div className="theme-section-title">
                                    PUBLIC ATTENTION · THIS THREAD
                                    <span className="forum-lane-badge" data-tip="Forum discussion semantically related to this thread. Discussion only — never counted as verified evidence.">DISCUSSION · UNVERIFIED</span>
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
                                                <span className="thread-forum-sim" data-tip="Semantic similarity to this thread">{Math.round(item.similarity * 100)}%</span>
                                            </span>
                                            <span className="thread-forum-headline">
                                                <TranslatableHeadline signalId={item.signal_id} original={item.headline} sourceLang={item.source_lang} />
                                            </span>
                                        </a>
                                    ))}
                                </div>
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
                                <div className="theme-section framing-section">
                                    <div className="framing-header-row">
                                        <h3 data-help="Each card shows how a country's media frames this topic. Tone ranges from −10 (critical) to +10 (supportive). Click any card to see country-specific signals.">How It's Covered</h3>
                                        <span className="framing-scope">
                                            top {countryFramingRows.length} of {data.countryBreakdown.length} countries by volume
                                        </span>
                                        <span className="framing-info-btn" data-tip="Each card shows how a country's media covers this topic. Tone −10 to +10: negative = framed critically, positive = framed supportively. Sub-themes co-occur most in that country's coverage. Click any card to see that country's signals.">?</span>
                                    </div>
                                    <div className="framing-grid">
                                        {framing.map((cf, idx) => {
                                            const sharePct = totalFramingSignals > 0
                                                ? Math.round((cf.signal_count / totalFramingSignals) * 100)
                                                : 0
                                            const isOrigin = cf.country_code === originCountry
                                            return (
                                                <div
                                                    key={cf.country_code}
                                                    className={`framing-card${isOrigin ? ' framing-card-origin' : ''}`}
                                                    onClick={() => setExpandedFraming(prev =>
                                                        prev === cf.country_code ? null : cf.country_code)}
                                                    data-tip={`Peek ${cf.country_name}'s coverage`}
                                                >
                                                    <div className="framing-card-header">
                                                        <span className="framing-rank">#{cf.volumeRank ?? idx + 1}</span>
                                                        <span className="framing-flag">{getFlag(cf.country_code)}</span>
                                                        <span className="framing-country-name">{cf.country_name}</span>
                                                    </div>
                                                    <div className="framing-stats">
                                                        <span className="framing-signal-count" data-tip="Signals from this country · share of total global coverage for this topic">
                                                            {cf.signal_count.toLocaleString()} sig
                                                            <span className="framing-share"> · {sharePct}%</span>
                                                        </span>
                                                        <span className="framing-tone" data-tip="Avg GDELT tone: how this country's media frames the topic. −10 = very critical, 0 = neutral, +10 = very supportive." style={{ color: getFramingSentimentColor(cf.avg_sentiment) }}>
                                                            {cf.avg_sentiment > 0 ? '+' : ''}{cf.avg_sentiment.toFixed(1)} tone
                                                        </span>
                                                    </div>
                                                    <div className="framing-sentiment-bar" data-tip="Tone bar: left = negative, center = neutral, right = positive">
                                                        <div
                                                            className="framing-sentiment-fill"
                                                            style={{
                                                                width: `${getSentimentBarWidth(cf.avg_sentiment)}%`,
                                                                backgroundColor: getFramingSentimentColor(cf.avg_sentiment)
                                                            }}
                                                        />
                                                    </div>
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
                                                                            ? <TranslatableHeadline signalId={sig.id} original={sig.headline!} sourceLang={sig.source_lang} />
                                                                            : sig.headline}
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

                        {/* Timeline */}
                        {data.timeline.length > 0 && (
                            <div className="theme-section">
                                <h3 data-help="Hourly signal volume over the selected time window. Colors show average sentiment: green = positive, yellow = neutral, red = negative.">Activity Timeline</h3>
                                <div className="timeline-chart">
                                    {data.timeline.map((t, i) => (
                                        <div
                                            key={i}
                                            className="timeline-bar"
                                            style={{
                                                height: `${Math.max(10, (t.count / Math.max(...data.timeline.map(x => x.count))) * 100)}%`,
                                                backgroundColor: getSentimentColor(t.sentiment)
                                            }}
                                            data-tip={`${formatTime(t.hour)}: ${t.count} signals`}
                                        />
                                    ))}
                                </div>
                                <div style={{ display: 'flex', gap: '12px', fontSize: '10px', color: 'var(--color-text-muted)', marginTop: '8px', justifyContent: 'center' }}>
                                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#4ade80' }}></span> Positive</span>
                                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#fbbf24' }}></span> Neutral</span>
                                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#f87171' }}></span> Negative</span>
                                </div>
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
                                    <h3>Key Subjects</h3>
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

                        {/* Top Sources */}
                        {data.topSources.length > 0 && (
                            <div className="theme-section">
                                <h3>Top Sources</h3>
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

                        {/* All coverage — collapsed by default. Replaces the old
                            always-on "Recent Coverage" list (metadata-only, no
                            headlines). Now shows real headlines linking to the
                            original article. Per-source coverage lives in the
                            expand under each Top Source above. */}
                        {data.signals.length > 0 && (
                            <div className="theme-section">
                                <button
                                    className="all-coverage-toggle"
                                    onClick={() => setShowAllCoverage(v => !v)}
                                    data-tip="Every recent article in this thread, newest first"
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

                    </>
                )}
            </div>
        </div>
    )
}
