import React, { useState, useEffect } from 'react';
import { IndicatorTooltip, VolumeIndicator } from './IndicatorTooltip';
import { TranslatableHeadline } from './TranslatableHeadline';
import PinReceiptButton from './PinReceiptButton';
import { useCrisis } from '../contexts/CrisisContext';
import { useWorkspace } from '../contexts/WorkspaceContext';
import { useFocus } from '../contexts/FocusContext';
import { Download, Pin, PinOff } from '../lib/icons';
import './CountryBrief.css';
import { getThemeLabel } from '../lib/themeLabels';
import { resolveTierChip } from '../lib/sourceProvenance';
import { buildKeySubjects, type KeySubject, type SubjectType } from '../lib/countryBriefSubjects';
import { Flag } from './Flag';

const SUBJECT_BADGE: Record<SubjectType, string> = {
    person: 'person',
    place: 'place',
    organization: 'org',
    group: 'group',
    event: 'event',
};
import { buildCountryBriefMarkdown, sanitizeFilenamePart } from '../lib/exportFormatters';
import { resolveCountryName } from '../lib/countryNames';
import { useFocusData } from '../contexts/FocusDataContext';
import { conflictsForCountry } from '../lib/conflictEvents';
import {
    buildCountryPublicAttentionNarrative,
    getPublicAttentionTopUrl,
    getTrendingSearchesUrl,
} from '../lib/publicAttention';
import { buildCountryBriefThreadSummary, type CountryBriefThreadInput } from '../lib/countryBriefThreads';
import { isPublicAttentionRelevant } from '../lib/publicAttentionFilters';
import { optionalFetchResponse } from '../lib/countryBriefFetch';
import { decodeEntities } from '../lib/decodeEntities';
import { humanizeCameoEvent } from '../lib/humanizeInternals';
import { CountQualifierChip, countQualifier } from '../lib/countQualifier';
import { LabelReviewChip } from '../lib/labelReviewChip';
import { EvidenceRoute } from './EvidenceRoute';
import { buildEvidenceRoute } from '../lib/evidenceRoute';

// ThemeChange interface reserved for future use
// interface ThemeChange {
//     theme: string;
//     change: number;
//     direction: 'up' | 'down';
//     count: number;
// }

interface Story {
    url: string;
    source: string;
    timestamp: string;
    sentiment: number;
    themeCode: string;
    headline?: string | null;
    id?: number;
    source_lang?: string | null;
}

function extractDomain(url: string): string {
    try { return new URL(url).hostname.replace(/^www\./, ''); }
    catch { return url; }
}

