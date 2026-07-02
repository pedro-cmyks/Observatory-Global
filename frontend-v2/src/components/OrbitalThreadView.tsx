import { useEffect, useMemo, useRef, useState } from 'react'
import {
    angleAt,
    bodyRadius,
    entrantsBetween,
    isComet,
    normalizeDistances,
    orbitRadius,
    presenceAlpha,
    type OrbitalBody,
    type OrbitalWindow,
} from '../lib/orbitalLayout'
import { resolveCountryName } from '../lib/countryNames'
import './OrbitalThreadView.css'

interface OrbitalPayload {
    contract: string
    theme: string
    centroid_basis?: 'stored' | 'computed'
    center: {
        label: string
        category: string | null
        crisis_relevant: boolean | null
        member_count: number
        window: OrbitalWindow
    } | null
    bodies: OrbitalBody[]
    reason?: string
}

interface OrbitalThreadViewProps {
    theme: string
    themeLabel: string
    hours: number
    onCountrySelect?: (code: string) => void
    onPersonSelect?: (name: string) => void
}

const TYPE_COLORS: Record<OrbitalBody['type'], string> = {
    person: '#a78bfa',
    organization: '#f59e0b',
    place: '#60a5fa',
    event: '#f472b6',
    country: '#22d3ee',
}

const EMPTY_REASONS: Record<string, string> = {
    topic_not_found: 'This thread has no engine record to orbit around.',
    unsupported_theme_kind: 'Orbital view needs a thread (dynamic or atlas topic), not a raw GDELT code.',
    no_members: 'No typed members recorded for this thread yet — the nightly engine pass populates them.',
    no_embeddings: 'Member signals are not embedded yet, so semantic distance cannot be measured.',
    no_embedded_members_in_window: 'No embedded member signals inside this time window.',
    error: 'Orbital data unavailable right now.',
}

function bodyLabel(b: OrbitalBody): string {
    return b.type === 'country' ? resolveCountryName(b.label) : b.label
}

