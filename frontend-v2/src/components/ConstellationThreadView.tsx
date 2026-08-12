import { useEffect, useMemo, useRef, useState } from 'react'
import { trackOnce } from '../lib/telemetry'
import {
    driftTailLength,
    entrantsBetween,
    isComet,
    type OrbitalBody,
    type OrbitalWindow,
} from '../lib/orbitalLayout'
import { IDENTITY_ROT, universeRadius } from '../lib/universeLayout'
import {
    placeConstellation,
    starStates,
    type ConstellationGeom,
    type StarState,
} from '../lib/constellationLayout'
import {
    centerOfMass,
    depthAlpha,
    depthScale,
    projectPos3,
    screenXY,
    stressNote,
    stressPct,
    stressTier,
    type Mds3dMeta,
    type Pos3,
} from '../lib/mds3d'
import { useTrackball } from '../hooks/useTrackball'
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
        /** The story core is node 0 of the MDS solve, so "distance to the core"
            survives the projection as a real measured distance. */
        pos3?: [number, number, number] | null
    } | null
    bodies: OrbitalBody[]
    /** Present when the backend could solve a distance-preserving 3D layout.
        Absent → this view keeps its 2D radial placement and says so. */
    mds?: Mds3dMeta | null
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
    topic_not_found: 'This story has no engine record to map into a constellation.',
    unsupported_theme_kind: 'Constellation view needs a story (dynamic or atlas topic), not a raw GDELT code.',
    no_members: 'No typed members recorded for this story yet — the nightly engine pass populates them.',
    no_embeddings: 'Member signals are not embedded yet, so semantic distance cannot be measured.',
    no_embedded_members: 'Member signals are not embedded yet, so semantic distance cannot be measured.',
    error: 'Constellation data unavailable right now.',
}

/** Padding between the projected cloud and the panel edge (3D path). */
const MARGIN_3D = 54

/**
 * A star ready to draw, from EITHER placement path. `rScale` folds in the size
 * cue of the active path (perspective × depth in 3D, the zoom counter-scale in
 * 2D) and `aScale` the depth dimming (1 in 2D — a flat map has no depth to
 * cue), so the render below never has to know which path produced it.
 */
interface RenderStar extends StarState {
    x: number
    y: number
    /** 0 = nearest … 1 = furthest. Constant on the 2D fallback. */
    depth: number
    rScale: number
    aScale: number
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

    const bodies = useMemo(() => payload?.bodies ?? [], [payload])

    // ── which placement is honest for THIS story ──────────────────────────
    // 3D only when the backend actually solved the layout AND served a real
    // coordinate for the core plus at least two bodies. Otherwise the fixed
    // radial stays — a measured radius with an arbitrary angle is honest;
    // an invented 3D geometry is not.
    const served = payload?.mds ?? null
    const centerPos3 = (payload?.center?.pos3 ?? null) as Pos3 | null
    const placedIn3d = useMemo(() => bodies.filter(b => b.pos3), [bodies])
    const use3d = !!served && !!centerPos3 && placedIn3d.length >= 2
    // The label describes the picture actually on screen: a served `mds` block
    // we could NOT render (no core coordinate, or fewer than two placed bodies)
    // must not claim a 3D geometry the radial fallback is not showing — and its
    // `unplaced` list would be a lie there too, since the radial draws every body.
    const mds = use3d ? served : null

    // hitTestBody is defined below (it needs the projected stars); route the tap
    // through a ref so the hook can be constructed before it.
    const tapRef = useRef<(lx: number, ly: number) => void>(() => {})
    const trackball = useTrackball({
        containerRef,
        // 3D: drag rotates the cloud (that IS the reading gesture — the geometry
        // is real, so turning it reveals structure). 2D fallback: nothing to
        // rotate, so drag keeps the pan it always had.
        navMode: use3d ? 'rotate' : 'pan',
        minZoom: 0.6, maxZoom: 10, wheelStep: 1.2,
        // No ambient spin here: the universe already spins, and a second
        // always-animating SVG is exactly the compositor load the 2026-07-03
        // kernel-panic post-mortem told us to avoid. Drag to rotate.
        ambient: false,
        paused: hovered !== null,
        onTap: (lx, ly) => tapRef.current(lx, ly),
    })
    const view = trackball.view

