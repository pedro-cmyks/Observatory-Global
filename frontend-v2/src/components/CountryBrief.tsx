import React, { useState, useEffect } from 'react';
import { IndicatorTooltip, VolumeIndicator } from './IndicatorTooltip';
import { useCrisis } from '../contexts/CrisisContext';
import './CountryBrief.css';
import { getThemeLabel } from '../lib/themeLabels';

// ThemeChange interface reserved for future use
// interface ThemeChange {
//     theme: string;
//     change: number;
//     direction: 'up' | 'down';
//     count: number;
// }

interface Story {
    title: string;
    url: string;
    source: string;
    timestamp: string;
    sentiment: number;
    themeCode: string;
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
    avg_sentiment: number;
    sentiment_trend: 'improving' | 'declining' | 'stable';
    top_stories?: Story[];
    indicators?: Indicators;
    error?: string;
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
    const anomaly = anomalies.find((a: any) => a.country_code === countryCode) ?? null
    const [data, setData] = useState<BriefData | null>(null);
    const [indicators, setIndicators] = useState<Indicators | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

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
                const detail = await detailRes.json();

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
                    const signals = await signalsRes.json();
                    topStories = (signals.signals || [])
                        .filter((s: any) => s.url)
                        .map((s: any) => {
                            const themes: string[] = Array.isArray(s.themes) ? s.themes : [];
                            // Pick first non-language theme so badges link to real narrative threads
                            const primaryTheme = themes.find(
                                (t: string) => t && !t.startsWith('WORLDLANGUAGES_') && !t.startsWith('TAX_WORLDLANGUAGES_')
                            ) || themes[0] || '';
                            const label = primaryTheme ? getThemeLabel(primaryTheme) : '';
                            // If the label is identical to the raw code, it's unmapped — omit it
                            const title = (label && label !== primaryTheme) ? label : '';
                            return {
                                title,
                                url: s.url,
                                source: s.source,
                                timestamp: s.timestamp,
                                sentiment: s.sentiment,
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
                    avg_sentiment: sentiment,
                    sentiment_trend: sentimentTrend,
                    top_stories: topStories,
                    indicators: indicatorsData
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
                        <h2>{countryName}</h2>
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
                        <h2>{countryName}</h2>
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
                    <span className="country-flag">{getCountryFlag(countryCode)}</span>
                    <h2>{countryName}</h2>
                </div>
                <button className="close-button" onClick={onClose} aria-label="Close brief">
                    ✕
                </button>
            </div>

            <p className="brief-subtitle">
                Executive Brief • Last {timeWindow}h • {data.signal_count.toLocaleString()} signals
            </p>

            {anomaly && (
                <div className="anomaly-badge">
                    <span className="anomaly-badge-icon">▲</span>
                    <span>{anomaly.multiplier.toFixed(0)}× above 7-day baseline</span>
                    <span className="anomaly-badge-level">{anomaly.level?.toUpperCase()}</span>
                </div>
            )}

            {/* Trust Indicators */}
            {indicators && !(indicators as Indicators & { error?: string }).error && (
                <section className="brief-section">
                    <h3>Trust Indicators</h3>
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
                <h3>Sentiment Overview <span className="sentiment-info-icon" data-tip="Scores range from −10 to +10. Negative = reporting is alarming, critical, or conflict-focused. Positive = coverage is favorable or optimistic. This reflects media tone, not whether the news is objectively good or bad.">?</span></h3>
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
                    <span className="sentiment-trend">
                        {data.sentiment_trend === 'improving' && '↑ Improving'}
                        {data.sentiment_trend === 'declining' && '↓ Declining'}
                        {data.sentiment_trend === 'stable' && '→ Stable'}
                    </span>
                </div>
                <p className="sentiment-warning">
                    Sentiment analysis is noisy and should be interpreted cautiously.
                </p>
            </section>

            {/* Top Themes */}
            <section className="brief-section">
                <h3>Top Themes</h3>
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

            {/* Top Sources */}
            <section className="brief-section">
                <h3>Top Sources</h3>
                <div className="source-list">
                    {data.top_sources.slice(0, 5).map((source, i) => (
                        <div key={i} className="source-item">
                            <span className="source-name">{source.name}</span>
                            <span className="source-count">{source.count} signals</span>
                        </div>
                    ))}
                </div>
            </section>

            {/* Top Stories / Recent Signals */}
            {data.top_stories && data.top_stories.length > 0 && (
                <section className="brief-section">
                    <h3>Recent Coverage <span style={{ fontWeight: 400, textTransform: 'none', fontSize: '9px', opacity: 0.5 }}>click theme to explore</span></h3>
                    <div className="story-list">
                        {data.top_stories.filter(s => s.title).slice(0, 5).map((story, i) => (
                            <a
                                key={i}
                                href={story.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="story-item"
                            >
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
                                <p className="story-meta">
                                    {story.source} · {new Date(story.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </p>
                            </a>
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
};

export default CountryBrief;
