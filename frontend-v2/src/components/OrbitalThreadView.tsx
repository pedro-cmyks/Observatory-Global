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
    const [size, setSize] = useState({ w: 560, h: 380 })

    // Callback ref, not mount-effect: the canvas div is absent during the
    // loading/empty branches, so a mount-only observer never attaches and the
    // svg keeps its default width (the UniverseView off-center-axis bug class).
    const resizeObserverRef = useRef<ResizeObserver | null>(null)
    const attachCanvas = useMemo(() => (element: HTMLDivElement | null) => {
        containerRef.current = element
        resizeObserverRef.current?.disconnect()
        resizeObserverRef.current = null
        if (!element) return
        const apply = (w: number, h: number) => setSize(prev => {
            const next = { w: Math.max(360, Math.round(w)), h: Math.max(300, Math.round(h)) }
            return prev.w === next.w && prev.h === next.h ? prev : next
        })
        apply(element.clientWidth, element.clientHeight)
        const observer = new ResizeObserver(entries => {
            const rect = entries[0]?.contentRect
            if (rect) apply(rect.width, rect.height)
        })
        observer.observe(element)
        resizeObserverRef.current = observer
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

    const width = size.w
    const height = size.h
    const cx = width / 2
    const cy = height / 2
    // Fill the panel: orbits are ellipses — a UNIFORM stretch of the radial
    // field, so the radial ORDER (semantic distance) is preserved exactly.
    const availX = cx - 44
    const availY = cy - 40
    const rBase = Math.min(availX, availY)
    const ex = Math.min(1.5, availX / rBase)
    const ey = Math.min(1.5, availY / rBase)
    const rMin = Math.max(54, rBase * 0.28)
    const rMax = rBase

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
                x: cx + r * ex * Math.cos(angle),
                y: cy + r * ey * Math.sin(angle),
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
            <div className="orbital-canvas" ref={attachCanvas}>
                <svg width={width} height={height} role="img" aria-label={`Orbital view of ${themeLabel}`}>
                    <defs>
                        {(Object.entries(TYPE_COLORS) as Array<[OrbitalBody['type'], string]>).map(([type, color]) => (
                            <radialGradient key={type} id={`orb-grad-${type}`} cx="35%" cy="32%" r="75%">
                                <stop offset="0%" stopColor="#f8fafc" stopOpacity="0.9" />
                                <stop offset="28%" stopColor={color} stopOpacity="0.95" />
                                <stop offset="100%" stopColor={color} stopOpacity="0.65" />
                            </radialGradient>
                        ))}
                        <radialGradient id="orb-center-glow" cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stopColor="#34d399" stopOpacity="0.35" />
                            <stop offset="55%" stopColor="#34d399" stopOpacity="0.08" />
                            <stop offset="100%" stopColor="#34d399" stopOpacity="0" />
                        </radialGradient>
                    </defs>

                    {/* starfield — deterministic, decorative only */}
                    {Array.from({ length: 70 }, (_, i) => {
                        const h = (i * 2654435761) % 100_000
                        return (
                            <circle
                                key={`star-${i}`}
                                cx={(h % 997) / 997 * width}
                                cy={((h * 31) % 991) / 991 * height}
                                r={i % 7 === 0 ? 1.1 : 0.6}
                                fill="#e2e8f0"
                                opacity={0.06 + ((h % 23) / 23) * 0.16}
                            />
                        )
                    })}

                    {/* static orbit ring guides (ellipses — uniform stretch,
                        radial ORDER = semantic distance preserved exactly) */}
                    {[0, 0.5, 1].map(g => (
                        <ellipse
                            key={g}
                            cx={cx} cy={cy}
                            rx={orbitRadius(g, rMin, rMax) * ex}
                            ry={orbitRadius(g, rMin, rMax) * ey}
                            className="orbital-ring"
                        />
                    ))}
                    <text x={cx} y={cy - orbitRadius(0, rMin, rMax) * ey - 6} className="orbital-ring-label">closest · same story</text>
                    <text x={cx} y={cy - orbitRadius(1, rMin, rMax) * ey + 14} className="orbital-ring-label orbital-ring-label--far">edge of the story</text>

                    {/* hover connection: body → center, the distance made visible */}
                    {hovered && (() => {
                        const p = visible.find(v => v.body.id === hovered.id)
                        if (!p) return null
                        return (
                            <g pointerEvents="none">
                                <line x1={cx} y1={cy} x2={p.x} y2={p.y} className="orbital-hover-link" />
                                <text x={(cx + p.x) / 2} y={(cy + p.y) / 2 - 6} className="orbital-hover-link-label">
                                    {hovered.dist.toFixed(3)}
                                </text>
                            </g>
                        )
                    })()}

                    {/* comet tails first (under bodies) */}
                    {visible.filter(p => p.comet).map(p => {
                        const dirX = Math.cos(p.angle - 0.4)
                        const dirY = Math.sin(p.angle - 0.4)
                        const r0 = bodyRadius(p.body.n)
                        return (
                            <g key={`tail-${p.body.id}`} pointerEvents="none">
                                <line
                                    x1={p.x} y1={p.y}
                                    x2={p.x - 40 * dirX} y2={p.y - 40 * dirY}
                                    stroke={TYPE_COLORS[p.body.type]}
                                    strokeOpacity={p.alpha * 0.18}
                                    strokeWidth={r0 * 1.5}
                                    strokeLinecap="round"
                                />
                                <line
                                    x1={p.x} y1={p.y}
                                    x2={p.x - 30 * dirX} y2={p.y - 30 * dirY}
                                    stroke={TYPE_COLORS[p.body.type]}
                                    strokeOpacity={p.alpha * 0.5}
                                    strokeWidth={1.4}
                                    strokeLinecap="round"
                                />
                            </g>
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
                                fill={`url(#orb-grad-${p.body.type})`}
                                stroke={hovered?.id === p.body.id ? 'rgba(248,250,252,0.9)' : 'rgba(226,232,240,0.25)'}
                                strokeWidth={hovered?.id === p.body.id ? 1.4 : 0.6}
                            />
                            {(labelIds.has(p.body.id) || hovered?.id === p.body.id) && (
                                <text x={p.x} y={p.y + bodyRadius(p.body.n) + 12} className="orbital-body-label">
                                    {bodyLabel(p.body)}
                                </text>
                            )}
                        </g>
                    ))}

                    {/* center: the thread — glow + compact core; label sits
                        BELOW the core (a big labeled disk read as a button);
                        prefers the engine's own name over id-derived labels */}
                    <g>
                        <circle cx={cx} cy={cy} r={64} fill="url(#orb-center-glow)" pointerEvents="none" />
                        <circle cx={cx} cy={cy} r={22} className="orbital-center" />
                        <text x={cx} y={cy + 40} className="orbital-center-label">
                            {(() => { const l = payload.center.label || themeLabel; return l.length > 30 ? `${l.slice(0, 28)}…` : l })()}
                        </text>
                        {payload.center.category && (
                            <text x={cx} y={cy + 53} className="orbital-center-category">
                                {payload.center.category}{payload.center.crisis_relevant ? ' · crisis' : ''}
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