    const window_ = payload?.center?.window ?? null
    const scrubT = useMemo(() => {
        if (!window_) return Date.now()
        const start = Date.parse(window_.start)
        const end = Date.parse(window_.end)
        return start + (end - start) * (scrubPct / 100)
    }, [window_, scrubPct])

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

    // Perspective zoom (shared with orbital, 2D path only): counter-scale star
    // radii by k^-0.55 so as you zoom, separations grow faster than sizes and
    // satellite stars visibly detach from their parent.
    const zoomShrink = Math.pow(view.k, -0.55)

    // ── 2D fallback placement ─────────────────────────────────────────────
    const stars2d: RenderStar[] = useMemo(() => {
        if (use3d || !window_) return []
        return placeConstellation(bodies, scrubT, geom, window_).map(p => ({
            ...p, depth: 0.5, rScale: zoomShrink, aScale: 1,
        }))
    }, [use3d, bodies, scrubT, window_, geom, zoomShrink])

    // ── 3D distance-preserving placement ──────────────────────────────────
    // Rotation axis = the cloud's center of mass (core included), so the story
    // never orbits an external point.
    const cloudCenter3 = useMemo(
        () => centerOfMass([
            ...(centerPos3 ? [centerPos3] : []),
            ...placedIn3d.map(b => b.pos3 as Pos3),
        ]),
        [centerPos3, placedIn3d],
    )
    // ORTHOGRAPHIC, deliberately (spread 0). This surface's whole claim is that
    // the distance you see IS the measured distance — and a perspective divide
    // breaks exactly that claim as you zoom (mds3d's own tests pin it: zoom
    // bends the distance the projection otherwise preserves). The screen zoom
    // in `screenXY` is a UNIFORM scale, so every distance ratio survives it at
    // any k, and the legend's claim holds everywhere in the view. Perspective
    // stays where positions are already labelled approximate: the universe.
    const spread = 0
    const box = useMemo(
        () => ({ w: width, h: height, margin: MARGIN_3D, view }),
        [width, height, view],
    )

    const states: StarState[] = useMemo(
        () => (window_ ? starStates(bodies, scrubT, window_) : []),
        [bodies, scrubT, window_],
    )

    const stars3d: RenderStar[] = useMemo(() => {
        if (!use3d) return []
        return states
            .filter(s => s.body.pos3)
            .map(s => {
                const p = projectPos3(s.body.pos3 as Pos3, trackball.rot, cloudCenter3, spread)
                const { sx, sy } = screenXY(p, box)
                return {
                    ...s, x: sx, y: sy, depth: p.depth,
                    rScale: depthScale(p.depth) * p.scale,
                    aScale: depthAlpha(p.depth),
                }
            })
            // painter order: draw far bodies first so near ones sit on top
            .sort((a, b) => b.depth - a.depth)
    }, [use3d, states, trackball.rot, cloudCenter3, spread, box])

    const core3d = useMemo(() => {
        if (!use3d || !centerPos3) return null
        const p = projectPos3(centerPos3, trackball.rot, cloudCenter3, spread)
        const { sx, sy } = screenXY(p, box)
        return { sx, sy, depth: p.depth, scale: p.scale }
    }, [use3d, centerPos3, trackball.rot, cloudCenter3, spread, box])

    // ── the ONE render list both paths feed ───────────────────────────────
    const visible = useMemo(
        () => (use3d ? stars3d : stars2d).filter(p => p.alpha > 0),
        [use3d, stars3d, stars2d],
    )
    const placedById = useMemo(() => new Map(visible.map(p => [p.body.id, p])), [visible])
    const labelIds = useMemo(() => {
        // Label the 8 highest-volume visible stars; hover/zoom reveals the rest.
        return new Set(
            [...visible].sort((a, b) => b.body.n - a.body.n).slice(0, 8).map(p => p.body.id),
        )
    }, [visible])

    /** Where the story core sits, and how big it draws, on the active path. */
    const anchor = use3d && core3d
        ? { x: core3d.sx, y: core3d.sy, k: depthScale(core3d.depth) * core3d.scale }
        : { x: cx, y: cy, k: 1 }