export function OrbitalThreadView({ theme, themeLabel, hours, onCountrySelect, onPersonSelect }: OrbitalThreadViewProps) {
    const [payload, setPayload] = useState<OrbitalPayload | null>(null)
    const [loading, setLoading] = useState(true)
    const [scrubPct, setScrubPct] = useState(100)
    const [hovered, setHovered] = useState<OrbitalBody | null>(null)
    const containerRef = useRef<HTMLDivElement | null>(null)
    const [width, setWidth] = useState(560)

    useEffect(() => {
        const element = containerRef.current
        if (!element) return
        const observer = new ResizeObserver(entries => {
            const w = entries[0]?.contentRect.width
            if (w) setWidth(Math.max(360, w))
        })
        observer.observe(element)
        return () => observer.disconnect()
    }, [])

    // §I time-model: the orbital view reads the story's OWN timeline (at least
    // a week), not the console's global window — time is legible inside via
    // the scrubber instead of being pre-filtered away.
    const orbitalHours = Math.max(hours, 168)

    useEffect(() => {
        let cancelled = false
        setLoading(true)
        setScrubPct(100)
        fetch(`/api/v2/theme/${encodeURIComponent(theme)}/orbital?hours=${orbitalHours}`)
            .then(r => r.json())
            .then(json => { if (!cancelled) setPayload(json) })
            .catch(() => { if (!cancelled) setPayload(null) })
            .finally(() => { if (!cancelled) setLoading(false) })
        return () => { cancelled = true }
    }, [theme, orbitalHours])

    const window_ = payload?.center?.window ?? null
    const scrubT = useMemo(() => {
        if (!window_) return Date.now()
        const start = Date.parse(window_.start)
        const end = Date.parse(window_.end)
        return start + (end - start) * (scrubPct / 100)
    }, [window_, scrubPct])

    const bodies = payload?.bodies ?? []
    const norm = useMemo(() => normalizeDistances(bodies), [bodies])

    const height = 380
    const cx = width / 2
    const cy = height / 2
    const rMin = 62
    const rMax = Math.min(cx, cy) - 28

    const placed = useMemo(() => {
        if (!window_) return []
        return bodies.map(body => {
            const alpha = presenceAlpha(body, scrubT)
            const r = orbitRadius(norm.get(body.id) ?? 0.5, rMin, rMax)
            const angle = angleAt(body, scrubT)
            return {
                body,
                alpha,
                comet: isComet(body, window_),
                x: cx + r * Math.cos(angle),
                y: cy + r * Math.sin(angle),
                angle,
                r,
            }
        })
    }, [bodies, norm, scrubT, window_, cx, cy, rMax])

    const visible = placed.filter(p => p.alpha > 0)
    const labelIds = useMemo(() => {
        // Label the 8 highest-volume visible bodies; hover reveals the rest.
        return new Set(
            [...visible].sort((a, b) => b.body.n - a.body.n).slice(0, 8).map(p => p.body.id),
        )
    }, [visible])

    // Bodies that entered within the trailing 7 days of the scrubbed moment —
    // the task the view must answer faster than the list.
    const recentEntrants = useMemo(() => {
        if (!window_) return []
        return entrantsBetween(bodies, scrubT - 7 * 24 * 3_600_000, scrubT)
    }, [bodies, scrubT, window_])

    if (loading) {
        return <section className="orbital-section"><div className="orbital-empty">Measuring orbits…</div></section>
    }
    if (!payload?.center || bodies.length === 0) {
        return (
            <section className="orbital-section">
                <div className="orbital-empty">
                    {EMPTY_REASONS[payload?.reason ?? 'error'] ?? EMPTY_REASONS.error}
                </div>
            </section>
        )
    }

    const scrubDate = new Date(scrubT)
    const atNow = scrubPct === 100

    return (
        <section className="orbital-section">
            <div className="orbital-canvas" ref={containerRef}>
                <svg width={width} height={height} role="img" aria-label={`Orbital view of ${themeLabel}`}>
                    {/* static orbit ring guides */}
                    {[0, 0.5, 1].map(g => (
                        <circle key={g} cx={cx} cy={cy} r={orbitRadius(g, rMin, rMax)} className="orbital-ring" />
                    ))}

                    {/* comet tails first (under bodies) */}
                    {visible.filter(p => p.comet).map(p => {
                        const tailLen = 26
                        const tx = p.x - tailLen * Math.cos(p.angle - 0.35)
                        const ty = p.y - tailLen * Math.sin(p.angle - 0.35)
                        return (
                            <line
                                key={`tail-${p.body.id}`}
                                x1={p.x} y1={p.y} x2={tx} y2={ty}
                                stroke={TYPE_COLORS[p.body.type]}
                                strokeOpacity={p.alpha * 0.45}
                                strokeWidth={1.6}
                            />
                        )
                    })}

                    {/* bodies */}
                    {visible.map(p => (
                        <g
                            key={p.body.id}
                            className={p.body.type === 'person' || p.body.type === 'country' ? 'orbital-body orbital-body--clickable' : 'orbital-body'}
                            opacity={p.alpha}
                            onMouseEnter={() => setHovered(p.body)}
                            onMouseLeave={() => setHovered(h => (h?.id === p.body.id ? null : h))}
                            onClick={() => {
                                if (p.body.type === 'country') onCountrySelect?.(p.body.label)
                                if (p.body.type === 'person') onPersonSelect?.(p.body.label)
                            }}
                        >
                            <circle
                                cx={p.x} cy={p.y}
                                r={bodyRadius(p.body.n)}
                                fill={TYPE_COLORS[p.body.type]}
                                fillOpacity={0.85}
                                stroke="rgba(226,232,240,0.5)"
                                strokeWidth={hovered?.id === p.body.id ? 1.6 : 0.7}
                            />
                            {(labelIds.has(p.body.id) || hovered?.id === p.body.id) && (
                                <text x={p.x} y={p.y + bodyRadius(p.body.n) + 11} className="orbital-body-label">
                                    {bodyLabel(p.body)}
                                </text>
                            )}
                        </g>
                    ))}

                    {/* center: the thread */}
                    <g>
                        <circle cx={cx} cy={cy} r={30} className="orbital-center" />
                        <text x={cx} y={cy - 2} className="orbital-center-label">
                            {themeLabel.length > 26 ? `${themeLabel.slice(0, 24)}…` : themeLabel}
                        </text>
                        {payload.center.category && (
                            <text x={cx} y={cy + 12} className="orbital-center-category">
                                {payload.center.category}
                            </text>
                        )}
                    </g>
                </svg>

                {hovered && (
                    <div className="orbital-hover">
                        <span className="orbital-hover-type" style={{ color: TYPE_COLORS[hovered.type] }}>
                            {hovered.type}{window_ && isComet(hovered, window_) ? ' · comet' : ''}
                        </span>
                        <strong>{bodyLabel(hovered)}</strong>
                        <em>{hovered.n} signal{hovered.n === 1 ? '' : 's'} · orbit {(hovered.dist).toFixed(3)}</em>
                        <em>
                            {new Date(hovered.first_seen).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            {' → '}
                            {new Date(hovered.last_seen).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </em>
                    </div>
                )}
            </div>

            <div className="orbital-scrubber">
                <span className="orbital-scrubber-time">
                    {atNow ? 'NOW' : scrubDate.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </span>
                <input
                    type="range"
                    min={0}
                    max={100}
                    value={scrubPct}
                    onChange={e => setScrubPct(Number(e.target.value))}
                    aria-label="Orbital time scrubber"
                    data-tip="Scrub time: bodies enter, orbit, and fade as the story develops"
                />
                <span className="orbital-scrubber-entrants" data-tip="Bodies whose first appearance falls in the 7 days before the scrubbed moment">
                    {recentEntrants.length} entered this week
                </span>
            </div>

            <div className="orbital-legend" aria-label="Orbital view legend">
                {(Object.entries(TYPE_COLORS) as Array<[OrbitalBody['type'], string]>).map(([type, color]) => (
                    <span key={type}><i style={{ background: color }} />{type}</span>
                ))}
                <span data-tip="Present for under a quarter of the story's lifespan"><i className="orbital-legend-comet" />comet</span>
                <span className="orbital-legend-note" data-tip="Orbit radius = semantic distance of the body's coverage to the thread centroid (closer = same story)">
                    closer orbit = semantically closer{payload.centroid_basis === 'computed' ? ' · computed centroid' : ''}
                </span>
            </div>
        </section>
    )
}
