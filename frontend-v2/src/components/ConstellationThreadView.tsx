import { useEffect, useMemo, useRef, useState } from 'react'
import { trackOnce } from '../lib/telemetry'
import {
    driftTailLength,
    entrantsBetween,
    isComet,
    type OrbitalBody,
    type OrbitalWindow,
} from '../lib/orbitalLayout'
import { universeRadius } from '../lib/universeLayout'
import {
    placeConstellation,
    type ConstellationGeom,
    type PlacedStar,
} from '../lib/constellationLayout'
import { resolveCountryName } from '../lib/countryNames'
import './ConstellationThreadView.css'

interface ConstellationPayload {
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

interface ConstellationThreadViewProps {
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
    topic_not_found: 'This thread has no engine record to map into a constellation.',
    unsupported_theme_kind: 'Constellation view needs a thread (dynamic or atlas topic), not a raw GDELT code.',
    no_members: 'No typed members recorded for this thread yet — the nightly engine pass populates them.',
    no_embeddings: 'Member signals are not embedded yet, so semantic distance cannot be measured.',
    no_embedded_members: 'Member signals are not embedded yet, so semantic distance cannot be measured.',
    error: 'Constellation data unavailable right now.',
}

function bodyLabel(b: OrbitalBody): string {
    return b.type === 'country' ? resolveCountryName(b.label) : b.label
}

export function ConstellationThreadView({ theme, themeLabel, hours, onCountrySelect, onPersonSelect }: ConstellationThreadViewProps) {
    const [payload, setPayload] = useState<ConstellationPayload | null>(null)
    const [loading, setLoading] = useState(true)
    const [scrubPct, setScrubPct] = useState(100)
    const [hovered, setHovered] = useState<OrbitalBody | null>(null)
    const containerRef = useRef<HTMLDivElement | null>(null)
    const [size, setSize] = useState({ w: 560, h: 380 })
    // Zoom/pan so you can get closer to the satellite stars (conserved from orbital).
    const [view, setView] = useState({ k: 1, tx: 0, ty: 0 })
    const panRef = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null)

    // Callback ref, not mount-effect: the canvas div is absent during the
    // loading/empty branches, so a mount-only observer never attaches (the
    // off-center-axis bug class shared with orbital/universe).
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

    // §I time-model: read the story's OWN timeline (at least a week), not the
    // console's global window — time is legible via the scrubber, not pre-filtered.
    const constellationHours = Math.max(hours, 168)

    useEffect(() => {
        let cancelled = false
        setLoading(true)
        setScrubPct(100)
        fetch(`/api/v2/theme/${encodeURIComponent(theme)}/orbital?hours=${constellationHours}`)
            .then(r => r.json())
            .then(json => { if (!cancelled) setPayload(json) })
            .catch(() => { if (!cancelled) setPayload(null) })
            .finally(() => { if (!cancelled) setLoading(false) })
        return () => { cancelled = true }
    }, [theme, constellationHours])

    const window_ = payload?.center?.window ?? null
    const scrubT = useMemo(() => {
        if (!window_) return Date.now()
        const start = Date.parse(window_.start)
        const end = Date.parse(window_.end)
        return start + (end - start) * (scrubPct / 100)
    }, [window_, scrubPct])

    const bodies = payload?.bodies ?? []
    // Thread's distance band — scales drift streaks so they compare within one system.
    const distSpan = useMemo(() => {
        if (bodies.length === 0) return 0
        const ds = bodies.map(b => b.dist)
        return Math.max(...ds) - Math.min(...ds)
    }, [bodies])

    const width = size.w
    const height = size.h
    const cx = width / 2
    const cy = height / 2
    // Fill the panel: a UNIFORM elliptical stretch of the radial field, so the
    // radial ORDER (semantic distance) is preserved exactly (shared with orbital).
    const availX = cx - 44
    const availY = cy - 40
    const rBase = Math.min(availX, availY)
    const ex = Math.min(1.5, availX / rBase)
    const ey = Math.min(1.5, availY / rBase)
    const rMin = Math.max(54, rBase * 0.28)
    const rMax = rBase

    const geom: ConstellationGeom = useMemo(
        () => ({ cx, cy, rMin, rMax, ex, ey }),
        [cx, cy, rMin, rMax, ex, ey],
    )

