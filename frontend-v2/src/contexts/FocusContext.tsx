/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import { nextFocusDims } from '../lib/focusReducer'

export type FocusType = 'thread' | 'theme' | 'entity' | 'person' | 'country' | 'source' | null
export type LockedBy = 'radar' | 'stream' | 'matrix' | 'anomaly' | null

export interface FocusState {
    type: FocusType
    value: string | null
    label: string | null
    /** Fix round 2026-07-17 item 8: the OPENER's human label for a theme/thread
     *  focus (universe node label, threads-row label). When present, chips must
     *  render it instead of skeleton-resolving the raw id — the raw-id fallback
     *  produced the generic "Narrative Thread" in the focus chip / map key. */
    knownLabel: string | null
}

export interface ConceptFilter {
    slug: string
    themes: string[]
    label: string
}

export interface RegionFilter {
    slug: string
    label: string
    countries: string[]
}

export type StreamLevel = 'all' | 'critical' | 'elevated' | 'notable' | 'conflict' | 'disaster' | 'trend' | 'person' | 'maritime' | null

export interface GlobalFilter {
    thread: string | null
    country: string | null
    theme: string | null
    entity: string | null
    person: string | null
    concept: ConceptFilter | null
    region: RegionFilter | null
    /** Item 8: the opener's human label for the current thread/theme focus.
     *  Lives and dies with thread/theme; null when the opener knew none. */
    themeLabel: string | null
    // timeRange REMOVED (2026-07-15): the VIEW selector is gone — the map
    // scrubber is time; each surface owns its fixed window.
    lockedBy: LockedBy
    streamLevel: StreamLevel
}

interface FocusContextValue {
    // New GlobalFilter state
    filter: GlobalFilter
    setThread: (thread: string | null, label?: string | null) => void
    setCountry: (country: string | null, source?: LockedBy) => void
    setTheme: (theme: string | null, source?: LockedBy, label?: string | null) => void
    setEntity: (entity: string | null) => void
    setPerson: (person: string | null) => void
    setConcept: (concept: ConceptFilter | null) => void
    setRegion: (region: RegionFilter | null) => void
    setStreamLevel: (level: StreamLevel) => void
    clearFilter: () => void
    // Map fly hint: set a country code to trigger a map flyTo
    mapFlyCountry: string | null
    setMapFlyCountry: (code: string | null) => void

    // Legacy / backwards compatible
    focus: FocusState
    setFocus: (type: FocusType, value: string, label?: string) => void
    clearFocus: () => void
    isActive: boolean
}

const defaultFilter: GlobalFilter = {
    thread: null,
    country: null,
    theme: null,
    entity: null,
    person: null,
    concept: null,
    region: null,
    themeLabel: null,
    lockedBy: null,
    streamLevel: 'notable',
}

const FocusContext = createContext<FocusContextValue | undefined>(undefined)

