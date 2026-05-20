/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useMemo, useCallback, type ReactNode } from 'react'
import { buildWorkspaceGraph, type WorkspaceGraph } from '../lib/workspaceGraph'
import { buildWorkspaceMarkdown, buildDossierMarkdown, fetchItemSignals } from '../lib/exportFormatters'

export type PinnedItemType = 'theme' | 'person' | 'country' | 'signal' | 'source' | 'chokepoint' | 'public_attention' | 'temporal_snapshot'

export interface PinnedItem {
    id: string
    type: PinnedItemType
    title: string
    urlParams: string // the query string to restore this view, e.g. "?theme=ARMEDCONFLICT"
    notes: string
    timestamp: number
    meta?: Record<string, unknown> // extra data like country code, signal text, etc.
}

interface WorkspaceContextType {
    isOpen: boolean
    setIsOpen: (open: boolean) => void
    items: PinnedItem[]
    graph: WorkspaceGraph
    graphLoading: boolean
    graphError: string | null
    pinItem: (item: Omit<PinnedItem, 'notes' | 'timestamp'>) => void
    unpinItem: (id: string) => void
    updateNotes: (id: string, notes: string) => void
    isPinned: (id: string) => boolean
    exportWorkspace: () => void
    exportDossier: () => Promise<void>
    sessionItems: PinnedItem[]
    trackVisit: (item: Omit<PinnedItem, 'notes' | 'timestamp'>) => void
    clearSession: () => void
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null)
const WORKSPACE_GRAPH_HOURS = 24

function getParam(item: PinnedItem, key: string): string | null {
    return new URLSearchParams(item.urlParams.replace(/^\?/, '')).get(key)
}

function getPinnedValue(item: PinnedItem): string {
    if (item.type === 'theme') return getParam(item, 'theme') || item.id.replace(/^theme-/, '')
    if (item.type === 'country') return getParam(item, 'country') || item.id.replace(/^country-/, '')
    if (item.type === 'source') return getParam(item, 'source') || item.id.replace(/^source-/, '')
    if (item.type === 'person') return getParam(item, 'person') || item.id.replace(/^person-/, '')
    if (item.type === 'public_attention') return getParam(item, 'attention') || item.id.replace(/^public-attention-/, '')
    return item.id
}

