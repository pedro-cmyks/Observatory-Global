import { useState, useCallback } from 'react'

export interface CustomConcept {
    slug: string
    label: string
    description: string
    themes: string[]
    custom: true
}

const STORAGE_KEY = 'atlas_custom_concepts_v1'

function load(): CustomConcept[] {
    try {
        const raw = localStorage.getItem(STORAGE_KEY)
        return raw ? JSON.parse(raw) : []
    } catch {
        return []
    }
}

function save(concepts: CustomConcept[]) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(concepts))
    } catch { /* noop */ }
}

function slugify(label: string): string {
    return `custom-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}`
}

export function useCustomConcepts() {
    const [concepts, setConcepts] = useState<CustomConcept[]>(load)

    const add = useCallback((label: string, description: string, themes: string[]) => {
        const base = slugify(label)
        const existing = load()
        // Ensure unique slug
        let slug = base
        let i = 2
        while (existing.some(c => c.slug === slug)) {
            slug = `${base}-${i++}`
        }
        const next = [...existing, { slug, label, description, themes, custom: true as const }]
        save(next)
        setConcepts(next)
        return slug
    }, [])

    const remove = useCallback((slug: string) => {
        const next = load().filter(c => c.slug !== slug)
        save(next)
        setConcepts(next)
    }, [])

    const update = useCallback((slug: string, label: string, description: string, themes: string[]) => {
        const next = load().map(c => c.slug === slug ? { ...c, label, description, themes } : c)
        save(next)
        setConcepts(next)
    }, [])

    return { concepts, add, remove, update }
}
