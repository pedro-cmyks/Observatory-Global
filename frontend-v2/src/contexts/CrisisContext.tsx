import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { useFocus } from './FocusContext'
import { timeRangeToHours } from '../lib/timeRanges'

interface AnomalyData {
    country_code: string
    country_name?: string
    current_count: number
    multiplier: number
    zscore: number
    level: 'normal' | 'notable' | 'elevated' | 'critical'
}

interface CrisisState {
    enabled: boolean
    anomalies: AnomalyData[]
    overallSeverity: 'normal' | 'notable' | 'elevated' | 'critical'
    loading: boolean
}

interface CrisisContextValue extends CrisisState {
    toggleCrisis: () => void
    refetchAnomalies: () => void
}

const CrisisContext = createContext<CrisisContextValue | undefined>(undefined)

const STORAGE_KEY = 'observatory_crisis_mode'

export const CrisisProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [enabled, setEnabled] = useState(() => {
        const stored = localStorage.getItem(STORAGE_KEY)
        return stored === 'true'
    })
    const [anomalies, setAnomalies] = useState<AnomalyData[]>([])
    const [overallSeverity, setOverallSeverity] = useState<'normal' | 'notable' | 'elevated' | 'critical'>('normal')
    const [loading, setLoading] = useState(false)

    // Use global time range for anomaly queries
    const { filter } = useFocus()
    const hours = Math.min(timeRangeToHours(filter.timeRange), 168) // Anomaly endpoint caps at 168h

    const fetchAnomalies = useCallback(async () => {
        setLoading(true)
        try {
            const res = await fetch(`/api/v2/anomalies?hours=${hours}&limit=10`)
            if (res.ok) {
                const data = await res.json()
                setAnomalies(data.anomalies || [])
                setOverallSeverity(data.overall_severity || 'normal')
            }
        } catch (e) {
            console.error('[CrisisContext] Fetch error:', e)
        } finally {
            setLoading(false)
        }
    }, [enabled, hours])

    useEffect(() => {
        fetchAnomalies()
        const interval = setInterval(fetchAnomalies, 5 * 60 * 1000)
        return () => clearInterval(interval)
    }, [fetchAnomalies])

    const toggleCrisis = useCallback(() => {
        setEnabled(prev => {
            const next = !prev
            localStorage.setItem(STORAGE_KEY, String(next))
            return next
        })
    }, [])

    return (
        <CrisisContext.Provider value={{
            enabled,
            anomalies,
            overallSeverity,
            loading,
            toggleCrisis,
            refetchAnomalies: fetchAnomalies
        }}>
            {children}
        </CrisisContext.Provider>
    )
}

export const useCrisis = () => {
    const ctx = useContext(CrisisContext)
    if (!ctx) throw new Error('useCrisis must be used within CrisisProvider')
    return ctx
}
