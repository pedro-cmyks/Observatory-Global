import { useEffect, useMemo, useRef, useState } from 'react'
import {
    bornBetween,
    categoryColor,
    cloudCenter,
    depthAlpha,
    depthScale,
    edgeOpacity,
    entitySpread,
    heatHalo,
    isHeating,
    isOrphan,
    litNodeIds,
    positionAt,
    universeAlpha,
    universeRadius,
    applyRot,
    IDENTITY_ROT,
    mul3,
    rotX,
    rotY,
    rotZ,
    type Rot3,
    type UniverseEdge,
    type UniverseNode,
} from '../lib/universeLayout'
import { OrbitalThreadView } from './OrbitalThreadView'
import './UniverseView.css'

interface UniversePayload {
    contract: string
    nodes: UniverseNode[]
    edges: UniverseEdge[]
    anchors: Array<{ category: string; x: number; y: number; z?: number; count: number }>
    meta: { topic_count: number; edge_basis: string; position_basis: string; timeline_days: number } | null
    reason?: string
}

interface UniverseViewProps {
    onThemeSelect: (themeId: string) => void
    /** Open thread (if any): the panel travels to that orbit and shows its
        story system here — one place for the same information (Pedro §7.3). */
    activeTheme?: string | null
    activeThemeLabel?: string
    hours?: number
    /** Inverse-focus lens: a country/person focused elsewhere in Atlas lights
        ITS stories in the field (Pedro 2026-07-03 — the gravity well). */
    focusKind?: 'country' | 'person' | null
    focusValue?: string | null
    onPersonSelect?: (name: string) => void
    onCountrySelect?: (code: string) => void
}

const WEEK_MS = 7 * 24 * 3_600_000