    const placed: PlacedStar[] = useMemo(() => {
        if (!window_) return []
        return placeConstellation(bodies, scrubT, geom, window_)
    }, [bodies, scrubT, window_, geom])

    const visible = placed.filter(p => p.alpha > 0)
    const placedById = useMemo(() => new Map(placed.map(p => [p.body.id, p])), [placed])
    const labelIds = useMemo(() => {
        // Label the 8 highest-volume visible stars; hover/zoom reveals the rest.
        return new Set(
            [...visible].sort((a, b) => b.body.n - a.body.n).slice(0, 8).map(p => p.body.id),
        )
    }, [visible])

    // Stars that entered within the trailing 7 days of the scrubbed moment —
    // the task the view must answer faster than the list.
    const recentEntrants = useMemo(() => {
        if (!window_) return []
        return entrantsBetween(bodies, scrubT - 7 * 24 * 3_600_000, scrubT)
    }, [bodies, scrubT, window_])

    // Tone of the story's coverage, coverage-weighted (by signal volume), in the
    // same ±1.0 neutral band the rim used — now shown as a Distributions strip
    // instead of on the star rims (eval P1-5, dossier canon: tone off the nodes).
    const toneDist = useMemo(() => {
        let neg = 0, neu = 0, pos = 0
        for (const b of bodies) {
            if (b.tone == null) continue
            if (b.tone < -1.0) neg += b.n
            else if (b.tone > 1.0) pos += b.n
            else neu += b.n
        }
        return { neg, neu, pos, total: neg + neu + pos }
    }, [bodies])

    if (loading) {
        return <section className="constellation-section"><div className="constellation-empty">Charting the constellation…</div></section>
    }
    if (!payload?.center || bodies.length === 0) {
        return (
            <section className="constellation-section">
                <div className="constellation-empty">
                    {EMPTY_REASONS[payload?.reason ?? 'error'] ?? EMPTY_REASONS.error}
                </div>
            </section>
        )
    }

    const scrubDate = new Date(scrubT)
    const atNow = scrubPct === 100
    // Perspective zoom (shared with orbital): counter-scale star radii by
    // k^-0.55 so as you zoom, separations grow faster than sizes and satellite
    // stars visibly detach from their parent.
    const zoomShrink = Math.pow(view.k, -0.55)

