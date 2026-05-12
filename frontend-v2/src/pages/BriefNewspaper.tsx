import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ComposableMap, Geographies, Geography } from 'react-simple-maps'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { resolveCountryName } from '../lib/countryNames'
import { TIME_RANGE_OPTIONS, TIME_RANGE_LABELS, timeRangeToHours, type TimeRange } from '../lib/timeRanges'
import './BriefNewspaper.css'

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

function signalColor(intensity: number): string {
    const r = Math.round(26 + (29 - 26) * intensity)
    const g = Math.round(37 + (158 - 37) * intensity)
    const b = Math.round(53 + (117 - 53) * intensity)
    return `rgb(${r},${g},${b})`
}

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
    const [countryQuery, setCountryQuery] = useState('')
    const [showCountryDropdown, setShowCountryDropdown] = useState(false)
    const countryInputRef = useRef<HTMLInputElement>(null)
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

    const signalMap = data
        ? new Map(data.top_countries.map(c => [c.code, c.signals]))
        : new Map<string, number>()
    const maxSignals = data
        ? Math.max(1, ...data.top_countries.map(c => c.signals))
        : 1
    const maxThemeCount = data?.top_themes.length
        ? Math.max(1, ...data.top_themes.map(t => t.count))
        : 1

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

                    {/* SIGNAL MAP — choropleth of signal density by country */}
                    <section className="brief-minimap">
                        <div className="brief-minimap-label">Signal density — {TIME_RANGE_LABELS[timeRange]}</div>
                        <ComposableMap
                            projection="geoMercator"
                            projectionConfig={{ scale: 130, center: [0, 20] }}
                            width={800}
                            height={380}
                        >
                            <Geographies geography={GEO_URL}>
                                {({ geographies }) =>
                                    geographies.map(geo => {
                                        const iso2 = NUMERIC_TO_ISO2[String(geo.id)]
                                        const count = iso2 ? (signalMap.get(iso2) ?? 0) : 0
                                        const intensity = count / maxSignals
                                        return (
                                            <Geography
                                                key={geo.rsmKey}
                                                geography={geo}
                                                fill={count > 0 ? signalColor(intensity) : '#12202e'}
                                                stroke="#0c1017"
                                                strokeWidth={0.5}
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

                    {/* COUNTRY FILTER */}
                    {data.top_countries.length > 0 && (() => {
                        const allCountries = data.top_countries
                        const q = countryQuery.toLowerCase().trim()
                        const suggestions = q
                            ? allCountries.filter(c =>
                                resolveCountryName(c.code, c.name).toLowerCase().includes(q) ||
                                c.code.toLowerCase().includes(q)
                              )
                            : allCountries
                        const activeCountry = countryFilter
                            ? allCountries.find(c => c.code === countryFilter)
                            : null

                        return (
                            <section className="brief-filter-row">
                                <span className="brief-filter-label">Country:</span>
                                {activeCountry ? (
                                    <div className="brief-filter-active">
                                        <span className="brief-filter-chip active">
                                            {resolveCountryName(activeCountry.code, activeCountry.name)}
                                        </span>
                                        <button
                                            className="brief-filter-clear"
                                            onClick={() => { setCountryFilter(null); setCountryQuery('') }}
                                        >
                                            ×
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
                                        />
                                        {showCountryDropdown && suggestions.length > 0 && (
                                            <div className="brief-country-dropdown">
                                                {suggestions.slice(0, 10).map(c => (
                                                    <button
                                                        key={c.code}
                                                        className="brief-country-option"
                                                        onMouseDown={e => e.preventDefault()}
                                                        onClick={() => {
                                                            setCountryFilter(c.code)
                                                            setCountryQuery('')
                                                            setShowCountryDropdown(false)
                                                        }}
                                                    >
                                                        <span>{resolveCountryName(c.code, c.name)}</span>
                                                        <span className="brief-country-option-count">{c.signals.toLocaleString()}</span>
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </section>
                        )
                    })()}

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

                                        {themeData && (
                                            <div className="brief-theme-bar-track">
                                                <div
                                                    className="brief-theme-bar"
                                                    style={{ width: `${(themeData.count / maxThemeCount) * 100}%` }}
                                                />
                                            </div>
                                        )}

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
