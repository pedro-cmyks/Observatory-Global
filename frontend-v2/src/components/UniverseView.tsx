import { useEffect, useMemo, useRef, useState } from 'react'
import {
    bornBetween,
    categoryColor,
    depthAlpha,
    depthScale,
    edgeOpacity,
    isOrphan,
    universeAlpha,
    universeRadius,
    yawProject,
    type UniverseEdge,
    type UniverseNode,
} from '../lib/universeLayout'
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
}

const WEEK_MS = 7 * 24 * 3_600_000

export function UniverseView({ onThemeSelect }: UniverseViewProps) {
    const [payload, setPayload] = useState<UniversePayload | null>(null)
    const [loading, setLoading] = useState(true)
    const [scrubPct, setScrubPct] = useState(100)
    const [hoveredId, setHoveredId] = useState<string | null>(null)
    const [view, setView] = useState({ k: 1, tx: 0, ty: 0 })
    // Yaw: the cloud's rotation around its vertical axis (spec §7.2). Slow
    // ambient spin; ANY interaction (hover/drag) pauses it — camera, not time.
    const [yaw, setYaw] = useState(0)
    const spinPausedRef = useRef(false)
    const dragRef = useRef<{ x: number; y: number; ty: number; yaw: number } | null>(null)
    const containerRef = useRef<HTMLDivElement | null>(null)
    const [size, setSize] = useState({ w: 1200, h: 700 })

    useEffect(() => {
        let raf = 0
        let last = performance.now()
        const tick = (now: number) => {
            const dt = (now - last) / 1000
            last = now
            if (!spinPausedRef.current && !document.hidden) {
                setYaw(y => y + dt * 0.06) // ~1 turn / 105s — ambient, not dizzy
            }
            raf = requestAnimationFrame(tick)
        }
        raf = requestAnimationFrame(tick)
        return () => cancelAnimationFrame(raf)
    }, [])

    useEffect(() => {
        spinPausedRef.current = hoveredId !== null
    }, [hoveredId])

    useEffect(() => {
        const element = containerRef.current
        if (!element) return
        const observer = new ResizeObserver(entries => {
            const rect = entries[0]?.contentRect
            if (rect) setSize({ w: Math.max(480, rect.width), h: Math.max(360, rect.height) })
        })
        observer.observe(element)
        return () => observer.disconnect()
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

    const nodes = useMemo(() => payload?.nodes ?? [], [payload])
    const edges = useMemo(() => payload?.edges ?? [], [payload])

    const timeSpan = useMemo(() => {
        const firsts = nodes.map(n => (n.first_seen ? Date.parse(n.first_seen) : Infinity))
        const start = Math.min(...(firsts.length ? firsts : [Date.now()]))
        return { start, end: Date.now() }
    }, [nodes])

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

    // Rotate the cloud (real PCA depth), then map to screen. Far bodies render
    // first, smaller and dimmer — turning the field separates what overlaps.
    const projected = useMemo(() => {
        const out = new Map<string, { sx: number; sy: number; depth: number }>()
        for (const n of nodes) {
            const p = yawProject(n.x, n.z, yaw)
            out.set(n.id, { sx: px(p.px), sy: py(n.y), depth: p.depth })
        }
        return out
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [nodes, yaw, view, size])

    const depthOrdered = useMemo(
        () => [...nodes].sort((a, b) => (projected.get(b.id)?.depth ?? 0) - (projected.get(a.id)?.depth ?? 0)),
        [nodes, projected],
    )

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
    if (!payload || nodes.length === 0) {
        return <div className="universe-empty">Universe data unavailable{payload?.reason ? ` (${payload.reason})` : ''}.</div>
    }

    return (
        <div className="universe-root">
            <div
                className="universe-canvas"
                ref={containerRef}
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
                    spinPausedRef.current = true
                    dragRef.current = { x: e.clientX, y: e.clientY, ty: view.ty, yaw }
                }}
                onPointerMove={e => {
                    const d = dragRef.current
                    if (!d) return
                    // horizontal drag ROTATES the cloud; vertical drag pans
                    setYaw(d.yaw + (e.clientX - d.x) * 0.004)
                    setView(v => ({ ...v, ty: d.ty + (e.clientY - d.y) }))
                }}
                onPointerUp={() => { dragRef.current = null; spinPausedRef.current = hoveredId !== null }}
                onPointerLeave={() => { dragRef.current = null; spinPausedRef.current = hoveredId !== null }}
            >
                <svg width={size.w} height={size.h} role="img" aria-label="Atlas story universe">
                    {/* constellation labels (rotate with the cloud) */}
                    {payload.anchors.filter(a => a.count >= 4).map(a => {
                        const p = yawProject(a.x, a.z, yaw)
                        return (
                            <text
                                key={a.category}
                                x={px(p.px)} y={py(a.y)}
                                className="universe-constellation"
                                opacity={depthAlpha(p.depth) * 0.9}
                            >
                                {a.category}
                            </text>
                        )
                    })}

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
                        const r = universeRadius(n.n) * Math.min(1.6, Math.max(0.8, view.k)) * depthScale(p.depth)
                        return (
                            <g
                                key={n.id}
                                className="universe-body"
                                opacity={(dimmed ? 0.12 : alpha) * depthAlpha(p.depth)}
                                onMouseEnter={() => setHoveredId(n.id)}
                                onMouseLeave={() => setHoveredId(h => (h === n.id ? null : h))}
                                onClick={() => onThemeSelect(n.id)}
                            >
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
