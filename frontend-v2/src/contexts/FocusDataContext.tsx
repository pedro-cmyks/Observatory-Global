/**
 * FocusDataProvider - Single source of truth for focus-filtered data.
 * 
 * Prevents double-fetch by having WorldMap and FocusSummaryPanel
 * consume the same state from this provider.
 */
import React, { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react'
import { useFocus } from './FocusContext'
import { type TimeRange, timeRangeToHours } from '../lib/timeRanges'

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

export interface AcledConflict {
    id: string
    date: string
    type: string
    sub_type: string
    actors: { actor1: string | null, actor2: string | null }
    location: { country: string, region?: string, name: string, latitude: number | null, longitude: number | null }
    fatalities: number
    notes?: string
    source: string
    severity?: string
    goldstein?: number
    mentions?: number
}

interface FocusDataState {
    nodes: NodeData[]
    flows: FlowData[]
    unfilteredFlows?: FlowData[]
    acledConflicts: AcledConflict[]
    summary: FocusSummary | null
    meta: FocusDataMeta
    loading: boolean
    isRefetching: boolean
    error: string | null
}

interface FocusDataContextValue extends FocusDataState {
    timeRange: TimeRange
    setTimeRange: (range: TimeRange) => void
    // Deprecated: for backward compatibility
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
    unfilteredFlows: [],
    acledConflicts: [],
    summary: null,
    meta: defaultMeta,
    loading: true,
    isRefetching: false,
    error: null
}

const FocusDataContext = createContext<FocusDataContextValue | undefined>(undefined)

export const FocusDataProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const { focus, filter, isActive, setTimeRange: setGlobalTimeRange } = useFocus()
    const timeRange = filter.timeRange
    const [state, setState] = useState<FocusDataState>(defaultState)
    const previousFlows = useRef<FlowData[]>([])

    const fetchData = useCallback(async () => {
        setState(prev => ({ ...prev, loading: prev.nodes.length === 0, isRefetching: true, error: null }))

        try {
            // Build base params - use range for new API
            const baseParams = new URLSearchParams({ range: timeRange })
            
            // Add explicit fields filter for payload reduction
            baseParams.set('fields', 'id,name,lat,lon,signalCount,sentiment,intensity')

            // Fetch nodes first, but preserve flows during the await
            setState(prev => ({ ...prev, flows: previousFlows.current }))

            // Add focus params if active
            if (isActive && focus.type && focus.value) {
                baseParams.set('focus_type', focus.type)
                baseParams.set('focus_value', focus.value)
            }

            // Fetch nodes first
            const nodesRes = await fetch(`/api/v2/nodes?${baseParams}`)
            if (!nodesRes.ok) throw new Error(`Nodes fetch failed: ${nodesRes.status}`)
            const nodesData = await nodesRes.json()

            // Safe render: cap nodes at 150 to prevent Deck.gl crashes
            const MAX_NODES = 150
            let safeNodes = nodesData.nodes || []
            if (safeNodes.length > MAX_NODES) {
                safeNodes = safeNodes.slice(0, MAX_NODES)
            }

            // Render globe immediately after nodes — don't wait for flows/acled
            setState(prev => ({
                ...prev,
                nodes: safeNodes,
                meta: {
                    totalCountries: nodesData.count || nodesData.nodes?.length || 0,
                    totalSignals: nodesData.totalSignals || 0,
                    isFiltered: nodesData.is_filtered || false
                },
                loading: false,
                error: null
            }))

            // 200ms stagger before secondary fetches
            await new Promise(r => setTimeout(r, 200))

            // Fetch flows with 12s timeout — render map without flows if slow
            const flowsParams = new URLSearchParams(baseParams.toString())
            flowsParams.delete('fields')
            let flowsData: { flows: FlowData[] } = { flows: [] }
            try {
                const flowsCtrl = new AbortController()
                const flowsTimer = setTimeout(() => flowsCtrl.abort(), 12000)
                const flowsRes = await fetch(`/api/v2/flows?${flowsParams}`, { signal: flowsCtrl.signal })
                clearTimeout(flowsTimer)
                if (flowsRes.ok) flowsData = await flowsRes.json()
            } catch {
                // Timeout or network error — map already visible without flows
            }

            // Fetch summary only when focused
            let summaryData: FocusSummary | null = null
            if (isActive && focus.type && focus.value) {
                try {
                    const summaryParams = new URLSearchParams({
                        focus_type: focus.type,
                        focus_value: focus.value,
                        hours: timeRangeToHours(timeRange).toString()
                    })
                    const summaryRes = await fetch(`/api/v2/focus?${summaryParams}`)
                    if (summaryRes.ok) {
                        summaryData = await summaryRes.json()
                    }
                } catch (e) {
                    console.warn('[FocusDataProvider] Summary fetch failed:', e)
                }
            }

            // Fetch conflict markers (ACLED if configured, GDELT Events fallback)
            let acledData: AcledConflict[] = []
            try {
                const hours = timeRangeToHours(timeRange)
                const days = Math.max(1, Math.min(30, Math.ceil(hours / 24)))
                const markersParams = new URLSearchParams({ days: days.toString(), limit: '500' })
                const markersRes = await fetch(`/api/v2/conflict-markers?${markersParams}`)
                if (markersRes.ok) {
                    const data = await markersRes.json()
                    acledData = data.markers || []
                }
            } catch (e) {
                console.warn('[FocusDataProvider] Conflict markers fetch failed:', e)
            }

            const newFlows = flowsData.flows || []
            previousFlows.current = newFlows

            // Update flows/acled without re-hiding the globe
            setState(prev => ({
                ...prev,
                flows: newFlows,
                unfilteredFlows: (!isActive) ? newFlows : prev.unfilteredFlows,
                acledConflicts: acledData,
                summary: summaryData,
                isRefetching: false
            }))

        } catch (err) {
            console.error('[FocusDataProvider] Fetch error:', err)
            setState(prev => ({
                ...prev,
                loading: false,
                isRefetching: false,
                error: err instanceof Error ? err.message : 'Unknown error'
            }))
        }
    }, [focus.type, focus.value, isActive, timeRange])

    // Use a native debounce to prevent rapid-click API thrashing
    const fetchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

    useEffect(() => {
        if (fetchTimeoutRef.current) {
            clearTimeout(fetchTimeoutRef.current)
        }
        fetchTimeoutRef.current = setTimeout(() => {
            fetchData()
        }, 300)
        
        return () => {
            if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current)
        }
    }, [fetchData])

    // Backward compatibility: convert hours to range
    const setTimeWindow = useCallback((hours: number) => {
        if (hours <= 24) setGlobalTimeRange('24h')
        else if (hours <= 168) setGlobalTimeRange('1w')
        else if (hours <= 720) setGlobalTimeRange('1m')
        else if (hours <= 2160) setGlobalTimeRange('3m')
        else setGlobalTimeRange('record')
    }, [setGlobalTimeRange])

    const value: FocusDataContextValue = {
        ...state,
        timeRange,
        setTimeRange: setGlobalTimeRange,
        timeWindow: timeRangeToHours(timeRange),
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