    // A tap that didn't drag = a CLICK. Pointer capture (the trackball's drag
    // machinery) eats the SVG <g> onClick, so selection is hit-tested here —
    // works for mouse AND touch, on both placement paths.
    tapRef.current = (lx: number, ly: number) => {
        let best: RenderStar | null = null
        for (const s of visible) {
            // The tap arrives in canvas pixels. 3D coordinates already are; 2D
            // ones live inside the translate/scale group, so map them out first.
            const sx = use3d ? s.x : s.x * view.k + view.tx
            const sy = use3d ? s.y : s.y * view.k + view.ty
            const r = universeRadius(s.body.n) * s.rScale * (use3d ? 1 : view.k)
            // `<=` so the LAST match in paint order wins — the star actually on
            // top (nearest, drawn last) is the one you clicked.
            if (Math.hypot(lx - sx, ly - sy) <= r + 6 && (!best || s.depth <= best.depth)) best = s
        }
        if (!best) return
        if (best.body.type === 'country') onCountrySelect?.(best.body.label)
        if (best.body.type === 'person') onPersonSelect?.(best.body.label)
    }

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
    // Label sizing: on the 2D path everything rides inside a scale(k) group, so
    // text must be counter-scaled. The 3D path bakes pan/zoom into the screen
    // coordinates themselves, so text is already in canvas pixels.
    const textK = use3d ? 1 : view.k
    const atRest = view.k === 1 && view.tx === 0 && view.ty === 0 && trackball.rot === IDENTITY_ROT

