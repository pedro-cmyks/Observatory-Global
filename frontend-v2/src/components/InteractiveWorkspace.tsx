import { useDeferredValue, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { ForceGraphMethods } from 'react-force-graph-2d'
import { Download, ExternalLink, Filter, FolderKanban, List, Loader2, Network, Pin, PinOff, Search, X } from 'lucide-react'
import { useWorkspace } from '../contexts/WorkspaceContext'
import {
    WORKSPACE_LINK_KINDS,
    WORKSPACE_NODE_TYPES,
    filterWorkspaceGraph,
    type WorkspaceGraphLink,
    type WorkspaceGraphNode,
    type WorkspaceLinkKind,
} from '../lib/workspaceGraph'
import type { PinnedItemType } from '../contexts/WorkspaceContext'
import './InvestigationWorkspace.css'

interface InteractiveWorkspaceProps {
    onNavigate: (urlParams: string) => void
}

const NODE_COLORS: Record<PinnedItemType, string> = {
    theme: '#34d399',
    country: '#60a5fa',
    source: '#f59e0b',
    person: '#a78bfa',
    signal: '#f87171',
    chokepoint: '#2dd4bf',
    public_attention: '#22d3ee',
}

const LINK_COLORS: Record<WorkspaceLinkKind, string> = {
    'shared-theme': 'rgba(52, 211, 153, 0.72)',
    'shared-source': 'rgba(245, 158, 11, 0.62)',
    'country-framing': 'rgba(96, 165, 250, 0.68)',
    'co-mentioned-person': 'rgba(167, 139, 250, 0.62)',
    'related-theme': 'rgba(45, 212, 191, 0.68)',
    'session-trail': 'rgba(148, 163, 184, 0.55)',
}

function formatFilterLabel(value: string): string {
    return value
        .replace(/_/g, ' ')
        .replace(/-/g, ' ')
        .replace(/\b\w/g, char => char.toUpperCase())
}

function toggleSetValue<T>(current: Set<T>, value: T): Set<T> {
    const next = new Set(current)
    if (next.has(value)) next.delete(value)
    else next.add(value)
    return next
}

function drawRoundedRect(ctx: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number): void {
    ctx.beginPath()
    ctx.moveTo(x + radius, y)
    ctx.lineTo(x + width - radius, y)
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius)
    ctx.lineTo(x + width, y + height - radius)
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
    ctx.lineTo(x + radius, y + height)
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius)
    ctx.lineTo(x, y + radius)
    ctx.quadraticCurveTo(x, y, x + radius, y)
    ctx.closePath()
}

function drawWorkspaceNode(node: WorkspaceGraphNode & { x?: number; y?: number }, ctx: CanvasRenderingContext2D, globalScale: number): void {
    const label = node.title.length > 32 ? `${node.title.slice(0, 29)}...` : node.title
    const subtitle = node.pinned ? formatFilterLabel(node.type) : node.subtitle || formatFilterLabel(node.type)
    const fontSize = Math.max(8, 12 / globalScale)
    const subtitleSize = Math.max(7, 9 / globalScale)
    const paddingX = 10 / globalScale
    const width = Math.max(92 / globalScale, ctx.measureText(label).width + paddingX * 2)
    const height = node.pinned ? 46 / globalScale : 38 / globalScale
    const x = (node.x ?? 0) - width / 2
    const y = (node.y ?? 0) - height / 2
    const color = NODE_COLORS[node.type]

    ctx.save()
    ctx.shadowColor = color
    ctx.shadowBlur = node.pinned ? 18 / globalScale : 8 / globalScale
    ctx.fillStyle = node.pinned ? 'rgba(12, 24, 43, 0.94)' : 'rgba(12, 24, 43, 0.48)'
    ctx.strokeStyle = node.pinned ? color : `${color}88`
    ctx.lineWidth = node.pinned ? 1.4 / globalScale : 1 / globalScale
    
    if (!node.pinned && node.subtitle === 'Visited this session') {
        ctx.setLineDash([4 / globalScale, 4 / globalScale])
    } else {
        ctx.setLineDash([])
    }

    drawRoundedRect(ctx, x, y, width, height, 6 / globalScale)
    ctx.fill()
    ctx.stroke()
    ctx.setLineDash([]) // reset

    ctx.shadowBlur = 0
    ctx.fillStyle = '#e2e8f0'
    ctx.font = `${node.pinned ? 600 : 500} ${fontSize}px Plus Jakarta Sans, system-ui, sans-serif`
    ctx.textAlign = 'left'
    ctx.textBaseline = 'middle'
    ctx.fillText(label, x + paddingX, y + height * 0.42)

    ctx.fillStyle = color
    ctx.font = `500 ${subtitleSize}px Space Grotesk, monospace`
    ctx.fillText(subtitle.toUpperCase(), x + paddingX, y + height * 0.72)
    ctx.restore()
}

