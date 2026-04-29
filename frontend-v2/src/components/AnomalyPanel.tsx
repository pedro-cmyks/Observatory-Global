import React, { useState, useEffect } from 'react'
import { useCrisis } from '../contexts/CrisisContext'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import { resolveCountryName } from '../lib/countryNames'
import { getThemeLabel } from '../lib/themeLabels'
import './AnomalyPanel.css'

const SEVERITY_COLORS: Record<string, string> = {
    critical: '#ef4444',
    elevated: '#f97316',
    notable:  '#fbbf24',
    normal:   '#4ade80',
}

export const AnomalyPanel: React.FC = () => {
    const { anomalies, nearMisses, themeAnomalies, meta, overallSeverity, loading } = useCrisis()
    const { setFocus, setMapFlyCountry } = useFocus()
    const { acledConflicts } = useFocusData()
    const [trendingSearches, setTrendingSearches] = useState<{ keyword: string; country_count: number }[]>([])

    useEffect(() => {
        fetch('/api/v2/trends/search?hours=24&limit=10')
            .then(r => r.ok ? r.json() : null)
            .then(d => { if (d?.trending) setTrendingSearches(d.trending) })
            .catch(() => {})
    }, [])

    const handleAnomalyClick = (countryCode: string) => {
        setFocus('country', countryCode)
        setMapFlyCountry(countryCode)
    }

    const severityColor = SEVERITY_COLORS[overallSeverity] ?? '#4ade80'

    return (
        <div className="anomaly-panel-container">
            {/* Status badge */}
            <div className="ap-status-bar">
                <span className="ap-pulse" style={{ background: severityColor, boxShadow: `0 0 6px ${severityColor}` }} />
                <span className="ap-status-label" style={{ color: severityColor }}>
                    {overallSeverity.toUpperCase()}
                </span>
                {meta && (
                    <span className="ap-meta">
                        {meta.active_countries} countries · {(meta.total_signals_24h / 1000).toFixed(1)}k signals
                    </span>
                )}
            </div>

            <div className="anomaly-body-grid">
                {/* ── Left: Geo alerts ── */}
                <div className="anomaly-col">
                    <div className="col-label">GEO ALERTS</div>
                    <div className="col-scroll">
                        {loading && anomalies.length === 0 ? (
                            <div className="ap-empty">Scanning…</div>
                        ) : anomalies.length === 0 && nearMisses.length === 0 ? (
                            <div className="ap-empty">No anomalies</div>
                        ) : anomalies.length === 0 ? (
                            <>
                                <div className="ap-empty ap-empty--sm">No critical spikes</div>
                                {nearMisses.map(a => (
                                    <div key={a.country_code} className="ap-row ap-row--mover clickable"
                                        onClick={() => handleAnomalyClick(a.country_code)}>
                                        <span className="ap-country">{resolveCountryName(a.country_code, a.country_name)}</span>
                                        <span className="ap-mult">{a.multiplier.toFixed(1)}×</span>
                                    </div>
                                ))}
                            </>
                        ) : (
                            anomalies.map(a => (
                                <div key={a.country_code}
                                    className={`ap-row ap-row--${a.level} clickable`}
                                    onClick={() => handleAnomalyClick(a.country_code)}>
                                    <span className="ap-badge">{a.level.slice(0, 4).toUpperCase()}</span>
                                    <span className="ap-country">{resolveCountryName(a.country_code, a.country_name)}</span>
                                    <span className="ap-mult">{a.multiplier.toFixed(1)}×</span>
                                </div>
                            ))
                        )}
                    </div>

                    {/* Conflict events */}
                    {acledConflicts && acledConflicts.length > 0 && (
                        <div className="ap-sub">
                            <div className="col-label" style={{ color: '#f87171' }}>CONFLICT EVENTS</div>
                            <div className="col-scroll-short">
                                {acledConflicts.slice(0, 8).map(c => {
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
                                        <span className="ap-country" title={a.theme}>
                                            {getThemeLabel(a.theme).slice(0, 24)}
                                        </span>
                                        <span className="ap-mult">{a.multiplier.toFixed(1)}×</span>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}

                    <div className="col-label" style={{ marginTop: themeAnomalies?.length ? '8px' : 0 }}>
                        TRENDING
                    </div>
                    <div className="col-scroll">
                        {trendingSearches.length === 0 ? (
                            <div className="ap-empty">No data yet</div>
                        ) : (
                            trendingSearches.map((t, i) => (
                                <div key={i} className="ap-row ap-row--trend">
                                    <span className="ap-rank">#{i + 1}</span>
                                    <span className="ap-keyword">{t.keyword}</span>
                                    {t.country_count > 1 && (
                                        <span className="ap-ctry-count">{t.country_count}</span>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
