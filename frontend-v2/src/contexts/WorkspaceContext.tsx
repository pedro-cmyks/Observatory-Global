/* eslint-disable react-refresh/only-export-components */
// W1 (L3 deep review 2026-07-05): ONE investigation store.
//
// This context used to be a SECOND pin system (PinnedItem + force-graph over
// localStorage 'atlas-workspace') living beside the Workbench — pins from L2
// panels never reached the dossier, research-plan pins never reached the
// panels. It is now a thin ADAPTER over the Workbench investigation store
// (lib/workbench.ts): every pin is a WorkbenchPin with a #227 frozen snapshot,
// visible in WorkbenchPanel and DossierView. The force-graph canvas was
// RETIRED (decision D1 — the universe view superseded it as the spatial
// surface); the legacy 'atlas-workspace' store is dropped on load (D5).
import { createContext, useContext, useState, useEffect, useMemo, useCallback, useRef, type ReactNode, type Dispatch, type SetStateAction } from 'react'
import {
    addPin as wbAddPin,
    createInvestigation,
    getActiveInvestigationId,
    getInvestigation,
    recordTrail,
    removePin as wbRemovePin,
    updatePinNote,
    updatePinSnapshot,
    type PinSnapshot,
} from '../lib/workbench'
import { extractSnapshotEvidence } from '../lib/pinEvidence'

export type PinnedItemType = 'theme' | 'person' | 'country' | 'signal' | 'source' | 'chokepoint' | 'public_attention' | 'temporal_snapshot'

/** Compatibility shape for the panel pin affordances (ThemeDetail,
 *  CountryBrief, EntityPanel, SourceProfile, PublicAttentionPanel,
 *  SignalStream). Persisted as a WorkbenchPin, not as this shape. */
export interface PinnedItem {
    id: string
    type: PinnedItemType
    title: string
    urlParams: string // the query string to restore this view, e.g. "?theme=ARMEDCONFLICT"
    notes: string
    timestamp: number
    meta?: Record<string, unknown>
}

interface WorkspaceContextType {
    /** Workbench overlay visibility (the ONE L3 home). */
    isOpen: boolean
    setIsOpen: Dispatch<SetStateAction<boolean>>
    /** Pins of the ACTIVE investigation, in the legacy PinnedItem shape. */
    items: PinnedItem[]
    pinItem: (item: Omit<PinnedItem, 'notes' | 'timestamp'>) => void
    unpinItem: (id: string) => void
    updateNotes: (id: string, notes: string) => void
    isPinned: (id: string) => boolean
    trackVisit: (item: Omit<PinnedItem, 'notes' | 'timestamp'>) => void
    /** Bumps on every store mutation — pass into refresh tokens. */
    version: number
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null)
const SNAPSHOT_HOURS = 24

function getParam(urlParams: string, key: string): string | null {
    return new URLSearchParams(urlParams.replace(/^\?/, '')).get(key)
}

function pinnedValue(item: Omit<PinnedItem, 'notes' | 'timestamp'>): string {
    if (item.type === 'theme') return getParam(item.urlParams, 'theme') || item.id.replace(/^theme-/, '')
    if (item.type === 'country') return getParam(item.urlParams, 'country') || item.id.replace(/^country-/, '')
    if (item.type === 'source') return getParam(item.urlParams, 'source') || item.id.replace(/^source-/, '')
    if (item.type === 'person') return getParam(item.urlParams, 'person') || item.id.replace(/^person-/, '')
    if (item.type === 'public_attention') return getParam(item.urlParams, 'attention') || item.id.replace(/^public-attention-/, '')
    return item.id
}

/** #227 for panel pins: freeze what the analyst saw. Tolerant extractor over
 *  the per-surface detail payloads — a failed fetch still leaves a minimal
 *  snapshot (label + capturedAt), never blocks the pin. */