    return (
        <section className="constellation-section">
            <div
                className="constellation-canvas"
                ref={attachCanvas}
                {...trackball.handlers}
                style={{ cursor: 'grab' }}
            >
                {!atRest && (
                    <button
                        className="constellation-reset"
                        onClick={() => trackball.reset()}
                        data-tip="Reset rotation and zoom"
                    >
                        ⌖
                    </button>
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

                    {/* The 2D path pans/zooms the whole group; the 3D path already
                        carries pan/zoom inside every projected coordinate, so it
                        must NOT be transformed again. */}
                    <g transform={use3d ? undefined : `translate(${view.tx} ${view.ty}) scale(${view.k})`}>
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
                        distance (3D: the MDS distance itself; 2D: radius =
                        absolute cosine); width + opacity are UNIFORM — a higher
                        cosine must NEVER read as a thicker or brighter link
                        (dossier canon: "cosine never thickens"). These are the
                        story's own members, so they are the faint proximity
                        tier, not a proof claim. */}
                    {visible.map(p => (
                        <line
                            key={`spoke-${p.body.id}`}
                            x1={anchor.x} y1={anchor.y} x2={p.x} y2={p.y}
                            stroke={TYPE_COLORS[p.body.type]}
                            strokeOpacity={p.alpha * p.aScale * (hovered?.id === p.body.id ? 0.6 : 0.22)}
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
                                strokeOpacity={Math.min(p.alpha * p.aScale, parent.alpha * parent.aScale) * 0.55}
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
                                <text x={(anchor.x + p.x) / 2} y={(anchor.y + p.y) / 2 - 5} className="constellation-hover-link-label">
                                    {hovered.dist.toFixed(3)}
                                </text>
                            </g>
                        )
                    })()}

                    {/* drift streaks: MEASURED late-vs-early mean distance to the
                        centroid, drawn along the SEMANTIC radial (core→star).
                        DIRECTION agrees with the legend + hover: receding
                        (drift>0) points OUTWARD (coverage moving away from the
                        story core), converging points INWARD. */}
                    {visible.map(p => {
                        const tail = driftTailLength(p.body.drift, distSpan)
                        if (tail === 0) return null
                        const receding = (p.body.drift ?? 0) > 0
                        const rx = p.x - anchor.x
                        const ry = p.y - anchor.y
                        const rlen = Math.hypot(rx, ry) || 1
                        const dir = receding ? 1 : -1
                        const tx = p.x + dir * (rx / rlen) * tail
                        const ty = p.y + dir * (ry / rlen) * tail
                        const r0 = universeRadius(p.body.n) * p.rScale
                        return (
                            <g key={`drift-${p.body.id}`} pointerEvents="none">
                                <line
                                    x1={p.x} y1={p.y} x2={tx} y2={ty}
                                    stroke={TYPE_COLORS[p.body.type]}
                                    strokeOpacity={p.alpha * p.aScale * 0.16}
                                    strokeWidth={r0 * 1.4}
                                    strokeLinecap="round"
                                />
                                <line
                                    x1={p.x} y1={p.y} x2={tx} y2={ty}
                                    stroke={TYPE_COLORS[p.body.type]}
                                    strokeOpacity={p.alpha * p.aScale * 0.5}
                                    strokeWidth={1.3}
                                    strokeLinecap="round"
                                />
                            </g>
                        )
                    })}

                    {/* stars (far → near, so the nearest sits on top) */}
                    {visible.map(p => {
                        const r = universeRadius(p.body.n) * p.rScale
                        return (
                            <g
                                key={p.body.id}
                                className={p.body.type === 'person' || p.body.type === 'country' ? 'constellation-body constellation-body--clickable' : 'constellation-body'}
                                opacity={p.alpha * p.aScale}
                                onMouseEnter={() => setHovered(p.body)}
                                onMouseLeave={() => setHovered(h => (h?.id === p.body.id ? null : h))}
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
                                        x={p.x} y={p.y + r + 12 / textK}
                                        className="constellation-body-label"
                                        style={{ fontSize: `${9.5 / textK}px` }}
                                    >
                                        {bodyLabel(p.body)}
                                    </text>
                                )}
                            </g>
                        )
                    })}

                    {/* the ANCHOR STAR: the thread — glow + compact core; label
                        BELOW; every member edge originates here. In 3D it is a
                        real node of the layout (node 0 of the MDS solve), so it
                        carries the same depth cues as any star. */}
                    <g>
                        <circle cx={anchor.x} cy={anchor.y} r={68 * anchor.k} fill="url(#con-center-glow)" pointerEvents="none" />
                        <circle cx={anchor.x} cy={anchor.y} r={22 * anchor.k} className="constellation-anchor" />
                        <text x={anchor.x} y={anchor.y + 40 * anchor.k} className="constellation-anchor-label">
                            {(() => { const l = payload.center.label || themeLabel; return l.length > 30 ? `${l.slice(0, 28)}…` : l })()}
                        </text>
                        {payload.center.category && (
                            <text x={anchor.x} y={anchor.y + 53 * anchor.k} className="constellation-anchor-category">
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
                {mds ? (
                    <span
                        className={`constellation-legend-note constellation-stress--${stressTier(mds.stress)}`}
                        data-tip="Positions are classical metric MDS over the measured cosine distances between the story core and each body's mean embedding. Distortion is Kruskal stress-1 — the honest error of squeezing high-dimensional distance into three axes. Drag to rotate."
                    >
                        distance ≈ semantic similarity · 3D distortion {stressPct(mds.stress)}% — {stressNote(mds.stress)}
                    </span>
                ) : (
                    <span className="constellation-legend-note" data-tip="No 3D layout for this story (too few placed bodies or no embeddings) — showing the fixed radial view: radius = measured cosine distance to the core.">
                        fixed scale · comparable across stories{payload.centroid_basis === 'computed' ? ' · computed centroid' : ''}
                    </span>
                )}
            </div>

            {mds && mds.unplaced && mds.unplaced.length > 0 && (
                <div className="constellation-unplaced" aria-label="Bodies without a measured position">
                    <span
                        className="constellation-unplaced-label"
                        data-tip="These bodies have no member embedding, so there is no measured distance to place them by. They are listed, never drawn at an invented coordinate."
                    >
                        unplaced ({mds.unplaced.length})
                    </span>
                    {mds.unplaced.slice(0, 8).map(id => {
                        const b = bodies.find(x => x.id === id)
                        return <span key={id} className="constellation-unplaced-chip">{b ? bodyLabel(b) : id}</span>
                    })}
                </div>
            )}
        </section>
    )
}
