import { useState, useEffect } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import './NarrativeDrift.css'

interface DriftPoint {
    date: string
    sentiment: number
    volume: number
}

interface NarrativeDriftProps {
    themeCode: string
    countryCode?: string | null
    days?: number
}

export function NarrativeDrift({ themeCode, countryCode, days = 14 }: NarrativeDriftProps) {
    const [data, setData] = useState<DriftPoint[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        let isMounted = true
        const fetchDrift = async () => {
            setLoading(true)
            setError(null)
            try {
                let url = `/api/v2/theme/${themeCode}/drift?days=${days}`
                if (countryCode) url += `&country_code=${countryCode}`
                const res = await fetch(url)
                if (!res.ok) throw new Error('Failed to fetch drift data')
                const json = await res.json()
                if (isMounted) setData(json.drift || [])
            } catch (err) {
                if (isMounted) setError(err instanceof Error ? err.message : 'Unknown error')
            } finally {
                if (isMounted) setLoading(false)
            }
        }
        
        fetchDrift()
        return () => { isMounted = false }
    }, [themeCode, countryCode, days])

    if (loading) return <div className="narrative-drift loading">Loading narrative drift...</div>
    if (error) return <div className="narrative-drift error">Error: {error}</div>
    if (!data.length) return <div className="narrative-drift empty">No drift data available for this period.</div>

    // Format dates for display
    const formattedData = data.map(d => ({
        ...d,
        displayDate: new Date(d.date).toLocaleDateString([], { month: 'short', day: 'numeric' })
    }))

    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const pt = payload[0].payload
            const s = pt.sentiment * 10
            const color = s >= 2 ? '#22c55e' : s <= -2 ? '#ef4444' : '#eab308'
            return (
                <div className="drift-tooltip">
                    <p className="drift-tooltip-date">{pt.displayDate}</p>
                    <p className="drift-tooltip-val" style={{ color }}>
                        Sentiment: {s > 0 ? '+' : ''}{s.toFixed(1)}
                    </p>
                    <p className="drift-tooltip-vol">
                        Signals: {pt.volume}
                    </p>
                </div>
            )
        }
        return null
    }

    return (
        <div className="narrative-drift">
            <div className="narrative-drift-header">
                <h3>Narrative Drift <span style={{ fontWeight: 400, opacity: 0.5, fontSize: '0.75rem', textTransform: 'none' }}>(Last {days} days)</span></h3>
            </div>
            <div className="narrative-drift-chart">
                <ResponsiveContainer width="100%" height={140}>
                    <LineChart data={formattedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                        <XAxis 
                            dataKey="displayDate" 
                            stroke="#475569" 
                            fontSize={10} 
                            tickLine={false}
                            axisLine={false}
                            dy={10}
                        />
                        <YAxis 
                            domain={[-1, 1]} 
                            stroke="#475569" 
                            fontSize={10} 
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(val) => (val * 10).toFixed(0)}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
                        <Line 
                            type="monotone" 
                            dataKey="sentiment" 
                            stroke="#3b82f6" 
                            strokeWidth={2}
                            dot={{ r: 2, fill: '#3b82f6', strokeWidth: 0 }}
                            activeDot={{ r: 4, fill: '#fff' }}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    )
}