async function fetchWorkspaceDetail(item: PinnedItem, signal: AbortSignal): Promise<unknown | undefined> {
    const value = getPinnedValue(item)
    if (!value || item.type === 'signal' || item.type === 'chokepoint' || item.type === 'temporal_snapshot') return undefined

    let url: string | null = null
    if (item.type === 'theme') {
        url = `/api/v2/theme/${encodeURIComponent(value)}?hours=${WORKSPACE_GRAPH_HOURS}`
    } else if (item.type === 'country') {
        url = `/api/v2/country/${encodeURIComponent(value)}?hours=${WORKSPACE_GRAPH_HOURS}`
    } else if (item.type === 'person') {
        const params = new URLSearchParams({
            focus_type: 'person',
            value,
            hours: String(WORKSPACE_GRAPH_HOURS),
        })
        url = `/api/v2/focus?${params.toString()}`
    } else if (item.type === 'source') {
        url = `/api/v2/source/${encodeURIComponent(value)}/profile?hours=${WORKSPACE_GRAPH_HOURS}`
    } else if (item.type === 'public_attention') {
        url = `/api/v2/search/unified?q=${encodeURIComponent(value)}&hours=${WORKSPACE_GRAPH_HOURS}`
    }

    if (!url) return undefined
    const response = await fetch(url, { signal })
    if (!response.ok) throw new Error(`${item.title}: HTTP ${response.status}`)
    const json = await response.json()
    if (json?.error) throw new Error(`${item.title}: ${json.error}`)
    return json
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
    const [isOpen, setIsOpen] = useState(false)
    const [items, setItems] = useState<PinnedItem[]>(() => {
        try {
            const stored = localStorage.getItem('atlas-workspace')
            return stored ? JSON.parse(stored) as PinnedItem[] : []
        } catch (e) {
            console.error("Failed to load workspace", e)
            return []
        }
    })
    const [details, setDetails] = useState<Record<string, unknown | undefined>>({})
    const [graphLoading, setGraphLoading] = useState(false)
    const [graphError, setGraphError] = useState<string | null>(null)

    const [sessionItems, setSessionItems] = useState<PinnedItem[]>([])

    // Save to localStorage when items change
    useEffect(() => {
        localStorage.setItem('atlas-workspace', JSON.stringify(items))
    }, [items])

    useEffect(() => {
        const allItems = [...items, ...sessionItems];
        const uniqueItems = Array.from(new Map(allItems.map(i => [i.id, i])).values());
        const fetchableItems = uniqueItems.filter(item => item.type !== 'signal' && item.type !== 'chokepoint')
        if (fetchableItems.length === 0) {
            Promise.resolve().then(() => {
                setDetails({})
                setGraphLoading(false)
                setGraphError(null)
            })
            return
        }

        const controller = new AbortController()

        const loadDetails = async () => {
            setGraphLoading(true)
            setGraphError(null)

            try {
                const results = await Promise.all(fetchableItems.map(async item => {
                    try {
                        const detail = await fetchWorkspaceDetail(item, controller.signal)
                        return [item.id, detail] as const
                    } catch (error) {
                        if (controller.signal.aborted) return [item.id, undefined] as const
                        console.warn('Failed to enrich workspace item', error)
                        return [item.id, undefined] as const
                    }
                }))
                if (controller.signal.aborted) return
                setDetails(Object.fromEntries(results))
            } catch (error) {
                if (controller.signal.aborted) return
                setGraphError(error instanceof Error ? error.message : 'Failed to load workspace graph')
            } finally {
                if (!controller.signal.aborted) setGraphLoading(false)
            }
        }

        void loadDetails()

        return () => controller.abort()
    }, [items, sessionItems])

    const pinItem = useCallback((item: Omit<PinnedItem, 'notes' | 'timestamp'>) => {
        setItems(prev => {
            if (prev.find(i => i.id === item.id)) return prev
            return [{ ...item, notes: '', timestamp: Date.now() }, ...prev]
        })
        setIsOpen(true) // auto-open workspace when pinning
    }, [])

    const unpinItem = useCallback((id: string) => {
        setItems(prev => prev.filter(i => i.id !== id))
    }, [])

    const updateNotes = useCallback((id: string, notes: string) => {
        setItems(prev => prev.map(i => i.id === id ? { ...i, notes } : i))
    }, [])

    const isPinned = useCallback((id: string) => items.some(i => i.id === id), [items])
    
    const trackVisit = useCallback((item: Omit<PinnedItem, 'notes' | 'timestamp'>) => {
        // Only track if it's not already pinned
        if (items.some(i => i.id === item.id)) return;
        
        setSessionItems(prev => {
            const filtered = prev.filter(i => i.id !== item.id)
            if (filtered.length !== prev.length && prev[0]?.id === item.id) return prev
            return [{ ...item, notes: '', timestamp: Date.now() }, ...filtered].slice(0, 20)
        })
    }, [items])

    const clearSession = useCallback(() => setSessionItems([]), [])

    const graph = useMemo(() => buildWorkspaceGraph({ items, sessionItems, details }), [items, sessionItems, details])

    const exportWorkspace = useCallback(() => {
        const md = buildWorkspaceMarkdown({ items, details })

        const blob = new Blob([md], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `atlas-workspace-${new Date().toISOString().split('T')[0]}.md`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }, [details, items])

    const exportDossier = useCallback(async () => {
        const dossierItems = items.filter(i => ['theme', 'country', 'person'].includes(i.type))
        const sections = await Promise.all(
            dossierItems.map(async item => ({ item, signals: await fetchItemSignals(item) }))
        )
        const md = buildDossierMarkdown(sections)
        const blob = new Blob([md], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `atlas-dossier-${new Date().toISOString().split('T')[0]}.md`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }, [items])

    return (
        <WorkspaceContext.Provider value={{ isOpen, setIsOpen, items, graph, graphLoading, graphError, pinItem, unpinItem, updateNotes, isPinned, exportWorkspace, exportDossier, sessionItems, trackVisit, clearSession }}>
            {children}
        </WorkspaceContext.Provider>
    )
}

export function useWorkspace() {
    const context = useContext(WorkspaceContext)
    if (!context) throw new Error("useWorkspace must be used within a WorkspaceProvider")
    return context
}
