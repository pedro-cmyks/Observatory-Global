import { useEffect, useMemo, useRef, useState } from 'react'
import { trackOnce } from '../lib/telemetry'
import { resolveThreadLabel } from '../lib/themeLabels'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { threadPin } from '../lib/capturePayloads'
import {
    bornBetween,
    categoryColor,
    cloudCenter,
    depthAlpha,
    depthScale,
    edgeOpacity,
    entitySpread,
    fastestRising,
    heatHalo,
    isOrphan,
    isSurging,
    litNodeIds,
    positionAt,
    universeAlpha,
    universeRadius,
    applyRot,
    type UniverseEdge,
    type UniverseNode,
} from '../lib/universeLayout'
import { useTrackball } from '../hooks/useTrackball'
import { useEclipseMode } from '../contexts/EclipseModeContext'
import { buildEclipseSets, eclipseTopicColor, ECLIPSE_COLOR, SHADOW_COLOR } from '../lib/eclipseSets'
import { PERSPECTIVE_FLOOR } from '../lib/mds3d'
import { ConstellationThreadView } from './ConstellationThreadView'
import { LoadingMoment } from './LoadingMoment'
import { LabelReviewChip } from '../lib/labelReviewChip'
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
    /** Item 8: the node's real label rides along so the focus chip never
     *  stores/falls back to the generic "Narrative Thread" skeleton. */
    onThemeSelect: (themeId: string, label?: string) => void
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
    // One-gesture ◆ capture (Exploration Flywheel 3.2): a hovered body IS a
    // thread/story — pin it straight into the active investigation.
    const { pinItem, unpinItem, isPinned } = useWorkspace()
    const [payload, setPayload] = useState<UniversePayload | null>(null)
    const [loading, setLoading] = useState(true)
    const [scrubPct, setScrubPct] = useState(100)
    const [hoveredId, setHoveredId] = useState<string | null>(null)
    // Universe's OWN classifiers (not the globe's HEAT/FLOW): filter the field
    // by what matters semantically here.
    const [crisisOnly, setCrisisOnly] = useState(false)
    const [orphansOnly, setOrphansOnly] = useState(false)
    // crisis_dynamics lens (2026-07-04 reframe): SURGING = measured movement
    // state from the shared Kalman field — crisis as dynamics, not category.
    const [surgingOnly, setSurgingOnly] = useState(false)
    // Travel state: when a thread is open we are AT its orbit; back returns to the field.
    const [orbitalVisible, setOrbitalVisible] = useState(false)
    const [traveling, setTraveling] = useState(false)
    // Camera state (rotation matrix + zoom/pan) and every gesture ref now live
    // in `useTrackball` — the ONE gesture layer shared with the story
    // constellation and the investigation cloud. Rotation stays an accumulated
    // 3x3 matrix about the cloud's center of MASS (spec §7.2/§7.4, Pedro
    // 2026-07-03 "roll disponible 3D... para donde sea"): no gimbal lock, no
    // clamp, any orientation.
    // Nav mode: drag ROTATES by default (fly around), or PANS (drag the cloud
    // across the screen). Two-finger touch always pans+zooms regardless.
    const [navMode, setNavMode] = useState<'rotate' | 'pan' | 'roll'>('rotate')
    const containerRef = useRef<HTMLDivElement | null>(null)
    const [size, setSize] = useState({ w: 1200, h: 700 })

    // Hover-exit grace period: the hover card renders at a FIXED corner, far
    // from the tiny body circle that triggers it. Without this, moving the
    // mouse toward the card's ◆ pin button leaves the body's hit-region on the
    // very first pixel of travel — onMouseLeave fires immediately and the card
    // (with the button) unmounts before the pointer arrives. A short delay,
    // cancelled by the card's own onMouseEnter, bridges body → card the same
    // way any hover-tooltip-with-a-button does.
    const hoverExitTimerRef = useRef<number | null>(null)
    const cancelHoverExit = () => {
        if (hoverExitTimerRef.current !== null) {
            window.clearTimeout(hoverExitTimerRef.current)
            hoverExitTimerRef.current = null
        }
    }
    const clearHoverSoon = (id: string) => {
        cancelHoverExit()
        hoverExitTimerRef.current = window.setTimeout(() => {
            setHoveredId(h => (h === id ? null : h))
        }, 220)
    }

    // Ambient spin, THERMALLY POLITE (2026-07-03 kernel panic post-mortem:
    // WindowServer watchdog timeout — a 60fps React re-render of 348 SVG
    // bodies contributes exactly that kind of compositor load) — now owned by
    // useTrackball: ~10fps yaw, stopped while the orbital view covers the field
    // (`ambient: !orbitalVisible`), while a hover card is open (`paused`),
    // while dragging, while the tab OR the panel is hidden, and after 90s of
    // rest. The hook's draggingRef independently holds the spin during a drag
    // so a hover-leave mid-drag never resumes it.

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

    // Reliability (council P1-6 / wish 19): /api/v2/universe intermittently
    // dies mid-flight (ERR_ABORTED). One automatic retry after a short beat,
    // then an HONEST failed state with a RETRY button (loadNonce re-arms this
    // effect) — never a dead "unavailable" wall with no way back.
    const [loadNonce, setLoadNonce] = useState(0)
    useEffect(() => {
        let cancelled = false
        // Timeout so a slow cache-miss (heavy PCA + neighbor build server-side)
        // surfaces as an empty state instead of an endless "Assembling…" spinner.
        const ctrl = new AbortController()
        setLoading(true)
        setPayload(null)
        const timer = setTimeout(() => ctrl.abort(), 20000)
        const attempt = (n: number): Promise<UniversePayload> =>
            fetch('/api/v2/universe', { signal: ctrl.signal })
                .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
                .catch(err => {
                    if (cancelled || ctrl.signal.aborted || n >= 1) throw err
                    return new Promise(res => setTimeout(res, 800)).then(() => attempt(n + 1))
                })
        attempt(0)
            .then(json => { if (!cancelled) setPayload(json) })
            .catch(() => { if (!cancelled) setPayload(null) })
            .finally(() => { if (!cancelled) { clearTimeout(timer); setLoading(false) } })
        return () => { cancelled = true; clearTimeout(timer); ctrl.abort() }
    }, [loadNonce])

    const allNodes = useMemo(() => payload?.nodes ?? [], [payload])
    const nodes = useMemo(
        () => allNodes.filter(n =>
            (!crisisOnly || n.crisis_relevant === true)
            && (!orphansOnly || isOrphan(n))
            && (!surgingOnly || isSurging(n)),
        ),
        [allNodes, crisisOnly, orphansOnly, surgingOnly],
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

    /* ECLIPSE LENS: when the reader ENTERED a total eclipse, the field recolors by
       MEMBERSHIP instead of category — the dominant story + its measured neighbours
       burn eclipse-red, the rest of the world reads shadow-cyan. Both stay fully
       visible (no dimming): the point is to SEE how big the eclipse is. Outside the
       lens this is null and every fill falls back to categoryColor, byte-identical. */
    const { mode: eclipseMode, data: eclipseData } = useEclipseMode()
    const eclipseSets = useMemo(() => {
        if (eclipseMode !== 'ambient' || !eclipseData?.dominant?.topic_id) return null
        const domId = eclipseData.dominant.topic_id
        const neighbors: string[] = []
        for (const e of edges) {
            if (e.a === domId) neighbors.push(e.b)
            else if (e.b === domId) neighbors.push(e.a)
        }
        return buildEclipseSets(eclipseData, neighbors)
    }, [eclipseMode, eclipseData, edges])

    // hitTestBody is defined below (it needs `projected`); route the tap through
    // a ref so the hook can be constructed before it.
    const tapRef = useRef<(lx: number, ly: number) => void>(() => {})
    // The ONE gesture layer (shared with the story + investigation clouds).
    // Ambient spin stops while a story system covers the field.
    const trackball = useTrackball({
        containerRef,
        navMode,
        minZoom: 0.6, maxZoom: 8, wheelStep: 1.12,
        ambient: !orbitalVisible,
        paused: hoveredId !== null,
        onTap: (lx, ly) => tapRef.current(lx, ly),
    })
    // (setRot stays on the hook for other consumers; every rotation write in
    // this view is a gesture, so the component only READS `rot`.)
    const { rot, view, setView } = trackball

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

    // Shared projection: free two-axis rotation about the mass center, then a
    // PERSPECTIVE divide using the real depth (Pedro 2026-07-03 "como en el
    // espacio": zoom in and your planet grows while the rest recedes toward the
    // distance). Perspective strengthens with zoom; at k=1 it's orthographic
    // (the honest map). `scale` = the per-body size/spread factor (near > 1,
    // far < 1). Positions stay a labeled approximation — this is a camera.
    const perspSpread = Math.min(1.6, Math.max(0, (view.k - 1) * 0.8))
    const project3 = (x: number, y: number, z: number | undefined) => {
        const p = applyRot(rot, x, y, z, massX, massY, massZ)
        // Floor the divisor: past spread ≈ 0.833 a near body drives it through
        // zero and the body mirrors through the cloud centre with a negative
        // radius (invalid SVG, and unclickable). Same guard as mds3d's.
        const scale = 1 / Math.max(PERSPECTIVE_FLOOR, 1 + (p.depth - 0.5) * 2.4 * perspSpread)
        const pxp = 0.5 + (p.px - 0.5) * scale
        const pyp = 0.5 + (p.py - 0.5) * scale
        return { sx: px(pxp), sy: py(pyp), depth: p.depth, scale }
    }

    const projected = useMemo(() => {
        const out = new Map<string, { sx: number; sy: number; depth: number; scale: number }>()
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

    // Hit-test a click at canvas-local (lx,ly) → the nearest visible body whose
    // rendered disk covers the point (nearest depth wins on overlap).
    const hitTestBody = (lx: number, ly: number): string | null => {
        let best: { id: string; depth: number } | null = null
        for (const n of nodes) {
            const p = projected.get(n.id)
            if (!p) continue
            const r = universeRadius(n.n) * Math.min(3.5, Math.max(0.8, view.k)) * depthScale(p.depth) * (p.scale ?? 1)
            if (Math.hypot(lx - p.sx, ly - p.sy) <= r + 6) {
                // NEAREST wins: depth 0 is closest, and depthOrdered paints
                // largest-depth first (underneath) — so picking the larger depth
                // opened the body hidden BEHIND the one you clicked.
                if (!best || p.depth < best.depth) best = { id: n.id, depth: p.depth }
            }
        }
        return best?.id ?? null
    }

    // A tap that didn't drag = a CLICK → open the body under the pointer.
    // Pointer-capture eats the SVG <g> onClick, so the hook hit-tests through
    // here (works for mouse AND touch). Fixes "click does nothing" (Pedro
    // 2026-07-03 — free-nav regression).
    tapRef.current = (lx: number, ly: number) => {
        const hit = hitTestBody(lx, ly)
        // Clicking the ALREADY-open thread re-enters its system (onThemeSelect
        // no-ops when the theme is unchanged, so the same node felt "dead").
        if (hit && hit === activeTheme) setOrbitalVisible(true)
        // Item 8: pass the node's REAL label with the id — the opener knows it;
        // downstream must never re-derive a generic from the raw id.
        else if (hit) onThemeSelect(hit, allNodes.find(n => n.id === hit)?.label)
    }

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
    // Fastest-rising stories — relative changed_10h (the shared movement
    // signal), RANK-based so a thin/fresh corpus can't saturate it.
    const heating = useMemo(() => fastestRising(nodes), [nodes])
    const heatingIds = useMemo(() => new Set(heating.map(n => n.id)), [heating])
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

    if (loading) {
        return (
            <div className="universe-empty">
                <div>Charting the universe…</div>
                <LoadingMoment compact />
            </div>
        )
    }
    if (!payload || allNodes.length === 0) {
        return (
            <div className="universe-empty">
                <div>Universe data unavailable{payload?.reason ? ` (${payload.reason})` : ''}.</div>
                <div className="universe-empty-note">
                    {payload
                        ? 'The endpoint answered but served no stories for this window.'
                        : 'The field endpoint did not answer (already retried once).'}
                </div>
                <button
                    className="universe-filter universe-retry"
                    onClick={() => setLoadNonce(n => n + 1)}
                    data-tip="Re-request /api/v2/universe"
                >
                    ↻ RETRY
                </button>
            </div>
        )
    }

    // AT an orbit: the story system replaces the field until back/close.
    if (activeTheme && orbitalVisible) {
        const fieldLabel = allNodes.find(n => n.id === activeTheme)?.label
        // #204 rule: never echo a raw dynamic-topic id as the orbit title.
        const orbitLabel = fieldLabel ?? activeThemeLabel ?? resolveThreadLabel(activeTheme)
        return (
            <div className="universe-root">
                <div className="universe-orbit-bar">
                    <button
                        className="universe-orbit-back"
                        onClick={() => {
                            setOrbitalVisible(false)
                            // Frame the open thread's body in the FIELD at a
                            // moderate zoom so you see WHERE it sits in the
                            // world, highlighted (Pedro 2026-07-03 — "la
                            // conexión más grande").
                            const body = allNodes.find(n => n.id === activeTheme)
                            if (body) {
                                const p = applyRot(rot, body.x, body.y, body.z, massX, massY, massZ)
                                const tx0 = margin + p.px * (size.w - 2 * margin)
                                const ty0 = margin + p.py * (size.h - 2 * margin)
                                const k = 1.5
                                setView({ k, tx: size.w / 2 - tx0 * k, ty: size.h / 2 - ty0 * k })
                            }
                        }}
                        data-tip="Back to the field — see where this story sits in the world"
                    >
                        ← UNIVERSE
                    </button>
                    <span className="universe-orbit-title">{orbitLabel}</span>
                    {/* P1-4: signpost that the node FILL encoding changed on
                        travel — category (field) → subject type (inside a story). */}
                    <span
                        className="universe-orbit-note"
                        data-tip="Inside a story, stars are colored by SUBJECT TYPE (person / org / place / event / country), not by narrative category as in the field."
                    >
                        colors = subject type
                    </span>
                </div>
                <div className="universe-orbit-body">
                    <ConstellationThreadView
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
                    className={`universe-filter ${surgingOnly ? 'active' : ''}`}
                    onClick={() => setSurgingOnly(v => !v)}
                    data-tip="Crisis as DYNAMICS: stories whose measured movement (Kalman velocity/trend) is surging right now — regardless of content"
                >
                    SURGING
                </button>
                <button
                    className={`universe-filter ${crisisOnly ? 'active' : ''}`}
                    onClick={() => setCrisisOnly(v => !v)}
                    data-tip="Harm-potential lens (semantic flag, R3.1) — content judged crisis-relevant; independent of current movement"
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
                        data-tip="Return to the open story's constellation"
                    >
                        ◉ TO STORY
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
                        className="universe-filter"
                        onClick={trackball.reset}
                        data-tip="Reset the camera: rotation, pan and zoom back to the default view. (Roll still available: alt-drag or two-finger twist)"
                    >
                        ⌖ RESET
                    </button>
                </span>
            </div>
            <div
                className={`universe-canvas${traveling ? ' universe-canvas--traveling' : ''}`}
                ref={attachCanvas}
                {...trackball.handlers}
            >
                <svg width={size.w} height={size.h} role="img" aria-label="Atlas story universe">
                    <defs>
                        <radialGradient id="universe-heat-halo" cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stopColor="#fb923c" stopOpacity="0.55" />
                            <stop offset="45%" stopColor="#f97316" stopOpacity="0.22" />
                            <stop offset="100%" stopColor="#f97316" stopOpacity="0" />
                        </radialGradient>
                        <radialGradient id="universe-active-glow" cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stopColor="#34d399" stopOpacity="0.5" />
                            <stop offset="55%" stopColor="#34d399" stopOpacity="0.14" />
                            <stop offset="100%" stopColor="#34d399" stopOpacity="0" />
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
                                /* family palette returns a var() expression — SVG
                                   presentation attrs don't substitute var(), so style. */
                                style={{ stroke: categoryColor(n.category) }}
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
                        // lens echo: an edge INSIDE the eclipse set burns with it
                        const eclipseEdge = Boolean(eclipseSets
                            && eclipseSets.eclipseTopics.has(e.a) && eclipseSets.eclipseTopics.has(e.b))
                        return (
                            <line
                                key={`${e.a}-${e.b}`}
                                x1={pa.sx} y1={pa.sy} x2={pb.sx} y2={pb.sy}
                                /* var() never substitutes in an SVG presentation attr — style it. */
                                style={{ stroke: eclipseEdge ? ECLIPSE_COLOR : '#7dd3fc' }}
                                /* U1 (dataviz audit): the field's claim is "relations exact", so
                                   idle edges must be faintly VISIBLE, not hover-only — floor the
                                   sim×depth part at 0.08 (scrub birth/decay alpha still applies,
                                   so dying nodes' edges keep fading honestly). Hover keeps 0.02
                                   de-emphasis as the contrast state. */
                                strokeOpacity={highlighted ? Math.max(0.08, edgeOpacity(e.sim) * depthDim) * Math.min(aa, ab) : 0.02}
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
                        const r = universeRadius(n.n) * Math.min(3.5, Math.max(0.8, view.k)) * depthScale(p.depth) * (p.scale ?? 1)
                        return (
                            <g
                                key={n.id}
                                className="universe-body"
                                opacity={(dimmed && !isActive && !lit ? 0.08 : Math.max(alpha, isActive || lit ? 0.95 : 0)) * depthAlpha(p.depth)}
                                onMouseEnter={() => { cancelHoverExit(); trackball.noteInteraction(); setHoveredId(n.id) }}
                                onMouseLeave={() => clearHoverSoon(n.id)}
                            >
                                {heatingIds.has(n.id) && !dimmed && (
                                    <circle
                                        cx={p.sx} cy={p.sy}
                                        r={r * heatHalo(n.velocity)}
                                        fill="url(#universe-heat-halo)"
                                        pointerEvents="none"
                                    />
                                )}
                                {isActive && (
                                    <>
                                        <circle cx={p.sx} cy={p.sy} r={r + 16} fill="url(#universe-active-glow)" pointerEvents="none" />
                                        <circle cx={p.sx} cy={p.sy} r={r + 5} fill="none" stroke="rgba(52, 211, 153, 0.95)" strokeWidth={2} />
                                        <circle cx={p.sx} cy={p.sy} r={r + 9} fill="none" stroke="rgba(52, 211, 153, 0.4)" strokeWidth={1} />
                                        <text x={p.sx} y={p.sy - r - 8} className="universe-active-label">◆ open story</text>
                                    </>
                                )}
                                <circle
                                    cx={p.sx} cy={p.sy}
                                    r={r}
                                    /* eclipse lens: red = the eclipse set, cyan = everything
                                       else (an unlisted body still belongs to "the rest of
                                       the world", so it reads shadow). */
                                    style={{ fill: eclipseSets ? (eclipseTopicColor(n.id, eclipseSets) ?? SHADOW_COLOR) : categoryColor(n.category) }}
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
                                    ? 'This entity sits in one or two stories — a focused, single-story actor'
                                    : 'This entity spans a few narrative categories'}>
                            {spread.shape === 'cross-cutting' ? '◇ cross-cutting' : spread.shape === 'concentrated' ? '◈ concentrated' : '◈ mixed'}
                        </span>
                    </div>
                )}

                {hovered && (
                    <div
                        className="universe-hover"
                        onMouseEnter={cancelHoverExit}
                        onMouseLeave={() => clearHoverSoon(hovered.id)}
                    >
                        <span style={{ color: categoryColor(hovered.category) }}>{hovered.category}</span>
                        <div className="universe-hover-title-row">
                            <strong>
                                {hovered.label}
                                {/* N15: Label Court verdict on the hover card — the ONE shared
                                    chip. Full copy (not the dot): the card tracks the pointer so
                                    its data-tip can never open; the chip must self-explain.
                                    Fires only on failed/partial; entailed/unchecked stay clean. */}
                                <LabelReviewChip labelStatus={hovered.label_status} />
                            </strong>
                            {/* One-gesture ◆ capture (Exploration Flywheel 3.2): a universe
                                body IS a thread/story — pin it straight into the active
                                investigation. stopPropagation on pointerdown/up (not just
                                click) because the canvas' own drag/click-to-open gesture is
                                driven by bubbled pointer events + coordinate hit-testing, not
                                a React onClick on the body — letting them bubble would both
                                start a drag from this button AND risk hit-testing straight
                                into opening the story underneath. */}
                            <button
                                className={`universe-hover-pin${isPinned(`theme-${hovered.id}`) ? ' universe-hover-pin--active' : ''}`}
                                data-tip={isPinned(`theme-${hovered.id}`) ? 'Unpin from investigation' : 'Pin to investigation'}
                                onPointerDown={e => e.stopPropagation()}
                                onPointerUp={e => e.stopPropagation()}
                                onClick={e => {
                                    e.stopPropagation()
                                    const pinId = `theme-${hovered.id}`
                                    if (isPinned(pinId)) unpinItem(pinId)
                                    else pinItem(threadPin(hovered.id, hovered.label))
                                }}
                            >
                                {isPinned(`theme-${hovered.id}`) ? '◆' : '◇'}
                            </button>
                        </div>
                        <em>{hovered.n.toLocaleString()} signals{isSurging(hovered) ? ' · SURGING' : ''}{hovered.crisis_relevant ? ' · crisis-relevant' : ''}{isOrphan(hovered) ? ' · ORPHAN (unlike every other story)' : ''}</em>
                        <em>
                            {hovered.first_seen ? new Date(hovered.first_seen).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '—'}
                            {' → '}
                            {hovered.last_seen ? new Date(hovered.last_seen).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '—'}
                        </em>
                        <em className="universe-hover-cta">click to open its story system</em>
                        {heatingIds.has(hovered.id) && <em className="universe-hover-heat">{hovered.trend ? hovered.trend : 'rising'} · movement {(hovered.velocity ?? 0).toFixed(2)}</em>}
                    </div>
                )}

                {/* P1-8: copy aligned to the real basis (Kalman-first, changed_10h fallback) */}
                {!litActive && heating.length > 0 && (
                    <div className="universe-heating-readout" data-tip="Fastest-rising stories now, by MEASURED movement: the shared Kalman velocity (topic_movement) where a story has one, otherwise its recent signal-change as a fallback — squashed to a comparable scale. One movement number, honestly labeled; measured, not a prediction.">
                        <span className="universe-heating-count">
                            <svg width="9" height="11" viewBox="0 0 9 11" aria-hidden="true" style={{ marginRight: 5, verticalAlign: '-1px' }}>
                                {/* upward spark — rising attention, vector not emoji */}
                                <path d="M4.5 0 L9 5.5 L6 5 L7 11 L4.5 7 L2 11 L3 5 L0 5.5 Z" fill="#fb923c" />
                            </svg>
                            Fastest rising
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
                    onChange={e => { trackOnce('scrubber_used', { surface: 'universe' }); setScrubPct(Number(e.target.value)) }}
                    aria-label="Universe time scrubber"
                    data-tip="Scrub time: stories are born, burn, and fade across the field"
                />
                <span className="universe-scrubber-stats" data-tip="Stories alive at the scrubbed moment · stories born in the trailing 7 days">
                    {aliveCount} alive · {newThisWeek} born this week
                </span>
            </div>

            <div className="universe-legend">
                <span data-tip="Node fill = the story's narrative CATEGORY (family palette). Opening a story recolors its members by SUBJECT TYPE (person / org / place / event / country) — the fill encodes a different variable inside a single story.">fill = category</span>
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
