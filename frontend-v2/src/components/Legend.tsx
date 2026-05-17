import React, { useState } from 'react'
import { getThemeLabel } from '../lib/themeLabels'
import { resolveCountryName } from '../lib/countryNames'

interface LegendProps {
    showHeatmap: boolean
    showFlows: boolean
    showAircraft: boolean
    showVessels: boolean
    showTerminator: boolean
    activeCountry?: string | null
    activeTheme?: string | null
    vesselCount?: number
    vesselConnected?: boolean
    aircraftError?: boolean
}

const Swatch: React.FC<{ color: string; label: string; tip?: string }> = ({ color, label, tip }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }} data-tip={tip}>
        <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: color, flexShrink: 0, boxShadow: `0 0 5px ${color}55` }} />
        <span style={{ fontSize: '11px', color: 'var(--color-text-primary)' }}>{label}</span>
    </div>
)

const ArcSwatch: React.FC<{ tip?: string }> = ({ tip }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }} data-tip={tip}>
        <svg width="28" height="10" viewBox="0 0 28 10" style={{ flexShrink: 0 }}>
            <path d="M2 9 Q14 1 26 9" stroke="url(#arcgrad)" strokeWidth="2.5" fill="none" strokeLinecap="round" />
            <defs>
                <linearGradient id="arcgrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#68dbae" />
                    <stop offset="100%" stopColor="#22d3ee" />
                </linearGradient>
            </defs>
        </svg>
        <span style={{ fontSize: '11px', color: 'var(--color-text-primary)' }}>Width = co-occurrence strength</span>
    </div>
)

const SectionHeader: React.FC<{ label: string; tip?: string }> = ({ label, tip }) => (
    <div
        data-tip={tip}
        style={{ color: 'var(--color-accent-primary)', fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '7px', cursor: tip ? 'help' : undefined }}
    >
        {label}
    </div>
)

