import React from 'react'

// Country name lookup
const COUNTRY_NAMES: Record<string, string> = {
    'AF': 'Afghanistan', 'AL': 'Albania', 'DZ': 'Algeria', 'AR': 'Argentina',
    'AU': 'Australia', 'AT': 'Austria', 'BD': 'Bangladesh', 'BE': 'Belgium',
    'BR': 'Brazil', 'CA': 'Canada', 'CL': 'Chile', 'CN': 'China',
    'CO': 'Colombia', 'CZ': 'Czech Republic', 'DK': 'Denmark', 'EG': 'Egypt',
    'FI': 'Finland', 'FR': 'France', 'DE': 'Germany', 'GH': 'Ghana',
    'GR': 'Greece', 'HK': 'Hong Kong', 'HU': 'Hungary', 'IN': 'India',
    'ID': 'Indonesia', 'IR': 'Iran', 'IQ': 'Iraq', 'IE': 'Ireland',
    'IL': 'Israel', 'IT': 'Italy', 'JP': 'Japan', 'KE': 'Kenya',
    'KR': 'South Korea', 'MY': 'Malaysia', 'MX': 'Mexico', 'NL': 'Netherlands',
    'NZ': 'New Zealand', 'NG': 'Nigeria', 'NO': 'Norway', 'PK': 'Pakistan',
    'PE': 'Peru', 'PH': 'Philippines', 'PL': 'Poland', 'PT': 'Portugal',
    'RO': 'Romania', 'RU': 'Russia', 'SA': 'Saudi Arabia', 'SG': 'Singapore',
    'ZA': 'South Africa', 'ES': 'Spain', 'SE': 'Sweden', 'CH': 'Switzerland',
    'TW': 'Taiwan', 'TH': 'Thailand', 'TR': 'Turkey', 'UA': 'Ukraine',
    'AE': 'UAE', 'GB': 'United Kingdom', 'US': 'United States', 'VE': 'Venezuela',
    'VN': 'Vietnam', 'BF': 'Burkina Faso', 'ET': 'Ethiopia', 'SY': 'Syria',
    'YE': 'Yemen', 'SD': 'Sudan', 'LY': 'Libya'
}

const getCountryName = (code: string): string => COUNTRY_NAMES[code] || code

// Normalize GDELT theme codes to readable names
const normalizeTheme = (theme: string): string => {
    if (!theme) return ''
    if (theme.startsWith('TAX_') || theme.startsWith('WB_') ||
        theme.startsWith('UNGP_') || theme.startsWith('CRISISLEX_') ||
        theme.startsWith('EPU_') || theme.startsWith('FNCACT')) {
        const parts = theme.split('_')
        for (let i = parts.length - 1; i >= 0; i--) {
            if (parts[i].length > 3 && !['TAX', 'WB', 'UNGP', 'EPU', 'FNCACT'].includes(parts[i])) {
                return parts[i].charAt(0) + parts[i].slice(1).toLowerCase()
            }
        }
        return ''
    }
    return theme
}

interface TooltipData {
    type: 'node' | 'flow'
    x: number
    y: number
    data: any
}

interface MapTooltipProps {
    tooltip: TooltipData | null
}

export const MapTooltip: React.FC<MapTooltipProps> = ({ tooltip }) => {
    if (!tooltip) return null

    const { type, x, y, data } = tooltip

    return (
        <div
            style={{
                position: 'fixed',
                left: x + 10,
                top: y + 10,
                background: 'rgba(10, 22, 40, 0.95)',
                border: '1px solid #1e3a5f',
                borderRadius: '8px',
                padding: '12px',
                minWidth: '180px',
                zIndex: 1000,
                pointerEvents: 'none',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
            }}
        >
            {type === 'node' && (
                <>
                    <div style={{ fontWeight: 'bold', color: '#fff', marginBottom: '8px', fontSize: '14px' }}>
                        {getCountryName(data.id || data.country_code)}
                    </div>
                    <div style={{ fontSize: '12px', color: '#e2e8f0', marginBottom: '4px' }}>
                        Signals: <strong>{(data.signalCount ?? data.signal_count ?? 0).toLocaleString()}</strong>
                    </div>
                    <div style={{ fontSize: '12px', color: '#e2e8f0', marginBottom: '4px' }}>
                        Sentiment: <strong style={{
                            color: (data.sentiment ?? data.avg_tone ?? 0) > 0 ? '#4ade80' : (data.sentiment ?? data.avg_tone ?? 0) < 0 ? '#f87171' : '#94a3b8'
                        }}>
                            {(data.sentiment ?? data.avg_tone ?? 0) > 0 ? '+' : ''}{(data.sentiment ?? data.avg_tone ?? 0).toFixed(2)}
                        </strong>
                    </div>
                    {(data.anomalyMultiplier ?? data.anomaly_multiplier) != null &&
                        (data.anomalyMultiplier ?? data.anomaly_multiplier) > 1.2 && (
                            <div style={{ fontSize: '12px', color: '#fbbf24', marginTop: '4px' }}>
                                ⚠️ {(data.anomalyMultiplier ?? data.anomaly_multiplier).toFixed(1)}× normal
                            </div>
                        )}
                    <div style={{ fontSize: '10px', color: '#6ba3d6', marginTop: '8px', fontStyle: 'italic' }}>
                        Click to focus on this country
                    </div>
                </>
            )}

            {type === 'flow' && (
                <>
                    <div style={{ fontWeight: 'bold', color: '#fff', marginBottom: '8px', fontSize: '14px' }}>
                        {getCountryName(data.sourceCountry || data.source)} ↔ {getCountryName(data.targetCountry || data.target)}
                    </div>
                    <div style={{ fontSize: '12px', color: '#e2e8f0', marginBottom: '4px' }}>
                        Strength: <strong>{Math.min((data.strength || 0) * 100, 100).toFixed(0)}%</strong>
                    </div>
                    {(data.sharedThemes || data.shared_themes)?.length > 0 && (
                        <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                            Shared: {(data.sharedThemes || data.shared_themes)
                                .map(normalizeTheme)
                                .filter(Boolean)
                                .slice(0, 3)
                                .join(', ') || 'Various topics'}
                        </div>
                    )}
                    <div style={{ fontSize: '10px', color: '#6ba3d6', marginTop: '8px', fontStyle: 'italic' }}>
                        Correlation, not causation
                    </div>
                </>
            )}
        </div>
    )
}

export type { TooltipData }
