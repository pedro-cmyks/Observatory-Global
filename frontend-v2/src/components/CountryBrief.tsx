import React, { useState, useEffect } from 'react';
import { IndicatorTooltip, VolumeIndicator } from './IndicatorTooltip';
import { useCrisis } from '../contexts/CrisisContext';
import { useWorkspace } from '../contexts/WorkspaceContext';
import { useFocus } from '../contexts/FocusContext';
import { Download, Pin, PinOff } from 'lucide-react';
import './CountryBrief.css';
import { getThemeLabel } from '../lib/themeLabels';
import { selectVisibleKeyPersons, type KeyPerson } from '../lib/countryBriefPeople';
import { buildCountryBriefMarkdown, sanitizeFilenamePart } from '../lib/exportFormatters';
import { resolveCountryName } from '../lib/countryNames';

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
    top_sources: Array<{ name: string; count: number }>;
    keyPersons: KeyPerson[];
    avg_sentiment: number;
    sentiment_trend: 'improving' | 'declining' | 'stable';
    top_stories?: Story[];
    indicators?: Indicators;
    error?: string;
    foreignSourcePct?: number | null;
}

interface CountryAnomaly {
    country_code: string;
    multiplier: number;
    level?: string;
}

interface CountryDetailResponse {
    totalSignals?: number;
    themes?: Array<{ name: string; count: number }>;
    sources?: Array<{ name: string; count: number }>;
    keyPersons?: KeyPerson[];
    sentiment?: number;
    foreignSourcePct?: number | null;
}

interface SignalResponseItem {
    url?: string;
    source?: string;
    timestamp?: string;
    sentiment?: number;
    themes?: string[];
}

interface SignalsResponse {
    signals?: SignalResponseItem[];
}

interface CountryBriefProps {
    countryCode: string;
    countryName: string;
    timeWindow: number; // hours
    onClose: () => void;
    onThemeSelect?: (theme: string) => void;
    inline?: boolean;
}

// Country flag emoji from code
// Country flag wrapper
const getCountryFlag = (code: string): string => {
    return code;
};

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
    const pinned = isPinned(`country-${countryCode}`);

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
        const fetchData = async () => {
            setLoading(true);
            setError(null);

            try {
                // Fetch country detail
                const detailRes = await fetch(
                    `/api/v2/country/${countryCode}?hours=${timeWindow}`
                );
                if (!detailRes.ok) {
                    throw new Error(`Failed to fetch country data: ${detailRes.status}`);
                }
                const detail = await detailRes.json() as CountryDetailResponse;

                // Fetch indicators
                const indicatorsRes = await fetch(
                    `/api/indicators/country/${countryCode}?hours=${timeWindow}`
                );
                let indicatorsData = null;
                if (indicatorsRes.ok) {
                    indicatorsData = await indicatorsRes.json();
                    if (!indicatorsData.error) {
                        setIndicators(indicatorsData);
                    }
                }

                // Fetch signals for top stories
                const signalsRes = await fetch(
                    `/api/v2/signals?country_code=${countryCode}&hours=${timeWindow}&limit=10`
                );
                let topStories: Story[] = [];
                if (signalsRes.ok) {
                    const signals = await signalsRes.json() as SignalsResponse;
                    topStories = (signals.signals || [])
                        .filter((s): s is SignalResponseItem & { url: string } => Boolean(s.url))
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
                }

                // Determine sentiment trend (simplified - would need historical data)
                let sentimentTrend: 'improving' | 'declining' | 'stable' = 'stable';
                const sentiment = detail.sentiment || 0;
                if (sentiment > 0.5) sentimentTrend = 'improving';
                else if (sentiment < -0.5) sentimentTrend = 'declining';

                setData({
                    country_code: countryCode,
                    hours: timeWindow,
                    signal_count: detail.totalSignals || 0,
                    top_themes: detail.themes || [],
                    top_sources: detail.sources || [],
                    keyPersons: selectVisibleKeyPersons(detail.keyPersons || []),
                    avg_sentiment: sentiment,
                    sentiment_trend: sentimentTrend,
                    top_stories: topStories,
                    indicators: indicatorsData,
                    foreignSourcePct: detail.foreignSourcePct ?? null,
                });
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load data');
            } finally {
                setLoading(false);
            }
        };

        if (countryCode) {
            fetchData();
        }
    }, [countryCode, timeWindow]);

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
                        {data.top_themes.filter(t => !t.name.startsWith('WORLDLANGUAGES_') && !t.name.startsWith('TAX_WORLDLANGUAGES_')).length}
                    </span>
                    <span className="cb-metric-label">themes</span>
                </div>
            </div>

            {anomaly && (
                <div className="anomaly-badge">
                    <span className="anomaly-badge-icon">▲</span>
                    <span>{anomaly.multiplier.toFixed(0)}× above 7-day baseline</span>
                    <span className="anomaly-badge-level">{anomaly.level?.toUpperCase()}</span>
                </div>
            )}

            {data.top_themes.filter(t => !t.name.startsWith('WORLDLANGUAGES_') && !t.name.startsWith('TAX_WORLDLANGUAGES_')).length > 0 && (
                <p className="cb-connection-note">
                    Coverage driven by {data.top_themes
                        .filter(t => !t.name.startsWith('WORLDLANGUAGES_') && !t.name.startsWith('TAX_WORLDLANGUAGES_'))
                        .slice(0, 2)
                        .map(t => getThemeLabel(t.name))
                        .join(' and ')}
                    {data.keyPersons.length > 0
                        ? `, with focus on ${data.keyPersons.slice(0, 2).map(p => p.name).join(' and ')}`
                        : ''}.
                </p>
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

            {/* Top Themes */}
            <section className="brief-section">
                <div className="cb-section-label">Top Themes</div>
                <div className="theme-list">
                    {data.top_themes
                        .filter(t => !t.name.startsWith('WORLDLANGUAGES_') && !t.name.startsWith('TAX_WORLDLANGUAGES_'))
                        .slice(0, 8)
                        .map((theme, i) => (
                        <button
                            key={i}
                            className={`theme-chip${anomaly && i === 0 ? ' anomaly-spike' : ''}`}
                            onClick={() => onThemeSelect?.(theme.name)}
                            data-tip={`Click to open ${getThemeLabel(theme.name)} narrative thread`}
                        >
                            {anomaly && i === 0 && <span className="spike-bars">▂▄▇</span>}
                            <span className="theme-name">{getThemeLabel(theme.name)}</span>
                            <span className="theme-count">{theme.count}</span>
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
