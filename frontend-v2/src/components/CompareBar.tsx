import { useState, useEffect } from 'react'
import './CompareBar.css'

interface CompareData {
    period_a: { label: string; signals: number; avg_sentiment: number }
    period_b: { label: string; signals: number; avg_sentiment: number }
    delta: { signals: number; signals_pct: number; sentiment: number }
}

interface CompareBarProps {
    entityType: 'theme' | 'country' | 'global'
    entityValue?: string
    hours: number
}

export function CompareBar({ entityType, entityValue, hours }: CompareBarProps) {
    const [data, setData] = useState<CompareData | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        const window = hours <= 24 ? '24h' : hours <= 168 ? '7d' : '30d'
        const params = new URLSearchParams({
            entity_type: entityType,
            window,
        })
        if (entityValue) params.append('entity_value', entityValue)

        fetch(`/api/v2/compare?${params}`)
            .then(r => r.ok ? r.json() : null)
            .then(d => { if (d && !d.error) setData(d) })
            .catch(() => {})
            .finally(() => setLoading(false))
    }, [entityType, entityValue, hours])

    if (loading || !data) return null

    const { delta } = data
    // Don't show if both periods have zero signals
    if (data.period_a.signals === 0 && data.period_b.signals === 0) return null

    const sigDir = delta.signals_pct > 0 ? 'up' : delta.signals_pct < 0 ? 'down' : 'flat'
    const sentDir = delta.sentiment > 0 ? 'up' : delta.sentiment < 0 ? 'down' : 'flat'
    const sigArrow = sigDir === 'up' ? '▲' : sigDir === 'down' ? '▼' : '→'
    const sentArrow = sentDir === 'up' ? '▲' : sentDir === 'down' ? '▼' : '→'

    return (
        <div className="compare-bar">
            <span className={`compare-chip compare-chip--${sigDir}`}>
                {sigArrow} {delta.signals_pct > 0 ? '+' : ''}{delta.signals_pct.toFixed(0)}% signals
            </span>
            <span className="compare-vs">vs previous</span>
            <span className={`compare-chip compare-chip--${sentDir}`}>
                {sentArrow} {delta.sentiment > 0 ? '+' : ''}{delta.sentiment.toFixed(2)} tone
            </span>
        </div>
    )
}
