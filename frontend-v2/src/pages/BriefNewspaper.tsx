import { useState, useEffect, useCallback, useRef } from 'react'
import { useSavedWatches, fetchWatchCount } from '../hooks/useSavedWatches'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ComposableMap, Geographies, Geography } from 'react-simple-maps'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { COUNTRY_OPTIONS, resolveCountryName } from '../lib/countryNames'
import { TIME_RANGE_OPTIONS, TIME_RANGE_LABELS, timeRangeToHours, type TimeRange } from '../lib/timeRanges'
import { readBriefingCache } from '../lib/briefingPrefetch'
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
    country?: string
    country_code?: string
    published_at?: string
    themes?: string[]
    sentiment?: number
}

interface CountryBriefData {
    countryCode: string
    name: string
    totalSignals: number
    sentiment: number
    sources: number
    themes: { name: string; count: number }[]
}

export function BriefNewspaper() {
    const navigate = useNavigate()
    const [searchParams, setSearchParams] = useSearchParams()
    const rangeParam = searchParams.get('range')
    const countryParam = searchParams.get('country')?.toUpperCase() ?? null
    const initialRange = TIME_RANGE_OPTIONS.includes(rangeParam as TimeRange)
        ? (rangeParam as TimeRange)
        : '24h'

    const [timeRange, setTimeRange] = useState<TimeRange>(initialRange)
    const { watches, remove: removeWatch, markSeen } = useSavedWatches()
    const [watchCounts, setWatchCounts] = useState<Record<string, number | null>>({})
    const [data, setData] = useState<BriefingData | null>(null)
    const [insight, setInsight] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)
    const [themeSignals, setThemeSignals] = useState<Record<string, ThemeSignal[]>>({})
    const [countryFilter, setCountryFilter] = useState<string | null>(countryParam)
    const [countryDetail, setCountryDetail] = useState<CountryBriefData | null>(null)
    const [countryLoading, setCountryLoading] = useState(false)
    const [countryError, setCountryError] = useState<string | null>(null)
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
            // Use Landing prefetch cache when available — eliminates visible loading delay
            const cached = readBriefingCache(h)
            let briefData: BriefingData
            if (cached) {
                briefData = cached.briefing as BriefingData
                setData(briefData)
                if (cached.insight) setInsight(cached.insight)
            } else {
                const [briefRes, insightRes] = await Promise.all([
                    fetch(`/api/v2/briefing?hours=${h}`),
                    fetch(`/api/v2/briefing/insight?hours=${h}`)
                ])
                if (!briefRes.ok) throw new Error(`Briefing request failed: ${briefRes.status}`)
                briefData = await briefRes.json()
                setData(briefData)
                if (insightRes.ok) {
                    const insightData = await insightRes.json()
                    if (insightData.insight) setInsight(insightData.insight)
                }
            }

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

    useEffect(() => {
        if (!countryFilter) {
            setCountryDetail(null)
            setCountryError(null)
            return
        }

        let cancelled = false
        setCountryLoading(true)
        setCountryError(null)

        Promise.all([
            fetch(`/api/v2/nodes?focus_type=country&focus_value=${countryFilter}&hours=${hours}&limit=5`)
                .then(async r => {
                    if (!r.ok) throw new Error(`Country summary request failed: ${r.status}`)
                    return r.json()
                }),
            fetch(`/api/v2/signals?country_code=${countryFilter}&hours=${hours}&limit=500`)
                .then(async r => {
                    if (!r.ok) throw new Error(`Country signals request failed: ${r.status}`)
                    return r.json()
                })
        ])
            .then(([nodeData, signalData]) => {
                if (cancelled) return
                const node = nodeData.nodes?.[0]
                const signals: ThemeSignal[] = Array.isArray(signalData)
                    ? signalData
                    : (signalData.signals ?? [])
                const themeCounts = new Map<string, number>()
                const sourceNames = new Set<string>()
                const countrySignalMap: Record<string, ThemeSignal[]> = {}
                let sentimentTotal = 0

                signals.forEach(signal => {
                    if (signal.source) sourceNames.add(signal.source)
                    sentimentTotal += Number((signal as ThemeSignal & { sentiment?: number }).sentiment ?? 0)
                    ;(signal.themes ?? []).forEach(theme => {
                        themeCounts.set(theme, (themeCounts.get(theme) ?? 0) + 1)
                        if (!countrySignalMap[theme]) countrySignalMap[theme] = []
                        if (countrySignalMap[theme].length < 3) {
                            countrySignalMap[theme].push({
                                ...signal,
                                country_code: signal.country_code ?? signal.country
                            })
                        }
                    })
                })

                const countryData: CountryBriefData = {
                    countryCode: countryFilter,
                    name: node?.name ?? resolveCountryName(countryFilter),
                    totalSignals: node?.signalCount ?? signals.length,
                    sentiment: node?.sentiment ?? (signals.length ? sentimentTotal / signals.length : 0),
                    sources: sourceNames.size,
                    themes: [...themeCounts.entries()]
                        .map(([name, count]) => ({ name, count }))
                        .sort((a, b) => b.count - a.count)
                        .slice(0, 10)
                }
                setCountryDetail(countryData)
                setThemeSignals(prev => ({ ...prev, ...countrySignalMap }))
            })
            .catch(e => {
                if (cancelled) return
                setCountryDetail(null)
                setCountryError(e instanceof Error ? e.message : 'Country data unavailable')
            })
            .finally(() => {
                if (!cancelled) setCountryLoading(false)
            })

        return () => { cancelled = true }
    }, [countryFilter, hours])

    useEffect(() => {
        if (watches.length === 0) return
        let cancelled = false
        void (async () => {
            const entries = await Promise.all(
                watches.map(async w => [w.id, await fetchWatchCount(w.filter)] as [string, number])
            )
            if (!cancelled) setWatchCounts(Object.fromEntries(entries))
        })()
        return () => { cancelled = true }
    }, [watches])

    const handleRangeChange = (range: TimeRange) => {
        setTimeRange(range)
        setSearchParams(countryFilter ? { range, country: countryFilter } : { range })
    }

    const selectCountry = (code: string | null) => {
        setCountryFilter(code)
        setCountryQuery('')
        setShowCountryDropdown(false)
        setSearchParams(code ? { range: timeRange, country: code } : { range: timeRange })
    }

    const goToAtlas = (params?: string) => {
        const next = new URLSearchParams(params)
        next.set('entry', 'brief')
        navigate(`/app?${next.toString()}`)
    }

    const atlasThemeParams = (theme: string, country?: string | null) => {
        const params = new URLSearchParams()
        params.set('theme', theme)
        if (country) params.set('country', country)
        return params.toString()
    }

    const moodLabel = (s: number) => s > 0.15 ? 'POSITIVE' : s < -0.15 ? 'NEGATIVE' : 'NEUTRAL'
    const moodClass = (s: number) => s > 0.15 ? 'mood-positive' : s < -0.15 ? 'mood-negative' : 'mood-neutral'

    const filteredThemeCountry = data?.theme_country?.map(row => ({
        ...row,
        countries: countryFilter
            ? row.countries.filter(c => c.code === countryFilter)
            : row.countries
    })).filter(row => !countryFilter || row.countries.length > 0)

    const countryThemes = countryFilter && countryDetail
        ? countryDetail.themes.slice(0, 6).map(t => ({
            theme: t.name,
            countries: [{
                code: countryFilter,
                name: countryDetail.name,
                count: t.count
            }]
        }))
        : null

    const activeThemes = countryThemes ?? filteredThemeCountry ?? data?.top_themes?.slice(0, 6).map(t => ({
        theme: t.theme,
        countries: []
    })) ?? []

    const displayedStats = countryFilter && countryDetail
        ? {
            total_signals: countryDetail.totalSignals,
            countries: 1,
            sources: countryDetail.sources,
            avg_sentiment: countryDetail.sentiment,
        }
        : data?.stats

    const tone = (s: number) => s > 0.1 ? 'positive' : s < -0.1 ? 'negative' : 'neutral'

    const buildGlobalFallback = (d: BriefingData): string => {
        const topThemeEntries = d.top_themes.slice(0, 3)
        const negTop = d.negative_sentiment.slice(0, 2)
        const posTop = d.positive_sentiment.slice(0, 2)
        const leader = d.top_countries[0]
        const runner = d.top_countries[1]
        const leaderName = leader ? resolveCountryName(leader.code, leader.name) : null
        const runnerName = runner ? resolveCountryName(runner.code, runner.name) : null
        const negNames = negTop.map(c => resolveCountryName(c.code, c.name)).join(' and ')
        const posNames = posTop.map(c => resolveCountryName(c.code, c.name)).join(' and ')
        const themeLabels = topThemeEntries.map(e => getThemeLabel(e.theme))
        const window = TIME_RANGE_LABELS[timeRange].toLowerCase()

        // Rotate narrative angle on each call so repeated views feel like different editions
        const variant = Math.floor(Math.random() * 4)

        if (variant === 0) {
            // Lead: dominant theme angle
            const parts: string[] = []
            if (themeLabels[0]) parts.push(`${themeLabels[0]} leads the ${window} feed.`)
            if (leaderName) parts.push(`${leaderName} accounts for the highest signal volume${runnerName ? `, ahead of ${runnerName}` : ''}.`)
            if (negNames) parts.push(`Critical framing concentrates in ${negNames}${posNames ? `; positive coverage peaks in ${posNames}` : ''}.`)
            if (themeLabels.length > 1) parts.push(`${themeLabels.slice(1).join(' and ')} round out the major storylines.`)
            return parts.join(' ')
        }

        if (variant === 1) {
            // Lead: geography / volume angle
            const parts: string[] = []
            if (leaderName) {
                parts.push(runnerName
                    ? `${leaderName} and ${runnerName} drive the bulk of ${window} coverage.`
                    : `${leaderName} dominates the ${window} signal landscape.`)
            }
            if (themeLabels[0]) parts.push(`${themeLabels[0]} is the period's defining narrative thread.`)
            if (themeLabels.length > 1) parts.push(`${themeLabels.slice(1).join(' and ')} also register significant activity.`)
            if (negNames) parts.push(`Sentiment runs most negative in ${negNames}.`)
            return parts.join(' ')
        }

        if (variant === 2) {
            // Lead: sentiment / tension angle
            const parts: string[] = []
            if (negNames) {
                parts.push(posNames
                    ? `The ${window} opens with sharp contrasts: press framing darkens in ${negNames} while ${posNames} attract unusually positive coverage.`
                    : `Media tone this ${window} turns most critical in ${negNames}.`)
            } else if (themeLabels[0]) {
                parts.push(`${themeLabels[0]} sets the tone for the ${window} edition.`)
            }
            if (themeLabels[0]) parts.push(`${themeLabels[0]} anchors the global narrative.`)
            if (leaderName) parts.push(`${leaderName} generates the most signals this period${runnerName ? `, with ${runnerName} close behind` : ''}.`)
            return parts.join(' ')
        }

        // variant === 3: volume-first, theme second
        const parts: string[] = []
        if (themeLabels[0]) parts.push(`${themeLabels[0]} shapes the ${window} brief across ${d.stats.countries} countries.`)
        if (leaderName) parts.push(`${leaderName} leads coverage volume${runnerName ? `, followed by ${runnerName}` : ''}.`)
        if (negNames) parts.push(`Harshest press scrutiny falls on ${negNames}${posNames ? `; brightest coverage on ${posNames}` : ''}.`)
        if (themeLabels.length > 1) parts.push(`${themeLabels.slice(1).join(' and ')} also feature across the feed.`)
        return parts.join(' ')
    }

    const buildCountryFallback = (detail: CountryBriefData): string => {
        const name = resolveCountryName(countryFilter!, detail.name)
        const topThemes = detail.themes.slice(0, 3).map(t => getThemeLabel(t.name))
        const t = tone(detail.sentiment)
        const window = TIME_RANGE_LABELS[timeRange].toLowerCase()

        const sentenceNeg = `Press framing runs predominantly critical — ongoing tension or crisis coverage.`
        const sentencePos = `Coverage carries an unusually positive tone. Watch for diplomatic, economic, or cultural milestones.`
        const sentenceNeutral = `Framing is broadly neutral across ${detail.sources} tracked sources.`
        const sentimentLine = t === 'negative' ? sentenceNeg : t === 'positive' ? sentencePos : sentenceNeutral

        const variant = Math.floor(Math.random() * 3)

        if (variant === 0) {
            const parts: string[] = []
            if (topThemes[0]) parts.push(`${name} coverage centres on ${topThemes[0]} this ${window}.`)
            if (topThemes.length > 1) parts.push(`${topThemes.slice(1).join(' and ')} also figure prominently.`)
            parts.push(sentimentLine)
            return parts.join(' ')
        }

        if (variant === 1) {
            const parts: string[] = []
            parts.push(sentimentLine)
            if (topThemes[0]) parts.push(`Lead narrative: ${topThemes[0]}.`)
            if (topThemes.length > 1) parts.push(`Secondary focus: ${topThemes.slice(1).join(', ')}.`)
            return parts.join(' ')
        }

        // variant === 2: theme volume-first
        const parts: string[] = []
        if (topThemes[0]) parts.push(`${topThemes[0]} leads ${name}'s ${window} picture.`)
        if (topThemes.length > 1) parts.push(`${topThemes.slice(1).join(' and ')} also active.`)
        parts.push(sentimentLine)
        return parts.join(' ')
    }

    const displayedInsight = countryFilter && countryDetail
        ? buildCountryFallback(countryDetail)
        : insight ?? (data ? buildGlobalFallback(data) : null)

    const dateStr = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })

    const signalMap = data
        ? new Map([
            ...data.top_countries.map(c => [c.code, c.signals] as const),
            ...(countryFilter && countryDetail ? [[countryFilter, countryDetail.totalSignals] as const] : [])
        ])
        : new Map<string, number>()
    const maxSignals = data
        ? Math.max(1, ...data.top_countries.map(c => c.signals), countryDetail?.totalSignals ?? 0)
        : 1
    const maxThemeCount = countryDetail?.themes.length
        ? Math.max(1, ...countryDetail.themes.map(t => t.count))
        : data?.top_themes.length
            ? Math.max(1, ...data.top_themes.map(t => t.count))
            : 1

    return (
        <div className="brief-page">
            <header className="brief-masthead">
                <div className="brief-nav-actions">
                    <button className="brief-back" onClick={() => navigate('/')}>← Home</button>
                    <button className="brief-back brief-back-primary" onClick={() => goToAtlas(countryFilter ? `country=${countryFilter}` : undefined)}>Open Console</button>
                </div>
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
                    <p>Loading brief…</p>
                </div>
            ) : data ? (
                <main className="brief-content">

                    {/* STATS BAR — global or selected-country metrics row */}
                    {displayedStats && <section className="brief-stats-bar">
                        <div className="brief-stat">
                            <span className="brief-stat-value">{displayedStats.total_signals.toLocaleString()}</span>
                            <span className="brief-stat-label">signals</span>
                        </div>
                        <div className="brief-stat-divider" />
                        <div className="brief-stat">
                            <span className="brief-stat-value">{displayedStats.countries}</span>
                            <span className="brief-stat-label">{displayedStats.countries === 1 ? 'country' : 'countries'}</span>
                        </div>
                        <div className="brief-stat-divider" />
                        <div className="brief-stat">
                            <span className="brief-stat-value">{displayedStats.sources}</span>
                            <span className="brief-stat-label">sources</span>
                        </div>
                        <div className="brief-stat-divider" />
                        <div
                            className={`brief-stat ${moodClass(displayedStats.avg_sentiment)}`}
                            data-tip="Aggregate sentiment across all signals in this window. Positive = media frames events favourably on balance. Negative = critical or alarming framing dominates. Neutral = mixed or factual coverage."
                        >
                            <span className="brief-stat-value">{moodLabel(displayedStats.avg_sentiment)}</span>
                            <span className="brief-stat-label">{countryFilter ? 'country mood' : 'global mood'}</span>
                        </div>
                    </section>}

                    {/* SIGNAL MAP — choropleth of signal density by country */}
                    <section className="brief-minimap">
                        <div
                            className="brief-minimap-label"
                            data-tip="Signal density: how many media signals Atlas captured per country in this window. Darker = more coverage. Coverage volume reflects media attention, not geopolitical importance."
                        >
                            Signal density — {TIME_RANGE_LABELS[timeRange]}
                        </div>
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
                                        const isSelected = Boolean(countryFilter && iso2 === countryFilter)
                                        return (
                                            <Geography
                                                key={geo.rsmKey}
                                                geography={geo}
                                                fill={countryFilter
                                                    ? isSelected
                                                        ? signalColor(Math.max(intensity, 0.85))
                                                        : '#0d1723'
                                                    : count > 0 ? signalColor(intensity) : '#12202e'}
                                                stroke={isSelected ? '#68dbae' : '#0c1017'}
                                                strokeWidth={isSelected ? 1.4 : 0.5}
                                                onClick={() => iso2 && selectCountry(iso2)}
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
                    {displayedInsight && (
                        <section className="brief-lead">
                            <div
                                className="brief-section-tag"
                                data-tip={countryFilter
                                    ? "Country-scoped summary derived from signal clusters and source patterns in this window."
                                    : "AI-generated pattern reading based on signal volume, sentiment shifts, and narrative spread. Describes observable coverage patterns — does not reflect Atlas editorial opinion."
                                }
                            >
                                {countryFilter ? 'COUNTRY ANALYSIS' : "EDITOR'S ANALYSIS"}
                            </div>
                            <p className="brief-lead-text">{displayedInsight}</p>
                        </section>
                    )}

                    <div className="brief-rule thin" />

                    {/* COUNTRY FILTER */}
                    {(() => {
                        const signalCounts = new Map(data.top_countries.map(c => [c.code, c.signals]))
                        if (countryFilter && countryDetail) {
                            signalCounts.set(countryFilter, countryDetail.totalSignals)
                        }
                        const apiNames = new Map(data.top_countries.map(c => [c.code, c.name]))
                        if (countryFilter && countryDetail) {
                            apiNames.set(countryFilter, countryDetail.name)
                        }
                        const allCountries = COUNTRY_OPTIONS.map(c => ({
                            code: c.code,
                            name: resolveCountryName(c.code, apiNames.get(c.code) ?? c.name),
                            signals: signalCounts.get(c.code) ?? 0,
                        }))
                        const q = countryQuery.toLowerCase().trim()
                        const suggestions = q
                            ? allCountries.filter(c =>
                                resolveCountryName(c.code, c.name).toLowerCase().includes(q) ||
                                c.code.toLowerCase().includes(q)
                              )
                            : allCountries
                        suggestions.sort((a, b) => {
                            if (b.signals !== a.signals) return b.signals - a.signals
                            return a.name.localeCompare(b.name)
                        })
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
                                            onClick={() => selectCountry(null)}
                                        >
                                            x
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
                                                        className={`brief-country-option${c.signals === 0 ? ' empty' : ''}`}
                                                        onMouseDown={e => e.preventDefault()}
                                                        onClick={() => selectCountry(c.code)}
                                                    >
                                                        <span>{resolveCountryName(c.code, c.name)}</span>
                                                        <span className="brief-country-option-count">{c.signals > 0 ? c.signals.toLocaleString() : 'not in top countries'}</span>
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
                            {countryLoading && countryFilter ? (
                                <article className="brief-article brief-empty-country">
                                    <div className="brief-article-header">
                                        <span className="brief-article-icon">◇</span>
                                        <h2 className="brief-article-theme">Loading themes for {resolveCountryName(countryFilter)}</h2>
                                    </div>
                                    <p>Checking this country's current signal clusters for the selected brief window.</p>
                                </article>
                            ) : activeThemes.length === 0 && countryFilter ? (
                                <article className="brief-article brief-empty-country">
                                    <div className="brief-article-header">
                                        <span className="brief-article-icon">◇</span>
                                        <h2 className="brief-article-theme">No active signals for {resolveCountryName(countryFilter)}</h2>
                                    </div>
                                    <p>
                                        {countryError
                                            ? 'Atlas could not load this country brief right now. Open the console to inspect broader context or expand the time range.'
                                            : 'Atlas has this country in the selector, but the current brief window has no country-level signals available.'}
                                    </p>
                                    <button
                                        className="brief-theme-link"
                                        onClick={() => goToAtlas(`country=${countryFilter}`)}
                                    >
                                        Open country in Atlas →
                                    </button>
                                </article>
                            ) : activeThemes.map((row, idx) => {
                                const themeData = countryFilter && countryDetail
                                    ? { theme: row.theme, count: row.countries[0]?.count ?? 0 }
                                    : data.top_themes.find(t => t.theme === row.theme)
                                const signals = themeSignals[row.theme] ?? []
                                const isLead = idx === 0 && !countryFilter
                                return (
                                    <article
                                        key={row.theme}
                                        className={`brief-article brief-article-clickable ${isLead ? 'brief-article-lead' : ''}`}
                                        role="button"
                                        tabIndex={0}
                                        onClick={() => goToAtlas(atlasThemeParams(row.theme, countryFilter))}
                                        onKeyDown={event => {
                                            if (event.key === 'Enter' || event.key === ' ') {
                                                event.preventDefault()
                                                goToAtlas(atlasThemeParams(row.theme, countryFilter))
                                            }
                                        }}
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
                                                        onClick={event => {
                                                            event.stopPropagation()
                                                            goToAtlas(atlasThemeParams(row.theme, c.code))
                                                        }}
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
                                            onClick={event => {
                                                event.stopPropagation()
                                                goToAtlas(atlasThemeParams(row.theme, countryFilter))
                                            }}
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

                    {watches.length > 0 && (
                        <>
                            <div className="brief-rule" />
                            <section className="brief-watches">
                                <div className="brief-section-tag">SAVED WATCHES</div>
                                <div className="brief-watches-grid">
                                    {watches.map(w => {
                                        const parts: string[] = []
                                        if (w.filter.country) parts.push(resolveCountryName(w.filter.country))
                                        if (w.filter.concept) parts.push(w.filter.concept.label)
                                        else if (w.filter.theme) parts.push(getThemeLabel(w.filter.theme))
                                        if (w.filter.person) parts.push(w.filter.person)
                                        if (w.filter.region) parts.push(w.filter.region.label)
                                        const atlasParams = [
                                            w.filter.country ? `country=${w.filter.country}` : null,
                                            w.filter.theme ? `theme=${encodeURIComponent(w.filter.theme)}` : null,
                                            w.filter.person ? `person=${encodeURIComponent(w.filter.person)}` : null,
                                        ].filter(Boolean).join('&')
                                        const currentCount = watchCounts[w.id] ?? null
                                        const prevCount = w.lastSeenCount ?? null
                                        const delta = currentCount !== null && prevCount !== null ? currentCount - prevCount : null
                                        return (
                                            <div key={w.id} className="brief-watch-card">
                                                <div className="brief-watch-name">{w.name}</div>
                                                <div className="brief-watch-scope">{parts.join(' · ') || 'Global'}</div>
                                                <div className="brief-watch-stats">
                                                    {currentCount === null ? (
                                                        <span className="brief-watch-count loading">—</span>
                                                    ) : (
                                                        <span className="brief-watch-count">{currentCount.toLocaleString()} signals today</span>
                                                    )}
                                                    {delta !== null && delta !== 0 && (
                                                        <span className={`brief-watch-delta ${delta > 0 ? 'up' : 'down'}`}>
                                                            {delta > 0 ? '↑' : '↓'}{Math.abs(delta)} vs last check
                                                        </span>
                                                    )}
                                                    {delta === 0 && prevCount !== null && (
                                                        <span className="brief-watch-delta neutral">no change</span>
                                                    )}
                                                </div>
                                                <div className="brief-watch-date">
                                                    Saved {new Date(w.createdAt).toLocaleDateString()}
                                                    {w.lastSeenAt && ` · checked ${new Date(w.lastSeenAt).toLocaleDateString()}`}
                                                </div>
                                                <div className="brief-watch-actions">
                                                    <button
                                                        className="brief-watch-open"
                                                        onClick={() => {
                                                            if (currentCount !== null) markSeen(w.id, currentCount)
                                                            goToAtlas(atlasParams || undefined)
                                                        }}
                                                    >Open in Atlas →</button>
                                                    <button className="brief-watch-remove" onClick={() => removeWatch(w.id)} title="Remove watch">×</button>
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            </section>
                        </>
                    )}

                    <div className="brief-rule" />

                    {/* CTA — enter Atlas */}
                    <section className="brief-cta">
                        <p className="brief-cta-label">Full intelligence terminal</p>
                        <button className="brief-cta-btn" onClick={() => goToAtlas(countryFilter ? `country=${countryFilter}` : undefined)}>
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
