import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { ForceGraphMethods } from 'react-force-graph-2d'
import {
    buildTemporalNarrativeGraph,
    type TemporalNarrativeBucket,
    type TemporalNarrativeLink,
    type TemporalNarrativeNode,
    type TemporalSignalInput,
} from '../lib/temporalNarrativeGraph'
import './TemporalNarrativeGraph.css'

interface TemporalNarrativeGraphProps {
    theme: string
    themeLabel: string
    signals: TemporalSignalInput[]
    onThemeSelect?: (theme: string) => void
    onCountrySelect?: (code: string) => void
    onPersonSelect?: (name: string) => void
    onSourceSelect?: (domain: string) => void
    onOpenInWorkspace?: () => void
    onPinSnapshot?: (bucket: TemporalNarrativeBucket) => void
}

type GraphNode = TemporalNarrativeNode & { x?: number; y?: number }
type GraphLink = TemporalNarrativeLink & { source: string | GraphNode; target: string | GraphNode }

const NODE_COLORS: Record<TemporalNarrativeNode['type'], string> = {
    theme: '#34d399',
    country: '#60a5fa',
    source: '#f59e0b',
    person: '#a78bfa',
}

const LINK_COLORS: Record<TemporalNarrativeLink['kind'], string> = {
    'country-theme': 'rgba(52, 211, 153, 0.74)',
    'source-country': 'rgba(245, 158, 11, 0.58)',
    'person-country': 'rgba(167, 139, 250, 0.58)',
    'related-theme': 'rgba(45, 212, 191, 0.58)',
}

function nodeRadius(node: TemporalNarrativeNode): number {
    return Math.max(5, Math.min(16, 5 + Math.sqrt(node.count) * 2.4))
}

function truncateLabel(label: string, maxLength = 24): string {
    if (label.length <= maxLength) return label
    return `${label.slice(0, maxLength - 3)}...`
}

function formatKind(kind: string): string {
    return kind.replace(/-/g, ' ')
}

function getLinkNode(value: string | GraphNode): GraphNode | null {
    if (typeof value === 'string') return null
    return value
}

