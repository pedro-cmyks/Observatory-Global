import React, { useState } from 'react'
import { resolveThreadLabel } from '../lib/themeLabels'
import { resolveCountryName } from '../lib/countryNames'

interface LegendProps {
    showHeatmap: boolean
    showFlows: boolean
    showAircraft: boolean
    showVessels: boolean
    showTerminator: boolean
    activeCountry?: string | null
    activeTheme?: string | null
    activeThemeLabel?: string | null
    vesselCount?: number
    vesselConnected?: boolean
    aircraftError?: boolean
    conflictCount?: number
    disasterCount?: number
    anomalyCount?: number
}

// Red ring marker used by the always-on anomaly layer (#179: this marker was
// rendered but never explained in the legend).
const RingSwatch: React.FC<{ color: string; label: string; tip?: string }> = ({ color, label, tip }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }} data-tip={tip}>
        <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'transparent', border: `2px solid ${color}`, flexShrink: 0, boxShadow: `0 0 5px ${color}55` }} />
        <span style={{ fontSize: '11px', color: 'var(--color-text-primary)' }}>{label}</span>
    </div>
)

const Swatch: React.FC<{ color: string; label: string; tip?: string }> = ({ color, label, tip }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }} data-tip={tip}>
        <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: color, flexShrink: 0, boxShadow: `0 0 5px ${color}55` }} />
        <span style={{ fontSize: '11px', color: 'var(--color-text-primary)' }}>{label}</span>
    </div>
)

// G4: conflict markers are shape-coded on the map — the key must show the
// same shapes, not three colored dots.
const ShapeSwatch: React.FC<{ shape: 'circle' | 'triangle' | 'square'; color: string; label: string; tip?: string }> = ({ shape, color, label, tip }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }} data-tip={tip}>
        <svg width="10" height="10" viewBox="0 0 10 10" style={{ flexShrink: 0 }}>
            {shape === 'circle' && <circle cx="5" cy="5" r="4" fill={color} />}
            {shape === 'triangle' && <polygon points="5,0.5 9.5,9 0.5,9" fill={color} />}
            {shape === 'square' && <rect x="1" y="1" width="8" height="8" fill={color} />}
        </svg>
        <span style={{ fontSize: '11px', color: 'var(--color-text-primary)' }}>{label}</span>
    </div>
)

const ArcSwatch: React.FC<{ tip?: string }> = ({ tip }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }} data-tip={tip}>
        <svg width="28" height="10" viewBox="0 0 28 10" style={{ flexShrink: 0 }}>
            <path d="M2 9 Q14 1 26 9" stroke="url(#arcgrad)" strokeWidth="2.5" fill="none" strokeLinecap="round" />
            <defs>
                {/* Theme-var stops: noir resolves to its own accents; the
                    emerald pair gets a visible arc on the light ground. */}
                <linearGradient id="arcgrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="var(--color-accent-primary, #68dbae)" />
                    <stop offset="100%" stopColor="var(--color-info, #22d3ee)" />
                </linearGradient>
            </defs>
        </svg>
        <span style={{ fontSize: '11px', color: 'var(--color-text-primary)' }}>Width = co-occurrence strength</span>
    </div>
)

