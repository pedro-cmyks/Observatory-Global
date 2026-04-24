import React, { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import type { TimeRange } from '../lib/timeRanges'

export type FocusType = 'theme' | 'person' | 'country' | 'source' | null
export type LockedBy = 'radar' | 'stream' | 'matrix' | 'anomaly' | null

export interface FocusState {
    type: FocusType
    value: string | null
    label: string | null
}

export interface GlobalFilter {
    country: string | null
    theme: string | null
    person: string | null
    timeRange: TimeRange
    lockedBy: LockedBy
}

interface FocusContextValue {
    // New GlobalFilter state
    filter: GlobalFilter
    setCountry: (country: string | null, source?: LockedBy) => void
    setTheme: (theme: string | null, source?: LockedBy) => void
    setPerson: (person: string | null) => void
    setTimeRange: (range: TimeRange) => void
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
    country: null,
    theme: null,
    person: null,
    timeRange: '24h',
    lockedBy: null
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

    const setCountry = useCallback((country: string | null, source: LockedBy = null) => {
        setFilter(prev => ({ 
            ...prev, 
            country, 
            lockedBy: country ? source : prev.theme ? prev.lockedBy : null 
        }))
        console.log(`[GlobalFilter] Set country=${country} by ${source || 'unknown'}`)
    }, [])

    const setTheme = useCallback((theme: string | null, source: LockedBy = null) => {
        setFilter(prev => ({ 
            ...prev, 
            theme, 
            lockedBy: theme ? source : prev.country ? prev.lockedBy : null 
        }))
        console.log(`[GlobalFilter] Set theme=${theme} by ${source || 'unknown'}`)
    }, [])

    const setTimeRange = useCallback((timeRange: TimeRange) => {
        setFilter(prev => ({ ...prev, timeRange }))
        console.log(`[GlobalFilter] Set timeRange=${timeRange}`)
    }, [])

    const setPerson = useCallback((person: string | null) => {
        setFilter(prev => ({ ...prev, person, country: null, theme: null, lockedBy: null }))
        console.log(`[GlobalFilter] Set person=${person}`)
    }, [])

    const clearFilter = useCallback(() => {
        setFilter(prev => ({ ...prev, country: null, theme: null, person: null, lockedBy: null }))
        console.log('[GlobalFilter] Cleared')
    }, [])

    // Legacy API mappings
    const focus: FocusState = {
        type: filter.person ? 'person' : filter.country ? 'country' : filter.theme ? 'theme' : null,
        value: filter.person || filter.country || filter.theme,
        label: filter.person || filter.country || filter.theme
    }

    const setFocus = useCallback((type: FocusType, value: string, _label?: string) => {
        if (type === 'country') {
            setCountry(value)
        } else if (type === 'theme') {
            setTheme(value)
        } else if (type === 'person') {
            setPerson(value)
        } else {
            clearFilter()
        }
    }, [setCountry, setTheme, setPerson, clearFilter])

    const clearFocus = clearFilter
    const isActive = filter.country !== null || filter.theme !== null || filter.person !== null

    return (
        <FocusContext.Provider value={{
            filter, setCountry, setTheme, setPerson, setTimeRange, clearFilter,
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
