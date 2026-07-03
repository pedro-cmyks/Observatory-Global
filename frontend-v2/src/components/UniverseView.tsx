import { useEffect, useMemo, useRef, useState } from 'react'
import {
    bornBetween,
    categoryColor,
    cloudCenter,
    depthAlpha,
    depthScale,
    edgeOpacity,
    isOrphan,
    positionAt,
    universeAlpha,
    universeRadius,
    rotateProject,
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
    onPersonSelect?: (name: string) => void
    onCountrySelect?: (code: string) => void
}

const WEEK_MS = 7 * 24 * 3_600_000

export function UniverseView({ onThemeSelect, activeTheme, activeThemeLabel, hours = 24, onPersonSelect, onCountrySelect }: UniverseViewProps) {
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
    const [yaw, setYaw] = useState(0)
    // pitch = the second rotation axis (free orbit, Pedro's "sin restringir a
    // un eje"). Clamped so the cloud never flips fully upside down.
    const [pitch, setPitch] = useState(0)
    // Nav mode: drag ROTATES by default (fly around), or PANS (drag the cloud
    // across the screen). Two-finger touch always pans+zooms regardless.
    const [navMode, setNavMode] = useState<'rotate' | 'pan'>('rotate')
    const spinPausedRef = useRef(false)
    const dragRef = useRef<{
        x: number; y: number; yaw: number; pitch: number; tx: number; ty: number; pan: boolean
    } | null>(null)
    // Multi-touch: track active pointers for two-finger pan + pinch-zoom.
    const pointersRef = useRef<Map<number, { x: number; y: number }>>(new Map())
    const pinchRef = useRef<{ dist: number; cx: number; cy: number; tx: number; ty: number; k: number } | null>(null)
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
                if (!spinPausedRef.current && !document.hidden && !resting) {
                    setYaw(y => y + (acc / 1000) * 0.06) // ~1 turn / 105s
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
        const p = rotateProject(x, y, z, yaw, pitch, massX, massY, massZ)
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
    }, [nodes, yaw, pitch, view, size, massX, massZ, massY, scrubT])

    const depthOrdered = useMemo(
        () => [...nodes].sort((a, b) => (projected.get(b.id)?.depth ?? 0) - (projected.get(a.id)?.depth ?? 0)),
        [nodes, projected],
    )

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
            const p = rotateProject(body.x, body.y, body.z, yaw, pitch, massX, massY, massZ)
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
                        data-tip="Drag to orbit the galaxy freely (both axes). Shift-drag or two fingers to move it"
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
                        className="universe-filter"
                        onClick={() => { setYaw(0); setPitch(0); setView({ k: 1, tx: 0, ty: 0 }) }}
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
                    lastInteractionRef.current = performance.now()
                    pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
                    if (pointersRef.current.size === 2) {
                        // begin pinch: two fingers = pan + zoom (touch)
                        const pts = [...pointersRef.current.values()]
                        pinchRef.current = {
                            dist: Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y),
                            cx: (pts[0].x + pts[1].x) / 2,
                            cy: (pts[0].y + pts[1].y) / 2,
                            tx: view.tx, ty: view.ty, k: view.k,
                        }
                        dragRef.current = null
                    } else {
                        // shift OR pan-mode OR right/middle button = PAN; else ROTATE
                        const pan = navMode === 'pan' || e.shiftKey || e.button === 2 || e.button === 1
                        dragRef.current = { x: e.clientX, y: e.clientY, yaw, pitch, tx: view.tx, ty: view.ty, pan }
                    }
                }}
                onPointerMove={e => {
                    if (pointersRef.current.has(e.pointerId)) {
                        pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
                    }
                    // two-finger pinch → pan + zoom about the finger midpoint
                    if (pinchRef.current && pointersRef.current.size === 2) {
                        const pts = [...pointersRef.current.values()]
                        const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y)
                        const cx = (pts[0].x + pts[1].x) / 2
                        const cy = (pts[0].y + pts[1].y) / 2
                        const p = pinchRef.current
                        const k = Math.min(8, Math.max(0.6, p.k * (dist / Math.max(1, p.dist))))
                        setView({ k, tx: p.tx + (cx - p.cx), ty: p.ty + (cy - p.cy) })
                        return
                    }
                    const d = dragRef.current
                    if (!d) return
                    lastInteractionRef.current = performance.now()
                    if (d.pan) {
                        setView(v => ({ ...v, tx: d.tx + (e.clientX - d.x), ty: d.ty + (e.clientY - d.y) }))
                    } else {
                        // free orbit: dx → yaw, dy → pitch (clamped so it never flips)
                        setYaw(d.yaw + (e.clientX - d.x) * 0.006)
                        setPitch(Math.max(-1.2, Math.min(1.2, d.pitch + (e.clientY - d.y) * 0.006)))
                    }
                }}
                onPointerUp={e => {
                    pointersRef.current.delete(e.pointerId)
                    if (pointersRef.current.size < 2) pinchRef.current = null
                    if (pointersRef.current.size === 0) dragRef.current = null
                    spinPausedRef.current = hoveredId !== null
                }}
                onPointerLeave={e => {
                    pointersRef.current.delete(e.pointerId)
                    pinchRef.current = null
                    dragRef.current = null
                    spinPausedRef.current = hoveredId !== null
                }}
                onContextMenu={e => e.preventDefault()}
                onDragStart={e => e.preventDefault()}
            >
                <svg width={size.w} height={size.h} role="img" aria-label="Atlas story universe">
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

                    {/* story bodies — far first, near last (painter's order) */}
                    {depthOrdered.map(n => {
                        const alpha = alphaById.get(n.id) ?? 0
                        if (alpha === 0) return null
                        const p = projected.get(n.id)
                        if (!p) return null
                        const dimmed = neighborIds !== null && !neighborIds.has(n.id)
                        const orphan = isOrphan(n)
                        const isActive = n.id === activeTheme
                        const r = universeRadius(n.n) * Math.min(1.6, Math.max(0.8, view.k)) * depthScale(p.depth)
                        return (
                            <g
                                key={n.id}
                                className="universe-body"
                                opacity={(dimmed && !isActive ? 0.12 : Math.max(alpha, isActive ? 0.95 : 0)) * depthAlpha(p.depth)}
                                                onMouseEnter={() => { lastInteractionRef.current = performance.now(); setHoveredId(n.id) }}
                                onMouseLeave={() => setHoveredId(h => (h === n.id ? null : h))}
                                onClick={() => onThemeSelect(n.id)}
                            >
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
                                {(labeledIds.has(n.id) || hoveredId === n.id) && (
                                    <text x={p.sx} y={p.sy + r + 11} className="universe-body-label">
                                        {n.label.length > 30 ? `${n.label.slice(0, 28)}…` : n.label}
                                    </text>
                                )}
                            </g>
                        )
                    })}
                </svg>

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
