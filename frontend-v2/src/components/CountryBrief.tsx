import React, { useState, useEffect } from 'react';
import { IndicatorTooltip, VolumeIndicator } from './IndicatorTooltip';
import './CountryBrief.css';

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
}

// Country flag emoji from code
const getCountryFlag = (code: string): string => {
    if (!code || code.length !== 2) return '🌍';
    const codePoints = code
        .toUpperCase()
        .split('')
        .map(char => 127397 + char.charCodeAt(0));
    return String.fromCodePoint(...codePoints);
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
    onThemeSelect
}) => {
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
                    topStories = (signals.signals || []).map((s: any) => ({
                        title: s.themes?.[0] || 'News from ' + s.source,
                        url: s.url,
                        source: s.source,
                        timestamp: s.timestamp,
                        sentiment: s.sentiment
                    }));
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
            <div className="country-brief">
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
            <div className="country-brief">
                <div className="brief-header">
                    <div className="brief-title">
                        <span className="country-flag">{getCountryFlag(countryCode)}</span>
                        <h2>{countryName}</h2>
                    </div>
                    <button className="close-button" onClick={onClose}>✕</button>
                </div>
                <div className="brief-error">
                    <p>⚠️ {error || 'No data available'}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="country-brief">
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
                <h3>Sentiment Overview</h3>
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
                    ⚠️ Sentiment analysis is noisy and should be interpreted cautiously.
                </p>
            </section>

            {/* Top Themes */}
            <section className="brief-section">
                <h3>Top Themes</h3>
                <div className="theme-list">
                    {data.top_themes.slice(0, 8).map((theme, i) => (
                        <button
                            key={i}
                            className="theme-chip"
                            onClick={() => onThemeSelect?.(theme.name)}
                            title={`Click to explore ${theme.name}`}
                        >
                            <span className="theme-name">{theme.name}</span>
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
                    <h3>Recent Coverage</h3>
                    <div className="story-list">
                        {data.top_stories.slice(0, 5).map((story, i) => (
                            <a
                                key={i}
                                href={story.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="story-item"
                            >
                                <p className="story-title">{story.title}</p>
                                <p className="story-meta">
                                    {story.source} • {new Date(story.timestamp).toLocaleTimeString()}
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
