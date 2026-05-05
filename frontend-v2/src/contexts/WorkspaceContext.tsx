import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

export type PinnedItemType = 'theme' | 'person' | 'country' | 'signal' | 'source' | 'chokepoint'

export interface PinnedItem {
    id: string
    type: PinnedItemType
    title: string
    urlParams: string // the query string to restore this view, e.g. "?theme=ARMEDCONFLICT"
    notes: string
    timestamp: number
    meta?: any // extra data like country code, signal text, etc.
}

interface WorkspaceContextType {
    isOpen: boolean
    setIsOpen: (open: boolean) => void
    items: PinnedItem[]
    pinItem: (item: Omit<PinnedItem, 'notes' | 'timestamp'>) => void
    unpinItem: (id: string) => void
    updateNotes: (id: string, notes: string) => void
    isPinned: (id: string) => boolean
    exportWorkspace: () => void
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null)

export function WorkspaceProvider({ children }: { children: ReactNode }) {
    const [isOpen, setIsOpen] = useState(false)
    const [items, setItems] = useState<PinnedItem[]>([])

    // Load from localStorage on mount
    useEffect(() => {
        try {
            const stored = localStorage.getItem('atlas-workspace')
            if (stored) {
                setItems(JSON.parse(stored))
            }
        } catch (e) {
            console.error("Failed to load workspace", e)
        }
    }, [])

    // Save to localStorage when items change
    useEffect(() => {
        localStorage.setItem('atlas-workspace', JSON.stringify(items))
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
        <WorkspaceContext.Provider value={{ isOpen, setIsOpen, items, pinItem, unpinItem, updateNotes, isPinned, exportWorkspace }}>
            {children}
        </WorkspaceContext.Provider>
    )
}

export function useWorkspace() {
    const context = useContext(WorkspaceContext)
    if (!context) throw new Error("useWorkspace must be used within a WorkspaceProvider")
    return context
}