const SectionHeader: React.FC<{ label: string; tip?: string }> = ({ label, tip }) => (
    <div
        data-tip={tip}
        style={{ color: 'var(--color-accent-primary)', fontFamily: 'var(--font-mono, monospace)', fontSize: '9.5px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '7px', cursor: tip ? 'help' : undefined }}
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
    activeThemeLabel,
    vesselCount = 0,
    vesselConnected = false,
    aircraftError = false,
    conflictCount = 0,
    disasterCount = 0,
    anomalyCount = 0,
}) => {
    // On phones the expanded legend floats over the stream/workbench; start
    // collapsed (a small "MAP KEY" button) so it never overlaps content. The
    // user can still expand it. Desktop keeps it open.
    const [collapsed, setCollapsed] = useState(
        () => typeof window !== 'undefined' && window.innerWidth <= 768,
    )

    const contextLabel = activeCountry
        ? resolveCountryName(activeCountry)
        : activeTheme
            ? resolveThreadLabel(activeTheme, activeThemeLabel)
            : null

    // Only credit sources that feed a currently-visible map layer, so the
    // footer never claims a feed (AIS, ADS-B) the user isn't seeing.
    // Country nodes / heat / flows derive from the FULL signal corpus — the
    // 'GDELT 2.0'-only label was stale (L7): 219 RSS feeds, NewsData, and the
    // social lane all feed signals_v2; conflict dots are GDELT CAMEO events.
    const activeSources = ['GDELT 2.0', 'RSS ×219', 'NewsData', 'Social']
    if (showVessels) activeSources.push('AIS Stream')
    if (showAircraft) activeSources.push('ADS-B Exchange')

    if (collapsed) {
        return (
            <button
                onClick={() => setCollapsed(false)}
                className="panel"
                style={{ position: 'absolute', bottom: '14px', left: '14px', padding: '6px 11px', cursor: 'pointer', zIndex: 800, fontSize: '11px', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border-subtle)' }}
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
            style={{ position: 'absolute', bottom: '14px', left: '14px', minWidth: '210px', maxWidth: '250px', maxHeight: 'calc(100% - 28px)', overflowY: 'auto', zIndex: 800, padding: '12px 14px' }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <span style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--color-text-secondary)' }}>Map Key</span>
                <button
                    onClick={() => setCollapsed(true)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', lineHeight: 1, padding: '0 2px', fontSize: '14px' }}
                    aria-label="Collapse legend"
                >
                    ×
                </button>
            </div>

            {contextLabel && (
                <div style={{ marginBottom: '10px', padding: '5px 8px', borderRadius: '4px', background: 'rgba(var(--color-accent-deep-rgb), 0.08)', border: '1px solid rgba(var(--color-accent-deep-rgb), 0.22)', fontSize: '11px', color: 'var(--color-accent-primary)' }}>
                    ◎ Filtered: {contextLabel}
                </div>
            )}

            {/* Always-on base layer: anomaly spike rings (#179 — these markers
                were visible on the map but absent from the legend) */}
            {anomalyCount > 0 && (
                <div style={{ marginBottom: '12px' }}>
                    <SectionHeader label={`Baseline spikes · ${anomalyCount}`} tip="Countries whose current signal volume deviates sharply from their own recent baseline. Ring size scales with signal count." />
                    <RingSwatch color="rgba(239,68,68,0.95)" label="Volume spike vs own baseline" tip="Red ring = country is far above its normal media volume right now. Always visible — not affected by layer toggles." />
                </div>
            )}

            {/* Active optional layers */}
            {showHeatmap && (
                <div style={{ marginBottom: '12px' }}>
                    <SectionHeader label="Countries heat layer" tip="Country color = composite anomaly (velocity, surprise, source diversity, local voice) vs each country's OWN baseline — NOT raw volume. A small country spiking above its norm outranks a high-volume one. Border thickness = signal volume." />
                    {/* Mirrors the Equal Earth heat ramp (lib/countryHeatStates
                        heatFillColor): transparent → deep blue → teal → amber →
                        vermilion → near-white. G1: luminance climbs monotonically
                        (CVD-validated), so brighter ALWAYS means hotter. */}
                    {/* Same stops AND alphas as the map fill (heatFillColor):
                        "at baseline" is nearly transparent on the map, so the
                        legend must not show it as vivid blue. */}
                    <div style={{ height: '8px', borderRadius: '4px', background: 'linear-gradient(90deg, rgba(30,70,165,0) 0%, rgba(30,70,165,0.30) 12%, rgba(18,135,158,0.55) 32%, rgba(196,120,32,0.80) 55%, rgba(253,108,84,0.94) 78%, rgba(255,226,205,1) 100%)', marginBottom: '4px' }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--color-text-muted)' }}>
                        <span>at baseline</span>
                        {/* G3: a 5-hue scale with endpoint labels only can't be
                            read back into values — one mid anchor. */}
                        <span style={{ opacity: 0.8 }}>elevated</span>
                        <span>spiking vs own norm</span>
                    </div>
                    <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', marginTop: '3px', opacity: 0.8 }}>
                        vs each country's own baseline — brighter = hotter
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
                        <RingSwatch color="rgba(0,255,210,0.8)" label="Chokepoint zone" tip="Strategic maritime chokepoint (Suez, Hormuz, Panama, Malacca, Bosphorus…). Bright ring = chokepoint relevant to the active filter." />
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

            {conflictCount > 0 && (
                <div style={{ marginBottom: '12px' }}>
                    <SectionHeader label={`Conflict Events · ${conflictCount}`} tip="Violent events extracted from GDELT event records. Marker size scales with reported severity." />
                    {/* G4 (dataviz audit): three warm hues at ~3px were
                        indistinguishable — markers are now SHAPE-coded
                        (circle/triangle/square), mirroring the map exactly. */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <ShapeSwatch shape="circle" color="rgba(239,68,68,0.9)" label="Armed force" tip="Fighting, artillery, aerial weapons, assassinations (GDELT CAMEO events)" />
                        <ShapeSwatch shape="triangle" color="rgba(249,115,22,0.85)" label="Unrest / repression" tip="Protests, riots, repression, assaults, abductions (GDELT CAMEO events)" />
                        <ShapeSwatch shape="square" color="rgba(234,179,8,0.8)" label="Coercion / posture" tip="Sanctions, seizures, mobilization, shows of force, other coercive events (GDELT CAMEO events)" />
                    </div>
                </div>
            )}

            {disasterCount > 0 && (
                <div style={{ marginBottom: '12px' }}>
                    <SectionHeader label={`Natural Hazards · ${disasterCount}`} tip="Structured disaster events from USGS (earthquakes) and GDACS (multi-hazard), last 72h. Minor green-alert wildfires are excluded. Click a marker to open the authoritative event page." />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <Swatch color="rgba(251,191,36,0.85)" label="Earthquake" tip="USGS — size scales with magnitude" />
                        <Swatch color="rgba(56,189,248,0.85)" label="Flood" tip="GDACS flood events" />
                        <Swatch color="rgba(167,139,250,0.85)" label="Cyclone" tip="GDACS tropical cyclones" />
                        <Swatch color="rgba(249,115,22,0.85)" label="Wildfire (Orange/Red)" tip="GDACS significant wildfires only" />
                    </div>
                </div>
            )}

            <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '9px', letterSpacing: '0.03em', color: 'var(--color-text-muted)', borderTop: '1px solid var(--color-border-subtle)', paddingTop: '8px', marginTop: '4px' }}>
                Sources: {activeSources.join(' · ')}
            </div>
        </div>
    )
}
