import React from 'react'
import { useCrisis } from '../contexts/CrisisContext'
import { useFocus } from '../contexts/FocusContext'

export const CrisisDashboard: React.FC = () => {
    const { enabled, anomalies, overallSeverity, loading } = useCrisis()
    const { setFocus, isActive: focusActive } = useFocus()

    if (!enabled) return null
    if (focusActive) return null // FocusSummaryPanel takes precedence

    const levelColors: Record<string, string> = {
        critical: '#ef4444',
        elevated: '#f97316',
        notable: '#fbbf24',
        normal: '#94a3b8'
    }

    // Severity indicator as CSS circle
    const severityIndicator = (level: string) => (
        <span style={{
            display: 'inline-block',
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: levelColors[level],
            marginRight: '4px'
        }} />
    );

    return (
        <div
            style={{
                position: 'fixed',
                right: '20px',
                top: '120px',
                width: '300px',
                maxHeight: 'calc(100vh - 150px)',
                background: 'linear-gradient(180deg, #1a0a0a 0%, #1f0d0d 100%)',
                border: `1px solid ${levelColors[overallSeverity]}`,
                borderRadius: '12px',
                overflow: 'hidden',
                boxShadow: `0 0 20px ${levelColors[overallSeverity]}40`,
                zIndex: 900
            }}
        >
            <div style={{
                padding: '16px',
                borderBottom: `1px solid ${levelColors[overallSeverity]}40`,
                background: `${levelColors[overallSeverity]}10`
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{
                        width: '12px',
                        height: '12px',
                        borderRadius: '50%',
                        background: '#ef4444',
                        boxShadow: '0 0 8px #ef4444'
                    }} />
                    <h3 style={{ margin: 0, fontSize: '14px', color: levelColors[overallSeverity], textTransform: 'uppercase' }}>
                        Crisis Dashboard
                    </h3>
                </div>
                <div style={{ marginTop: '8px', fontSize: '12px', color: '#94a3b8' }}>
                    Overall: <strong style={{ color: levelColors[overallSeverity] }}>{overallSeverity.toUpperCase()}</strong>
                </div>
            </div>

            <div style={{ padding: '16px', overflowY: 'auto', maxHeight: 'calc(100vh - 280px)' }}>
                {loading ? (
                    <div style={{ color: '#94a3b8', fontSize: '12px' }}>Loading anomalies...</div>
                ) : anomalies.length === 0 ? (
                    <div style={{ color: '#94a3b8', fontSize: '12px' }}>No significant anomalies detected.</div>
                ) : (
                    <>
                        <div style={{ fontSize: '11px', color: '#6ba3d6', textTransform: 'uppercase', marginBottom: '12px' }}>
                            Country Activity Spikes
                        </div>
                        {anomalies.map((a) => (
                            <div
                                key={a.country_code}
                                style={{
                                    padding: '10px',
                                    marginBottom: '8px',
                                    background: 'rgba(255,255,255,0.03)',
                                    borderRadius: '8px',
                                    borderLeft: `3px solid ${levelColors[a.level]}`
                                }}
                            >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{ fontWeight: 'bold', color: '#fff' }}>
                                        {severityIndicator(a.level)} {a.country_name || a.country_code} <span style={{ opacity: 0.7, fontSize: '0.9em' }}>({a.country_code})</span>
                                    </span>
                                    <span style={{ fontSize: '12px', color: levelColors[a.level] }} title="Multiplier: Signal count relative to 7-day baseline">
                                        {a.multiplier?.toFixed(1)}× normal
                                    </span>
                                </div>
                                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }} title="Z-Score: Standard deviations from mean">
                                    {a.current_count.toLocaleString()} signals (z: {a.zscore?.toFixed(1)})
                                </div>
                                <button
                                    onClick={() => setFocus('country', a.country_code, a.country_code)}
                                    style={{
                                        marginTop: '8px',
                                        padding: '4px 8px',
                                        fontSize: '10px',
                                        background: 'transparent',
                                        border: `1px solid ${levelColors[a.level]}`,
                                        borderRadius: '4px',
                                        color: levelColors[a.level],
                                        cursor: 'pointer'
                                    }}
                                >
                                    Investigate →
                                </button>
                            </div>
                        ))}
                    </>
                )}
            </div>

            <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.05)', fontSize: '10px', color: '#6ba3d6' }}>
                Baseline: 7-day rolling average
            </div>
        </div>
    )
}
