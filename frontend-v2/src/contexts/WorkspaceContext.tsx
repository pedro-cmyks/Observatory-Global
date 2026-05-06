/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useMemo, type ReactNode } from 'react'
import { buildWorkspaceGraph, type WorkspaceGraph } from '../lib/workspaceGraph'

export type PinnedItemType = 'theme' | 'person' | 'country' | 'signal' | 'source' | 'chokepoint'

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
    return item.id
}

async function fetchWorkspaceDetail(item: PinnedItem, signal: AbortSignal): Promise<unknown | undefined> {
    const value = getPinnedValue(item)
    if (!value || item.type === 'signal' || item.type === 'chokepoint') return undefined

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

    // Save to localStorage when items change
    useEffect(() => {
        localStorage.setItem('atlas-workspace', JSON.stringify(items))
    }, [items])

    useEffect(() => {
        const fetchableItems = items.filter(item => item.type !== 'signal' && item.type !== 'chokepoint')
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
    }, [items])

    const pinItem = (item: Omit<PinnedItem, 'notes' | 'timestamp'>) => {
        setItems(prev => {
            if (prev.find(i => i.id === item.id)) return prev
            return [{ ...item, notes: '', timestamp: Date.now() }, ...prev]
        })
        setIsOpen(true) // auto-open workspace when pinning
    }

    const unpinItem = (id: string) => {
        setItems(prev => prev.filter(i => i.id !== id))
    }

    const updateNotes = (id: string, notes: string) => {
        setItems(prev => prev.map(i => i.id === id ? { ...i, notes } : i))
    }

    const isPinned = (id: string) => items.some(i => i.id === id)
    const graph = useMemo(() => {
        try {
            return buildWorkspaceGraph({ items, details })
        } catch (e) {
            console.error('[WorkspaceGraph] build failed', e)
            return { nodes: [], links: [] }
        }
    }, [items, details])

    const exportWorkspace = () => {
        let md = `# Atlas Investigation Workspace\n\n`
        md += `*Exported: ${new Date().toUTCString()}*\n\n---\n\n`

        if (items.length === 0) {
            md += `*Workspace is empty.*\n`
        } else {
            items.forEach(item => {
                md += `## [${item.type.toUpperCase()}] ${item.title}\n`
                md += `- **Pinned on:** ${new Date(item.timestamp).toLocaleString()}\n`
                md += `- **URL Context:** \`${item.urlParams}\`\n\n`
                if (item.notes.trim()) {
                    md += `### Notes\n${item.notes}\n\n`
                }
                md += `---\n\n`
            })
        }

        const blob = new Blob([md], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `atlas-workspace-${new Date().toISOString().split('T')[0]}.md`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    return (
        <WorkspaceContext.Provider value={{ isOpen, setIsOpen, items, graph, graphLoading, graphError, pinItem, unpinItem, updateNotes, isPinned, exportWorkspace }}>
            {children}
        </WorkspaceContext.Provider>
    )
}

export function useWorkspace() {
    const context = useContext(WorkspaceContext)
    if (!context) throw new Error("useWorkspace must be used within a WorkspaceProvider")
    return context
}
