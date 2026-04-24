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
    const { anomalies, overallSeverity, loading } = useCrisis()
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
                {loading && anomalies.length === 0 ? (
                    <div className="empty-state">Scanning metrics...</div>
                ) : anomalies.length === 0 ? (
                    <div className="empty-state">No anomalies detected in the last 24h</div>
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
        </div>
    )
}