export function InteractiveWorkspace({ onNavigate }: InteractiveWorkspaceProps) {
    const { isOpen, setIsOpen, items, sessionItems, graph, graphLoading, graphError, pinItem, unpinItem, updateNotes, exportWorkspace } = useWorkspace()
    const [query, setQuery] = useState('')
    const deferredQuery = useDeferredValue(query)
    const [nodeTypes, setNodeTypes] = useState<Set<PinnedItemType>>(() => new Set(WORKSPACE_NODE_TYPES))
    const [linkKinds, setLinkKinds] = useState<Set<WorkspaceLinkKind>>(() => new Set(WORKSPACE_LINK_KINDS))
    const [showSessionTrail, setShowSessionTrail] = useState(true)
    const [showNotes, setShowNotes] = useState(true)
    const [sidePanelMode, setSidePanelMode] = useState<'trail' | 'pinned'>('trail')
    const boardRef = useRef<HTMLDivElement | null>(null)
    const graphRef = useRef<ForceGraphMethods<WorkspaceGraphNode, WorkspaceGraphLink> | undefined>(undefined)
    const [boardSize, setBoardSize] = useState({ width: 760, height: 560 })

    useEffect(() => {
        const element = boardRef.current
        if (!element) return
        const observer = new ResizeObserver(entries => {
            const entry = entries[0]
            if (!entry) return
            setBoardSize({
                width: Math.max(320, entry.contentRect.width),
                height: Math.max(320, entry.contentRect.height),
            })
        })
        observer.observe(element)
        return () => observer.disconnect()
    }, [])

    const filteredGraph = useMemo(() => {
        const base = filterWorkspaceGraph(graph, {
            query: deferredQuery,
            nodeTypes,
            linkKinds,
        })

        if (!showSessionTrail) {
            const nodes = base.nodes.filter(n => !(n.pinned === false && n.subtitle === 'Visited this session'))
            const nodeIds = new Set(nodes.map(n => n.id))
            const links = base.links.filter(l => nodeIds.has(String(l.source)) && nodeIds.has(String(l.target)) && l.kind !== 'session-trail')
            return { nodes, links }
        }

        return base
    }, [graph, deferredQuery, nodeTypes, linkKinds, showSessionTrail])

    // Strengthen repulsion, set link distance, and add boundary force
    useEffect(() => {
        const fg = graphRef.current
        if (!fg) return
        fg.d3Force('charge')?.strength(-320)
        fg.d3Force('link')?.distance(110)
        // Keep nodes away from canvas edges so labels don't clip
        const pad = 80
        const w = boardSize.width
        const h = boardSize.height
        fg.d3Force('bounds', () => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            for (const node of (filteredGraph.nodes as any[])) {
                if (node.x < pad) node.vx = (node.vx ?? 0) + (pad - node.x) * 0.08
                else if (node.x > w - pad) node.vx = (node.vx ?? 0) - (node.x - (w - pad)) * 0.08
                if (node.y < pad) node.vy = (node.vy ?? 0) + (pad - node.y) * 0.08
                else if (node.y > h - pad) node.vy = (node.vy ?? 0) - (node.y - (h - pad)) * 0.08
            }
        })
        fg.d3ReheatSimulation()
    }, [filteredGraph, boardSize])

    const activeNodeCount = filteredGraph.nodes.length
    const activeLinkCount = filteredGraph.links.length

    const drawLinkLabel = useCallback((link: WorkspaceGraphLink, ctx: CanvasRenderingContext2D, globalScale: number) => {
        // Only draw labels when zoomed in enough to be readable
        if (globalScale < 1.2) return
        const src = link.source as { x?: number; y?: number }
        const tgt = link.target as { x?: number; y?: number }
        if (src.x == null || src.y == null || tgt.x == null || tgt.y == null) return
        const midX = (src.x + tgt.x) / 2
        const midY = (src.y + tgt.y) / 2
        const label = formatFilterLabel(link.kind)
        const fontSize = Math.max(6, 7 / globalScale)
        ctx.save()
        ctx.font = `500 ${fontSize}px Space Grotesk, monospace`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        // Pill background
        const tw = ctx.measureText(label).width
        const ph = fontSize * 1.4
        const pw = tw + fontSize
        ctx.fillStyle = 'rgba(9, 18, 33, 0.82)'
        ctx.beginPath()
        ctx.roundRect(midX - pw / 2, midY - ph / 2, pw, ph, ph / 2)
        ctx.fill()
        ctx.fillStyle = LINK_COLORS[link.kind]
        ctx.fillText(label, midX, midY)
        ctx.restore()
    }, [])

    return (
        <>
            <button
                type="button"
                className={`workspace-toggle-tab tip-right ${isOpen ? 'open' : ''} ${items.length === 0 && !isOpen ? 'pulse-hint' : ''}`}
                onClick={() => setIsOpen(!isOpen)}
                data-tip={items.length === 0 ? 'Investigation Workspace — pin countries, topics & people here' : 'Investigation Workspace'}
                aria-label="Investigation Workspace"
            >
                <FolderKanban size={18} />
            </button>

            <section className={`investigation-workspace workspace-board-shell ${isOpen ? 'workspace-open' : ''}`} aria-label="Interactive investigation workspace">
                <header className="workspace-header workspace-board-header">
                    <div>
                        <h2>
                            <Network size={16} color="#10b981" />
                            Narrative Intelligence Workspace Board
                        </h2>
                        <p>{activeNodeCount} nodes · {activeLinkCount} relationships</p>
                    </div>
                    <div className="workspace-header-actions">
                        {graphLoading && (
                            <span className="workspace-loading" data-tip="Refreshing graph relationships">
                                <Loader2 size={14} />
                            </span>
                        )}
                        <button
                            type="button"
                            className={`workspace-icon-btn ${showNotes ? 'active' : ''}`}
                            onClick={() => setShowNotes(value => !value)}
                            data-tip="Show or hide notes panel"
                            aria-label="Show or hide notes panel"
                        >
                            <List size={16} />
                        </button>
                        <button
                            type="button"
                            className="workspace-icon-btn"
                            onClick={exportWorkspace}
                            data-tip="Export Workspace as Markdown"
                            aria-label="Export Workspace as Markdown"
                            disabled={items.length === 0}
                            style={{ opacity: items.length === 0 ? 0.5 : 1 }}
                        >
                            <Download size={16} />
                        </button>
                        <button
                            type="button"
                            className="workspace-icon-btn"
                            onClick={() => setIsOpen(false)}
                            data-tip="Close Workspace"
                            aria-label="Close Workspace"
                        >
                            <X size={16} />
                        </button>
                    </div>
                </header>

                <div className="workspace-board-layout">
                    <aside className="workspace-filter-rail" aria-label="Workspace graph filters">
                        <div className="workspace-filter-heading">
                            <Filter size={13} />
                            Filter Graph
                        </div>
                        <label className="workspace-search">
                            <Search size={13} />
                            <input
                                value={query}
                                onChange={event => setQuery(event.target.value)}
                                placeholder="Filter graph"
                            />
                        </label>

                        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#cbd5e1', cursor: 'pointer', padding: '0 4px', marginBottom: '16px' }}>
                            <input
                                type="checkbox"
                                checked={showSessionTrail}
                                onChange={e => setShowSessionTrail(e.target.checked)}
                                style={{ accentColor: '#10b981', cursor: 'pointer' }}
                            />
                            Show Session Trail
                        </label>

                        <div className="workspace-filter-group">
                            <span>Node types</span>
                            {WORKSPACE_NODE_TYPES.map(type => (
                                <button
                                    key={type}
                                    type="button"
                                    className={`workspace-filter-chip ${nodeTypes.has(type) ? 'active' : ''}`}
                                    onClick={() => setNodeTypes(current => toggleSetValue(current, type))}
                                >
                                    <span style={{ background: NODE_COLORS[type] }} />
                                    {type}
                                </button>
                            ))}
                        </div>

                        <div className="workspace-filter-group">
                            <span>Relationships</span>
                            {WORKSPACE_LINK_KINDS.map(kind => (
                                <button
                                    key={kind}
                                    type="button"
                                    className={`workspace-filter-chip link-kind ${linkKinds.has(kind) ? 'active' : ''}`}
                                    onClick={() => setLinkKinds(current => toggleSetValue(current, kind))}
                                >
                                    <span style={{ background: LINK_COLORS[kind] }} />
                                    {formatFilterLabel(kind)}
                                </button>
                            ))}
                        </div>

                        {graphError && (
                            <div className="workspace-graph-warning">
                                Some relationships could not load.
                            </div>
                        )}
                    </aside>

                    <main className="workspace-graph-stage" ref={boardRef}>
                        {items.length === 0 ? (
                            <div className="workspace-empty workspace-empty-board">
                                <FolderKanban size={24} />
                                <p>Your workspace is empty.</p>
                                <p style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap', justifyContent: 'center' }}>
                                    Click any <Pin size={13} style={{ color: '#94a3b8', flexShrink: 0 }} /> icon inside a country, topic, or person panel to add it here.
                                </p>
                            </div>
                        ) : filteredGraph.nodes.length === 0 ? (
                            <div className="workspace-empty workspace-empty-board">
                                <Filter size={24} />
                                <p>No nodes match this filter.</p>
                                <p>Clear the search box or re-enable node and relationship filters.</p>
                            </div>
                        ) : (
                            <ForceGraph2D<WorkspaceGraphNode, WorkspaceGraphLink>
                                ref={graphRef}
                                graphData={filteredGraph}
                                width={boardSize.width}
                                height={boardSize.height}
                                nodeId="id"
                                nodeVal={node => Math.max(8, Math.log10((node.weight || 1) + 10) * 5)}
                                nodeCanvasObject={drawWorkspaceNode}
                                nodePointerAreaPaint={(node, color, ctx) => {
                                    ctx.fillStyle = color
                                    ctx.fillRect((node.x ?? 0) - 70, (node.y ?? 0) - 24, 140, 48)
                                }}
                                linkColor={link => LINK_COLORS[link.kind]}
                                linkWidth={link => Math.max(1, Math.min(4, Math.log10((link.weight || 1) + 1)))}
                                linkDirectionalParticles={link => link.weight > 10 ? 1 : 0}
                                linkDirectionalParticleSpeed={0.003}
                                linkDirectionalParticleWidth={1.5}
                                linkCanvasObjectMode={() => 'after'}
                                linkCanvasObject={drawLinkLabel}
                                cooldownTicks={150}
                                d3AlphaDecay={0.015}
                                d3VelocityDecay={0.22}
                                backgroundColor="rgba(0,0,0,0)"
                                onNodeClick={node => {
                                    if (node.urlParams) onNavigate(node.urlParams)
                                }}
                                nodeLabel={node => `${node.title} (${node.type})`}
                                linkLabel={link => formatFilterLabel(link.kind)}
                            />
                        )}
                    </main>

                    {showNotes && (
                        <aside className="workspace-notes-panel" aria-label="Pinned workspace items">
                            <div className="workspace-notes-header">
                                <div className="workspace-side-tabs" role="tablist" aria-label="Workspace side panel">
                                    <button
                                        type="button"
                                        className={sidePanelMode === 'trail' ? 'active' : ''}
                                        onClick={() => setSidePanelMode('trail')}
                                    >
                                        Trail
                                        <span>{sessionItems.length}</span>
                                    </button>
                                    <button
                                        type="button"
                                        className={sidePanelMode === 'pinned' ? 'active' : ''}
                                        onClick={() => setSidePanelMode('pinned')}
                                    >
                                        Pinned
                                        <span>{items.length}</span>
                                    </button>
                                </div>
                            </div>
                            <div className="workspace-content workspace-list-content">
                                {sidePanelMode === 'trail' ? (
                                    sessionItems.length === 0 ? (
                                        <div className="workspace-empty">
                                            <p>No trail yet.</p>
                                            <p style={{ marginTop: '8px', opacity: 0.7 }}>Open countries, topics, people, sources, or public attention items to build a path.</p>
                                        </div>
                                    ) : (
                                        <div className="workspace-trail-list">
                                            {[...sessionItems].reverse().map((item, index) => {
                                                const pinned = items.some(p => p.id === item.id)
                                                const originAttention = item.meta?.originAttention
                                                return (
                                                    <article key={`${item.id}-${item.timestamp}`} className="workspace-trail-item">
                                                        <span className="workspace-trail-index">{String(index + 1).padStart(2, '0')}</span>
                                                        <div className="workspace-trail-body">
                                                            <span className="workspace-item-type">{formatFilterLabel(item.type)}</span>
                                                            <button
                                                                type="button"
                                                                className="workspace-trail-title"
                                                                onClick={() => onNavigate(item.urlParams)}
                                                            >
                                                                {item.title}
                                                            </button>
                                                            {Boolean(originAttention) && (
                                                                <span className="workspace-trail-origin">from {String(originAttention)}</span>
                                                            )}
                                                        </div>
                                                        <div className="workspace-item-actions">
                                                            <button
                                                                type="button"
                                                                className="workspace-action-btn"
                                                                onClick={() => onNavigate(item.urlParams)}
                                                                data-tip="Open trail point"
                                                                aria-label={`Open ${item.title}`}
                                                            >
                                                                <ExternalLink size={14} />
                                                            </button>
                                                            <button
                                                                type="button"
                                                                className="workspace-action-btn"
                                                                disabled={pinned}
                                                                onClick={() => {
                                                                    if (!pinned) {
                                                                        pinItem({
                                                                            id: item.id,
                                                                            type: item.type,
                                                                            title: item.title,
                                                                            urlParams: item.urlParams,
                                                                            meta: item.meta,
                                                                        })
                                                                    }
                                                                }}
                                                                data-tip={pinned ? 'Already pinned' : 'Pin this trail point'}
                                                                aria-label={`Pin ${item.title}`}
                                                                style={{ opacity: pinned ? 0.45 : 1 }}
                                                            >
                                                                <Pin size={14} />
                                                            </button>
                                                        </div>
                                                    </article>
                                                )
                                            })}
                                        </div>
                                    )
                                ) : items.length === 0 ? (
                                    <div className="workspace-empty">
                                        <p>Nothing pinned yet.</p>
                                        <p style={{ marginTop: '8px', opacity: 0.7 }}>Pinned items appear here with notes and export controls.</p>
                                    </div>
                                ) : (
                                    items.map(item => (
                                        <article key={item.id} className="workspace-item">
                                            <div className="workspace-item-header">
                                                <div className="workspace-item-title-area">
                                                    <span className="workspace-item-type">{formatFilterLabel(item.type)}</span>
                                                    <span className="workspace-item-title">{item.title}</span>
                                                </div>
                                                <div className="workspace-item-actions">
                                                    <button
                                                        type="button"
                                                        className="workspace-action-btn"
                                                        onClick={() => onNavigate(item.urlParams)}
                                                        data-tip="Open in View"
                                                        aria-label={`Open ${item.title}`}
                                                    >
                                                        <ExternalLink size={14} />
                                                    </button>
                                                    <button
                                                        type="button"
                                                        className="workspace-action-btn unpin"
                                                        onClick={() => unpinItem(item.id)}
                                                        data-tip="Unpin"
                                                        aria-label={`Unpin ${item.title}`}
                                                    >
                                                        <PinOff size={14} />
                                                    </button>
                                                </div>
                                            </div>
                                            <div className="workspace-item-notes">
                                                <textarea
                                                    className="workspace-textarea"
                                                    placeholder="Add investigative notes..."
                                                    value={item.notes}
                                                    onChange={event => updateNotes(item.id, event.target.value)}
                                                />
                                            </div>
                                        </article>
                                    ))
                                )}
                            </div>
                        </aside>
                    )}
                </div>
            </section>
        </>
    )
}