export function UniverseView({ onThemeSelect, activeTheme, activeThemeLabel, hours = 24, focusKind = null, focusValue = null, onPersonSelect, onCountrySelect }: UniverseViewProps) {
    const [payload, setPayload] = useState<UniversePayload | null>(null)
    const [loading, setLoading] = useState(true)
    const [scrubPct, setScrubPct] = useState(100)
    const [hoveredId, setHoveredId] = useState<string | null>(null)
    const [view, setView] = useState({ k: 1, tx: 0, ty: 0 })
    // Universe's OWN classifiers (not the globe's HEAT/FLOW): filter the field
    // by what matters semantically here.
    const [crisisOnly, setCrisisOnly] = useState(false)
    const [orphansOnly, setOrphansOnly] = useState(false)
    // Travel state: when a thread is open we are AT its orbit; back returns to the field.
    const [orbitalVisible, setOrbitalVisible] = useState(false)
    const [traveling, setTraveling] = useState(false)
    // Yaw: rotation around the cloud's center of MASS (spec §7.2). Ambient
    // spin pauses on any interaction — camera, not time.
    // Orientation as an accumulated 3x3 rotation matrix (trackball/arcball —
    // Pedro 2026-07-03 "roll disponible 3D... para donde sea"). Free 3-axis
    // rotation: no gimbal lock, no clamp, any orientation. Chosen over Euler
    // yaw/pitch/roll after weighing both (spec §7.4) + web-grounded review.
    const [rot, setRot] = useState<Rot3>(IDENTITY_ROT)
    // Nav mode: drag ROTATES by default (fly around), or PANS (drag the cloud
    // across the screen). Two-finger touch always pans+zooms regardless.
    const [navMode, setNavMode] = useState<'rotate' | 'pan' | 'roll'>('rotate')
    const spinPausedRef = useRef(false)
    const draggingRef = useRef(false) // true during any active drag — spin must not resume mid-drag
    // Incremental drag: store the LAST pointer pos + mode; each move composes
    // a small rotation (trackball) or pans. lastAngle tracks two-finger twist.
    const dragRef = useRef<{ lastX: number; lastY: number; mode: 'orbit' | 'roll' | 'pan'; tx: number; ty: number } | null>(null)
    // Multi-touch: track active pointers for two-finger pan + pinch-zoom.
    const pointersRef = useRef<Map<number, { x: number; y: number }>>(new Map())
    const pinchRef = useRef<{ dist: number; cx: number; cy: number; tx: number; ty: number; k: number; angle: number } | null>(null)
    const containerRef = useRef<HTMLDivElement | null>(null)
    const [size, setSize] = useState({ w: 1200, h: 700 })

    // Ambient spin, THERMALLY POLITE (2026-07-03 kernel panic post-mortem:
    // WindowServer watchdog timeout — a 60fps React re-render of 348 SVG
    // bodies contributes exactly that kind of compositor load):
    //  - yaw updates at ~10fps, not every frame
    //  - stops entirely while the orbital view covers the field
    //  - auto-rests after 90s without interaction; any hover/drag re-arms it
    const lastInteractionRef = useRef(performance.now())
    useEffect(() => {
        if (orbitalVisible) return // field hidden — no reason to animate
        let raf = 0
        let last = performance.now()
        let acc = 0
        const tick = (now: number) => {
            const dt = now - last
            last = now
            acc += dt
            const resting = now - lastInteractionRef.current > 90_000
            if (acc >= 100) { // ~10fps
                if (!spinPausedRef.current && !draggingRef.current && !document.hidden && !resting) {
                    const dyaw = (acc / 1000) * 0.06 // ~1 turn / 105s
                    setRot(r => mul3(rotY(dyaw), r)) // ambient spin about screen-vertical
                }
                acc = 0
            }
            raf = requestAnimationFrame(tick)
        }
        raf = requestAnimationFrame(tick)
        return () => cancelAnimationFrame(raf)
    }, [orbitalVisible])

    useEffect(() => {
        spinPausedRef.current = hoveredId !== null
    }, [hoveredId])
    // note: draggingRef independently holds the spin during drags (set in
    // the pointer handlers) so a hover-leave mid-drag never resumes the spin

    // Callback ref: the canvas div does NOT exist during the loading/orbital
    // branches, so a mount-only observer never fires and the svg stays at the
    // 1200×700 default inside a ~590px panel (the off-center rotation axis
    // Pedro saw was this, not the rotation math).
    const resizeObserverRef = useRef<ResizeObserver | null>(null)
    const attachCanvas = useMemo(() => (element: HTMLDivElement | null) => {
        containerRef.current = element
        resizeObserverRef.current?.disconnect()
        resizeObserverRef.current = null
        if (!element) return
        const apply = (w: number, h: number) => {
            const next = { w: Math.max(360, w), h: Math.max(280, h) }
            setSize(prev => (prev.w === next.w && prev.h === next.h ? prev : next))
        }
        apply(element.clientWidth, element.clientHeight)
        const observer = new ResizeObserver(entries => {
            const rect = entries[0]?.contentRect
            if (rect) apply(rect.width, rect.height)
        })
        observer.observe(element)
        resizeObserverRef.current = observer
    }, [])

    useEffect(() => {
        let cancelled = false
        fetch('/api/v2/universe')
            .then(r => r.json())
            .then(json => { if (!cancelled) setPayload(json) })
            .catch(() => { if (!cancelled) setPayload(null) })
            .finally(() => { if (!cancelled) setLoading(false) })
        return () => { cancelled = true }
    }, [])

    const allNodes = useMemo(() => payload?.nodes ?? [], [payload])
    const nodes = useMemo(
        () => allNodes.filter(n =>
            (!crisisOnly || n.crisis_relevant === true) && (!orphansOnly || isOrphan(n)),
        ),
        [allNodes, crisisOnly, orphansOnly],
    )
    const edges = useMemo(() => payload?.edges ?? [], [payload])

    const timeSpan = useMemo(() => {
        const firsts = allNodes.map(n => (n.first_seen ? Date.parse(n.first_seen) : Infinity))
        const start = Math.min(...(firsts.length ? firsts : [Date.now()]))
        return { start, end: Date.now() }
    }, [allNodes])

    const scrubT = timeSpan.start + (timeSpan.end - timeSpan.start) * (scrubPct / 100)

    const nodeById = useMemo(() => new Map(nodes.map(n => [n.id, n])), [nodes])
    const neighborIds = useMemo(() => {
        if (!hoveredId) return null
        const set = new Set<string>([hoveredId])
        for (const e of edges) {
            if (e.a === hoveredId) set.add(e.b)
            if (e.b === hoveredId) set.add(e.a)
        }
        return set
    }, [hoveredId, edges])

    const margin = 46
    const px = (x: number) => (margin + x * (size.w - 2 * margin)) * view.k + view.tx
    const py = (y: number) => (margin + y * (size.h - 2 * margin)) * view.k + view.ty

    // Rotation axis = center of MASS of the full cloud (stable across filters),
    // re-centered to the panel middle — never an external orbit.
    const { cx: massX, cz: massZ } = useMemo(() => cloudCenter(allNodes), [allNodes])
    const massY = useMemo(
        () => (allNodes.length ? allNodes.reduce((s, n) => s + n.y, 0) / allNodes.length : 0.5),
        [allNodes],
    )

    // Shared projection: free two-axis rotation about the mass center, then
    // screen-map. Used by every layer so nodes/edges/labels/trails agree.
    const project3 = (x: number, y: number, z: number | undefined) => {
        const p = applyRot(rot, x, y, z, massX, massY, massZ)
        return { sx: px(p.px), sy: py(p.py), depth: p.depth }
    }

    const projected = useMemo(() => {
        const out = new Map<string, { sx: number; sy: number; depth: number }>()
        for (const n of nodes) {
            // trajectories (spec 7.2): the position AT the scrubbed moment,
            // interpolated along the topic's real snapshot track
            const pos = positionAt(n, scrubT)
            out.set(n.id, project3(pos.x, pos.y, pos.z))
        }
        return out
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [nodes, rot, view, size, massX, massZ, massY, scrubT])

    const depthOrdered = useMemo(
        () => [...nodes].sort((a, b) => (projected.get(b.id)?.depth ?? 0) - (projected.get(a.id)?.depth ?? 0)),
        [nodes, projected],
    )

    // Inverse-focus lens (the GRAVITY WELL): a focused country/person lights
    // its stories; the rest dims. A ghost "sun" sits at the barycenter of the
    // lit stories with gravity lines to each — and a readout of the entity's
    // narrative FOOTPRINT (concentrated vs cross-cutting).
    const litIds = useMemo(() => litNodeIds(nodes, focusKind, focusValue), [nodes, focusKind, focusValue])
    // Frame the lit constellation when the focus changes (one-shot per entity).
    const focusKey = `${focusKind}:${focusValue}`
    useEffect(() => {
        const ids = litNodeIds(nodes, focusKind, focusValue)
        if (ids.size === 0 || nodes.length === 0) return
        const lit = nodes.filter(n => ids.has(n.id))
        // barycenter in normalized rotated space → recenter with a gentle zoom
        let bx = 0, by = 0, k = 0
        for (const n of lit) { const p = applyRot(rot, n.x, n.y, n.z, massX, massY, massZ); bx += p.px; by += p.py; k++ }
        if (!k) return
        bx /= k; by /= k
        const zoom = 1.5
        const targetX = (margin + bx * (size.w - 2 * margin))
        const targetY = (margin + by * (size.h - 2 * margin))
        setView({ k: zoom, tx: size.w / 2 - targetX * zoom, ty: size.h / 2 - targetY * zoom })
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [focusKey])
    const litActive = litIds.size > 0
    // Heating stories (measured attention acceleration) — the top mover named.
    const heating = useMemo(
        () => nodes.filter(isHeating).sort((a, b) => (b.velocity ?? 0) - (a.velocity ?? 0)),
        [nodes],
    )
    const litNodes = useMemo(() => nodes.filter(n => litIds.has(n.id)), [nodes, litIds])
    const spread = useMemo(() => (litActive ? entitySpread(litNodes) : null), [litActive, litNodes])
    const sun = useMemo(() => {
        if (!litActive) return null
        let sx = 0, sy = 0, k = 0
        for (const n of litNodes) {
            const p = projected.get(n.id)
            if (p) { sx += p.sx; sy += p.sy; k++ }
        }
        return k ? { sx: sx / k, sy: sy / k } : null
    }, [litActive, litNodes, projected])

    // Travel: an open thread pulls the camera to its body, then the story
    // system appears in this panel (the "viaje").
    useEffect(() => {
        if (!activeTheme) {
            setOrbitalVisible(false)
            setTraveling(false)
            return
        }
        const body = allNodes.find(n => n.id === activeTheme)
        setTraveling(true)
        if (body) {
            const p = applyRot(rot, body.x, body.y, body.z, massX, massY, massZ)
            const targetX = (margin + p.px * (size.w - 2 * margin))
            const targetY = (margin + p.py * (size.h - 2 * margin))
            const k = 2.6
            setView({ k, tx: size.w / 2 - targetX * k, ty: size.h / 2 - targetY * k })
        }
        const id = window.setTimeout(() => {
            setOrbitalVisible(true)
            setTraveling(false)
        }, body ? 520 : 120)
        return () => window.clearTimeout(id)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTheme])

    const alphaById = useMemo(() => {
        const out = new Map<string, number>()
        for (const n of nodes) out.set(n.id, universeAlpha(n, scrubT))
        return out
    }, [nodes, scrubT])

    const aliveCount = useMemo(
        () => nodes.reduce((acc, n) => acc + ((alphaById.get(n.id) ?? 0) > 0 ? 1 : 0), 0),
        [nodes, alphaById],
    )
    const newThisWeek = useMemo(() => bornBetween(nodes, scrubT, WEEK_MS).length, [nodes, scrubT])

    const labeledIds = useMemo(() => {
        const visible = nodes.filter(n => (alphaById.get(n.id) ?? 0) > 0.4)
        return new Set([...visible].sort((a, b) => b.n - a.n).slice(0, 14).map(n => n.id))
    }, [nodes, alphaById])

    const hovered = hoveredId ? nodeById.get(hoveredId) : null
    const atNow = scrubPct === 100

    if (loading) return <div className="universe-empty">Charting the universe…</div>
    if (!payload || allNodes.length === 0) {
        return <div className="universe-empty">Universe data unavailable{payload?.reason ? ` (${payload.reason})` : ''}.</div>
    }

    // AT an orbit: the story system replaces the field until back/close.
    if (activeTheme && orbitalVisible) {
        const fieldLabel = allNodes.find(n => n.id === activeTheme)?.label
        const orbitLabel = fieldLabel ?? activeThemeLabel ?? activeTheme
        return (
            <div className="universe-root">
                <div className="universe-orbit-bar">
                    <button
                        className="universe-orbit-back"
                        onClick={() => setOrbitalVisible(false)}
                        data-tip="Back to the full story universe"
                    >
                        ← UNIVERSE
                    </button>
                    <span className="universe-orbit-title">{orbitLabel}</span>
                </div>
                <div className="universe-orbit-body">
                    <OrbitalThreadView
                        theme={activeTheme}
                        themeLabel={orbitLabel}
                        hours={hours}
                        onCountrySelect={onCountrySelect}
                        onPersonSelect={onPersonSelect}
                    />
                </div>
            </div>
        )
    }

    return (
        <div className="universe-root">
            <div className="universe-filters">
                <button
                    className={`universe-filter ${crisisOnly ? 'active' : ''}`}
                    onClick={() => setCrisisOnly(v => !v)}
                    data-tip="Only crisis-relevant stories (R3.1 flag)"
                >
                    CRISIS
                </button>
                <button
                    className={`universe-filter ${orphansOnly ? 'active' : ''}`}
                    onClick={() => setOrphansOnly(v => !v)}
                    data-tip="Only semantic orphans — stories unlike every other living story"
                >
                    ORPHANS
                </button>
                {activeTheme && !orbitalVisible && !traveling && (
                    <button
                        className="universe-filter"
                        onClick={() => setOrbitalVisible(true)}
                        data-tip="Return to the open story's system"
                    >
                        ◉ TO ORBIT
                    </button>
                )}
                <span className="universe-nav-modes">
                    <button
                        className={`universe-filter ${navMode === 'rotate' ? 'active' : ''}`}
                        onClick={() => setNavMode('rotate')}
                        data-tip="Drag to orbit the galaxy freely in 3D (any axis). Alt-drag or two-finger twist = roll. Shift-drag / two fingers = move"
                    >
                        ⟲ ORBIT
                    </button>
                    <button
                        className={`universe-filter ${navMode === 'pan' ? 'active' : ''}`}
                        onClick={() => setNavMode('pan')}
                        data-tip="Drag to move the whole cloud across the screen. Scroll or pinch to zoom"
                    >
                        ✋ MOVE
                    </button>
                    <button
                        className={`universe-filter ${navMode === 'roll' ? 'active' : ''}`}
                        onClick={() => setNavMode('roll')}
                        data-tip="Drag horizontally to ROLL (spin the field around the view axis). Also: alt-drag, or two-finger twist on touch"
                    >
                        ↻ ROLL
                    </button>
                    <button
                        className="universe-filter"
                        onClick={() => { setRot(IDENTITY_ROT); setView({ k: 1, tx: 0, ty: 0 }) }}
                        data-tip="Reset the camera"
                    >
                        ⌖
                    </button>
                </span>
            </div>
            <div
                className={`universe-canvas${traveling ? ' universe-canvas--traveling' : ''}`}
                ref={attachCanvas}
                onWheel={e => {
                    e.preventDefault()
                    const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12
                    setView(v => {
                        const k = Math.min(8, Math.max(0.6, v.k * factor))
                        const rect = containerRef.current?.getBoundingClientRect()
                        const mx = (e.clientX - (rect?.left ?? 0))
                        const my = (e.clientY - (rect?.top ?? 0))
                        return {
                            k,
                            tx: mx - (mx - v.tx) * (k / v.k),
                            ty: my - (my - v.ty) * (k / v.k),
                        }
                    })
                }}
                onPointerDown={e => {
                    e.preventDefault()
                    try { (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId) } catch { /* synthetic/inactive pointer */ }
                    spinPausedRef.current = true
                    draggingRef.current = true
                    lastInteractionRef.current = performance.now()
                    pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
                    if (pointersRef.current.size === 2) {
                        // begin pinch: two fingers = pan + zoom + TWIST→roll (touch)
                        const pts = [...pointersRef.current.values()]
                        pinchRef.current = {
                            dist: Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y),
                            cx: (pts[0].x + pts[1].x) / 2,
                            cy: (pts[0].y + pts[1].y) / 2,
                            angle: Math.atan2(pts[1].y - pts[0].y, pts[1].x - pts[0].x),
                            tx: view.tx, ty: view.ty, k: view.k,
                        }
                        dragRef.current = null
                    } else {
                        // pan-mode/shift/right/middle = PAN; alt/ctrl = ROLL; else ORBIT
                        const mode: 'orbit' | 'roll' | 'pan' =
                            (navMode === 'pan' || e.shiftKey || e.button === 2 || e.button === 1) ? 'pan'
                            : (navMode === 'roll' || e.altKey || e.ctrlKey || e.metaKey) ? 'roll'
                            : 'orbit'
                        dragRef.current = { lastX: e.clientX, lastY: e.clientY, mode, tx: view.tx, ty: view.ty }
                    }
                }}
                onPointerMove={e => {
                    if (pointersRef.current.has(e.pointerId)) {
                        pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
                    }
                    // two-finger: pan + pinch-zoom + twist→roll about the midpoint
                    if (pinchRef.current && pointersRef.current.size === 2) {
                        const pts = [...pointersRef.current.values()]
                        const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y)
                        const cx = (pts[0].x + pts[1].x) / 2
                        const cy = (pts[0].y + pts[1].y) / 2
                        const angle = Math.atan2(pts[1].y - pts[0].y, pts[1].x - pts[0].x)
                        const p = pinchRef.current
                        const k = Math.min(8, Math.max(0.6, p.k * (dist / Math.max(1, p.dist))))
                        setView({ k, tx: p.tx + (cx - p.cx), ty: p.ty + (cy - p.cy) })
                        const dRoll = angle - p.angle
                        if (Math.abs(dRoll) > 1e-4) setRot(r => mul3(rotZ(dRoll), r))
                        pinchRef.current = { ...p, angle }
                        lastInteractionRef.current = performance.now()
                        return
                    }
                    const d = dragRef.current
                    if (!d) return
                    lastInteractionRef.current = performance.now()
                    const dx = e.clientX - d.lastX
                    const dy = e.clientY - d.lastY
                    d.lastX = e.clientX; d.lastY = e.clientY
                    if (d.mode === 'pan') {
                        setView(v => ({ ...v, tx: v.tx + dx, ty: v.ty + dy }))
                    } else if (d.mode === 'roll') {
                        setRot(r => mul3(rotZ(dx * 0.01), r))
                    } else {
                        // free trackball orbit: screen-space incremental rotation
                        // (premultiply → no fixed up-vector, roll emerges from combined drags)
                        setRot(r => mul3(mul3(rotX(-dy * 0.006), rotY(dx * 0.006)), r))
                    }
                }}
                onPointerUp={e => {
                    pointersRef.current.delete(e.pointerId)
                    if (pointersRef.current.size < 2) pinchRef.current = null
                    if (pointersRef.current.size === 0) { dragRef.current = null; draggingRef.current = false }
                    spinPausedRef.current = hoveredId !== null
                }}
                onPointerLeave={e => {
                    pointersRef.current.delete(e.pointerId)
                    if (pointersRef.current.size === 0) { pinchRef.current = null; dragRef.current = null; draggingRef.current = false }
                    spinPausedRef.current = hoveredId !== null
                }}
                onContextMenu={e => e.preventDefault()}
                onDragStart={e => e.preventDefault()}
            >
                <svg width={size.w} height={size.h} role="img" aria-label="Atlas story universe">
                    <defs>
                        <radialGradient id="universe-heat-halo" cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stopColor="#fb923c" stopOpacity="0.55" />
                            <stop offset="45%" stopColor="#f97316" stopOpacity="0.22" />
                            <stop offset="100%" stopColor="#f97316" stopOpacity="0" />
                        </radialGradient>
                    </defs>
                    {/* constellation labels (rotate with the cloud) */}
                    {!orphansOnly && payload.anchors.filter(a => a.count >= 4).map(a => {
                        const p = project3(a.x, a.y, a.z)
                        return (
                            <text
                                key={a.category}
                                x={p.sx} y={p.sy}
                                className="universe-constellation"
                                opacity={depthAlpha(p.depth) * 0.9}
                            >
                                {a.category}
                            </text>
                        )
                    })}

                    {/* hovered node's REAL path through the field */}
                    {hoveredId && (() => {
                        const n = nodeById.get(hoveredId)
                        if (!n?.track || n.track.length < 2) return null
                        const pts = [...n.track.map(tp => ({ x: tp.x, y: tp.y, z: tp.z })), { x: n.x, y: n.y, z: n.z }]
                        const screen = pts.map(pt => {
                            const p = project3(pt.x, pt.y, pt.z)
                            return `${p.sx},${p.sy}`
                        })
                        return (
                            <polyline
                                points={screen.join(' ')}
                                fill="none"
                                stroke={categoryColor(n.category)}
                                strokeOpacity={0.45}
                                strokeWidth={1.2}
                                strokeDasharray="2 3"
                                pointerEvents="none"
                            />
                        )
                    })()}

                    {/* semantic edges (full-space truth) */}
                    {edges.map(e => {
                        const pa = projected.get(e.a)
                        const pb = projected.get(e.b)
                        if (!pa || !pb) return null
                        const aa = alphaById.get(e.a) ?? 0
                        const ab = alphaById.get(e.b) ?? 0
                        if (aa === 0 || ab === 0) return null
                        const highlighted = neighborIds ? (neighborIds.has(e.a) && neighborIds.has(e.b)) : true
                        const depthDim = depthAlpha(Math.max(pa.depth, pb.depth))
                        return (
                            <line
                                key={`${e.a}-${e.b}`}
                                x1={pa.sx} y1={pa.sy} x2={pb.sx} y2={pb.sy}
                                stroke="#7dd3fc"
                                strokeOpacity={highlighted ? edgeOpacity(e.sim) * Math.min(aa, ab) * depthDim : 0.02}
                                strokeWidth={highlighted && neighborIds ? 1.4 : 0.7}
                            />
                        )
                    })}

                    {/* GRAVITY WELL: focused entity's ghost sun at the barycenter
                        of its stories + a line to each lit story (drawn under
                        the bodies). The sun is an OVERLAY — it never moves the
                        semantic positions, so the field stays honest. */}
                    {litActive && sun && (
                        <g pointerEvents="none">
                            {litNodes.map(n => {
                                const p = projected.get(n.id)
                                if (!p) return null
                                return (
                                    <line key={`grav-${n.id}`}
                                        x1={sun.sx} y1={sun.sy} x2={p.sx} y2={p.sy}
                                        stroke="#fbbf24" strokeOpacity={0.28} strokeWidth={1} />
                                )
                            })}
                            <circle cx={sun.sx} cy={sun.sy} r={9} fill="#fbbf24" fillOpacity={0.22} />
                            <circle cx={sun.sx} cy={sun.sy} r={4} fill="#fde68a" />
                        </g>
                    )}

                    {/* story bodies — far first, near last (painter's order) */}
                    {depthOrdered.map(n => {
                        const alpha = alphaById.get(n.id) ?? 0
                        if (alpha === 0) return null
                        const p = projected.get(n.id)
                        if (!p) return null
                        // when an entity is focused, its stories stay lit, the rest ghosts
                        const lit = litActive && litIds.has(n.id)
                        const dimmed = (neighborIds !== null && !neighborIds.has(n.id)) || (litActive && !lit)
                        const orphan = isOrphan(n)
                        const isActive = n.id === activeTheme
                        const r = universeRadius(n.n) * Math.min(1.6, Math.max(0.8, view.k)) * depthScale(p.depth)
                        return (
                            <g
                                key={n.id}
                                className="universe-body"
                                opacity={(dimmed && !isActive && !lit ? 0.08 : Math.max(alpha, isActive || lit ? 0.95 : 0)) * depthAlpha(p.depth)}
                                                onMouseEnter={() => { lastInteractionRef.current = performance.now(); setHoveredId(n.id) }}
                                onMouseLeave={() => setHoveredId(h => (h === n.id ? null : h))}
                                onClick={() => onThemeSelect(n.id)}
                            >
                                {isHeating(n) && !dimmed && (
                                    <circle
                                        cx={p.sx} cy={p.sy}
                                        r={r * heatHalo(n.velocity)}
                                        fill="url(#universe-heat-halo)"
                                        pointerEvents="none"
                                    />
                                )}
                                {isActive && (
                                    <circle
                                        cx={p.sx} cy={p.sy}
                                        r={r + 5}
                                        fill="none"
                                        stroke="rgba(52, 211, 153, 0.9)"
                                        strokeWidth={1.6}
                                    />
                                )}
                                <circle
                                    cx={p.sx} cy={p.sy}
                                    r={r}
                                    fill={categoryColor(n.category)}
                                    fillOpacity={0.85}
                                    stroke={n.crisis_relevant ? 'rgba(248,113,113,0.85)' : orphan ? 'rgba(226,232,240,0.8)' : 'rgba(226,232,240,0.35)'}
                                    strokeWidth={n.crisis_relevant ? 1.4 : orphan ? 1.1 : 0.6}
                                    strokeDasharray={orphan ? '3 2.4' : undefined}
                                />
                                {(labeledIds.has(n.id) || hoveredId === n.id || lit) && (
                                    <text x={p.sx} y={p.sy + r + 11} className="universe-body-label">
                                        {n.label.length > 30 ? `${n.label.slice(0, 28)}…` : n.label}
                                    </text>
                                )}
                            </g>
                        )
                    })}
                </svg>

                {litActive && spread && (
                    <div className="universe-footprint">
                        <span className="universe-footprint-entity">{focusValue}</span>
                        <span className="universe-footprint-stat">
                            {spread.stories} {spread.stories === 1 ? 'story' : 'stories'} · {spread.categories} {spread.categories === 1 ? 'category' : 'categories'}
                        </span>
                        <span className={`universe-footprint-shape universe-footprint-shape--${spread.shape}`}
                            data-tip={spread.shape === 'cross-cutting'
                                ? 'This entity spans many narrative categories — a dominant, cross-cutting figure right now'
                                : spread.shape === 'concentrated'
                                    ? 'This entity sits in one or two stories — a focused, single-thread actor'
                                    : 'This entity spans a few narrative categories'}>
                            {spread.shape === 'cross-cutting' ? '◇ cross-cutting' : spread.shape === 'concentrated' ? '◈ concentrated' : '◈ mixed'}
                        </span>
                    </div>
                )}

                {hovered && (
                    <div className="universe-hover">
                        <span style={{ color: categoryColor(hovered.category) }}>{hovered.category}</span>
                        <strong>{hovered.label}</strong>
                        <em>{hovered.n.toLocaleString()} signals{hovered.crisis_relevant ? ' · crisis-relevant' : ''}{isOrphan(hovered) ? ' · ORPHAN (unlike every other story)' : ''}</em>
                        <em>
                            {hovered.first_seen ? new Date(hovered.first_seen).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '—'}
                            {' → '}
                            {hovered.last_seen ? new Date(hovered.last_seen).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '—'}
                        </em>
                        <em className="universe-hover-cta">click to open its story system</em>
                        {isHeating(hovered) && <em className="universe-hover-heat">heating · accel {(hovered.velocity ?? 0).toFixed(2)}</em>}
                    </div>
                )}

                {!litActive && heating.length > 0 && (
                    <div className="universe-heating-readout" data-tip="Stories whose signal count is accelerating over the snapshot history — measured attention velocity, not a prediction">
                        <span className="universe-heating-count">
                            <svg width="9" height="11" viewBox="0 0 9 11" aria-hidden="true" style={{ marginRight: 5, verticalAlign: '-1px' }}>
                                {/* upward spark — rising attention, vector not emoji */}
                                <path d="M4.5 0 L9 5.5 L6 5 L7 11 L4.5 7 L2 11 L3 5 L0 5.5 Z" fill="#fb923c" />
                            </svg>
                            {heating.length} heating
                        </span>
                        <span className="universe-heating-top">{heating[0].label.length > 26 ? `${heating[0].label.slice(0, 24)}…` : heating[0].label}</span>
                    </div>
                )}
            </div>

            <div className="universe-scrubber">
                <span className="universe-scrubber-time">
                    {atNow ? 'NOW' : new Date(scrubT).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit' })}
                </span>
                <input
                    type="range"
                    min={0} max={100} value={scrubPct}
                    onChange={e => setScrubPct(Number(e.target.value))}
                    aria-label="Universe time scrubber"
                    data-tip="Scrub time: stories are born, burn, and fade across the field"
                />
                <span className="universe-scrubber-stats" data-tip="Stories alive at the scrubbed moment · stories born in the trailing 7 days">
                    {aliveCount} alive · {newThisWeek} born this week
                </span>
            </div>

            <div className="universe-legend">
                <span><i className="universe-legend-dot" />size = volume (log)</span>
                <span><i className="universe-legend-edge" />line = semantic proximity (measured in full 768-dim space)</span>
                <span><i className="universe-legend-crisis" />red ring = crisis-relevant</span>
                <span data-tip="Best semantic neighbor below the isolated band — a story unlike every other living story"><i className="universe-legend-orphan" />dashed = orphan</span>
                <span className="universe-legend-note" data-tip={payload.meta?.position_basis ?? ''}>
                    positions approximate · relations exact · drag to rotate, scroll to zoom
                </span>
            </div>
        </div>
    )
}
