import { useState, useEffect } from 'react'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import './Briefing.css'

interface BriefingData {
    period_hours: number
    stats: {
        total_signals: number
        countries: number
        sources: number
        avg_sentiment: number
    }
    top_countries: { code: string; name: string; signals: number; sentiment: number }[]
    negative_sentiment: { code: string; name: string; sentiment: number; signals: number }[]
    positive_sentiment: { code: string; name: string; sentiment: number; signals: number }[]
    top_themes: { theme: string; count: number }[]
    top_sources: { source: string; count: number }[]
}

interface BriefingProps {
    hours: number
    onClose: () => void
    onCountrySelect: (code: string) => void
    onThemeSelect: (theme: string) => void
}

export function Briefing({ hours, onClose, onCountrySelect, onThemeSelect }: BriefingProps) {
    const [data, setData] = useState<BriefingData | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetch(`/api/v2/briefing?hours=${hours}`)
            .then(res => res.json())
            .then(setData)
            .catch(console.error)
            .finally(() => setLoading(false))
    }, [hours])

    const getSentimentEmoji = (s: number) => s > 0.1 ? '🟢' : s < -0.1 ? '🔴' : '🟡'

    if (loading) return (
        <div className="briefing-overlay" onClick={onClose}>
            <div className="briefing-panel" onClick={e => e.stopPropagation()}>
                <div className="briefing-loading">Loading briefing...</div>
            </div>
        </div>
    )

    if (!data) return null

    return (
        <div className="briefing-overlay" onClick={onClose}>
            <div className="briefing-panel" onClick={e => e.stopPropagation()}>
                <button className="briefing-close" onClick={onClose}>×</button>

                <div className="briefing-header">
                    <span className="briefing-icon">🌅</span>
                    <div>
                        <h2>Global Briefing</h2>
                        <p className="briefing-time">Last {hours} hours</p>
                    </div>
                </div>

                <div className="briefing-stats">
                    <div className="stat-card">
                        <span className="stat-value">{data.stats.total_signals.toLocaleString()}</span>
                        <span className="stat-label">Signals</span>
                    </div>
                    <div className="stat-card">
                        <span className="stat-value">{data.stats.countries}</span>
                        <span className="stat-label">Countries</span>
                    </div>
                    <div className="stat-card">
                        <span className="stat-value">{data.stats.sources}</span>
                        <span className="stat-label">Sources</span>
                    </div>
                    <div className="stat-card">
                        <span className="stat-value" style={{
                            color: data.stats.avg_sentiment > 0 ? '#4ade80' :
                                data.stats.avg_sentiment < 0 ? '#f87171' : '#fbbf24'
                        }}>
                            {data.stats.avg_sentiment.toFixed(2)}
                        </span>
                        <span className="stat-label">Avg Mood</span>
                    </div>
                </div>

                <div className="briefing-section">
                    <h3>📈 Most Active</h3>
                    <div className="country-list">
                        {data.top_countries.slice(0, 5).map(c => (
                            <div key={c.code} className="country-item" onClick={() => { onCountrySelect(c.code); onClose() }}>
                                <span>{c.name}</span>
                                <span className="country-signals">{c.signals.toLocaleString()}</span>
                                <span>{getSentimentEmoji(c.sentiment)}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="briefing-section two-col">
                    <div>
                        <h3>🔴 Most Negative</h3>
                        {data.negative_sentiment.slice(0, 3).map(c => (
                            <div key={c.code} className="country-item small" onClick={() => { onCountrySelect(c.code); onClose() }}>
                                <span>{c.name}</span>
                                <span className="negative">{c.sentiment.toFixed(2)}</span>
                            </div>
                        ))}
                    </div>
                    <div>
                        <h3>🟢 Most Positive</h3>
                        {data.positive_sentiment.slice(0, 3).map(c => (
                            <div key={c.code} className="country-item small" onClick={() => { onCountrySelect(c.code); onClose() }}>
                                <span>{c.name}</span>
                                <span className="positive">+{c.sentiment.toFixed(2)}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="briefing-section">
                    <h3>📰 Top Themes</h3>
                    <div className="theme-chips">
                        {data.top_themes.slice(0, 6).map(t => (
                            <div key={t.theme} className="theme-chip" onClick={() => { onThemeSelect(t.theme); onClose() }}>
                                <span>{getThemeIcon(t.theme)}</span>
                                <span>{getThemeLabel(t.theme)}</span>
                                <span className="chip-count">{t.count}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="briefing-section">
                    <h3>🔗 Top Sources</h3>
                    <div className="source-tags">
                        {data.top_sources.map(s => (
                            <span key={s.source} className="source-tag">{s.source} ({s.count})</span>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}
