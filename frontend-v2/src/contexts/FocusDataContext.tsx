/**
 * FocusDataProvider - Single source of truth for focus-filtered data.
 * 
 * Prevents double-fetch by having WorldMap and FocusSummaryPanel
 * consume the same state from this provider.
 */
/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react'
import { useFocus } from './FocusContext'
import { buildFocusRequestKey } from '../lib/focusRequestKey'
import { fetchWithTimeout } from '../lib/fetchWithTimeout'
import { FOCUS_TIMEOUT_MS } from '../lib/focusLoadingState'

// Types
export interface NodeData {
    id: string
    name: string
    lat: number
    lon: number
    intensity: number
    heat?: number
    anomalyLevel?: string
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
    focus: { type: string; value: string; hours: number }
    summary: {
        total_signals: number
        total_countries: number
        generated_at: string
    }
    nodes: Array<{
        country_code: string
        signal_count: number
        avg_sentiment: number
        unique_sources: number
    }>
    related_topics: Array<{ topic: string; count: number }>
    top_sources: Array<{ source: string; count: number; avg_sentiment: number }>
    headlines: Array<{ url: string; source: string; time: string | null }>
}

export interface FocusDataMeta {
    totalCountries: number
    totalSignals: number
    isFiltered: boolean
    source?: string | null
    coverage?: {
        source?: string | null
        modelVersion?: string | null
        requestedHours?: number | null
        partialCoverage?: boolean | null
        // Live-window disclosure (cold-user probe §4): /api/v2/nodes drops every
        // country it cannot plot, so what it COUNTED and what it could MAP are
        // different numbers. Both are served now so the header can print the
        // counted base and name the undrawn remainder instead of absorbing it.
        basis?: string
        label?: string
        note?: string
        counted_countries?: number
        counted_signals?: number
        mapped_countries?: number
        mapped_signals?: number
        unmapped_countries?: number
        unmapped_signals?: number
    } | null
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

// The VIEW time selector is GONE (2026-07-15, the scrubber is time): this
// provider serves the AMBIENT live picture at a fixed 24h window; former
// timeRange/setTimeRange/timeWindow plumbing deleted with it.
interface FocusDataContextValue extends FocusDataState {
    refetch: () => void
}

const defaultMeta: FocusDataMeta = {
    totalCountries: 0,
    totalSignals: 0,
    isFiltered: false,
    source: null,
    coverage: null,
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
    const { focus, isActive } = useFocus()
    const [state, setState] = useState<FocusDataState>(defaultState)
    const previousFlows = useRef<FlowData[]>([])
    const activeRequestKey = useRef<string | null>(null)
    const activeRequestSeq = useRef(0)
    const activeAbortController = useRef<AbortController | null>(null)

    const fetchData = useCallback(async () => {
        const requestKey = buildFocusRequestKey({
            isActive,
            focusType: focus.type,
            focusValue: focus.value,
        })
        const controller = new AbortController()
        activeAbortController.current?.abort()
        activeAbortController.current = controller
        const requestSeq = activeRequestSeq.current + 1
        activeRequestSeq.current = requestSeq
        activeRequestKey.current = requestKey
        const isCurrentRequest = () => (
            activeRequestKey.current === requestKey
            && activeRequestSeq.current === requestSeq
            && !controller.signal.aborted
        )

        setState(prev => ({ ...prev, loading: prev.nodes.length === 0, isRefetching: true, error: null }))

        try {
            // Build base params - use range for new API.
            // Nodes/flows are AMBIENT — always the live 24h picture (S4
            // doctrine, now the only mode: the selector is gone, looking
            // back happens on the map scrubber).
            const baseParams = new URLSearchParams({ range: '24h' })
            
            // Add explicit fields filter for payload reduction
            baseParams.set('fields', 'id,name,lat,lon,signalCount,sentiment,intensity,heat,anomalyLevel')

            // Fetch nodes first, but preserve flows during the await
            setState(prev => ({ ...prev, flows: previousFlows.current }))

            // Add focus params if active.
            // Flywheel compound-focus note: /api/v2/nodes accepts a SINGLE
            // focus_type/focus_value (backend workspace.py:150 — theme|person|
            // country|source, one at a time). Under a compound frame
            // (country ∧ theme ∧ person) the map therefore scopes to the ONE
            // strongest dimension via the collapsed `focus` (priority
            // thread>person>country>theme). This is intentional, not a bug:
            // SignalStream already ANDs all three into /api/v2/signals and
            // carries the true intersection. A full compound-scoped map needs a
            // new backend endpoint accepting combined scope (deferred).
            if (isActive && focus.type && focus.value) {
                baseParams.set('focus_type', focus.type)
                baseParams.set('focus_value', focus.value)
            }

            // Fetch nodes first
            const nodesRes = await fetch(`/api/v2/nodes?${baseParams}`, { signal: controller.signal })
            if (!nodesRes.ok) throw new Error(`Nodes fetch failed: ${nodesRes.status}`)
            const nodesData = await nodesRes.json()
            if (!isCurrentRequest()) return

            // Safe render: cap at 217 (all sovereign countries) to prevent Deck.gl memory issues
            const MAX_NODES = 217
            let safeNodes = nodesData.nodes || []
            if (safeNodes.length > MAX_NODES) {
                safeNodes = safeNodes.slice(0, MAX_NODES)
            }

            // Render globe immediately after nodes — don't wait for flows/acled
            // Preserve stale nodes during refetch when new response is empty (avoids 0-flash in command bar)
            setState(prev => ({
                ...prev,
                nodes: safeNodes.length > 0 ? safeNodes : (prev.isRefetching ? prev.nodes : safeNodes),
                meta: safeNodes.length > 0 ? {
                    totalCountries: nodesData.count || nodesData.nodes?.length || 0,
                    totalSignals: nodesData.totalSignals || 0,
                    isFiltered: nodesData.is_filtered || false,
                    source: nodesData.source ?? null,
                    coverage: nodesData.coverage ?? null,
                } : (prev.isRefetching ? prev.meta : {
                    totalCountries: 0, totalSignals: 0, isFiltered: false, source: null, coverage: null
                }),
                loading: false,
                error: null
            }))

            // 200ms stagger before secondary fetches
            await new Promise(r => setTimeout(r, 200))
            if (!isCurrentRequest()) return

            // Fetch flows with 12s timeout — render map without flows if slow
            const flowsParams = new URLSearchParams(baseParams.toString())
            flowsParams.delete('fields')
            let flowsData: { flows: FlowData[] } = { flows: [] }
            try {
                const flowsCtrl = new AbortController()
                const flowsTimer = setTimeout(() => flowsCtrl.abort(), 12000)
                controller.signal.addEventListener('abort', () => flowsCtrl.abort(), { once: true })
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
                    // Focus summary = the live day (matches the ambient
                    // picture the summary annotates).
                    const summaryParams = new URLSearchParams({
                        focus_type: focus.type,
                        value: focus.value,
                        hours: '24'
                    })
                    // N26: this was the last unbounded `/api/v2/focus` caller.
                    // The outer `controller` cancels a STALE request on focus
                    // change, but nothing bounded a HUNG one — measured in
                    // the browser at 23.4s while EntityPanel's own (bounded)
                    // request had long since settled. The sibling `flows`
                    // fetch above already had a 12s bound; this one now
                    // matches EntityPanel's client bound and composes with
                    // the outer signal rather than replacing it.
                    const summaryRes = await fetchWithTimeout(`/api/v2/focus?${summaryParams}`, {
                        timeoutMs: FOCUS_TIMEOUT_MS,
                        parentSignal: controller.signal,
                    })
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
                // Conflict markers = the live day, like the map they sit on.
                const markersParams = new URLSearchParams({ days: '1', limit: '500' })
                const markersRes = await fetch(`/api/v2/conflict-markers?${markersParams}`, { signal: controller.signal })
                if (markersRes.ok) {
                    const data = await markersRes.json()
                    acledData = data.markers || []
                }
            } catch (e) {
                console.warn('[FocusDataProvider] Conflict markers fetch failed:', e)
            }

            const newFlows = flowsData.flows || []
            if (!isCurrentRequest()) return
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
            if (!isCurrentRequest()) return
            console.error('[FocusDataProvider] Fetch error:', err)
            setState(prev => ({
                ...prev,
                loading: false,
                isRefetching: false,
                error: err instanceof Error ? err.message : 'Unknown error'
            }))
        }

    }, [focus.type, focus.value, isActive])

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

    const value: FocusDataContextValue = {
        ...state,
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
