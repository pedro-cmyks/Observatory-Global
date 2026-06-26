import React, { useState, useEffect } from 'react'
import { useCrisis } from '../contexts/CrisisContext'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import { useFocusRelation } from '../hooks/useFocusRelation'
import { resolveCountryName } from '../lib/countryNames'
import { getThemeLabel } from '../lib/themeLabels'
import { getPublicAttentionTopUrl, getTrendingSearchesUrl, getForumAttentionUrl } from '../lib/publicAttention'
import { isPublicAttentionRelevant } from '../lib/publicAttentionFilters'
import './AnomalyPanel.css'

const SEVERITY_COLORS: Record<string, string> = {
    critical: '#ef4444',
    elevated: '#f97316',
    notable:  '#fbbf24',
    normal:   '#4ade80',
}

interface AnomalyPanelProps {
    onWikiClick?: (query: string) => void
    onPublicAttentionSelect?: (item: { title: string; views?: number; country_count?: number; country?: string; countryName?: string }) => void
}

export const AnomalyPanel: React.FC<AnomalyPanelProps> = ({ onWikiClick, onPublicAttentionSelect }) => {
    const { anomalies, nearMisses, themeAnomalies, meta, overallSeverity, loading } = useCrisis()
    const { filter, setFocus, setMapFlyCountry } = useFocus()
    const { acledConflicts } = useFocusData()
    const relation = useFocusRelation()
    const activeCountry = filter.country
    // #234: when a non-country entity is focused, re-scope this panel's
    // public-attention + conflicts to the focus's dominant country (the shared
    // focus-relation context). Honest: only when a relation exists.
    const relationCountry = !activeCountry && relation.relationActive && relation.kind !== 'country'
        ? relation.dominantCountry : null
    const scopeCountry = activeCountry ?? relationCountry
    const activeTheme = filter.theme
    const streamLevel = filter.streamLevel
    const [wikiArticles, setWikiArticles] = useState<{ title: string; views: number; country_count?: number }[]>([])
    const [wikiLoading, setWikiLoading] = useState(true)
    const [wikiError, setWikiError] = useState(false)
    const [trendSearches, setTrendSearches] = useState<{ keyword: string; rank?: number | null; timestamp?: string }[]>([])
    const [trendsLoading, setTrendsLoading] = useState(false)
    const [trendsStaleHours, setTrendsStaleHours] = useState<number | null>(null)
    // C1/C2: forum discussion lane (Reddit) — labeled discussion, never evidence.
    const [forumItems, setForumItems] = useState<{ subreddit?: string | null; headline: string; url?: string; source_lang?: string | null }[]>([])

    useEffect(() => {
        setWikiLoading(true)
        setWikiError(false)
        fetch(getPublicAttentionTopUrl(10, scopeCountry ?? undefined))
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                type WikiItem = { title: string; views: number; country_count?: number }
                const raw: WikiItem[] = d?.articles ?? []
                const deduped = Array.from(new Map(raw.map(a => [a.title, a])).values())
                setWikiArticles(deduped.filter(a => isPublicAttentionRelevant(a.title)))
            })
            .catch(() => { setWikiError(true); setWikiArticles([]) })
            .finally(() => setWikiLoading(false))
    }, [scopeCountry])

    useEffect(() => {
        if (!scopeCountry) { setTrendSearches([]); return }
        setTrendsLoading(true)
        fetch(getTrendingSearchesUrl(8, 24, scopeCountry))
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                const items = d?.trending ?? []
                setTrendSearches(items)
                if (items.length > 0 && items[0].timestamp) {
                    const ageH = (Date.now() - new Date(items[0].timestamp).getTime()) / 3_600_000
                    setTrendsStaleHours(ageH > 25 ? Math.round(ageH) : null)
                } else {
                    setTrendsStaleHours(null)
                }
            })
            .catch(() => { setTrendSearches([]); setTrendsStaleHours(null) })
            .finally(() => setTrendsLoading(false))
    }, [scopeCountry])

    // Forum (Reddit) discussion — scoped to the active country, else global.
    // Guard against the response race: the global (no-country) fetch fired on
    // mount must not overwrite the country-scoped result if it resolves later.
    useEffect(() => {
        let ignore = false
        fetch(getForumAttentionUrl(6, scopeCountry ?? undefined))
            .then(r => r.ok ? r.json() : null)
            .then(d => { if (!ignore) setForumItems(d?.forum?.items ?? []) })
            .catch(() => { if (!ignore) setForumItems([]) })
        return () => { ignore = true }
    }, [scopeCountry])

    const handleAnomalyClick = (countryCode: string) => {
        setFocus('country', countryCode)
        setMapFlyCountry(countryCode)
    }

    // When a country is active (or a focus relation resolves one), filter
    // conflicts to that country. ACLED uses full names, GDELT 2-letter codes.
    const visibleConflicts = scopeCountry
        ? acledConflicts.filter(c => {
            const loc = c.location.country || ''
            const name = resolveCountryName(scopeCountry).toLowerCase()
            return loc === scopeCountry || loc.toLowerCase() === name
        })
        : acledConflicts

    const severityColor = SEVERITY_COLORS[overallSeverity] ?? '#4ade80'

    return (
        <div className="anomaly-panel-container">
            {/* Status badge */}
            <div className="ap-status-bar">
                <span className="ap-pulse" style={{ background: severityColor, boxShadow: `0 0 6px ${severityColor}` }} />
                <span className="ap-status-label" style={{ color: severityColor }}>
                    {overallSeverity.toUpperCase()}
                </span>
                {activeTheme && (
                    <span className="ap-focus-badge ap-focus-theme" title={`Narrative Thread active: ${getThemeLabel(activeTheme)}`}>
                        THREAD: {getThemeLabel(activeTheme).slice(0, 22)}
                    </span>
                )}
                {streamLevel && streamLevel !== 'notable' && streamLevel !== 'all' && !activeTheme && (
                    <span className={`ap-focus-badge ap-focus-stream ap-focus-stream--${streamLevel}`}>
                        STREAM: {streamLevel.toUpperCase()}
                    </span>
                )}
                {relationCountry && (
                    <span className="ap-focus-badge ap-focus-theme"
                        title={`Re-scoped to the focus's dominant country: ${resolveCountryName(relationCountry)}`}>
                        {(relation.value || '').toUpperCase().slice(0, 14)} → {relationCountry}
                    </span>
                )}
                {meta && (
                    <span className="ap-meta" data-tip="Anomaly baseline: all countries and signals tracked in last 24h (fixed window for anomaly detection)">
                        {meta.active_countries} countries · {(meta.total_signals_24h / 1000).toFixed(1)}k signals (24h baseline)
                    </span>
                )}
            </div>

            <div className="anomaly-body-grid">
                {/* ── Left: Geo alerts ── */}
                <div className="anomaly-col">
                    <div className="ap-geo-section">
                    <div className="col-label">GEO ALERTS</div>
                    <div className="ap-confidence-label">model confidence &gt; 0.8</div>
                    <div className="col-scroll">
                        {loading && anomalies.length === 0 ? (
                            <div className="ap-empty">Scanning…</div>
                        ) : anomalies.length === 0 && nearMisses.length === 0 ? (
                            <div className="ap-empty">No anomalies</div>
                        ) : anomalies.length === 0 ? (
                            <>
                                <div className="ap-empty ap-empty--sm">No critical spikes</div>
                                {nearMisses.map(a => (
                                    <div key={a.country_code}
                                        className={`ap-row ap-row--mover clickable${a.country_code === activeCountry ? ' ap-row--selected' : ''}`}
                                        onClick={() => handleAnomalyClick(a.country_code)}>
                                        <span className="ap-country">{resolveCountryName(a.country_code, a.country_name)}</span>
                                        <span className="ap-mult">{a.multiplier.toFixed(1)}×</span>
                                    </div>
                                ))}
                            </>
                        ) : (
                            anomalies.map((a, idx) => (
                                <div key={a.country_code}
                                    className={`ap-row ap-row--${a.level} clickable${a.country_code === activeCountry ? ' ap-row--selected' : ''}`}
                                    onClick={() => handleAnomalyClick(a.country_code)}>
                                    <span className="ap-anom-id">A-{String(idx + 1).padStart(3, '0')}</span>
                                    <span className="ap-country">{resolveCountryName(a.country_code, a.country_name)}</span>
                                    <span className="ap-mult">{a.multiplier.toFixed(1)}×</span>
                                    <button className="ap-brief-btn" onClick={e => { e.stopPropagation(); handleAnomalyClick(a.country_code) }}>
                                        BRIEF
                                    </button>
                                </div>
                            ))
                        )}
                    </div>

                    </div>{/* /ap-geo-section */}
                    {/* Conflict events — filtered to active country when one is selected */}
                    {visibleConflicts && visibleConflicts.length > 0 && (
                        <div className="ap-sub">
                            <div className="col-label" style={{ color: '#f87171' }}>
                                {scopeCountry ? `CONFLICTS · ${resolveCountryName(scopeCountry)}` : 'CONFLICT EVENTS'}
                            </div>
                            <div className="col-scroll-short">
                                {visibleConflicts.slice(0, 8).map(c => {
                                    const loc = c.location?.name || c.location?.country || '?'
                                    const src = c.source === 'gdelt_events' ? 'G' : 'A'
                                    return (
                                        <div key={c.id} className="ap-row ap-row--conflict clickable"
                                            onClick={() => handleAnomalyClick(c.location.country)}>
                                            <span className="ap-src-tag" style={{ color: src === 'A' ? '#f87171' : '#fb923c' }}>{src}</span>
                                            <span className="ap-conflict-info">
                                                <span className="ap-conflict-loc">{loc}</span>
                                                <span className="ap-conflict-type">{c.type?.replace('Use conventional military force', 'Military force').slice(0, 30)}</span>
                                            </span>
                                            {c.fatalities > 0 && <span className="ap-fatalities">{c.fatalities}†</span>}
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    )}
                </div>

                {/* ── Right: Intelligence feeds ── */}
                <div className="anomaly-col col-right-border">
                    {themeAnomalies && themeAnomalies.length > 0 && (
                        <>
                            <div className="col-label">THEME SPIKES</div>
                            <div className="col-scroll-short">
                                {themeAnomalies.map(a => (
                                    <div key={a.theme} className="ap-row ap-row--theme clickable"
                                        onClick={() => setFocus('theme', a.theme)}>
                                        <span className="ap-badge" style={{ color: '#f59e0b' }}>↑</span>
                                        <span className="ap-country" data-tip={a.theme}>
                                            {getThemeLabel(a.theme).slice(0, 24)}
                                        </span>
                                        <span className="ap-mult">{a.multiplier.toFixed(1)}×</span>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}

                    {/* PUBLIC ATTENTION — combined Trends + Wiki, scoped to active country */}
                    <div className="col-label"
                        style={{ marginTop: themeAnomalies?.length ? '8px' : 0 }}
                        data-tip={activeCountry
                            ? `What people in ${resolveCountryName(activeCountry)} are searching (Google Trends, 24h) and reading (Wikipedia, 7-day). Click any item to investigate.`
                            : 'Top Wikipedia articles by global pageviews. Click any item to investigate in the center panel.'}>
                        {scopeCountry
                            ? `PUBLIC ATTENTION · ${resolveCountryName(scopeCountry).toUpperCase()}`
                            : 'PUBLIC ATTENTION · GLOBAL'}
                    </div>
                    <div className="col-scroll">
                        {/* Trends rows — shown only when country active */}
                        {scopeCountry && (trendsLoading ? (
                            <div className="ap-empty">Loading searches…</div>
                        ) : trendSearches.length > 0 ? (<>
                            {trendsStaleHours && (
                                <div className="ap-empty" style={{ color: '#f59e0b', fontSize: '10px', padding: '2px 0 4px' }}
                                    data-tip="Google rate-limits high-volume country feeds from cloud IPs. Showing most recent available data.">
                                    searches from {trendsStaleHours}h ago
                                </div>
                            )}
                            {trendSearches.slice(0, 5).map((t, i) => (
                                <div
                                    key={`trend-${i}`}
                                    className="ap-row ap-row--trend clickable"
                                    onClick={() => onWikiClick?.(t.keyword)}
                                    data-tip={`Investigate "${t.keyword}"`}
                                >
                                    <span className="ap-src-tag" style={{ color: '#34d399' }}>S</span>
                                    <span className="ap-keyword">{t.keyword}</span>
                                </div>
                            ))}
                        </>) : null)}

                        {/* Wiki rows */}
                        {wikiLoading ? (
                            <div className="ap-empty">Loading articles…</div>
                        ) : wikiError ? (
                            <div className="ap-empty">Wikipedia data unavailable</div>
                        ) : wikiArticles.length === 0 ? (
                            <div className="ap-empty">No attention data</div>
                        ) : (
                            wikiArticles.slice(0, scopeCountry && trendSearches.length > 0 ? 5 : 10).map((a, i) => {
                                const displayTitle = a.title.replace(/_/g, ' ')
                                const canOpen = Boolean(onPublicAttentionSelect || onWikiClick)
                                return (
                                    <div
                                        key={`wiki-${i}`}
                                        className={`ap-row ap-row--trend${canOpen ? ' clickable' : ''}`}
                                        onClick={canOpen ? () => {
                                            if (onPublicAttentionSelect) {
                                                onPublicAttentionSelect({
                                                    ...a,
                                                    title: displayTitle,
                                                    country: scopeCountry ?? undefined,
                                                    countryName: scopeCountry ? resolveCountryName(scopeCountry) : undefined,
                                                })
                                            } else {
                                                onWikiClick?.(displayTitle)
                                            }
                                        } : undefined}
                                        data-tip={canOpen ? `Investigate "${displayTitle}"` : undefined}
                                    >
                                        <span className="ap-src-tag" style={{ color: '#818cf8' }}>W</span>
                                        <span className="ap-keyword">{displayTitle}</span>
                                        {!scopeCountry && a.country_count && a.country_count > 1 && (
                                            <span className="ap-ctry-count">{a.country_count}</span>
                                        )}
                                    </div>
                                )
                            })
                        )}

                        {/* Forum discussion (Reddit) — narrative-discovery lane,
                            labeled, never presented as verified evidence. */}
                        {forumItems.length > 0 && (<>
                            <div className="ap-forum-divider"
                                data-tip="Forum discussion (Reddit). What people are saying — discussion, not verified evidence.">
                                forum discussion
                            </div>
                            {forumItems.map((f, i) => (
                                <div
                                    key={`forum-${i}`}
                                    className="ap-row ap-row--trend clickable"
                                    onClick={() => {
                                        // Forums aren't in the thread inference, so we can't open
                                        // "the forum's thread". Instead find the closest Atlas
                                        // bucket: search the topic (signal matches + coverage).
                                        if (onPublicAttentionSelect) {
                                            onPublicAttentionSelect({
                                                title: f.headline,
                                                country: scopeCountry ?? undefined,
                                                countryName: scopeCountry ? resolveCountryName(scopeCountry) : undefined,
                                            })
                                        } else {
                                            onWikiClick?.(f.headline)
                                        }
                                    }}
                                    data-tip={`Find the Atlas coverage closest to "${f.headline}"`}
                                >
                                    <span className="ap-src-tag" style={{ color: '#fb923c' }}>F</span>
                                    <span className="ap-keyword">{f.headline}</span>
                                    {f.subreddit && <span className="ap-ctry-count">{f.subreddit}</span>}
                                    {f.url && (
                                        <a
                                            className="ap-forum-link"
                                            href={f.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            onClick={e => e.stopPropagation()}
                                            data-tip="Open the original post on Reddit"
                                        >↗</a>
                                    )}
                                </div>
                            ))}
                        </>)}
                    </div>
                </div>
            </div>
        </div>
    )
}