function drawNode(node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number, dimmed = false, isLeaf = false): void {
    const radius = (isLeaf ? Math.max(3, nodeRadius(node) * 0.55) : nodeRadius(node)) / globalScale
    const color = NODE_COLORS[node.type]
    const x = node.x ?? 0
    const y = node.y ?? 0
    const label = truncateLabel(node.label)
    const fontSize = Math.max(7, 10 / globalScale)

    ctx.save()
    ctx.globalAlpha = dimmed ? 0.15 : 1
    ctx.shadowColor = color
    ctx.shadowBlur = node.type === 'theme' ? 14 / globalScale : 8 / globalScale
    ctx.beginPath()
    ctx.arc(x, y, radius, 0, Math.PI * 2)
    ctx.fillStyle = node.type === 'theme' ? 'rgba(16, 185, 129, 0.95)' : color
    ctx.fill()
    ctx.lineWidth = 1 / globalScale
    ctx.strokeStyle = 'rgba(226, 232, 240, 0.62)'
    ctx.stroke()

    if ((node.type === 'theme' || globalScale >= 0.9) && (!isLeaf || globalScale >= 1.4)) {
        ctx.shadowBlur = 0
        ctx.font = `600 ${fontSize}px Plus Jakarta Sans, system-ui, sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        ctx.fillStyle = '#e2e8f0'
        ctx.fillText(label, x, y + radius + 3 / globalScale)
    }

    ctx.restore()
}

export function TemporalNarrativeGraph({
    theme,
    themeLabel,
    signals,
    onThemeSelect,
    onCountrySelect,
    onPersonSelect,
    onSourceSelect,
    onOpenInWorkspace,
    onPinSnapshot,
}: TemporalNarrativeGraphProps) {
    const graph = useMemo(() => buildTemporalNarrativeGraph({ theme, themeLabel, signals }), [theme, themeLabel, signals])
    const graphKey = `${theme}:${graph.buckets.length}:${graph.buckets.at(-1)?.id ?? 'empty'}`
    const [bucketSelection, setBucketSelection] = useState<{ graphKey: string; index: number } | null>(null)
    const [hoveredNode, setHoveredNode] = useState<TemporalNarrativeNode | null>(null)
    const hoveredNodeRef = useRef<TemporalNarrativeNode | null>(null)
    const connectedIdsRef = useRef<Set<string>>(new Set())
    const canvasRef = useRef<HTMLDivElement | null>(null)
    const graphRef = useRef<ForceGraphMethods<TemporalNarrativeNode, TemporalNarrativeLink> | undefined>(undefined)
    const [canvasSize, setCanvasSize] = useState({ width: 560, height: 320 })

    useEffect(() => {
        const element = canvasRef.current
        if (!element) return
        const observer = new ResizeObserver(entries => {
            const entry = entries[0]
            if (!entry) return
            setCanvasSize({
                width: Math.max(320, entry.contentRect.width),
                height: Math.max(280, entry.contentRect.height),
            })
        })
        observer.observe(element)
        return () => observer.disconnect()
    }, [])

    const lastBucketIndex = Math.max(0, graph.buckets.length - 1)
    const bucketIndex = bucketSelection?.graphKey === graphKey
        ? Math.min(bucketSelection.index, lastBucketIndex)
        : lastBucketIndex
    const bucket = graph.buckets[bucketIndex]

    const graphData = useMemo(() => {
        if (!bucket) return { nodes: [], links: [], leafIds: new Set<string>() }
        // Count degree per node to identify leaves (degree === 1)
        const degree = new Map<string, number>()
        for (const l of bucket.links) {
            degree.set(l.source, (degree.get(l.source) ?? 0) + 1)
            degree.set(l.target, (degree.get(l.target) ?? 0) + 1)
        }
        const leafIds = new Set(
            bucket.nodes
                .filter(n => n.type !== 'theme' && (degree.get(n.id) ?? 0) <= 1)
                .map(n => n.id)
        )
        return {
            nodes: [...bucket.nodes],
            links: bucket.links.map(l => ({ ...l })),
            leafIds,
        }
    }, [bucket])

    const leafIdsRef = useRef<Set<string>>(new Set())
    useEffect(() => { leafIdsRef.current = graphData.leafIds }, [graphData.leafIds])

    useEffect(() => {
        const fg = graphRef.current
        if (!fg || !bucket) return
        fg.d3Force('charge')?.strength(-170)
        fg.d3Force('link')?.distance(84)
        fg.d3ReheatSimulation()
        const timeoutId = window.setTimeout(() => fg.zoomToFit(350, 36), 250)
        return () => window.clearTimeout(timeoutId)
    }, [bucket])

    // Sync hover state to refs so draw callbacks (called every frame) see latest value
    useEffect(() => {
        hoveredNodeRef.current = hoveredNode
        if (!hoveredNode) {
            connectedIdsRef.current = new Set()
            return
        }
        const connected = new Set<string>([hoveredNode.id])
        for (const link of graphData.links) {
            const srcId = typeof link.source === 'string' ? link.source : (link.source as GraphNode).id
            const tgtId = typeof link.target === 'string' ? link.target : (link.target as GraphNode).id
            if (srcId === hoveredNode.id) connected.add(tgtId)
            if (tgtId === hoveredNode.id) connected.add(srcId)
        }
        connectedIdsRef.current = connected
    }, [hoveredNode, graphData.links])

    const handleNodeClick = useCallback((node: TemporalNarrativeNode) => {
        if (node.type === 'country') onCountrySelect?.(node.id.replace(/^country-/, ''))
        if (node.type === 'person') onPersonSelect?.(node.label)
        if (node.type === 'source') onSourceSelect?.(node.label)
        if (node.type === 'theme') onThemeSelect?.(node.id.replace(/^theme-/, ''))
    }, [onCountrySelect, onPersonSelect, onSourceSelect, onThemeSelect])

    const drawLinkLabel = useCallback((link: GraphLink, ctx: CanvasRenderingContext2D, globalScale: number) => {
        if (globalScale < 1.35 || link.count < 2) return
        const source = getLinkNode(link.source)
        const target = getLinkNode(link.target)
        if (!source || !target || source.x == null || source.y == null || target.x == null || target.y == null) return
        const hovered = hoveredNodeRef.current
        if (hovered) {
            const connected = connectedIdsRef.current
            if (!connected.has(source.id) || !connected.has(target.id)) return
        }
        const x = (source.x + target.x) / 2
        const y = (source.y + target.y) / 2
        ctx.save()
        ctx.font = `500 ${Math.max(6, 7 / globalScale)}px Space Grotesk, monospace`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillStyle = LINK_COLORS[link.kind]
        ctx.fillText(`${formatKind(link.kind)} ${link.count}`, x, y)
        ctx.restore()
    }, [])

    if (!bucket) {
        return (
            <section className="temporal-graph-section">
                <div className="temporal-graph-header">
                    <div>
                        <h3>Evolution Graph</h3>
                        <p>No recent coverage sample available for graphing.</p>
                    </div>
                </div>
            </section>
        )
    }

    return (
        <section className="temporal-graph-section">
            <div className="temporal-graph-header">
                <div>
                    <h3>Evolution Graph</h3>
                    <p>Connections from the recent coverage sample, bucketed over time.</p>
                </div>
                <div className="temporal-graph-stats">
                    <span>{bucket.signalCount} signals</span>
                    <span>{bucket.nodes.length} nodes</span>
                    <span>{bucket.links.length} links</span>
                    {onOpenInWorkspace && (
                        <button className="temporal-graph-workspace-btn" onClick={onOpenInWorkspace} data-tip="Open Workspace">
                            ⊞ Workspace
                        </button>
                    )}
                    {onPinSnapshot && (
                        <button className="temporal-graph-workspace-btn" onClick={() => onPinSnapshot(bucket)} data-tip="Pin selected time bucket">
                            Pin bucket
                        </button>
                    )}
                </div>
            </div>

            <div className="temporal-graph-canvas" ref={canvasRef}>
                <ForceGraph2D
                    ref={graphRef}
                    graphData={graphData}
                    width={canvasSize.width}
                    height={canvasSize.height}
                    nodeId="id"
                    nodeCanvasObject={(node, ctx, globalScale) => {
                        const n = node as GraphNode
                        const hovered = hoveredNodeRef.current
                        const dimmed = hovered !== null && !connectedIdsRef.current.has(n.id)
                        const isLeaf = leafIdsRef.current.has(n.id)
                        drawNode(n, ctx, globalScale, dimmed, isLeaf)
                    }}
                    nodePointerAreaPaint={(node, color, ctx) => {
                        const graphNode = node as GraphNode
                        ctx.fillStyle = color
                        ctx.beginPath()
                        ctx.arc(graphNode.x ?? 0, graphNode.y ?? 0, nodeRadius(graphNode) + 4, 0, Math.PI * 2)
                        ctx.fill()
                    }}
                    linkWidth={link => {
                        const l = link as TemporalNarrativeLink & { source: string | GraphNode; target: string | GraphNode }
                        const hovered = hoveredNodeRef.current
                        if (!hovered) return Math.max(1, Math.min(5, Number(l.count ?? 1)))
                        const srcId = typeof l.source === 'string' ? l.source : (l.source as GraphNode).id
                        const tgtId = typeof l.target === 'string' ? l.target : (l.target as GraphNode).id
                        const connected = connectedIdsRef.current
                        return connected.has(srcId) && connected.has(tgtId)
                            ? Math.max(1, Math.min(5, Number(l.count ?? 1)))
                            : 0.5
                    }}
                    linkColor={link => {
                        const l = link as TemporalNarrativeLink & { source: string | GraphNode; target: string | GraphNode }
                        const hovered = hoveredNodeRef.current
                        if (!hovered) return LINK_COLORS[l.kind]
                        const srcId = typeof l.source === 'string' ? l.source : (l.source as GraphNode).id
                        const tgtId = typeof l.target === 'string' ? l.target : (l.target as GraphNode).id
                        const connected = connectedIdsRef.current
                        return connected.has(srcId) && connected.has(tgtId)
                            ? LINK_COLORS[l.kind]
                            : 'rgba(255,255,255,0.05)'
                    }}
                    linkDirectionalParticles={link => Math.min(3, Math.max(1, Math.floor(Number((link as TemporalNarrativeLink).count ?? 1) / 2)))}
                    linkDirectionalParticleWidth={1.4}
                    linkDirectionalParticleSpeed={0.004}
                    linkCanvasObjectMode={() => 'after'}
                    linkCanvasObject={(link, ctx, globalScale) => drawLinkLabel(link as GraphLink, ctx, globalScale)}
                    backgroundColor="rgba(0,0,0,0)"
                    cooldownTicks={80}
                    onNodeHover={node => setHoveredNode(node ? node as TemporalNarrativeNode : null)}
                    onNodeClick={node => handleNodeClick(node as TemporalNarrativeNode)}
                />

                {hoveredNode && (
                    <div className="temporal-graph-hover">
                        <span>{hoveredNode.type}</span>
                        <strong>{hoveredNode.label}</strong>
                        <em>{hoveredNode.count} connections</em>
                    </div>
                )}
            </div>

            <TemporalScrubber
                bucket={bucket}
                buckets={graph.buckets}
                bucketIndex={bucketIndex}
                onChange={index => setBucketSelection({ graphKey, index })}
            />

            <div className="temporal-graph-legend" aria-label="Temporal graph legend">
                {Object.entries(NODE_COLORS).map(([type, color]) => (
                    <span key={type}>
                        <i style={{ background: color }} />
                        {type}
                    </span>
                ))}
            </div>
        </section>
    )
}

function TemporalScrubber({
    bucket,
    buckets,
    bucketIndex,
    onChange,
}: {
    bucket: TemporalNarrativeBucket
    buckets: TemporalNarrativeBucket[]
    bucketIndex: number
    onChange: (index: number) => void
}) {
    return (
        <div className="temporal-graph-scrubber">
            <span>{bucket.label}</span>
            <input
                type="range"
                min={0}
                max={Math.max(0, buckets.length - 1)}
                value={bucketIndex}
                onChange={event => onChange(Number(event.target.value))}
                aria-label="Narrative graph time bucket"
            />
            <span>{bucket.signalCount} in bucket</span>
        </div>
    )
}
