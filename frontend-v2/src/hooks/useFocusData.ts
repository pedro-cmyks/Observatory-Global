import { useEffect, useState, useCallback } from 'react'
import { useFocus } from '../contexts/FocusContext'

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

interface FocusDataState {
    nodes: NodeData[]
    flows: FlowData[]
    loading: boolean
    error: string | null
    meta: {
        totalCountries: number
        totalSignals: number
        isFiltered: boolean
    }
}

export function useFocusData(timeWindowHours: number = 24) {
    const { focus, isActive } = useFocus()
    const [state, setState] = useState<FocusDataState>({
        nodes: [],
        flows: [],
        loading: true,
        error: null,
        meta: { totalCountries: 0, totalSignals: 0, isFiltered: false }
    })

    const fetchData = useCallback(async () => {
        setState(prev => ({ ...prev, loading: true, error: null }))

        try {
            // Build query params
            const params = new URLSearchParams({ hours: timeWindowHours.toString() })

            if (isActive && focus.type && focus.value) {
                params.set('focus_type', focus.type)
                params.set('focus_value', focus.value)
            }

            // Fetch nodes and flows in parallel
            const [nodesRes, flowsRes] = await Promise.all([
                fetch(`/api/v2/nodes?${params}`),
                fetch(`/api/v2/flows?${params}`)
            ])

            if (!nodesRes.ok || !flowsRes.ok) {
                throw new Error('Failed to fetch map data')
            }

            const nodesData = await nodesRes.json()
            const flowsData = await flowsRes.json()

            setState({
                nodes: nodesData.nodes || [],
                flows: flowsData.flows || [],
                loading: false,
                error: null,
                meta: {
                    totalCountries: nodesData.count || nodesData.nodes?.length || 0,
                    totalSignals: nodesData.totalSignals || 0,
                    isFiltered: nodesData.is_filtered || false
                }
            })

        } catch (err) {
            console.error('[useFocusData] Error:', err)
            setState(prev => ({
                ...prev,
                loading: false,
                error: err instanceof Error ? err.message : 'Unknown error'
            }))
        }
    }, [focus.type, focus.value, isActive, timeWindowHours])

    // Refetch when focus or time window changes
    useEffect(() => {
        fetchData()
    }, [fetchData])

    return { ...state, refetch: fetchData }
}