function timeAgo(iso: string): string {
    const h = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000);
    if (h < 1) return 'just now';
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h / 24)}d ago`;
}

interface Indicators {
    diversity: {
        score: number;
        tooltip: string;
        unique_count: number;
    };
    quality: {
        score: number;
        tooltip: string;
        allowlisted_count: number;
    };
    volume: {
        multiplier: number | null;
        z_score: number | null;
        level: string;
        tooltip: string;
    };
    error?: string;
}

interface BriefData {
    country_code: string;
    hours: number;
    signal_count: number;
    top_themes: Array<{ name: string; count: number }>;
    narrative_threads: CountryBriefThreadInput[];
    top_sources: Array<{ name: string; count: number }>;
    keySubjects: KeySubject[];
    avg_sentiment: number;
    sentiment_trend: 'improving' | 'declining' | 'stable';
    top_stories?: Story[];
    publicAttention?: {
        searches: Array<{ keyword: string; rank?: number | null }>;
        wikiArticles: Array<{ title: string; views?: number | null }>;
        forum?: Array<{ headline?: string | null; subreddit?: string | null; url?: string }>;
    };
    indicators?: Indicators;
    error?: string;
    foreignSourcePct?: number | null;
}

interface CountryAnomaly {
    country_code: string;
    multiplier: number;
    level?: string;
}

interface SignalResponseItem {
    id?: number;
    url?: string;
    source?: string;
    timestamp?: string;
    sentiment?: number;
    themes?: string[];
    persons?: string[];
    headline?: string | null;
    source_lang?: string | null;
}

interface SignalsResponse {
    signals?: SignalResponseItem[];
}

interface NodesResponse {
    nodes?: Array<{
        id?: string;
        countryCode?: string;
        signalCount?: number;
        sentiment?: number;
    }>;
}

interface TrendsResponse {
    trending?: Array<{ keyword: string; rank?: number | null }>;
}

interface WikiTopResponse {
    articles?: Array<{ title: string; views?: number | null }>;
}

interface ThreadsResponse {
    threads?: CountryBriefThreadInput[];
}

interface VoiceMixRelation {
    self_voice_ratio: number;
    foreign_voice_ratio: number;
    self_voice: number;
    attributable_voices: number;
    soft_power_local_language: number;
    soft_power_ratio: number;
    dominant_outsider: { origin: string; n: number } | null;
}

interface CountryBriefProps {
    countryCode: string;
    countryName: string;
    timeWindow: number; // hours
    onClose: () => void;
    onThemeSelect?: (theme: string) => void;
    onSourceClick?: (domain: string) => void;
    onAttentionItemClick?: (query: string) => void;
    inline?: boolean;
}

function incrementCount(map: Map<string, number>, value: string | undefined) {
    if (!value) return;
    map.set(value, (map.get(value) ?? 0) + 1);
}

function topCounts(map: Map<string, number>, limit: number): Array<{ name: string; count: number }> {
    return [...map.entries()]
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, limit);
}

// Sentiment color
const getSentimentColor = (sentiment: number): string => {
    if (sentiment >= 2) return '#22c55e';
    if (sentiment <= -2) return '#ef4444';
    return '#eab308';
};

// Sentiment label
const getSentimentLabel = (sentiment: number): string => {
    if (sentiment >= 3) return 'Very Positive';
    if (sentiment >= 1) return 'Positive';
    if (sentiment <= -3) return 'Very Negative';
    if (sentiment <= -1) return 'Negative';
    return 'Neutral';
};

export const CountryBrief: React.FC<CountryBriefProps> = ({
    countryCode,
    countryName,
    timeWindow,
    onClose,
    onThemeSelect,
    onSourceClick,
    onAttentionItemClick,
    inline
}) => {
    const cls = `country-brief${inline ? ' country-brief--inline' : ''}`
    const { anomalies } = useCrisis()
    const anomaly = (anomalies as CountryAnomaly[]).find(a => a.country_code === countryCode) ?? null
    const displayCountryName = resolveCountryName(countryCode, countryName)
    const [data, setData] = useState<BriefData | null>(null);
    const [indicators, setIndicators] = useState<Indicators | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const { pinItem, unpinItem, isPinned } = useWorkspace();
    const { setPerson } = useFocus();
    const { summary, acledConflicts } = useFocusData();
    // #232 UX slice: entering a country SHOWS its conflict events (same data
    // the dock/map markers use — no new fetch). Geography-join only.
    const countryConflicts = conflictsForCountry(acledConflicts, countryCode);
    const [showAllConflicts, setShowAllConflicts] = useState(false);
    const pinned = isPinned(`country-${countryCode}`);
    const [voiceMix, setVoiceMix] = useState<VoiceMixRelation | null>(null);
    // Top Publishers: click expands the source's recent coverage inline (same
    // pattern as ThemeDetail), not a jump straight to the bare profile panel.
    const [expandedSource, setExpandedSource] = useState<string | null>(null);
    // D8: the local top_stories sample rarely contains a given publisher's
    // articles — expanding used to say "no recent coverage" next to a real
    // count. Fetch that publisher's window signals on demand instead.
    const [sourceFetch, setSourceFetch] = useState<{ name: string; stories: Array<{ id?: number; headline?: string | null; url: string; timestamp: string; source_lang?: string | null }>; loading: boolean } | null>(null);
    useEffect(() => {
        if (!expandedSource) { setSourceFetch(null); return; }
        const local = (data?.top_stories || []).filter(st => st.source === expandedSource);
        if (local.length > 0) { setSourceFetch(null); return; }
        let ignore = false;
        setSourceFetch({ name: expandedSource, stories: [], loading: true });
        fetch(`/api/v2/signals?country_code=${countryCode}&source=${encodeURIComponent(expandedSource)}&hours=${timeWindow}&limit=8`)
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                if (ignore) return;
                // Stored headlines can carry HTML entities (&#x639;…) — decode
                // before render (the _serialize_evidence class of bug). Shared
                // decoder — one implementation product-wide.
                const decode = (t: string | null | undefined) => (t ? decodeEntities(t) : t);
                const stories = (d?.signals || []).map((sig: { id?: number; headline?: string | null; source_url?: string; url?: string; timestamp: string; source_lang?: string | null }) => ({
                    id: sig.id, headline: decode(sig.headline), url: sig.source_url || sig.url || '#',
                    timestamp: sig.timestamp, source_lang: sig.source_lang,
                }));
                setSourceFetch({ name: expandedSource, stories, loading: false });
            })
            .catch(() => { if (!ignore) setSourceFetch({ name: expandedSource, stories: [], loading: false }); });
        return () => { ignore = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [expandedSource, countryCode, timeWindow]);
    const [showAllSources, setShowAllSources] = useState(false);

    const downloadMarkdown = (filename: string, content: string) => {
        const blob = new Blob([content], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const handleExportBrief = () => {
        if (!data) return
        const keyPersons = data.keySubjects.filter(s => s.type === 'person').map(s => ({ name: s.name, count: s.count }))
        const md = buildCountryBriefMarkdown({ countryName: displayCountryName, data: { ...data, keyPersons } })
        const date = new Date().toISOString().split('T')[0]
        downloadMarkdown(`atlas-country-${sanitizeFilenamePart(displayCountryName)}-${date}.md`, md)
    }

    useEffect(() => {
        const controller = new AbortController();

        const fetchData = async () => {
            setLoading(true);
            setError(null);
            setIndicators(null);

            try {
                const [nodeRes, indicatorsRes, signalsRes, trendsRes, wikiRes, threadsRes, voiceRes, forumRes] = await Promise.all([
                    optionalFetchResponse(() => fetch(`/api/v2/nodes?focus_type=country&focus_value=${countryCode}&hours=${timeWindow}&limit=1`, { signal: controller.signal })),
                    optionalFetchResponse(() => fetch(`/api/indicators/country/${countryCode}?hours=${timeWindow}`, { signal: controller.signal })),
                    fetch(`/api/v2/signals?country_code=${countryCode}&hours=${timeWindow}&limit=500`, { signal: controller.signal }),
                    optionalFetchResponse(() => fetch(getTrendingSearchesUrl(5, Math.min(timeWindow, 168), countryCode), { signal: controller.signal })),
                    optionalFetchResponse(() => fetch(getPublicAttentionTopUrl(5, countryCode), { signal: controller.signal })),
                    optionalFetchResponse(() => fetch(`/api/v2/threads?hours=${timeWindow}&limit=24&country_code=${countryCode}`, { signal: controller.signal })),
                    optionalFetchResponse(() => fetch(`/api/v2/voice-mix?hours=${Math.max(timeWindow, 168)}&country=${countryCode}`, { signal: controller.signal })),
                    optionalFetchResponse(() => fetch(`/api/v2/public-attention?country=${countryCode}&limit=4&hours=${Math.max(timeWindow, 336)}`, { signal: controller.signal })),
                ]);

                if (!signalsRes.ok) {
                    throw new Error(`Failed to fetch country signals: ${signalsRes.status}`);
                }

                const nodeData = nodeRes?.ok ? await nodeRes.json() as NodesResponse : null;
                let indicatorsData = null;
                if (indicatorsRes?.ok) {
                    indicatorsData = await indicatorsRes.json();
                    if (!indicatorsData.error && !controller.signal.aborted) setIndicators(indicatorsData);
                }

                const signalsPayload = await signalsRes.json() as SignalsResponse;
                const trendsPayload = trendsRes?.ok ? await trendsRes.json() as TrendsResponse : null;
                const wikiPayload = wikiRes?.ok ? await wikiRes.json() as WikiTopResponse : null;
                const forumPayload = forumRes?.ok ? await forumRes.json() as { forum?: { items?: Array<{ headline?: string | null; subreddit?: string | null; url?: string; source_lang?: string | null; id?: number }> } } : null;
                const threadsPayload = threadsRes?.ok ? await threadsRes.json() as ThreadsResponse : null;
                const voicePayload = voiceRes?.ok ? await voiceRes.json() as { relation?: VoiceMixRelation } : null;
                if (!controller.signal.aborted) setVoiceMix(voicePayload?.relation ?? null);
                const signals = signalsPayload.signals || [];
                const themeCounts = new Map<string, number>();
                const sourceCounts = new Map<string, number>();
                const personCounts = new Map<string, number>();
                let sentimentTotal = 0;

                signals.forEach(signal => {
                    sentimentTotal += signal.sentiment || 0;
                    incrementCount(sourceCounts, signal.source || (signal.url ? extractDomain(signal.url) : undefined));
                    (signal.themes || []).forEach(theme => incrementCount(themeCounts, theme));
                    (signal.persons || []).forEach(person => incrementCount(personCounts, person));
                });

                // Surface the country's OWN-language press first: a brief about
                // Italy should lead with Italian headlines (translated), not only
                // GDELT's English coverage of Italy. Non-English/known-language
                // signals rank ahead of en/xx, otherwise order is preserved.
                const isOwnVoice = (s: SignalResponseItem) => {
                    const l = (s.source_lang || '').toLowerCase();
                    return l && !['en', 'xx', 'un', 'und'].includes(l);
                };
                const topStories: Story[] = signals
                    .filter((s): s is SignalResponseItem & { url: string } => Boolean(s.url))
                    .slice()
                    .sort((a, b) => Number(isOwnVoice(b)) - Number(isOwnVoice(a)))
                    .slice(0, 10)
                    .map((s) => {
                        const themes: string[] = Array.isArray(s.themes) ? s.themes : [];
                        const primaryTheme = themes.find(
                            (t: string) => t && !t.startsWith('WORLDLANGUAGES_') && !t.startsWith('TAX_WORLDLANGUAGES_')
                        ) || themes[0] || '';
                        return {
                            url: s.url,
                            source: s.source || extractDomain(s.url),
                            timestamp: s.timestamp || new Date().toISOString(),
                            sentiment: s.sentiment || 0,
                            themeCode: primaryTheme,
                            headline: s.headline ? decodeEntities(s.headline) : s.headline,
                            id: s.id,
                            source_lang: (s as SignalResponseItem & { source_lang?: string | null }).source_lang,
                        };
                    });

                const node = nodeData?.nodes?.[0];
                const focusSummary = summary?.focus.type === 'country' && summary.focus.value === countryCode
                    ? summary
                    : null;
                const summarySources = focusSummary?.top_sources.map(source => ({
                    name: source.source,
                    count: source.count,
                })) ?? [];
                const sentiment = node?.sentiment ?? (signals.length > 0 ? sentimentTotal / signals.length : 0);
                let sentimentTrend: 'improving' | 'declining' | 'stable' = 'stable';
                if (sentiment > 0.5) sentimentTrend = 'improving';
                else if (sentiment < -0.5) sentimentTrend = 'declining';

                if (controller.signal.aborted) return;
                setData({
                    country_code: countryCode,
                    hours: timeWindow,
                    signal_count: focusSummary?.summary.total_signals ?? node?.signalCount ?? signals.length,
                    top_themes: topCounts(themeCounts, 12),
                    narrative_threads: threadsPayload?.threads ?? [],
                    top_sources: summarySources.length > 0 ? summarySources : topCounts(sourceCounts, 15),
                    keySubjects: buildKeySubjects(topCounts(personCounts, 40), 8),
                    avg_sentiment: sentiment,
                    sentiment_trend: sentimentTrend,
                    top_stories: topStories,
                    publicAttention: {
                        searches: (trendsPayload?.trending ?? []).slice(0, 5),
                        wikiArticles: Array.from(new Map((wikiPayload?.articles ?? []).map((a: { title: string }) => [a.title, a])).values()).slice(0, 5),
                        // L3 (Pedro): forums ARE public attention — one surface,
                        // per-source badges; forum items stay verified=false.
                        forum: (forumPayload?.forum?.items ?? []).slice(0, 4),
                    },
                    indicators: indicatorsData,
                    foreignSourcePct: null,
                });
            } catch (err) {
                if (controller.signal.aborted) return;
                setError(err instanceof Error ? err.message : 'Failed to load data');
            } finally {
                if (!controller.signal.aborted) setLoading(false);
            }
        };

        if (countryCode) {
            fetchData();
        }

        return () => controller.abort();
    }, [countryCode, timeWindow, summary]);

    if (loading) {
        return (
            <div className={cls}>
                <div className="brief-header">
                    <div className="brief-title">
                        <Flag code={countryCode} title={displayCountryName} className="country-flag" />
                        <h2>{displayCountryName}</h2>
                    </div>
                    <button className="close-button" onClick={onClose}>✕</button>
                </div>
                <div className="brief-loading">
                    <div className="spinner"></div>
                    <p>Loading brief...</p>
                </div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className={cls}>
                <div className="brief-header">
                    <div className="brief-title">
                        <Flag code={countryCode} title={displayCountryName} className="country-flag" />
                        <h2>{displayCountryName}</h2>
                    </div>
                    <button className="close-button" onClick={onClose}>✕</button>
                </div>
                <div className="brief-error">
                    <p>Error: {error || 'No data available'}</p>
                </div>
            </div>
        );
    }

    const threadSummary = buildCountryBriefThreadSummary({
        threads: data.narrative_threads,
        fallbackThemes: data.top_themes,
    })

    // #173 Evidence Route breadcrumb — the coverage funnel from this Country
    // down to the raw Evidence Signals. Foreign share prefers the ownership-based
    // voice-mix ratio; falls back to foreignSourcePct; omitted when neither known.
    const foreignPct = voiceMix && voiceMix.attributable_voices > 0
        ? Math.round(voiceMix.foreign_voice_ratio * 100)
        : (typeof data.foreignSourcePct === 'number' ? data.foreignSourcePct : null)
    const evidenceRouteSteps = buildEvidenceRoute({
        countryName: displayCountryName,
        outletCount: data.top_sources.length,
        foreignSourcePct: foreignPct,
        atlasTopicCount: data.top_themes.length,
        narrativeThreadCount: threadSummary.count,
        evidenceSignalCount: data.signal_count,
    })
    const scrollToSection = (targetId: string) => {
        document.getElementById(targetId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }

    return (
        <div className={cls}>
            <div className="brief-header" id="cb-header">
                <div className="brief-title">
                    <div className="cb-kicker">COUNTRY INTELLIGENCE</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Flag code={countryCode} title={displayCountryName} className="country-flag" />
                        <h2>{displayCountryName}</h2>
                        <button
                            className={`cb-icon-btn${pinned ? ' active' : ''}`}
                            onClick={() => {
                                const pinnedId = `country-${countryCode}`
                                if (pinned) {
                                    unpinItem(pinnedId)
                                } else {
                                    const params = new URLSearchParams()
                                    params.set('country', countryCode)
                                    pinItem({
                                        id: pinnedId,
                                        type: 'country',
                                        title: displayCountryName,
                                        urlParams: `?${params.toString()}`
                                    })
                                }
                            }}
                            data-tip={pinned ? 'Remove from Investigation Workspace' : 'Pin to Investigation Workspace'}
                        >
                            {pinned ? <PinOff size={12} /> : <Pin size={12} />}
                        </button>
                    </div>
                </div>
                <div className="brief-header-actions">
                    <button
                        className="brief-export-button"
                        onClick={handleExportBrief}
                        data-tip="Export country brief as Markdown"
                        aria-label="Export country brief"
                    >
                        <Download size={13} />
                        <span className="brief-export-label">Export</span>
                    </button>
                    <button className="close-button" onClick={onClose} aria-label="Close brief">
                        ✕
                    </button>
                </div>
            </div>

            {/* #173 Evidence Route — the honest coverage funnel, each chip its real
                count, clickable to scroll to the panel it names. */}
            <EvidenceRoute steps={evidenceRouteSteps} onStepClick={scrollToSection} />

            <div className="cb-metrics">
                <div>
                    <span className="cb-metric-value">
                        {data.signal_count.toLocaleString()}
                        <CountQualifierChip count={data.signal_count} windowLabel={`${timeWindow}h`} base="raw" />
                    </span>
                    <span className="cb-metric-label">signals</span>
                </div>
                <div>
                    <span className="cb-metric-value" style={{ color: getSentimentColor(data.avg_sentiment * 10) }}>
                        {data.avg_sentiment >= 0 ? '+' : ''}{(data.avg_sentiment * 10).toFixed(1)}
                    </span>
                    <span className="cb-metric-label">sentiment</span>
                </div>
                <div>
                    <span className="cb-metric-value">
                        {threadSummary.count}
                    </span>
                    <span className="cb-metric-label">{threadSummary.label}</span>
                </div>
            </div>

            {anomaly && (
                <div className="anomaly-badge">
                    <span className="anomaly-badge-icon">▲</span>
                    <span>{anomaly.multiplier.toFixed(0)}× above 7-day baseline</span>
                    <span className="anomaly-badge-level">{anomaly.level?.toUpperCase()}</span>
                </div>
            )}

            <p className="cb-connection-note cb-connection-note--analysis">
                {buildCountryPublicAttentionNarrative({
                    countryName: displayCountryName,
                    signalCount: data.signal_count,
                    hours: timeWindow,
                    topThemes: data.top_themes,
                    topSearches: data.publicAttention?.searches,
                    topWikiArticles: data.publicAttention?.wikiArticles,
                    topThread: (() => {
                        const t = threadSummary.rows.find(r => !r.belowGate)
                        return t ? { label: t.label, count: t.count } : undefined
                    })(),
                })}
                {(() => {
                    // D9: only name people with real corroboration — a 1-signal
                    // byline told the reader nothing ("include Agnes").
                    const people = data.keySubjects.filter(s => s.type === 'person' && (s.count ?? 0) >= 5);
                    return people.length >= 2
                        ? ` Most-covered figures: ${people.slice(0, 2).map(p => p.name).join(' and ')}.`
                        : '';
                })()}
            </p>

            {/* Narrative Threads */}
            <section className="brief-section" id="cb-threads">
                <div className="cb-section-label">Narrative Threads</div>
                <div className="theme-list">
                    {/* B1: no positional "critical" marker — a country volume spike
                        doesn't make the first thread critical. B2 (#214): show the
                        GATED count (what the detail panel serves), with raw on hover,
                        and split below-gate threads into the UNVERIFIED tray below so
                        raw coverage stops masquerading as a confident thread. */}
                    {threadSummary.rows
                        .filter(t => !t.belowGate)
                        .slice(0, 8)
                        .map((thread, i) => (
                        <button
                            key={i}
                            className="theme-chip"
                            onClick={() => onThemeSelect?.(thread.name)}
                            data-tip={thread.rawCount > thread.count
                                ? `${countQualifier(thread.count, `${timeWindow}h`, 'verified').tip} ${thread.rawCount.toLocaleString()} were assigned before the gate. Click to open the thread.`
                                : `Click to open ${thread.label} narrative thread`}
                        >
                            <span className="theme-name">
                                {thread.label}
                                {/* N15: court failed/partial → compact under-review dot
                                    (shared chip, dot variant — dense chip row). */}
                                <LabelReviewChip labelStatus={thread.labelStatus} variant="dot" />
                            </span>
                            <span className="theme-count">
                                {thread.count}
                                {thread.rawCount > thread.count && (
                                    <CountQualifierChip count={thread.count} windowLabel={`${timeWindow}h`} base="verified" />
                                )}
                            </span>
                        </button>
                    ))}
                </div>
                {threadSummary.rows.some(t => t.belowGate) && (
                    <details className="cb-belowgate-tray">
                        <summary>
                            {threadSummary.rows.filter(t => t.belowGate).length} unverified · raw coverage, nothing cleared the relevance gate
                        </summary>
                        <div className="theme-list">
                            {threadSummary.rows
                                .filter(t => t.belowGate)
                                .slice(0, 8)
                                .map((thread, i) => (
                                <button
                                    key={i}
                                    className="theme-chip theme-chip--unverified"
                                    onClick={() => onThemeSelect?.(thread.name)}
                                    data-tip={`${thread.rawCount} assigned, 0 cleared the gate — open to inspect the raw coverage`}
                                >
                                    <span className="theme-name">
                                        {thread.label}
                                        <LabelReviewChip labelStatus={thread.labelStatus} variant="dot" />
                                    </span>
                                    <span className="theme-count">{thread.rawCount}</span>
                                </button>
                            ))}
                        </div>
                    </details>
                )}
            </section>

            {/* Conflict events (#232 UX slice) — the same markers the map/dock
                show, joined to this country by GEOGRAPHY only. Honest framing:
                GDELT CAMEO is machine-coded and geo is approximate. */}
            {countryConflicts.length > 0 && (
                <section className="brief-section">
                    <div className="cb-section-label">
                        Conflict Events <span className="cb-section-subcopy">related by country, not by story</span>
                    </div>
                    <p className="cb-conflict-note"
                        data-tip="GDELT CAMEO events are machine-coded from news mentions; locations are approximate. ACLED rows (A) are analyst-verified.">
                        {countryConflicts.length} event{countryConflicts.length === 1 ? '' : 's'} in {displayCountryName} this window · machine-coded, geo approximate
                    </p>
                    <div className="cb-conflict-list">
                        {countryConflicts.slice(0, showAllConflicts ? 15 : 5).map(ev => {
                            const src = ev.source === 'gdelt_events' ? 'G' : 'A';
                            const actors = [ev.actors?.actor1, ev.actors?.actor2].filter(Boolean).join(' → ');
                            // Jargon purge (wish 7): CAMEO codebook imperatives ("Use
                            // unconventional violence") read as leaked internals — show
                            // the human event noun; the verbatim codebook string moves
                            // into the hover, never deleted.
                            const humanType = humanizeCameoEvent(ev.type);
                            const tipParts = [
                                actors ? `${actors}${ev.date ? ` · ${ev.date.slice(0, 10)}` : ''}` : (ev.date ? ev.date.slice(0, 10) : null),
                                ev.type && ev.type !== humanType ? `CAMEO codebook: “${ev.type}”` : null,
                            ].filter(Boolean);
                            return (
                                <div key={ev.id} className="cb-conflict-row"
                                    data-tip={tipParts.length ? tipParts.join(' · ') : undefined}>
                                    <span className={`cb-conflict-src cb-conflict-src--${src.toLowerCase()}`}>{src}</span>
                                    <span className="cb-conflict-type">{humanType}</span>
                                    <span className="cb-conflict-place">{ev.location?.name || ''}</span>
                                    {ev.fatalities > 0 && <span className="cb-conflict-fatal">{ev.fatalities}†</span>}
                                </div>
                            );
                        })}
                    </div>
                    {countryConflicts.length > 5 && (
                        <button className="cb-conflict-toggle" onClick={() => setShowAllConflicts(v => !v)}>
                            {showAllConflicts ? 'Show fewer' : `Show all ${Math.min(countryConflicts.length, 15)}`}
                        </button>
                    )}
                </section>
            )}

            {/* Public Attention */}
            <section className="brief-section">
                <div className="cb-section-label">Public Attention <span className="cb-section-subcopy">people-side proxy</span></div>
                <p className="cb-public-attention-note">
                    Google searches and Wikipedia pageviews are country/language-edition proxies. They enrich the media picture, but they are not a population-normalized opinion poll.
                </p>
                <div className="cb-attention-grid">
                    <div className="cb-attention-column">
                        <span className="cb-attention-heading">Search</span>
                        {(data.publicAttention?.searches ?? []).length > 0 ? (
                            data.publicAttention!.searches.filter(x => isPublicAttentionRelevant(x.keyword)).slice(0, 4).map(item => (
                                <div
                                    key={item.keyword}
                                    className={`cb-attention-row${onAttentionItemClick ? ' cb-attention-row--clickable' : ''}`}
                                    onClick={onAttentionItemClick ? () => onAttentionItemClick(item.keyword) : undefined}
                                    data-tip={onAttentionItemClick ? `Investigate "${item.keyword}"` : undefined}
                                >
                                    <span>{item.keyword}</span>
                                    <strong>{item.rank ? `#${item.rank}` : 'trend'}</strong>
                                </div>
                            ))
                        ) : (
                            <div className="cb-attention-empty">No Google Trends data for this window.</div>
                        )}
                    </div>
                    <div className="cb-attention-column">
                        <span className="cb-attention-heading">Wiki</span>
                        {(data.publicAttention?.wikiArticles ?? []).length > 0 ? (
                            data.publicAttention!.wikiArticles.filter(w => isPublicAttentionRelevant(w.title)).slice(0, 4).map(item => (
                                <div
                                    key={item.title}
                                    className={`cb-attention-row${onAttentionItemClick ? ' cb-attention-row--clickable' : ''}`}
                                    onClick={onAttentionItemClick ? () => onAttentionItemClick(item.title.replace(/_/g, ' ')) : undefined}
                                    data-tip={onAttentionItemClick ? `Investigate "${item.title.replace(/_/g, ' ')}"` : undefined}
                                >
                                    <span>{item.title.replace(/_/g, ' ')}</span>
                                    <strong>{(item.views ?? 0).toLocaleString()}</strong>
                                </div>
                            ))
                        ) : (
                            <div className="cb-attention-empty">No Wikipedia pageview data for this proxy.</div>
                        )}
                    </div>
                    <div className="cb-attention-column">
                        <span className="cb-attention-heading">Forum <span className="cb-forum-unverified">unverified</span></span>
                        {(data.publicAttention?.forum ?? []).length > 0 ? (
                            data.publicAttention!.forum!.map((f, i) => (
                                <a
                                    key={i}
                                    className="cb-attention-row cb-attention-row--forum"
                                    href={f.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    data-tip={f.subreddit ? `Discussion on ${f.subreddit} — open thread` : 'Open discussion'}
                                >
                                    <span>{f.headline ? decodeEntities(f.headline) : '(untitled)'}</span>
                                    {f.subreddit && <strong className="cb-forum-src">{f.subreddit}</strong>}
                                </a>
                            ))
                        ) : (
                            <div className="cb-attention-empty">No forum discussion mentioning this country in the window.</div>
                        )}
                    </div>
                </div>
            </section>

            {/* Key Subjects — typed: person is one type, not the only one (#176) */}
            {data.keySubjects.length > 0 && (
                <section className="brief-section">
                    <div className="cb-section-label">Key Subjects <span style={{ fontWeight: 400, textTransform: 'none', opacity: 0.6 }}>people, places &amp; topics in the coverage</span></div>
                    <div className="brief-person-list">
                        {data.keySubjects.map(subject => {
                            const clickable = subject.type === 'person';
                            return (
                                <button
                                    key={`${subject.type}:${subject.name}`}
                                    className="brief-person-chip"
                                    onClick={clickable ? () => setPerson(subject.name) : undefined}
                                    disabled={!clickable}
                                    data-tip={clickable
                                        ? `${subject.count} mentions — open person focus`
                                        : `${subject.type} · ${subject.count} mentions`}
                                >
                                    <span className="brief-subject-badge" data-type={subject.type}>{SUBJECT_BADGE[subject.type]}</span>
                                    <span className="brief-person-name">{subject.name}</span>
                                    <span className="brief-person-count">{subject.count}</span>
                                </button>
                            );
                        })}
                    </div>
                </section>
            )}

            {/* Trust Indicators */}
            {indicators && !(indicators as Indicators & { error?: string }).error && (
                <section className="brief-section">
                    <div className="cb-section-label">Trust Indicators</div>
                    <div className="indicators-stack">
                        <IndicatorTooltip
                            score={indicators.diversity?.score || 0}
                            label="Source Diversity"
                            tooltip={indicators.diversity?.tooltip || 'No data available'}
                        />
                        <IndicatorTooltip
                            score={indicators.quality?.score || 0}
                            label="Source Quality"
                            tooltip={indicators.quality?.tooltip || 'No data available'}
                        />
                        <VolumeIndicator
                            multiplier={indicators.volume?.multiplier || null}
                            zScore={indicators.volume?.z_score || null}
                            level={indicators.volume?.level || 'unknown'}
                            tooltip={indicators.volume?.tooltip || 'No data available'}
                        />
                    </div>
                </section>
            )}

            {/* Voice Mix — self-coverage vs outside voices (#235) */}
            {voiceMix && voiceMix.attributable_voices > 0 && (() => {
                const selfPct = Math.round(voiceMix.self_voice_ratio * 100);
                const softPct = Math.round(voiceMix.soft_power_ratio * 100);
                const barColor = selfPct >= 50 ? 'var(--accent-green, #34d399)'
                    : selfPct >= 20 ? 'var(--accent-amber, #fbbf24)'
                    : 'var(--accent-red, #f87171)';
                return (
                    <section className="brief-section">
                        <div className="cb-section-label">
                            Voice Mix
                            <span className="sentiment-info-icon" data-tip="Self-coverage is defined by outlet OWNERSHIP, not language: a domestic outlet covering its own country. Foreign outlets in the local language (e.g. BBC Persian) count as soft power, not self-coverage. Ratios are over signals whose outlet origin is known.">?</span>
                        </div>
                        <div style={{ fontSize: '1.4rem', fontWeight: 700, color: barColor }}>
                            {selfPct}% <span style={{ fontSize: '0.8rem', fontWeight: 400, color: 'var(--text-secondary, #9ca3af)' }}>covered by its own press</span>
                        </div>
                        <div style={{ height: 6, borderRadius: 3, background: 'var(--bg-tertiary, #1f2937)', margin: '6px 0 8px', overflow: 'hidden' }}>
                            <div style={{ width: `${selfPct}%`, height: '100%', background: barColor }} />
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary, #9ca3af)', lineHeight: 1.5 }}>
                            {voiceMix.self_voice} of {voiceMix.attributable_voices} attributable voices are domestic.
                            {voiceMix.dominant_outsider && (
                                <> Loudest outsider: <strong>{voiceMix.dominant_outsider.origin}</strong> ({voiceMix.dominant_outsider.n}).</>
                            )}
                            {softPct > 0 && (
                                <> {softPct}% is foreign media in the local language (soft power, not self-coverage).</>
                            )}
                        </div>
                    </section>
                );
            })()}

            {/* Sentiment */}
            <section className="brief-section">
                <div className="cb-section-label">Sentiment Overview <span className="sentiment-info-icon" data-tip="Scores range from −10 to +10. Negative = reporting is alarming, critical, or conflict-focused. Positive = coverage is favorable or optimistic. This reflects media tone, not whether the news is objectively good or bad.">?</span></div>
                <div className="sentiment-display">
                    <span
                        className="sentiment-value"
                        style={{ color: getSentimentColor(data.avg_sentiment * 10) }}
                    >
                        {data.avg_sentiment >= 0 ? '+' : ''}{(data.avg_sentiment * 10).toFixed(1)}
                    </span>
                    <span className="sentiment-label">
                        {getSentimentLabel(data.avg_sentiment * 10)}
                    </span>
                    {data.signal_count < 10 && (
                        <span className="coverage-badge coverage-badge--thin" data-tip={`Only ${data.signal_count} signals in this window — treat as indicative only`}>
                            thin coverage
                        </span>
                    )}
                    {data.signal_count >= 10 && data.signal_count < 50 && (
                        <span className="coverage-badge coverage-badge--limited" data-tip={`${data.signal_count} signals — limited data, interpret with caution`}>
                            limited
                        </span>
                    )}
                    <span className="sentiment-trend">
                        {data.sentiment_trend === 'improving' && '↑ Improving'}
                        {data.sentiment_trend === 'declining' && '↓ Declining'}
                        {data.sentiment_trend === 'stable' && '→ Stable'}
                    </span>
                </div>
                <p className="sentiment-warning">
                    Sentiment analysis is noisy and should be interpreted cautiously.
                </p>
                {data.foreignSourcePct !== null && data.foreignSourcePct !== undefined && data.foreignSourcePct > 60 && (
                    <p className="geo-provenance-warning" data-tip="Most coverage comes from media outlets based outside this country. Signals reflect how foreign media covers this country, not necessarily local events.">
                        {data.foreignSourcePct}% foreign-sourced coverage
                    </p>
                )}
            </section>

            {/* Top Sources */}
            <section className="brief-section" id="cb-sources">
                <div className="cb-section-label">Top Publishers <span style={{ fontWeight: 400, textTransform: 'none', opacity: 0.6 }}>who's covering this country</span></div>
                <div className="source-list">
                    {(showAllSources ? data.top_sources : data.top_sources.slice(0, 5)).map((source, i) => {
                        // Expand-in-place pattern (mirrors ThemeDetail): click a
                        // publisher → its recent coverage opens inline + a "Full
                        // source profile ↗" link to the full panel. No silent
                        // jump to the bare profile.
                        const isOpen = expandedSource === source.name
                        const localStories = isOpen
                            ? (data.top_stories || []).filter(s => s.source === source.name)
                            : []
                        const srcStories = localStories.length > 0
                            ? localStories
                            : (isOpen && sourceFetch?.name === source.name ? sourceFetch.stories : [])
                        const srcLoading = isOpen && localStories.length === 0 && sourceFetch?.name === source.name && sourceFetch.loading
                        // Gold-eval defect (batch 4): this row had zero tier reference —
                        // state media (irna.ir) rendered indistinguishable from any other
                        // outlet. No per-source origin/is_state_media in this aggregate,
                        // so 'unknown' is suppressed rather than guessed (absence over noise).
                        const tc = resolveTierChip(source.name, undefined)
                        return (
                            <div key={i} className="source-group">
                                <button
                                    type="button"
                                    className={`source-item source-item--btn${isOpen ? ' source-active' : ''}`}
                                    onClick={() => setExpandedSource(isOpen ? null : source.name)}
                                    data-tip={`Read ${source.name}'s recent coverage of this country`}
                                >
                                    <span className="source-name">{source.name}</span>
                                    {tc.tier !== 'unknown' && (
                                        <span className={`l2-tier-chip l2-tier-chip--${tc.tier}`} data-tip={tc.tip}>{tc.label}</span>
                                    )}
                                    <span className="source-count">{source.count} signals</span>
                                    <span className="source-see-articles">{isOpen ? '▴' : '▾'}</span>
                                </button>
                                {isOpen && (
                                    <div className="source-coverage">
                                        {onSourceClick && (
                                            <button
                                                type="button"
                                                className="source-full-profile-btn"
                                                onClick={(e) => { e.stopPropagation(); onSourceClick(source.name) }}
                                            >
                                                Full source profile ↗
                                            </button>
                                        )}
                                        {srcLoading ? (
                                            <p className="coverage-source-empty">Loading {source.name}'s coverage…</p>
                                        ) : srcStories.length === 0 ? (
                                            <p className="coverage-source-empty">
                                                Couldn't fetch {source.name}'s articles right now —
                                                the {source.count}-signal count is from the {timeWindow}h window.
                                            </p>
                                        ) : (
                                            <div className="coverage-articles">
                                                {srcStories.slice(0, 8).map((story, j) => (
                                                    <a
                                                        key={j}
                                                        href={story.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="story-item"
                                                        data-tip="Open article in new tab"
                                                    >
                                                        <p className="story-source-line">
                                                            <span className="story-age">{timeAgo(story.timestamp)}</span>
                                                        </p>
                                                        {story.headline && (
                                                            <p className="story-headline" style={{ margin: '2px 0 4px', fontSize: '0.85rem', lineHeight: 1.35 }}>
                                                                {typeof story.id === 'number'
                                                                    ? <TranslatableHeadline signalId={story.id} original={story.headline} sourceLang={story.source_lang} />
                                                                    : story.headline}
                                                            </p>
                                                        )}
                                                    </a>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )
                    })}
                    {data.top_sources.length > 5 && (
                        <button
                            type="button"
                            className="source-show-all-btn"
                            onClick={() => setShowAllSources(v => !v)}
                            data-tip={showAllSources ? 'Collapse back to the top 5' : `Show the remaining ${data.top_sources.length - 5} publishers`}
                        >
                            {showAllSources
                                ? 'Show top 5 only'
                                : `Show all ${data.top_sources.length} publishers`}
                        </button>
                    )}
                </div>
            </section>

            {/* Recent Signals — actual articles detected, not synthetic titles */}
            {data.top_stories && data.top_stories.length > 0 && (
                <section className="brief-section" id="cb-signals">
                    <div className="cb-section-label">Recent Signals <span style={{ fontWeight: 400, textTransform: 'none', opacity: 0.6 }}>articles detected in last {timeWindow}h</span></div>
                    <div className="story-list">
                        {data.top_stories.slice(0, 6).map((story, i) => (
                            <a
                                key={i}
                                href={story.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="story-item"
                                data-tip="Open article in new tab"
                            >
                                <p className="story-source-line" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <span className="story-domain">{extractDomain(story.url)}</span>
                                    <span className="story-age">{timeAgo(story.timestamp)}</span>
                                    <span style={{ marginLeft: 'auto' }}>
                                        <PinReceiptButton
                                            contextLabel={displayCountryName}
                                            citation={{
                                                headline: story.headline || extractDomain(story.url),
                                                source: extractDomain(story.url) || undefined,
                                                url: story.url || undefined,
                                                // N1: countryCode is the BRIEF's country (story
                                                // subject scope), not the outlet's origin — never
                                                // stored as an origin assertion.
                                                sourceLang: story.source_lang || undefined,
                                                gateStatus: 'unknown',
                                                publishedDate: story.timestamp ? String(story.timestamp).slice(0, 10) : undefined,
                                            }}
                                        />
                                    </span>
                                </p>
                                {story.headline && (
                                    <p className="story-headline" style={{ margin: '2px 0 4px', fontSize: '0.85rem', lineHeight: 1.35 }}>
                                        {typeof story.id === 'number'
                                            ? <TranslatableHeadline signalId={story.id} original={story.headline} sourceLang={story.source_lang} />
                                            : story.headline}
                                    </p>
                                )}
                                {story.themeCode && (
                                    <span
                                        className="story-theme-badge"
                                        onClick={(e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            onThemeSelect?.(story.themeCode);
                                        }}
                                        data-tip={`Open narrative thread: ${getThemeLabel(story.themeCode)}`}
                                    >
                                        {getThemeLabel(story.themeCode)}
                                    </span>
                                )}
                            </a>
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
};

export default CountryBrief;
