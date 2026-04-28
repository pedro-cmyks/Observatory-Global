import React from 'react'
import { useCrisis } from '../contexts/CrisisContext'
import { useFocus } from '../contexts/FocusContext'
import './AnomalyPanel.css'

// Country code → name fallback for unresolved GDELT codes
const COUNTRY_NAMES: Record<string, string> = {
    AL: 'Albania', KV: 'Kosovo', SI: 'Slovenia', RI: 'Indonesia',
    RB: 'Serbia', MN: 'Mongolia', RE: 'Réunion', AN: 'Netherlands Antilles',
    LY: 'Libya', GZ: 'Gaza', WE: 'West Bank', YM: 'Yemen',
    LS: 'Lesotho', AF: 'Afghanistan', IR: 'Iran', US: 'United States',
    GB: 'United Kingdom', DE: 'Germany', FR: 'France', CN: 'China',
    RU: 'Russia', IL: 'Israel', ES: 'Spain', IT: 'Italy',
    JP: 'Japan', IN: 'India', BR: 'Brazil', AU: 'Australia',
    CA: 'Canada', MX: 'Mexico', TR: 'Turkey', SA: 'Saudi Arabia',
    PK: 'Pakistan', NG: 'Nigeria', ZA: 'South Africa', EG: 'Egypt',
    UA: 'Ukraine', PL: 'Poland', KR: 'South Korea', TW: 'Taiwan',
}

const resolveCountryName = (code: string, apiName?: string): string => {
    if (apiName && apiName !== code && apiName.length > 2) return apiName
    return COUNTRY_NAMES[code] || code
}

export const AnomalyPanel: React.FC = () => {
    const { anomalies, nearMisses, themeAnomalies, meta, overallSeverity, loading } = useCrisis()
    const { setFocus, setMapFlyCountry } = useFocus()

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
        </div>
    )
}
