import React from 'react'
import { useCrisis } from '../contexts/CrisisContext'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import { resolveCountryName } from '../lib/countryNames'
import './AnomalyPanel.css'

export const AnomalyPanel: React.FC = () => {
    const { anomalies, nearMisses, themeAnomalies, meta, overallSeverity, loading } = useCrisis()
    const { setFocus, setMapFlyCountry } = useFocus()
    const { acledConflicts } = useFocusData()

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
            <div className="anomaly-description">Countries with unusual signal spikes vs 7-day baseline</div>

            <div className="anomaly-list">
                {loading && anomalies.length === 0 && nearMisses.length === 0 ? (
                    <div className="empty-state">Scanning metrics...</div>
                ) : anomalies.length === 0 ? (
                    <div className="calm-state">
                        <div className="calm-state-message">No anomalies detected in the last 24h</div>
                        {meta && (
                            <div className="calm-state-stats">
                                <div className="stat-item">
                                    <span className="stat-value">{meta.active_countries}</span>
                                    <span className="stat-label">countries</span>
                                </div>
                                <div className="stat-item">
                                    <span className="stat-value">{(meta.total_signals_24h / 1000).toFixed(1)}k</span>
                                    <span className="stat-label">signals/24h</span>
                                </div>
                            </div>
                        )}
                        {nearMisses.length > 0 && (
                            <div className="near-misses">
                                <div className="near-misses-header">TOP MOVERS (BELOW THRESHOLD)</div>
                                {nearMisses.map(a => (
                                    <div 
                                        key={a.country_code} 
                                        className={`anomaly-row level-nearmiss clickable`}
                                        onClick={() => handleAnomalyClick(a.country_code)}
                                    >
                                        <div className="country-info">
                                            <span className="country-name">{resolveCountryName(a.country_code, a.country_name)}</span>
                                        </div>
                                        <div className="metrics">
                                            <span className="multiplier">{a.multiplier.toFixed(1)}× norm</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
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
                                <span className="multiplier">{a.multiplier.toFixed(1)}× above normal</span>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {themeAnomalies && themeAnomalies.length > 0 && (
                <div className="theme-anomaly-section">
                    <div className="theme-anomaly-header" style={{
                        fontSize: '9px', fontWeight: 'bold', color: '#64748b', letterSpacing: '0.05em', 
                        marginTop: '12px', marginBottom: '8px', paddingLeft: '8px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '12px'
                    }}>THEME SPIKES</div>
                    <div className="anomaly-list">
                        {themeAnomalies.map(a => (
                            <div 
                                key={a.theme} 
                                className="anomaly-row level-elevated clickable"
                                onClick={() => setFocus('theme', a.theme)}
                            >
                                <div className="level-badge" style={{ backgroundColor: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b' }}>SPIKE</div>
                                <div className="country-info">
                                    <span className="country-name" style={{ textTransform: 'uppercase' }}>{a.theme.replace(/_/g, ' ')}</span>
                                </div>
                                <div className="metrics">
                                    <span className="multiplier">{a.multiplier.toFixed(1)}× norm</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {acledConflicts && acledConflicts.length > 0 && (
                <div className="theme-anomaly-section">
                    <div className="theme-anomaly-header" style={{
                        fontSize: '9px', fontWeight: 'bold', color: '#64748b', letterSpacing: '0.05em', 
                        marginTop: '12px', marginBottom: '8px', paddingLeft: '8px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '12px'
                    }}>RECENT KINETIC CONFLICTS (ACLED)</div>
                    <div className="anomaly-list">
                        {acledConflicts.slice(0, 15).map(c => (
                            <div 
                                key={c.id} 
                                className="anomaly-row level-critical clickable"
                                onClick={() => handleAnomalyClick(c.location.country)}
                            >
                                <div className="level-badge" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}>
                                    {c.fatalities > 0 ? `${c.fatalities} KIA` : 'WARN'}
                                </div>
                                <div className="country-info">
                                    <span className="country-name" style={{ fontSize: '11px' }}>{c.location.country} - {c.type}</span>
                                    <span style={{ fontSize: '9px', color: '#64748b', display: 'block', marginTop: '2px' }}>{c.location.name}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