async function fetchPanelSnapshot(item: Omit<PinnedItem, 'notes' | 'timestamp'>): Promise<PinSnapshot | null> {
    const value = pinnedValue(item)
    if (!value || item.type === 'signal' || item.type === 'chokepoint' || item.type === 'temporal_snapshot') return null

    let url: string | null = null
    if (item.type === 'theme') url = `/api/v2/theme/${encodeURIComponent(value)}?hours=${SNAPSHOT_HOURS}`
    else if (item.type === 'country') url = `/api/v2/country/${encodeURIComponent(value)}?hours=${SNAPSHOT_HOURS}`
    else if (item.type === 'person') url = `/api/v2/focus?${new URLSearchParams({ focus_type: 'person', value, hours: String(SNAPSHOT_HOURS) })}`
    else if (item.type === 'source') url = `/api/v2/source/${encodeURIComponent(value)}/profile?hours=${SNAPSHOT_HOURS}`
    else if (item.type === 'public_attention') url = `/api/v2/search/unified?q=${encodeURIComponent(value)}&hours=${SNAPSHOT_HOURS}`
    if (!url) return null

    const response = await fetch(url)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const json = await response.json() as Record<string, unknown>

    // Evidence: shared tolerant extractor — prefers gate-verified/top-score
    // rows over merely-recent ones when the payload carries those fields
    // (freeze the CORE of the thread, not its latest drift).
    const evidence = extractSnapshotEvidence(json)

    const metrics: Record<string, string | number> = {}
    for (const key of ['total', 'signalCount', 'signal_count', 'gated_signal_count']) {
        const v = json[key]
        if (typeof v === 'number') { metrics[key] = v; break }
    }

    const count = Object.values(metrics)[0]
    return {
        capturedAt: new Date().toISOString(),
        summary: `${item.title} · ${item.type}${count !== undefined ? ` · ${count} signals` : ''}`,
        metrics,
        evidence,
    }
}

function toWorkbenchPin(item: Omit<PinnedItem, 'notes' | 'timestamp'>) {
    return {
        anchorId: item.id,
        anchorType: item.type,
        label: item.title,
        open: { surface: 'l2_params', params: { urlParams: item.urlParams } },
        snapshot: { capturedAt: new Date().toISOString(), summary: `${item.title} · ${item.type}` },
    }
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
    const [isOpen, setIsOpen] = useState(false)
    const [version, setVersion] = useState(0)
    const lastTrailRef = useRef<string | null>(null)

    // D5 (2026-07-05): drop the legacy second store. Pins were per-browser
    // localStorage only (never server-side); pre-unification pins are dev-era.
    useEffect(() => {
        try { localStorage.removeItem('atlas-workspace') } catch { /* non-fatal */ }
    }, [])

    const bump = useCallback(() => setVersion(v => v + 1), [])

    const items = useMemo<PinnedItem[]>(() => {
        void version
        const activeId = getActiveInvestigationId()
        const inv = activeId ? getInvestigation(activeId) : null
        if (!inv) return []
        return inv.pins.map(p => ({
            id: p.anchorId,
            type: (p.anchorType as PinnedItemType) ?? 'theme',
            title: p.label,
            urlParams: String((p.open?.params as Record<string, unknown> | undefined)?.urlParams ?? ''),
            notes: p.note ?? '',
            timestamp: Date.parse(p.pinnedAt) || 0,
        }))
    }, [version])

    const ensureInvestigation = useCallback((title: string): string => {
        const activeId = getActiveInvestigationId()
        if (activeId && getInvestigation(activeId)) return activeId
        return createInvestigation(title).id
    }, [])

    const pinItem = useCallback((item: Omit<PinnedItem, 'notes' | 'timestamp'>) => {
        const invId = ensureInvestigation(item.title)
        wbAddPin(invId, toWorkbenchPin(item))
        bump()
        // Enrich the frozen snapshot asynchronously; the pin never waits.
        fetchPanelSnapshot(item)
            .then(snap => { if (snap) { updatePinSnapshot(invId, item.id, snap); bump() } })
            .catch(() => { /* minimal snapshot stays */ })
    }, [bump, ensureInvestigation])

    const unpinItem = useCallback((id: string) => {
        const activeId = getActiveInvestigationId()
        if (!activeId) return
        wbRemovePin(activeId, id)
        bump()
    }, [bump])

    const updateNotes = useCallback((id: string, notes: string) => {
        const activeId = getActiveInvestigationId()
        if (!activeId) return
        updatePinNote(activeId, id, notes)
        bump()
    }, [bump])

    const isPinned = useCallback((id: string) => items.some(i => i.id === id), [items])

    // Visits feed the ACTIVE investigation's trail (deduped against the last
    // step) — no investigation, no trail; we don't record browsing outside an
    // investigation context.
    const trackVisit = useCallback((item: Omit<PinnedItem, 'notes' | 'timestamp'>) => {
        const activeId = getActiveInvestigationId()
        if (!activeId || !getInvestigation(activeId)) return
        if (lastTrailRef.current === item.id) return
        lastTrailRef.current = item.id
        recordTrail(activeId, 'open', item.title)
    }, [])

    return (
        <WorkspaceContext.Provider value={{ isOpen, setIsOpen, items, pinItem, unpinItem, updateNotes, isPinned, trackVisit, version }}>
            {children}
        </WorkspaceContext.Provider>
    )
}

export function useWorkspace() {
    const context = useContext(WorkspaceContext)
    if (!context) throw new Error("useWorkspace must be used within a WorkspaceProvider")
    return context
}
