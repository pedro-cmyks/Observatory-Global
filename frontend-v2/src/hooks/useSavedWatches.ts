import { useState, useCallback } from 'react'
import type { GlobalFilter } from '../contexts/FocusContext'

export interface SavedWatch {
    id: string
    name: string
    filter: Pick<GlobalFilter, 'country' | 'theme' | 'person' | 'concept' | 'region'>
    createdAt: string
}

const STORAGE_KEY = 'atlas_saved_watches_v1'

function load(): SavedWatch[] {
    try {
        const raw = localStorage.getItem(STORAGE_KEY)
        return raw ? JSON.parse(raw) : []
    } catch {
        return []
    }
}

function save(watches: SavedWatch[]) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(watches))
    } catch { /* noop */ }
}

export function useSavedWatches() {
    const [watches, setWatches] = useState<SavedWatch[]>(load)

    const add = useCallback((name: string, filter: GlobalFilter) => {
        const w: SavedWatch = {
            id: `watch-${Date.now()}`,
            name: name.trim(),
            filter: {
                country: filter.country,
                theme: filter.theme,
                person: filter.person,
                concept: filter.concept,
                region: filter.region,
            },
            createdAt: new Date().toISOString(),
        }
        const next = [...load(), w]
        save(next)
        setWatches(next)
        return w.id
    }, [])

    const remove = useCallback((id: string) => {
        const next = load().filter(w => w.id !== id)
        save(next)
        setWatches(next)
    }, [])

    return { watches, add, remove }
}
