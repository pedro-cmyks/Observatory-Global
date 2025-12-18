/**
 * FocusDataProvider - Single source of truth for focus-filtered data.
 * 
 * Prevents double-fetch by having WorldMap and FocusSummaryPanel
 * consume the same state from this provider.
 */
import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { useFocus } from './FocusContext'

// Types
export interface NodeData {
    id: string
    name: string
    lat: number
    lon: number
    intensity: number
    sentiment: number
    signalCount: number
    sourceCount: number
}

export interface FlowData {
    source: [number, number]
    target: [number, number]
    sourceCountry: string
    targetCountry: string
    strength: number
}

export interface FocusSummary {
    stats: {
        total_signals: number
        unique_sources: number
        unique_countries: number
        avg_sentiment: number
    }
    related_topics: Array<{ topic: string; count: number }>
    top_sources: Array<{ source: string; count: number; avg_sentiment: number }>
    headlines: Array<{ url: string; source: string; time: string | null }>
}

export interface FocusDataMeta {
    totalCountries: number
    totalSignals: number
    isFiltered: boolean
}

interface FocusDataState {
    nodes: NodeData[]
    flows: FlowData[]
    summary: FocusSummary | null
    meta: FocusDataMeta
    loading: boolean
    error: string | null
}

interface FocusDataContextValue extends FocusDataState {
    timeWindow: number
    setTimeWindow: (hours: number) => void
    refetch: () => void
}

const defaultMeta: FocusDataMeta = {
    totalCountries: 0,
    totalSignals: 0,
    isFiltered: false
}

const defaultState: FocusDataState = {
    nodes: [],
    flows: [],
    summary: null,
    meta: defaultMeta,
    loading: true,
    error: null
}

const FocusDataContext = createContext<FocusDataContextValue | undefined>(undefined)

export const FocusDataProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const { focus, isActive } = useFocus()
    const [timeWindow, setTimeWindow] = useState(24)
    const [state, setState] = useState<FocusDataState>(defaultState)

    const fetchData = useCallback(async () => {
        setState(prev => ({ ...prev, loading: true, error: null }))

        try {
            // Build base params
            const baseParams = new URLSearchParams({ hours: timeWindow.toString() })

            // Add focus params if active
            if (isActive && focus.type && focus.value) {
                baseParams.set('focus_type', focus.type)
                baseParams.set('focus_value', focus.value)
            }

            // Fetch nodes and flows in parallel
            const [nodesRes, flowsRes] = await Promise.all([
                fetch(`/api/v2/nodes?${baseParams}`),
                fetch(`/api/v2/flows?${baseParams}`)
            ])

            if (!nodesRes.ok) {
                throw new Error(`Nodes fetch failed: ${nodesRes.status}`)
            }
            if (!flowsRes.ok) {
                throw new Error(`Flows fetch failed: ${flowsRes.status}`)
            }

            const nodesData = await nodesRes.json()
            const flowsData = await flowsRes.json()

            // Fetch summary only when focused
            let summaryData: FocusSummary | null = null
            if (isActive && focus.type && focus.value) {
                try {
                    const summaryParams = new URLSearchParams({
                        focus_type: focus.type,
                        focus_value: focus.value,
                        hours: timeWindow.toString()
                    })
                    const summaryRes = await fetch(`/api/v2/focus?${summaryParams}`)
                    if (summaryRes.ok) {
                        summaryData = await summaryRes.json()
                    }
                } catch (e) {
                    console.warn('[FocusDataProvider] Summary fetch failed:', e)
                }
            }

            setState({
                nodes: nodesData.nodes || [],
                flows: flowsData.flows || [],
                summary: summaryData,
                meta: {
                    totalCountries: nodesData.count || nodesData.nodes?.length || 0,
                    totalSignals: nodesData.totalSignals || 0,
                    isFiltered: nodesData.is_filtered || false
                },
                loading: false,
                error: null
            })

        } catch (err) {
            console.error('[FocusDataProvider] Fetch error:', err)
            setState(prev => ({
                ...prev,
                loading: false,
                error: err instanceof Error ? err.message : 'Unknown error'
            }))
        }
    }, [focus.type, focus.value, isActive, timeWindow])

    // Refetch when focus or time window changes
    useEffect(() => {
        fetchData()
    }, [fetchData])

    const value: FocusDataContextValue = {
        ...state,
        timeWindow,
        setTimeWindow,
        refetch: fetchData
    }

    return (
        <FocusDataContext.Provider value={value}>
            {children}
        </FocusDataContext.Provider>
    )
}

export const useFocusData = (): FocusDataContextValue => {
    const context = useContext(FocusDataContext)
    if (!context) {
        throw new Error('useFocusData must be used within a FocusDataProvider')
    }
    return context
}