    return (
        <section className="constellation-section">
            <div
                className="constellation-canvas"
                ref={attachCanvas}
                onWheel={e => {
                    e.preventDefault()
                    const factor = e.deltaY < 0 ? 1.3 : 1 / 1.3
                    const rect = containerRef.current?.getBoundingClientRect()
                    const mx = e.clientX - (rect?.left ?? 0)
                    const my = e.clientY - (rect?.top ?? 0)
                    setView(v => {
                        const k = Math.min(10, Math.max(1, v.k * factor))
                        return { k, tx: mx - (mx - v.tx) * (k / v.k), ty: my - (my - v.ty) * (k / v.k) }
                    })
                }}
                onPointerDown={e => { panRef.current = { x: e.clientX, y: e.clientY, tx: view.tx, ty: view.ty } }}
                onPointerMove={e => {
                    const p = panRef.current
                    if (!p) return
                    setView(v => ({ ...v, tx: p.tx + (e.clientX - p.x), ty: p.ty + (e.clientY - p.y) }))
                }}
                onPointerUp={() => { panRef.current = null }}
                onPointerLeave={() => { panRef.current = null }}
                style={{ cursor: view.k > 1 ? 'grab' : 'default' }}
            >
                {view.k > 1 && (
                    <button className="constellation-reset" onClick={() => setView({ k: 1, tx: 0, ty: 0 })} data-tip="Reset zoom">⌖</button>
                )}
                <svg width={width} height={height} role="img" aria-label={`Constellation view of ${themeLabel}`}>
                    <defs>
                        {(Object.entries(TYPE_COLORS) as Array<[OrbitalBody['type'], string]>).map(([type, color]) => (
                            <radialGradient key={type} id={`con-grad-${type}`} cx="35%" cy="32%" r="75%">
                                <stop offset="0%" stopColor="#f8fafc" stopOpacity="0.9" />
                                <stop offset="28%" stopColor={color} stopOpacity="0.95" />
                                <stop offset="100%" stopColor={color} stopOpacity="0.65" />
                            </radialGradient>
                        ))}
                        <radialGradient id="con-center-glow" cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stopColor="#34d399" stopOpacity="0.4" />
                            <stop offset="55%" stopColor="#34d399" stopOpacity="0.1" />
                            <stop offset="100%" stopColor="#34d399" stopOpacity="0" />
                        </radialGradient>
                    </defs>

                    <g transform={`translate(${view.tx} ${view.ty}) scale(${view.k})`}>
                    {/* starfield — deterministic backdrop, decorative only */}
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

                    {/* HUB SPOKES: anchor→member. LENGTH carries the semantic
                        distance (radius = absolute cosine); width + opacity are
                        UNIFORM — a higher cosine must NEVER read as a thicker or
                        brighter link (dossier canon: "cosine never thickens").
                        These are the story's own members, so they are the faint
                        proximity tier, not a proof claim. */}
                    {visible.map(p => (
                        <line
                            key={`spoke-${p.body.id}`}
                            x1={cx} y1={cy} x2={p.x} y2={p.y}
                            stroke={TYPE_COLORS[p.body.type]}
                            strokeOpacity={p.alpha * (hovered?.id === p.body.id ? 0.6 : 0.22)}
                            strokeWidth={0.7}
                            strokeDasharray={p.comet ? '3 3' : undefined}
                            strokeLinecap="round"
                            pointerEvents="none"
                        />
                    ))}

                    {/* CO-OCCURRENCE EDGES: a satellite (≥75% shared signals) links
                        to its parent star with a SOLID edge whose width ∝ the
                        MEASURED shared-signal overlap — this is the one link whose
                        weight is honest to thicken (a real co-occurrence strength,
                        the confirmed tier), replacing the orbit's fake sub-orbit. */}
                    {visible.map(p => {
                        if (!p.moonParentId) return null
                        const parent = placedById.get(p.moonParentId)
                        if (!parent || parent.alpha <= 0) return null
                        const overlap = p.body.moon_overlap ?? 0.75
                        return (
                            <line
                                key={`cooc-${p.body.id}`}
                                x1={parent.x} y1={parent.y} x2={p.x} y2={p.y}
                                stroke="#e2e8f0"
                                strokeOpacity={Math.min(p.alpha, parent.alpha) * 0.55}
                                strokeWidth={0.8 + overlap * 2.2}
                                strokeLinecap="round"
                                pointerEvents="none"
                            />
                        )
                    })}

                    {/* hover: the star→anchor distance made explicit (the measured,
                        cross-thread-comparable cosine) */}
                    {hovered && (() => {
                        const p = visible.find(v => v.body.id === hovered.id)
                        if (!p) return null
                        return (
                            <g pointerEvents="none">
                                <text x={(cx + p.x) / 2} y={(cy + p.y) / 2 - 5} className="constellation-hover-link-label">
                                    {hovered.dist.toFixed(3)}
                                </text>
                            </g>
                        )
                    })()}

                    {/* drift streaks: MEASURED late-vs-early mean distance to the
                        centroid, drawn along the SEMANTIC radial (center→star).
                        DIRECTION now agrees with the legend + hover (the eval found
                        the orbit's render was inverted): receding (drift>0) points
                        OUTWARD (coverage moving away from the story core), converging
                        points INWARD. */}
                    {visible.map(p => {
                        const tail = driftTailLength(p.body.drift, distSpan)
                        if (tail === 0) return null
                        const receding = (p.body.drift ?? 0) > 0
                        const rx = p.x - cx
                        const ry = p.y - cy
                        const rlen = Math.hypot(rx, ry) || 1
                        const dir = receding ? 1 : -1
                        const tx = p.x + dir * (rx / rlen) * tail
                        const ty = p.y + dir * (ry / rlen) * tail
                        const r0 = universeRadius(p.body.n) * zoomShrink
                        return (
                            <g key={`drift-${p.body.id}`} pointerEvents="none">
                                <line
                                    x1={p.x} y1={p.y} x2={tx} y2={ty}
                                    stroke={TYPE_COLORS[p.body.type]}
                                    strokeOpacity={p.alpha * 0.16}
                                    strokeWidth={r0 * 1.4}
                                    strokeLinecap="round"
                                />
                                <line
                                    x1={p.x} y1={p.y} x2={tx} y2={ty}
                                    stroke={TYPE_COLORS[p.body.type]}
                                    strokeOpacity={p.alpha * 0.5}
                                    strokeWidth={1.3}
                                    strokeLinecap="round"
                                />
                            </g>
                        )
                    })}

                    {/* stars */}
                    {visible.map(p => {
                        const r = universeRadius(p.body.n) * zoomShrink
                        return (
                            <g
                                key={p.body.id}
                                className={p.body.type === 'person' || p.body.type === 'country' ? 'constellation-body constellation-body--clickable' : 'constellation-body'}
                                opacity={p.alpha}
                                onMouseEnter={() => setHovered(p.body)}
                                onMouseLeave={() => setHovered(h => (h?.id === p.body.id ? null : h))}
                                onClick={() => {
                                    if (p.body.type === 'country') onCountrySelect?.(p.body.label)
                                    if (p.body.type === 'person') onPersonSelect?.(p.body.label)
                                }}
                            >
                                {/* Rim is a NEUTRAL outline (+ hover-highlight /
                                    comet dash). Tone lives in the Distributions
                                    strip below, not on the node — one variable per
                                    channel, matching the dossier canon (eval P1-5). */}
                                <circle
                                    cx={p.x} cy={p.y}
                                    r={r}
                                    fill={`url(#con-grad-${p.body.type})`}
                                    stroke={hovered?.id === p.body.id ? 'rgba(248,250,252,0.9)' : 'rgba(226,232,240,0.32)'}
                                    strokeWidth={hovered?.id === p.body.id ? 1.4 : 0.7}
                                    strokeDasharray={p.comet ? '3 2.2' : undefined}
                                />
                                {/* IGNITION: a bright inner core whose opacity =
                                    cumulative-activity luminosity (re-codes the
                                    orbit's angular sweep). A star fully "ignited"
                                    has its whole story in by the scrubbed moment. */}
                                {p.ignition > 0.02 && (
                                    <circle
                                        cx={p.x} cy={p.y}
                                        r={Math.max(1, r * 0.5)}
                                        fill="#f8fafc"
                                        opacity={p.ignition * p.alpha * 0.7}
                                        pointerEvents="none"
                                    />
                                )}
                                {(labelIds.has(p.body.id) || hovered?.id === p.body.id || view.k >= 1.6) && (
                                    <text
                                        x={p.x} y={p.y + r + 12 / view.k}
                                        className="constellation-body-label"
                                        style={{ fontSize: `${9.5 / view.k}px` }}
                                    >
                                        {bodyLabel(p.body)}
                                    </text>
                                )}
                            </g>
                        )
                    })}

                    {/* the ANCHOR STAR: the thread — glow + compact core; label
                        BELOW; every member edge originates here. */}
                    <g>
                        <circle cx={cx} cy={cy} r={68} fill="url(#con-center-glow)" pointerEvents="none" />
                        <circle cx={cx} cy={cy} r={22} className="constellation-anchor" />
                        <text x={cx} y={cy + 40} className="constellation-anchor-label">
                            {(() => { const l = payload.center.label || themeLabel; return l.length > 30 ? `${l.slice(0, 28)}…` : l })()}
                        </text>
                        {payload.center.category && (
                            <text x={cx} y={cy + 53} className="constellation-anchor-category">
                                {payload.center.category}{payload.center.crisis_relevant ? ' · crisis' : ''}
                            </text>
                        )}
                    </g>
                    </g>
                </svg>

                {hovered && (
                    <div className="constellation-hover">
                        <span className="constellation-hover-type" style={{ color: TYPE_COLORS[hovered.type] }}>
                            {hovered.type}{window_ && isComet(hovered, window_) ? ' · comet' : ''}{hovered.moon_of ? ` · satellite (${Math.round((hovered.moon_overlap ?? 0) * 100)}% shared coverage)` : ''}
                        </span>
                        <strong>{bodyLabel(hovered)}</strong>
                        <em>{hovered.n} signal{hovered.n === 1 ? '' : 's'} · distance {(hovered.dist).toFixed(3)}{hovered.tone != null ? ` · tone ${hovered.tone > 0 ? '+' : ''}${hovered.tone.toFixed(2)}` : ''}</em>
                        {hovered.drift != null && Math.abs(hovered.drift) > 1e-6 && (
                            <em>{hovered.drift > 0 ? '↗ receding from the story' : '↘ converging on it'} ({hovered.drift > 0 ? '+' : ''}{hovered.drift.toFixed(3)})</em>
                        )}
                        <em>
                            {new Date(hovered.first_seen).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            {' → '}
                            {new Date(hovered.last_seen).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </em>
                    </div>
                )}
            </div>

            <div className="constellation-scrubber">
                <span className="constellation-scrubber-time">
                    {atNow ? 'NOW' : scrubDate.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </span>
                <input
                    type="range"
                    min={0}
                    max={100}
                    value={scrubPct}
                    onChange={e => { trackOnce('scrubber_used', { surface: 'constellation' }); setScrubPct(Number(e.target.value)) }}
                    aria-label="Constellation time scrubber"
                    data-tip="Scrub time: stars ignite, brighten as their coverage fills in, and fade as the story develops"
                />
                <span className="constellation-scrubber-entrants" data-tip="Stars whose first appearance falls in the 7 days before the scrubbed moment">
                    {recentEntrants.length} entered this week
                </span>
            </div>

            {toneDist.total > 0 && (
                <div className="constellation-distributions" aria-label="Tone of coverage">
                    <span
                        className="constellation-dist-label"
                        data-tip="How this story's coverage skews in tone (mean sentiment of each member's signals, weighted by signal volume). Shown here — not on the star rims — so each visual channel carries one variable (dossier canon)."
                    >
                        tone of coverage
                    </span>
                    <span className="constellation-dist-bar">
                        <i style={{ width: `${(toneDist.neg / toneDist.total) * 100}%`, background: 'rgba(248, 113, 113, 0.85)' }} />
                        <i style={{ width: `${(toneDist.neu / toneDist.total) * 100}%`, background: 'rgba(148, 163, 184, 0.55)' }} />
                        <i style={{ width: `${(toneDist.pos / toneDist.total) * 100}%`, background: 'rgba(52, 211, 153, 0.85)' }} />
                    </span>
                    <span className="constellation-dist-counts">
                        <b style={{ color: '#f87171' }}>{toneDist.neg} −</b>
                        <b style={{ color: '#94a3b8' }}>{toneDist.neu} ·</b>
                        <b style={{ color: '#34d399' }}>{toneDist.pos} +</b>
                    </span>
                </div>
            )}

            <div className="constellation-legend" aria-label="Constellation view legend">
                {(Object.entries(TYPE_COLORS) as Array<[OrbitalBody['type'], string]>).map(([type, color]) => (
                    <span key={type}><i style={{ background: color }} />{type}</span>
                ))}
                <span data-tip="Spoke LENGTH = the star's semantic distance to the story core (measured cosine). Width and brightness are uniform on purpose — a closer star is nearer the core, never a 'stronger' link (dossier rule: cosine never thickens)"><i className="constellation-legend-edge" />spoke = distance</span>
                <span data-tip="Solid link between two stars = MEASURED co-occurrence: a small entity that shares 75%+ of its signals with a bigger one. Width scales with the shared-signal overlap (the one link whose weight is honest)"><i className="constellation-legend-cooc" />co-occurrence</span>
                <span data-tip="A bright inner core scaled by how much of the star's coverage has landed by the scrubbed moment — the story filling in"><i className="constellation-legend-ignition" />core = activity</span>
                <span data-tip="Dashed star: present for under a quarter of the story's lifespan — a brief visitor"><i className="constellation-legend-comet" />comet</span>
                <span data-tip="The streak is MEASURED drift: mean centroid-distance of the star's late signals vs its early ones. Outward = its coverage is receding from the story; inward = converging"><i className="constellation-legend-drift" />streak = semantic drift</span>
                <span className="constellation-legend-note" data-tip="Distance to the anchor = semantic distance of the star's coverage to the thread centroid, on a FIXED scale — so a star's distance means the same in every story (comparable across threads)">
                    fixed scale · comparable across stories{payload.centroid_basis === 'computed' ? ' · computed centroid' : ''}
                </span>
            </div>
        </section>
    )
}
