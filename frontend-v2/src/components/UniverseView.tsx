import { useEffect, useMemo, useRef, useState } from 'react'
import {
    bornBetween,
    categoryColor,
    edgeOpacity,
    universeAlpha,
    universeRadius,
    type UniverseEdge,
    type UniverseNode,
} from '../lib/universeLayout'
import './UniverseView.css'

interface UniversePayload {
    contract: string
    nodes: UniverseNode[]
    edges: UniverseEdge[]
    anchors: Array<{ category: string; x: number; y: number; count: number }>
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
    const dragRef = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null)
    const containerRef = useRef<HTMLDivElement | null>(null)
    const [size, setSize] = useState({ w: 1200, h: 700 })

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
                    dragRef.current = { x: e.clientX, y: e.clientY, tx: view.tx, ty: view.ty }
                }}
                onPointerMove={e => {
                    const d = dragRef.current
                    if (!d) return
                    setView(v => ({ ...v, tx: d.tx + (e.clientX - d.x), ty: d.ty + (e.clientY - d.y) }))
                }}
                onPointerUp={() => { dragRef.current = null }}
                onPointerLeave={() => { dragRef.current = null }}
            >
                <svg width={size.w} height={size.h} role="img" aria-label="Atlas story universe">
                    {/* constellation labels */}
                    {payload.anchors.filter(a => a.count >= 4).map(a => (
                        <text key={a.category} x={px(a.x)} y={py(a.y)} className="universe-constellation">
                            {a.category}
                        </text>
                    ))}

                    {/* semantic edges (full-space truth) */}
                    {edges.map(e => {
                        const na = nodeById.get(e.a)
                        const nb = nodeById.get(e.b)
                        if (!na || !nb) return null
                        const aa = alphaById.get(e.a) ?? 0
                        const ab = alphaById.get(e.b) ?? 0
                        if (aa === 0 || ab === 0) return null
                        const highlighted = neighborIds ? (neighborIds.has(e.a) && neighborIds.has(e.b)) : true
                        return (
                            <line
                                key={`${e.a}-${e.b}`}
                                x1={px(na.x)} y1={py(na.y)} x2={px(nb.x)} y2={py(nb.y)}
                                stroke="#7dd3fc"
                                strokeOpacity={highlighted ? edgeOpacity(e.sim) * Math.min(aa, ab) : 0.02}
                                strokeWidth={highlighted && neighborIds ? 1.4 : 0.7}
                            />
                        )
                    })}

                    {/* story bodies */}
                    {nodes.map(n => {
                        const alpha = alphaById.get(n.id) ?? 0
                        if (alpha === 0) return null
                        const dimmed = neighborIds !== null && !neighborIds.has(n.id)
                        return (
                            <g
                                key={n.id}
                                className="universe-body"
                                opacity={dimmed ? 0.12 : alpha}
                                onMouseEnter={() => setHoveredId(n.id)}
                                onMouseLeave={() => setHoveredId(h => (h === n.id ? null : h))}
                                onClick={() => onThemeSelect(n.id)}
                            >
                                <circle
                                    cx={px(n.x)} cy={py(n.y)}
                                    r={universeRadius(n.n) * Math.min(1.6, Math.max(0.8, view.k))}
                                    fill={categoryColor(n.category)}
                                    fillOpacity={0.85}
                                    stroke={n.crisis_relevant ? 'rgba(248,113,113,0.85)' : 'rgba(226,232,240,0.35)'}
                                    strokeWidth={n.crisis_relevant ? 1.4 : 0.6}
                                />
                                {(labeledIds.has(n.id) || hoveredId === n.id) && (
                                    <text x={px(n.x)} y={py(n.y) + universeRadius(n.n) + 11} className="universe-body-label">
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
                        <em>{hovered.n.toLocaleString()} signals{hovered.crisis_relevant ? ' · crisis-relevant' : ''}</em>
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
                <span className="universe-legend-note" data-tip={payload.meta?.position_basis ?? ''}>
                    positions approximate · relations exact · scroll to zoom, drag to pan
                </span>
            </div>
        </div>
    )
}
