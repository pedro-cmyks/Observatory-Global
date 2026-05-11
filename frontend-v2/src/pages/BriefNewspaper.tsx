import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { resolveCountryName } from '../lib/countryNames'
import { TIME_RANGE_OPTIONS, TIME_RANGE_LABELS, timeRangeToHours, type TimeRange } from '../lib/timeRanges'
import './BriefNewspaper.css'

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
    theme_country?: { theme: string; countries: { code: string; name: string; count: number }[] }[]
}

interface ThemeSignal {
    id: string | number
    headline: string
    source: string
    country_code?: string
    published_at?: string
}

export function BriefNewspaper() {
    const navigate = useNavigate()
    const [searchParams, setSearchParams] = useSearchParams()
    const initialRange = (searchParams.get('range') as TimeRange) || '24h'

    const [timeRange, setTimeRange] = useState<TimeRange>(initialRange)
    const [data, setData] = useState<BriefingData | null>(null)
    const [insight, setInsight] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)
    const [themeSignals, setThemeSignals] = useState<Record<string, ThemeSignal[]>>({})
    const [countryFilter, setCountryFilter] = useState<string | null>(null)
    const [now] = useState(new Date())

    const hours = timeRangeToHours(timeRange)

    const fetchData = useCallback(async (h: number) => {
        setLoading(true)
        setData(null)
        setInsight(null)
        setThemeSignals({})
        try {
            const [briefRes, insightRes] = await Promise.all([
                fetch(`/api/v2/briefing?hours=${h}`),
                fetch(`/api/v2/briefing/insight?hours=${h}`)
            ])
            const briefData: BriefingData = await briefRes.json()
            setData(briefData)
            const insightData = await insightRes.json()
            if (insightData.insight) setInsight(insightData.insight)

            // Fetch top 3 headlines per top theme (parallel)
            const topThemes = briefData.top_themes?.slice(0, 6) ?? []
            const signalFetches = topThemes.map(t =>
                fetch(`/api/v2/signals?theme=${encodeURIComponent(t.theme)}&limit=3&hours=${Math.min(h, 48)}`)
                    .then(r => r.json())
                    .then((d: { signals?: ThemeSignal[] } | ThemeSignal[]) => ({
                        theme: t.theme,
                        signals: Array.isArray(d) ? d.slice(0, 3) : (d.signals ?? []).slice(0, 3)
                    }))
                    .catch(() => ({ theme: t.theme, signals: [] }))
            )
            const results = await Promise.all(signalFetches)
            const map: Record<string, ThemeSignal[]> = {}
            results.forEach(r => { map[r.theme] = r.signals })
            setThemeSignals(map)
        } catch (e) {
            console.error(e)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchData(hours)
    }, [hours, fetchData])

    const handleRangeChange = (range: TimeRange) => {
        setTimeRange(range)
        setSearchParams({ range })
    }

    const goToAtlas = (params?: string) => {
        navigate(`/app${params ? `?${params}` : ''}`)
    }

    const moodLabel = (s: number) => s > 0.15 ? 'POSITIVE' : s < -0.15 ? 'NEGATIVE' : 'NEUTRAL'
    const moodClass = (s: number) => s > 0.15 ? 'mood-positive' : s < -0.15 ? 'mood-negative' : 'mood-neutral'

    const filteredThemeCountry = data?.theme_country?.map(row => ({
        ...row,
        countries: countryFilter
            ? row.countries.filter(c => c.code === countryFilter)
            : row.countries
    })).filter(row => !countryFilter || row.countries.length > 0)

    const activeThemes = filteredThemeCountry ?? data?.top_themes?.slice(0, 6).map(t => ({
        theme: t.theme,
        countries: []
    })) ?? []

    const dateStr = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })

    return (
        <div className="brief-page">
            <header className="brief-masthead">
                <button className="brief-back" onClick={() => navigate('/app')}>← Atlas</button>
                <div className="brief-masthead-center">
                    <div className="brief-edition-flag">INTELLIGENCE BRIEF</div>
                    <h1 className="brief-title">ATLAS</h1>
                    <div className="brief-dateline">{dateStr}</div>
                </div>
                <div className="brief-range-selector">
                    {TIME_RANGE_OPTIONS.slice(0, 5).map(r => (
                        <button
                            key={r}
                            className={`brief-range-btn ${timeRange === r ? 'active' : ''}`}
                            onClick={() => handleRangeChange(r)}
                        >
                            {TIME_RANGE_LABELS[r]}
                        </button>
                    ))}
                </div>
            </header>

            <div className="brief-rule" />

            {loading ? (
                <div className="brief-loading">
                    <div className="brief-loading-lines">
                        {[90, 75, 60, 80, 45].map((w, i) => (
                            <div key={i} className="brief-loading-line" style={{ width: `${w}%` }} />
                        ))}
                    </div>
                    <p>Composing brief...</p>
                </div>
            ) : data ? (
                <main className="brief-content">

                    {/* STATS BAR — global metrics row */}
                    <section className="brief-stats-bar">
                        <div className="brief-stat">
                            <span className="brief-stat-value">{data.stats.total_signals.toLocaleString()}</span>
                            <span className="brief-stat-label">signals</span>
                        </div>
                        <div className="brief-stat-divider" />
                        <div className="brief-stat">
                            <span className="brief-stat-value">{data.stats.countries}</span>
                            <span className="brief-stat-label">countries</span>
                        </div>
                        <div className="brief-stat-divider" />
                        <div className="brief-stat">
                            <span className="brief-stat-value">{data.stats.sources}</span>
                            <span className="brief-stat-label">sources</span>
                        </div>
                        <div className="brief-stat-divider" />
                        <div className={`brief-stat ${moodClass(data.stats.avg_sentiment)}`}>
                            <span className="brief-stat-value">{moodLabel(data.stats.avg_sentiment)}</span>
                            <span className="brief-stat-label">global mood</span>
                        </div>
                    </section>

                    <div className="brief-rule thin" />

                    {/* LEAD STORY — AI insight */}
                    {insight && (
                        <section className="brief-lead">
                            <div className="brief-section-tag">EDITOR'S ANALYSIS</div>
                            <p className="brief-lead-text">{insight}</p>
                        </section>
                    )}

                    <div className="brief-rule thin" />

                    {/* COUNTRY FILTER ROW */}
                    {data.top_countries.length > 0 && (
                        <section className="brief-filter-row">
                            <span className="brief-filter-label">Filter by country:</span>
                            <button
                                className={`brief-filter-chip ${!countryFilter ? 'active' : ''}`}
                                onClick={() => setCountryFilter(null)}
                            >
                                All
                            </button>
                            {data.top_countries.slice(0, 8).map(c => (
                                <button
                                    key={c.code}
                                    className={`brief-filter-chip ${countryFilter === c.code ? 'active' : ''}`}
                                    onClick={() => setCountryFilter(countryFilter === c.code ? null : c.code)}
                                >
                                    {resolveCountryName(c.code, c.name)}
                                </button>
                            ))}
                        </section>
                    )}

                    <div className="brief-rule thin" />

                    {/* THEME SECTIONS — main editorial body */}
                    <section className="brief-body">
                        <div className="brief-columns">
                            {activeThemes.map((row, idx) => {
                                const themeData = data.top_themes.find(t => t.theme === row.theme)
                                const signals = themeSignals[row.theme] ?? []
                                const isLead = idx === 0 && !countryFilter
                                return (
                                    <article
                                        key={row.theme}
                                        className={`brief-article ${isLead ? 'brief-article-lead' : ''}`}
                                    >
                                        <div className="brief-article-header">
                                            <span className="brief-article-icon">{getThemeIcon(row.theme)}</span>
                                            <h2 className="brief-article-theme">{getThemeLabel(row.theme)}</h2>
                                            {themeData && (
                                                <span className="brief-article-count">{themeData.count.toLocaleString()} signals</span>
                                            )}
                                        </div>

                                        {row.countries.length > 0 && (
                                            <div className="brief-article-countries">
                                                {row.countries.slice(0, 4).map(c => (
                                                    <button
                                                        key={c.code}
                                                        className="brief-country-pill"
                                                        onClick={() => goToAtlas(`country=${c.code}`)}
                                                    >
                                                        {resolveCountryName(c.code, c.name)}
                                                        <span className="brief-pill-count">
                                                            {c.count >= 1000 ? `${(c.count / 1000).toFixed(1)}k` : c.count}
                                                        </span>
                                                    </button>
                                                ))}
                                            </div>
                                        )}

                                        {signals.length > 0 && (
                                            <ul className="brief-headlines">
                                                {signals.map((s, i) => (
                                                    <li key={s.id ?? i} className="brief-headline-item">
                                                        <span className="brief-headline-text">{s.headline}</span>
                                                        <span className="brief-headline-meta">
                                                            {s.country_code && (
                                                                <span className="brief-headline-country">{resolveCountryName(s.country_code, s.country_code)}</span>
                                                            )}
                                                            <span className="brief-headline-source">{s.source}</span>
                                                        </span>
                                                    </li>
                                                ))}
                                            </ul>
                                        )}

                                        <button
                                            className="brief-theme-link"
                                            onClick={() => goToAtlas(`theme=${row.theme}`)}
                                        >
                                            Explore in Atlas →
                                        </button>
                                    </article>
                                )
                            })}
                        </div>
                    </section>

                    <div className="brief-rule" />

                    {/* BOTTOM ROW — active + sentiment + sources */}
                    <section className="brief-bottom-row">
                        <div className="brief-bottom-col">
                            <h3 className="brief-bottom-heading">Most Active</h3>
                            {data.top_countries.slice(0, 5).map(c => (
                                <button
                                    key={c.code}
                                    className="brief-bottom-country"
                                    onClick={() => goToAtlas(`country=${c.code}`)}
                                >
                                    <span>{resolveCountryName(c.code, c.name)}</span>
                                    <span className="brief-bottom-num">{c.signals.toLocaleString()}</span>
                                </button>
                            ))}
                        </div>
                        <div className="brief-bottom-col">
                            <h3 className="brief-bottom-heading">Most Negative</h3>
                            {data.negative_sentiment.slice(0, 4).map(c => (
                                <button
                                    key={c.code}
                                    className="brief-bottom-country"
                                    onClick={() => goToAtlas(`country=${c.code}`)}
                                >
                                    <span>{resolveCountryName(c.code, c.name)}</span>
                                    <span className="brief-bottom-num negative">{c.sentiment.toFixed(2)}</span>
                                </button>
                            ))}
                        </div>
                        <div className="brief-bottom-col">
                            <h3 className="brief-bottom-heading">Most Positive</h3>
                            {data.positive_sentiment.slice(0, 4).map(c => (
                                <button
                                    key={c.code}
                                    className="brief-bottom-country"
                                    onClick={() => goToAtlas(`country=${c.code}`)}
                                >
                                    <span>{resolveCountryName(c.code, c.name)}</span>
                                    <span className="brief-bottom-num positive">+{c.sentiment.toFixed(2)}</span>
                                </button>
                            ))}
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
                    </section>

                    <div className="brief-rule" />

                    {/* CTA — enter Atlas */}
                    <section className="brief-cta">
                        <p className="brief-cta-label">Full intelligence terminal</p>
                        <button className="brief-cta-btn" onClick={() => goToAtlas()}>
                            Enter Atlas →
                        </button>
                    </section>

                </main>
            ) : (
                <div className="brief-error">Failed to load briefing data.</div>
            )}
        </div>
    )
}
