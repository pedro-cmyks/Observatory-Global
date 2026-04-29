import React, { useState, useEffect } from 'react'
import { useCrisis } from '../contexts/CrisisContext'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import { resolveCountryName } from '../lib/countryNames'
import './AnomalyPanel.css'

export const AnomalyPanel: React.FC = () => {
    const { anomalies, nearMisses, themeAnomalies, meta, overallSeverity, loading } = useCrisis()
    const { setFocus, setMapFlyCountry } = useFocus()
    const { acledConflicts } = useFocusData()
    const [trendingSearches, setTrendingSearches] = useState<{ keyword: string; country_count: number }[]>([])

    useEffect(() => {
        fetch('/api/v2/trends?hours=24&limit=10')
            .then(r => r.ok ? r.json() : null)
            .then(d => { if (d?.trending) setTrendingSearches(d.trending) })
            .catch(() => {})
    }, [])

    const handleAnomalyClick = (countryCode: string) => {
        setFocus('country', countryCode)
        setMapFlyCountry(countryCode)
    }

    return (
        <div className={`anomaly-panel-container severity-${overallSeverity}`}>
            <div className={`severity-header ${overallSeverity}`}>
                <span className="pulse-dot"></span>
                SYSTEM STATUS: {overallSeverity.toUpperCase()}
            </div>

            <div className="anomaly-body-grid">
                {/* ── Left column: Geo alerts ── */}
                <div className="anomaly-col">
                    <div className="col-label">GEO ALERTS</div>
                    <div className="anomaly-list col-scroll">
                        {loading && anomalies.length === 0 && nearMisses.length === 0 ? (
                            <div className="empty-state">Scanning...</div>
                        ) : anomalies.length === 0 ? (
                            <>
                                <div className="calm-state-message" style={{ fontSize: '10px', color: '#64748b', padding: '8px 0', textAlign: 'center' }}>
                                    No anomalies detected
                                </div>
                                {meta && (
                                    <div className="calm-state-stats">
                                        <div className="stat-item">
                                            <span className="stat-value">{meta.active_countries}</span>
                                            <span className="stat-label">countries</span>
                                        </div>
                                        <div className="stat-item">
                                            <span className="stat-value">{(meta.total_signals_24h / 1000).toFixed(1)}k</span>
                                            <span className="stat-label">signals</span>
                                        </div>
                                    </div>
                                )}
                                {nearMisses.length > 0 && (
                                    <div className="near-misses">
                                        <div className="near-misses-header">TOP MOVERS</div>
                                        {nearMisses.map(a => (
                                            <div
                                                key={a.country_code}
                                                className="anomaly-row level-nearmiss clickable"
                                                onClick={() => handleAnomalyClick(a.country_code)}
                                            >
                                                <div className="country-info">
                                                    <span className="country-name">{resolveCountryName(a.country_code, a.country_name)}</span>
                                                </div>
                                                <div className="metrics">
                                                    <span className="multiplier">{a.multiplier.toFixed(1)}×</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </>
                        ) : (
                            anomalies.map(a => (
                                <div
                                    key={a.country_code}
                                    className={`anomaly-row level-${a.level} clickable`}
                                    onClick={() => handleAnomalyClick(a.country_code)}
                                >
                                    <div className="level-badge">{a.level.substring(0, 4).toUpperCase()}</div>
                                    <div className="country-info">
                                        <span className="country-name">{resolveCountryName(a.country_code, a.country_name)}</span>
                                    </div>
                                    <div className="metrics">
                                        <span className="multiplier">{a.multiplier.toFixed(1)}×</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>

                    {acledConflicts && acledConflicts.length > 0 && (
                        <div className="col-sub-section">
                            <div className="col-label" style={{ color: '#ef4444' }}>KINETIC (ACLED)</div>
                            <div className="anomaly-list col-scroll-short">
                                {acledConflicts.slice(0, 10).map(c => (
                                    <div
                                        key={c.id}
                                        className="anomaly-row level-critical clickable"
                                        onClick={() => handleAnomalyClick(c.location.country)}
                                    >
                                        <div className="level-badge" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}>
                                            {c.fatalities > 0 ? `${c.fatalities}` : '!'}
                                        </div>
                                        <div className="country-info">
                                            <span className="country-name" style={{ fontSize: '10px' }}>{c.location.country}</span>
                                            <span style={{ fontSize: '9px', color: '#64748b' }}>{c.type}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* ── Right column: Intelligence feeds ── */}
                <div className="anomaly-col col-right-border">
                    {themeAnomalies && themeAnomalies.length > 0 && (
                        <>
                            <div className="col-label">THEME SPIKES</div>
                            <div className="anomaly-list col-scroll-short">
                                {themeAnomalies.map(a => (
                                    <div
                                        key={a.theme}
                                        className="anomaly-row level-elevated clickable"
                                        onClick={() => setFocus('theme', a.theme)}
                                    >
                                        <div className="level-badge" style={{ backgroundColor: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b' }}>↑</div>
                                        <div className="country-info">
                                            <span className="country-name" style={{ textTransform: 'uppercase', fontSize: '10px' }}>
                                                {a.theme.replace(/_/g, ' ')}
                                            </span>
                                        </div>
                                        <div className="metrics">
                                            <span className="multiplier">{a.multiplier.toFixed(1)}×</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}

                    <div className="col-label" style={{ marginTop: themeAnomalies?.length ? '8px' : 0 }}>
                        TRENDING (GOOGLE)
                    </div>
                    <div className="anomaly-list col-scroll">
                        {trendingSearches.length === 0 ? (
                            <div className="empty-state" style={{ padding: '12px 4px' }}>No data yet</div>
                        ) : (
                            trendingSearches.map((t, i) => (
                                <div key={i} className="anomaly-row level-nearmiss" style={{ cursor: 'default' }}>
                                    <div className="level-badge" style={{ color: '#60a5fa', minWidth: '18px' }}>
                                        {i + 1}
                                    </div>
                                    <div className="country-info">
                                        <span className="country-name" style={{ textTransform: 'none', fontSize: '11px' }}>{t.keyword}</span>
                                        {t.country_count > 1 && (
                                            <span style={{ fontSize: '9px', color: '#60a5fa' }}>{t.country_count} countries</span>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
