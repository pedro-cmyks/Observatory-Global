import React, { useState, useEffect } from 'react';
import { IndicatorTooltip, VolumeIndicator } from './IndicatorTooltip';
import { useCrisis } from '../contexts/CrisisContext';
import { useWorkspace } from '../contexts/WorkspaceContext';
import { useFocus } from '../contexts/FocusContext';
import { Download, Pin, PinOff } from '../lib/icons';
import './CountryBrief.css';
import { getThemeLabel } from '../lib/themeLabels';
import { selectVisibleKeyPersons, type KeyPerson } from '../lib/countryBriefPeople';
import { buildCountryBriefMarkdown, sanitizeFilenamePart } from '../lib/exportFormatters';
import { resolveCountryName } from '../lib/countryNames';
import { useFocusData } from '../contexts/FocusDataContext';
import {
    buildCountryPublicAttentionNarrative,
    getPublicAttentionTopUrl,
    getTrendingSearchesUrl,
} from '../lib/publicAttention';
import { buildCountryBriefThreadSummary, type CountryBriefThreadInput } from '../lib/countryBriefThreads';
import { optionalFetchResponse } from '../lib/countryBriefFetch';

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
    keyPersons: KeyPerson[];
    avg_sentiment: number;
    sentiment_trend: 'improving' | 'declining' | 'stable';
    top_stories?: Story[];
    publicAttention?: {
        searches: Array<{ keyword: string; rank?: number | null }>;
        wikiArticles: Array<{ title: string; views?: number | null }>;
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
    url?: string;
    source?: string;
    timestamp?: string;
    sentiment?: number;
    themes?: string[];
    persons?: string[];
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

// Country flag emoji from code
// Country flag wrapper
const getCountryFlag = (code: string): string => {
    return code;
};

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
    onSourceClick: _onSourceClick,
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
    const { summary } = useFocusData();
    const pinned = isPinned(`country-${countryCode}`);
    const [voiceMix, setVoiceMix] = useState<VoiceMixRelation | null>(null);

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
        const md = buildCountryBriefMarkdown({ countryName: displayCountryName, data })
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
                const [nodeRes, indicatorsRes, signalsRes, trendsRes, wikiRes, threadsRes, voiceRes] = await Promise.all([
                    optionalFetchResponse(() => fetch(`/api/v2/nodes?focus_type=country&focus_value=${countryCode}&hours=${timeWindow}&limit=1`, { signal: controller.signal })),
                    optionalFetchResponse(() => fetch(`/api/indicators/country/${countryCode}?hours=${timeWindow}`, { signal: controller.signal })),
                    fetch(`/api/v2/signals?country_code=${countryCode}&hours=${timeWindow}&limit=500`, { signal: controller.signal }),
                    optionalFetchResponse(() => fetch(getTrendingSearchesUrl(5, Math.min(timeWindow, 168), countryCode), { signal: controller.signal })),
                    optionalFetchResponse(() => fetch(getPublicAttentionTopUrl(5, countryCode), { signal: controller.signal })),
                    optionalFetchResponse(() => fetch(`/api/v2/threads?hours=${timeWindow}&limit=24&country_code=${countryCode}`, { signal: controller.signal })),
                    optionalFetchResponse(() => fetch(`/api/v2/voice-mix?hours=${Math.max(timeWindow, 168)}&country=${countryCode}`, { signal: controller.signal })),
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

                const topStories: Story[] = signals
                    .filter((s): s is SignalResponseItem & { url: string } => Boolean(s.url))
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
                            themeCode: primaryTheme
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
                    top_sources: summarySources.length > 0 ? summarySources : topCounts(sourceCounts, 8),
                    keyPersons: selectVisibleKeyPersons(topCounts(personCounts, 20)),
                    avg_sentiment: sentiment,
                    sentiment_trend: sentimentTrend,
                    top_stories: topStories,
                    publicAttention: {
                        searches: (trendsPayload?.trending ?? []).slice(0, 5),
                        wikiArticles: Array.from(new Map((wikiPayload?.articles ?? []).map((a: { title: string }) => [a.title, a])).values()).slice(0, 5),
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
                        <span className="country-flag">{getCountryFlag(countryCode)}</span>
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
                        <span className="country-flag">{getCountryFlag(countryCode)}</span>
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

    return (
        <div className={cls}>
            <div className="brief-header">
                <div className="brief-title">
                    <div className="cb-kicker">COUNTRY INTELLIGENCE</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="country-flag">{getCountryFlag(countryCode)}</span>
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
                        Export
                    </button>
                    <button className="close-button" onClick={onClose} aria-label="Close brief">
                        ✕
                    </button>
                </div>
            </div>

            <div className="cb-metrics">
                <div>
                    <span className="cb-metric-value">{data.signal_count.toLocaleString()}</span>
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
                })}
                {data.keyPersons.length > 0
                    ? ` People most visible in the media layer include ${data.keyPersons.slice(0, 2).map(p => p.name).join(' and ')}.`
                    : ''}
            </p>

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
                            data.publicAttention!.searches.slice(0, 4).map(item => (
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
                            data.publicAttention!.wikiArticles.slice(0, 4).map(item => (
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
                </div>
            </section>

            {/* Narrative Threads */}
            <section className="brief-section">
                <div className="cb-section-label">Narrative Threads</div>
                <div className="theme-list">
                    {threadSummary.rows
                        .slice(0, 8)
                        .map((thread, i) => (
                        <button
                            key={i}
                            className={`theme-chip${anomaly && i === 0 ? ' anomaly-spike' : ''}`}
                            onClick={() => onThemeSelect?.(thread.name)}
                            data-tip={`Click to open ${thread.label} narrative thread`}
                        >
                            {anomaly && i === 0 && <span className="spike-bars">▂▄▇</span>}
                            <span className="theme-name">{thread.label}</span>
                            <span className="theme-count">{thread.count}</span>
                        </button>
                    ))}
                </div>
            </section>

            {/* Key People */}
            {data.keyPersons.length > 0 && (
                <section className="brief-section">
                    <div className="cb-section-label">People Mentioned <span style={{ fontWeight: 400, textTransform: 'none', opacity: 0.6 }}>click to filter signals</span></div>
                    <div className="brief-person-list">
                        {data.keyPersons.map(person => (
                            <button
                                key={person.name}
                                className="brief-person-chip"
                                onClick={() => setPerson(person.name)}
                                data-tip={`${person.count} mentions — open person focus`}
                            >
                                <span className="brief-person-name">{person.name}</span>
                                <span className="brief-person-count">{person.count}</span>
                            </button>
                        ))}
                    </div>
                </section>
            )}

            {/* Top Sources */}
            <section className="brief-section">
                <div className="cb-section-label">Top Publishers <span style={{ fontWeight: 400, textTransform: 'none', opacity: 0.6 }}>who's covering this country</span></div>
                <div className="source-list">
                    {data.top_sources.slice(0, 5).map((source, i) => (
                        <div key={i} className="source-item">
                            <span className="source-name">{source.name}</span>
                            <span className="source-count">{source.count} signals</span>
                        </div>
                    ))}
                </div>
            </section>

            {/* Recent Signals — actual articles detected, not synthetic titles */}
            {data.top_stories && data.top_stories.length > 0 && (
                <section className="brief-section">
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
                                <p className="story-source-line">
                                    <span className="story-domain">{extractDomain(story.url)}</span>
                                    <span className="story-age">{timeAgo(story.timestamp)}</span>
                                </p>
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
