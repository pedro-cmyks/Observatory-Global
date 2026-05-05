import React, { useEffect, useState } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import { timeRangeToHours } from '../lib/timeRanges'
import './SourceIntegrityPanel.css'

interface GlobalBriefing {
    stats: {
        total_signals: number
        sources: number
    }
    top_sources: Array<{
        source: string
        count: number
    }>
}

export const SourceIntegrityPanel: React.FC = () => {
    const { filter } = useFocus()
    const { summary, timeRange, loading: focusLoading } = useFocusData()
    const [globalData, setGlobalData] = useState<GlobalBriefing | null>(null)
    const [loading, setLoading] = useState(false)

    // Fetch global briefing if not locked to anything
    useEffect(() => {
        let isMounted = true
        if (filter.country || filter.theme) {
            setGlobalData(null)
            return
        }

        const fetchGlobal = async () => {
            setLoading(true)
            try {
                const hours = timeRangeToHours(timeRange)
                const res = await fetch(`/api/v2/briefing?hours=${hours}`)
                if (!res.ok) throw new Error(`briefing ${res.status}`)
                const data = await res.json()
                if (isMounted) setGlobalData(data)
            } catch (e) {
                console.error('[SourceIntegrityPanel] Global fetch error', e)
            } finally {
                if (isMounted) setLoading(false)
            }
        }
        fetchGlobal()

        return () => { isMounted = false }
    }, [filter.country, filter.theme, timeRange])

    // Compute metrics
    const isLoading = focusLoading || loading
    let totalSignals = 0
    let uniqueSources = 0
    let topSources: Array<{ name: string; count: number }> = []

    if (summary) {
        totalSignals = summary.summary.total_signals
        uniqueSources = summary.nodes.reduce((acc, n) => acc + n.unique_sources, 0)
        topSources = summary.top_sources.map(s => ({ name: s.source, count: s.count }))
    } else if (globalData) {
        totalSignals = globalData.stats.total_signals
        uniqueSources = globalData.stats.sources
        topSources = globalData.top_sources.map(s => ({ name: s.source, count: s.count }))
    }

    const concentration = totalSignals > 0 && topSources.length > 0
        ? (topSources[0].count / totalSignals) * 100
        : 0

    // Approximate diversity score (0-100)
    const diversityScore = totalSignals > 0
        ? Math.min(100, Math.round((uniqueSources / Math.sqrt(totalSignals)) * 50))
        : 0

    // Quality proxy: inverse of concentration (highly concentrated = lower quality/higher bias risk)
    const qualityScore = Math.max(0, 100 - concentration * 1.5)



    return (
        <div className="source-panel-container">
            <div className="source-header">
                <div>SOURCE HEALTH: {filter.country ? filter.country : filter.theme ? filter.theme : 'GLOBAL AGGREGATE'}</div>
                {isLoading && <div className="loading-spinner" />}
            </div>

            <div className="source-content">
                <div className="metrics-grid">
                    <div className="metric-box">
                        <div className="metric-label">SOURCE DIVERSITY</div>
                        <div className={`metric-value ${diversityScore >= 80 ? 'good' : diversityScore >= 50 ? 'warn' : 'bad'}`}>
                            {totalSignals === 0 ? '--' : diversityScore.toFixed(0)}
                        </div>
                        <div className="metric-subtitle">how many different sources</div>
                    </div>
                    <div className="metric-box">
                        <div className="metric-label">SOURCE QUALITY</div>
                        <div className={`metric-value ${qualityScore >= 80 ? 'good' : qualityScore >= 50 ? 'warn' : 'bad'}`}>
                            {totalSignals === 0 ? '--' : qualityScore.toFixed(0)}
                        </div>
                        <div className="metric-subtitle">reliability of active sources</div>
                    </div>
                    <div className="metric-box">
                        <div className="metric-label">TOP SOURCE SHARE</div>
                        <div className={`metric-value ${concentration < 20 ? 'good' : concentration <= 40 ? 'warn' : 'bad'}`}>
                            {totalSignals === 0 ? '--' : `${concentration.toFixed(1)}%`}
                        </div>
                        <div className="metric-subtitle">% of signals from single source</div>
                    </div>
                </div>

                <div className="distribution-section">
                    <div className="section-title">MOST ACTIVE SOURCES</div>
                    <div className="bar-chart">
                        {topSources.length === 0 ? (
                            <div className="empty-state">No source data available</div>
                        ) : (
                            topSources.slice(0, 5).map((s, idx) => {
                                const pct = (s.count / totalSignals) * 100
                                return (
                                    <div key={idx} className="bar-row">
                                        <div className="source-name" title={s.name || 'Unknown'}>
                                            {(s.name || 'Unknown').length > 30 ? (s.name || '').substring(0, 30) + '...' : (s.name || 'Unknown')}
                                        </div>
                                        <div className="bar-track">
                                            <div className="bar-fill" style={{ width: `${pct}%` }}></div>
                                        </div>
                                        <div className="source-pct">{pct.toFixed(1)}%</div>
                                    </div>
                                )
                            })
                        )}
                    </div>
                </div>

                <div className="footer-stats">
                    Active Sources: <span className="highlight">{uniqueSources.toLocaleString()}</span> networks
                </div>
            </div>
        </div>
    )
}
