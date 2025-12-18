import React, { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

export type FocusType = 'theme' | 'person' | 'country' | 'source' | null

export interface FocusState {
    type: FocusType
    value: string | null
    label: string | null
}

interface FocusContextValue {
    focus: FocusState
    setFocus: (type: FocusType, value: string, label?: string) => void
    clearFocus: () => void
    isActive: boolean
}

const defaultFocus: FocusState = {
    type: null,
    value: null,
    label: null
}

const FocusContext = createContext<FocusContextValue | undefined>(undefined)

export const FocusProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [focus, setFocusState] = useState<FocusState>(defaultFocus)

    const setFocus = useCallback((type: FocusType, value: string, label?: string) => {
        setFocusState({
            type,
            value,
            label: label || value
        })
        console.log(`[Focus] Set: ${type} = ${value}`)
    }, [])

    const clearFocus = useCallback(() => {
        setFocusState(defaultFocus)
        console.log('[Focus] Cleared')
    }, [])

    const isActive = focus.type !== null && focus.value !== null

    return (
        <FocusContext.Provider value={{ focus, setFocus, clearFocus, isActive }}>
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