export const Legend: React.FC<LegendProps> = ({
    showHeatmap,
    showFlows,
    showAircraft,
    showVessels,
    showTerminator,
    activeCountry,
    activeTheme,
    vesselCount = 0,
    vesselConnected = false,
    aircraftError = false,
}) => {
    const [collapsed, setCollapsed] = useState(false)

    const contextLabel = activeCountry
        ? resolveCountryName(activeCountry)
        : activeTheme
            ? getThemeLabel(activeTheme)
            : null

    if (collapsed) {
        return (
            <button
                onClick={() => setCollapsed(false)}
                className="panel"
                style={{ position: 'fixed', bottom: '20px', left: '20px', padding: '6px 11px', cursor: 'pointer', zIndex: 800, fontSize: '11px', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border-subtle)' }}
                data-tip="Show map legend"
                aria-label="Show map legend"
            >
                MAP KEY
            </button>
        )
    }

    return (
        <div
            className="panel"
            style={{ position: 'fixed', bottom: '20px', left: '20px', minWidth: '220px', maxWidth: '260px', zIndex: 800, padding: '12px 14px' }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <span style={{ fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--color-text-secondary)' }}>Map Key</span>
                <button
                    onClick={() => setCollapsed(true)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', lineHeight: 1, padding: '0 2px', fontSize: '14px' }}
                    aria-label="Collapse legend"
                >
                    ×
                </button>
            </div>

            {contextLabel && (
                <div style={{ marginBottom: '10px', padding: '5px 8px', borderRadius: '4px', background: 'rgba(104, 219, 174, 0.08)', border: '1px solid rgba(104, 219, 174, 0.18)', fontSize: '11px', color: '#68dbae' }}>
                    ◎ Filtered: {contextLabel}
                </div>
            )}

            {/* Always-on: country nodes */}
            <div style={{ marginBottom: '12px' }}>
                <SectionHeader label="Countries" tip="Node size = total signals (log scale). Color = average news tone. Glow ring = above-baseline activity spike." />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <Swatch color="var(--color-sentiment-positive)" label="Positive tone" tip="Avg sentiment > 0.1 (scale: −1 to +1)" />
                    <Swatch color="var(--color-sentiment-neutral)" label="Neutral tone" tip="Avg sentiment between −0.1 and +0.1" />
                    <Swatch color="var(--color-sentiment-negative)" label="Negative tone" tip="Avg sentiment < −0.1" />
                    <Swatch color="var(--color-accent-secondary)" label="Baseline spike" tip="Current signals significantly above that country's 7-day rolling average" />
                </div>
            </div>

            {/* Active optional layers */}
            {showHeatmap && (
                <div style={{ marginBottom: '12px' }}>
                    <SectionHeader label="Heat Layer" tip="Country fill intensity = normalized deviation from baseline. Red = far above-average media volume." />
                    <div style={{ height: '8px', borderRadius: '4px', background: 'linear-gradient(90deg, rgba(29,78,216,0.6), rgba(251,146,60,0.8), rgba(239,68,68,0.95))', marginBottom: '4px' }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--color-text-muted)' }}>
                        <span>at baseline</span>
                        <span>far above baseline</span>
                    </div>
                </div>
            )}

            {showFlows && (
                <div style={{ marginBottom: '12px' }}>
                    <SectionHeader
                        label={contextLabel ? `Flows · ${contextLabel.slice(0, 18)}` : 'Narrative Flows'}
                        tip={contextLabel ? `Arcs show countries with shared media themes related to ${contextLabel}` : 'Arcs connect countries sharing dominant narrative themes. Not directional — shared attention, not causation.'}
                    />
                    <ArcSwatch tip="Jaccard similarity of theme co-occurrence between countries" />
                    <div style={{ fontSize: '10px', color: 'var(--color-severity-notable)', marginTop: '5px' }}>
                        Non-directional · shared attention
                    </div>
                </div>
            )}

            {showVessels && (
                <div style={{ marginBottom: '12px' }}>
                    <SectionHeader
                        label={`Vessels${vesselCount > 0 ? ` · ${vesselCount}` : ''}${vesselConnected ? ' · live' : ' · connecting'}`}
                        tip="AIS transponder positions near strategic maritime chokepoints (Suez, Strait of Hormuz, Panama, Malacca, Bosphorus, etc.)"
                    />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <Swatch color="rgba(0,220,200,0.9)" label="> 10 kn — underway" tip="Vessel speed above 10 knots (active transit)" />
                        <Swatch color="rgba(0,180,160,0.7)" label="≤ 10 kn — slow / anchored" tip="Vessel speed 10 knots or below (slow transit, anchoring, or stopped)" />
                    </div>
                </div>
            )}

            {showAircraft && (
                <div style={{ marginBottom: '12px' }}>
                    <SectionHeader
                        label={aircraftError ? 'Aircraft · no data' : 'Aircraft · ADS-B live'}
                        tip="ADS-B transponder positions. Cruise altitude defined as > 10,000 ft."
                    />
                    {aircraftError ? (
                        <div style={{ fontSize: '11px', color: 'var(--color-severity-notable)' }}>Feed unavailable — toggle off to reduce noise</div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <Swatch color="rgba(255,255,255,0.85)" label="> 10,000 ft — cruise" />
                            <Swatch color="rgba(255,210,80,0.85)" label="5,000–10,000 ft — mid" />
                            <Swatch color="rgba(255,140,40,0.85)" label="< 5,000 ft — low" />
                        </div>
                    )}
                </div>
            )}

            {showTerminator && (
                <div style={{ marginBottom: '12px' }}>
                    <SectionHeader label="Day / Night" tip="Solar terminator position at current UTC time. Dark overlay = night side." />
                    <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                        <span style={{ width: '22px', height: '10px', borderRadius: '3px', background: 'rgba(0,8,25,0.56)', border: '1px solid rgba(80,120,180,0.4)', flexShrink: 0 }} />
                        <span style={{ fontSize: '11px', color: 'var(--color-text-primary)' }}>Night side shadow</span>
                    </div>
                </div>
            )}

            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', borderTop: '1px solid var(--color-border-subtle)', paddingTop: '8px', marginTop: '4px' }}>
                Sources: GDELT 2.0 · AIS Stream · ADS-B Exchange · ACLED
            </div>
        </div>
    )
}
