import React from 'react'
import { useCrisis } from '../contexts/CrisisContext'
import { useFocus } from '../contexts/FocusContext'
import './AnomalyPanel.css'

export const AnomalyPanel: React.FC = () => {
    const { anomalies, overallSeverity, loading } = useCrisis()
    const { setCountry } = useFocus()

    const handleAnomalyClick = (countryCode: string) => {
        setCountry(countryCode, 'anomaly')
    }

    return (
        <div className={`anomaly-panel-container severity-${overallSeverity}`}>
            <div className={`severity-header ${overallSeverity}`}>
                <span className="pulse-dot"></span>
                SYSTEM STATUS: {overallSeverity.toUpperCase()}
            </div>

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
                                <span className="country-code">{a.country_code}</span>
                                <span className="country-name">{a.country_name || a.country_code}</span>
                            </div>
                            <div className="metrics">
                                <span className="multiplier">{a.multiplier.toFixed(1)}×</span>
                                <span className="zscore">z: {a.zscore.toFixed(1)}</span>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}