export const FocusProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    // Force clear any old stuck local storage keys just in case
    useEffect(() => {
        localStorage.removeItem('atlas-time-range')
        localStorage.removeItem('timeRange')
    }, [])

    const [filter, setFilter] = useState<GlobalFilter>(defaultFilter)
    const [mapFlyCountry, setMapFlyCountry] = useState<string | null>(null)

    // These five setters route dimension transitions through the pure
    // nextFocusDims reducer (lib/focusReducer.ts) so country/theme/person can
    // co-exist (compound focus) instead of clobbering each other. Only the
    // string dimensions are pulled off the reducer result — concept/region
    // stay untouched here (they're typed `unknown` on FocusDims and are only
    // ever managed by setConcept/setRegion).
    const setThread = useCallback((thread: string | null, label: string | null = null) => {
        setFilter(prev => {
            const d = nextFocusDims(prev, { dim: 'thread', value: thread, label })
            return {
                ...prev,
                thread: d.thread, country: d.country, theme: d.theme,
                entity: d.entity, person: d.person, themeLabel: d.themeLabel,
                // thread stays an exclusive full reset, same as before.
                concept: null,
                region: null,
                lockedBy: null,
            }
        })
        console.log(`[GlobalFilter] Set thread=${thread}`)
    }, [])

    const setCountry = useCallback((country: string | null, source: LockedBy = null) => {
        setFilter(prev => {
            const d = nextFocusDims(prev, { dim: 'country', value: country })
            return {
                ...prev,
                thread: d.thread, country: d.country, theme: d.theme,
                entity: d.entity, person: d.person, themeLabel: d.themeLabel,
                lockedBy: country ? source : prev.theme ? prev.lockedBy : null
            }
        })
        console.log(`[GlobalFilter] Set country=${country} by ${source || 'unknown'}`)
    }, [])

    const setTheme = useCallback((theme: string | null, source: LockedBy = null, label: string | null = null) => {
        setFilter(prev => {
            const d = nextFocusDims(prev, { dim: 'theme', value: theme, label })
            return {
                ...prev,
                thread: d.thread, country: d.country, theme: d.theme,
                entity: d.entity, person: d.person, themeLabel: d.themeLabel,
                lockedBy: theme ? source : prev.country ? prev.lockedBy : null
            }
        })
        console.log(`[GlobalFilter] Set theme=${theme} by ${source || 'unknown'}`)
    }, [])

    const setEntity = useCallback((entity: string | null) => {
        setFilter(prev => {
            const d = nextFocusDims(prev, { dim: 'entity', value: entity })
            return {
                ...prev,
                thread: d.thread, country: d.country, theme: d.theme,
                entity: d.entity, person: d.person, themeLabel: d.themeLabel,
                concept: null,
                region: null,
                lockedBy: null,
            }
        })
        console.log(`[GlobalFilter] Set entity=${entity}`)
    }, [])

    const setPerson = useCallback((person: string | null) => {
        setFilter(prev => {
            const d = nextFocusDims(prev, { dim: 'person', value: person })
            return {
                ...prev, // preserves concept, region, streamLevel, lockedBy, etc.
                thread: d.thread, country: d.country, theme: d.theme,
                entity: d.entity, person: d.person, themeLabel: d.themeLabel,
                lockedBy: person ? prev.lockedBy : (prev.country || prev.theme ? prev.lockedBy : null),
            }
        })
        console.log(`[GlobalFilter] Set person=${person}`)
    }, [])

    const setConcept = useCallback((concept: ConceptFilter | null) => {
        // Setting a concept also sets the primary theme for panels that only read filter.theme
        const primaryTheme = concept?.themes[0] ?? null
        setFilter(prev => ({
            ...prev,
            concept,
            theme: primaryTheme,
            thread: null,
            themeLabel: null,
            entity: null,
            person: null,
            lockedBy: null,
        }))
        console.log(`[GlobalFilter] Set concept=${concept?.slug} (${concept?.themes.length} themes)`)
    }, [])

    const setRegion = useCallback((region: RegionFilter | null) => {
        setFilter(prev => ({
            ...prev,
            region,
            thread: null,
            country: null,
            entity: null,
            person: null,
            theme: null,
            themeLabel: null,
            concept: null,
            lockedBy: null,
        }))
        console.log(`[GlobalFilter] Set region=${region?.slug} (${region?.countries.length} countries)`)
    }, [])

    const setStreamLevel = useCallback((level: StreamLevel) => {
        setFilter(prev => ({ ...prev, streamLevel: level }))
    }, [])

    const clearFilter = useCallback(() => {
        setFilter(prev => ({
            ...prev,
            thread: null,
            country: null,
            theme: null,
            themeLabel: null,
            entity: null,
            person: null,
            concept: null,
            region: null,
            lockedBy: null,
        }))
        console.log('[GlobalFilter] Cleared')
    }, [])

    // Legacy API mappings
    // Compound-focus note: filter.country/filter.theme/filter.person can now all
    // be non-null at once (see nextFocusDims) — this collapse into a single
    // legacy FocusType/value pair is a priority ORDER for outbound endpoints
    // that only accept one dimension, not a claim that only one is active.
    const threadAnchor = filter.thread?.split('--')[0] ?? null
    const entityFocusValue = filter.person || filter.entity
    const focus: FocusState = {
        // Legacy backend endpoints currently accept theme/person/country/source.
        // Keep thread/entity in GlobalFilter, but adapt outbound focus params
        // until native Thread/Entity Focus endpoints exist.
        type: threadAnchor ? 'theme' : entityFocusValue ? 'person' : filter.country ? 'country' : filter.theme ? 'theme' : null,
        value: threadAnchor || entityFocusValue || filter.country || filter.theme,
        label: filter.thread || entityFocusValue || filter.country || filter.theme,
        // Item 8: only a thread/theme focus carries an opener-supplied label.
        knownLabel: (filter.thread || filter.theme) ? filter.themeLabel : null,
    }

    const setFocus = useCallback((type: FocusType, value: string, label?: string) => {
        if (type === 'thread') {
            setThread(value, label ?? null)
        } else if (type === 'country') {
            setCountry(value)
        } else if (type === 'theme') {
            setTheme(value, null, label ?? null)
        } else if (type === 'entity') {
            setEntity(value)
        } else if (type === 'person') {
            setPerson(value)
        } else {
            clearFilter()
        }
    }, [setThread, setCountry, setTheme, setEntity, setPerson, clearFilter])

    const clearFocus = clearFilter
    const isActive = filter.thread !== null || filter.country !== null || filter.theme !== null || filter.entity !== null || filter.person !== null || filter.concept !== null || filter.region !== null

    return (
        <FocusContext.Provider value={{
            filter, setThread, setCountry, setTheme, setEntity, setPerson, setConcept, setRegion, setStreamLevel, clearFilter,
            mapFlyCountry, setMapFlyCountry,
            focus, setFocus, clearFocus, isActive
        }}>
            {children}
        </FocusContext.Provider>
    )
}

export const useFocus = (): FocusContextValue => {
    const context = useContext(FocusContext)
    if (!context) {
        throw new Error('useFocus must be used within a FocusProvider')
    }
    return context
}
