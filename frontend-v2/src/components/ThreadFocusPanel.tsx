import { useEffect, useMemo, useState } from 'react'
import type { LivingThreadSelection } from './NarrativeThreads'
import { PanelSkeleton } from './PanelSkeleton'
import './ThreadFocusPanel.css'

interface ThreadEvidence {
    id: string
    headline: string
    source: string
    url?: string
    country_code?: string
    country_name?: string
    timestamp?: string
    confidence?: number
    evidence_role?: string
}

type ThreadDetail = LivingThreadSelection & {
    avg_confidence?: number
    why_now?: string
    source_mix?: { top_sources?: string[]; source_count?: number }
    quality?: {
        lex_pct?: number
        method_mix?: { lex?: number; theme?: number }
        source_flags?: { aggregator_dominant?: boolean }
        geo_flags?: { unresolved_country_code?: boolean }
        entity_flags?: { raw_entity_field_untyped?: boolean }
    }
    related_threads?: Array<{ topic?: string; label?: string; co_signals?: number }>
    evidence_samples?: ThreadEvidence[]
}

interface ThreadFocusPanelProps {
    thread: LivingThreadSelection
    hours: number
    onClose: () => void
    onCountrySelect?: (code: string) => void
    onSourceClick?: (domain: string) => void
}

const formatCount = (value: number) => value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value.toLocaleString()

const Sparkline = ({ data, trend }: { data: Array<{ hour: string; count: number }>, trend: string }) => {
    if (!data || data.length < 2) return <div className="thread-focus-empty-chart">No timeline yet.</div>
    const max = Math.max(...data.map(point => point.count), 1)
    const points = data.map((point, index) => {
        const x = (index / (data.length - 1)) * 100
        const y = 34 - (point.count / max) * 30
        return `${x},${y}`
    }).join(' ')
    const stroke = trend === 'accelerating' ? '#ef4444' : trend === 'fading' ? '#64748b' : '#60a5fa'
    return (
        <svg className="thread-focus-chart" viewBox="0 0 100 36" preserveAspectRatio="none">
            <polyline points={points} stroke={stroke} />
        </svg>
    )
}

export function ThreadFocusPanel({ thread, hours, onClose, onCountrySelect, onSourceClick }: ThreadFocusPanelProps) {
    const [detail, setDetail] = useState<ThreadDetail | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [translations, setTranslations] = useState<Record<string, string>>({})

    useEffect(() => {
        const controller = new AbortController()
        setLoading(true)
        setError(null)
        fetch(`/api/v2/threads/${encodeURIComponent(thread.thread_id)}?hours=${hours}`, { signal: controller.signal })
            .then(response => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`)
                return response.json()
            })
            .then(payload => setDetail(payload.thread ? { ...payload.thread, label: thread.label } : thread))
            .catch(err => {
                if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'Failed to load thread')
            })
            .finally(() => {
                if (!controller.signal.aborted) setLoading(false)
            })
        return () => controller.abort()
    }, [thread, hours])

    // Lazy translation: when evidence samples land, ask the backend for
    // English versions. Backend caches per (signal_id, target_lang) so
    // repeat opens of the same panel are free. Renders original
    // headline regardless; the translation appears in italic underneath
    // when ready and only when it differs from the source.
    useEffect(() => {
        const samples = detail?.evidence_samples
        if (!samples || samples.length === 0) return
        const ids = samples
            .map(s => Number(s.id))
            .filter(n => Number.isFinite(n) && n > 0)
        if (ids.length === 0) return
        const controller = new AbortController()
        fetch('/api/v2/translate/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ signal_ids: ids, to: 'en' }),
            signal: controller.signal,
        })
            .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
            .then(payload => {
                const next: Record<string, string> = {}
                for (const t of (payload?.translations || [])) {
                    if (t.translated && typeof t.signal_id !== 'undefined') {
                        next[String(t.signal_id)] = t.translated
                    }
                }
                setTranslations(next)
            })
            .catch(() => { /* silent — frontend falls back to original */ })
        return () => controller.abort()
    }, [detail?.evidence_samples])

    const active: ThreadDetail = detail || thread
    const displayTrend = (active as any).trend === 'surging' ? 'accelerating' : active.trend
    const confidencePct = Math.round(((active.confidence_pct ?? ((active as ThreadDetail).avg_confidence || 0) * 100)) * 10) / 10
    const lexPct = active.quality?.lex_pct != null ? Math.round(active.quality.lex_pct * 1000) / 10 : null
    const topSources = active.source_mix?.top_sources || active.top_sources || []
    const countryPairs = useMemo(() => active.top_countries.map((code, index) => ({
        code,
        name: active.top_country_names[index] || code,
    })), [active.top_countries, active.top_country_names])

    return (
        <div className="thread-focus-panel">
            <div className="thread-focus-header">
                <div>
                    <div className="thread-focus-kicker">LIVING THREAD</div>
                    <h2>{active.label}</h2>
                </div>
                <button className="thread-focus-close" onClick={onClose} aria-label="Close thread focus">×</button>
            </div>

            {loading && <PanelSkeleton rows={4} />}
            {error && <div className="thread-focus-error">Could not load thread detail: {error}</div>}

            {!loading && !error && (
                <>
                    <p className="thread-focus-why">{active.why_now || `${formatCount(active.signal_count)} signals across ${active.country_count} countries.`}</p>

                    <div className="thread-focus-stats">
                        <div><strong>{formatCount(active.signal_count)}</strong><span>signals</span></div>
                        <div><strong>{active.country_count}</strong><span>countries</span></div>
                        <div><strong>{active.source_count}</strong><span>sources</span></div>
                        <div><strong>{confidencePct}%</strong><span>confidence</span></div>
                    </div>

                    <div className="thread-focus-section">
                        <div className="thread-focus-section-title">Where It Is Concentrated</div>
                        <div className="thread-focus-chip-row">
                            {countryPairs.map(country => (
                                <button key={country.code} className="thread-focus-chip" onClick={() => onCountrySelect?.(country.code)}>
                                    {country.code}<span>{country.name}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="thread-focus-section">
                        <div className="thread-focus-section-title">Movement</div>
                        <Sparkline data={active.hourly_timeline} trend={displayTrend} />
                        <div className="thread-focus-movement">
                            <span>{active.changed_10h > 0 ? '+' : ''}{active.changed_10h} signals in 10h</span>
                            <span>{displayTrend}</span>
                            {lexPct != null && <span>{lexPct}% lexical support</span>}
                        </div>
                    </div>

                    <div className="thread-focus-section">
                        <div className="thread-focus-section-title">Sources Driving It</div>
                        <div className="thread-focus-source-list">
                            {topSources.slice(0, 6).map((source: string) => (
                                <button key={source} onClick={() => onSourceClick?.(source)}>{source}</button>
                            ))}
                        </div>
                    </div>

                    <div className="thread-focus-section">
                        <div className="thread-focus-section-title">Evidence</div>
                        {(active.evidence_samples || []).length === 0 ? (
                            <div className="thread-focus-muted">Evidence samples are still being assembled for this thread.</div>
                        ) : (
                            <div className="thread-focus-evidence">
                                {(active.evidence_samples || []).slice(0, 6).map((sample: ThreadEvidence) => {
                                    const tr = translations[sample.id]
                                    const showTranslation = tr && tr !== sample.headline
                                    return (
                                        <a key={sample.id} href={sample.url || '#'} target="_blank" rel="noopener noreferrer">
                                            <strong>{sample.headline}</strong>
                                            {showTranslation && (
                                                <em className="thread-focus-evidence-translation">{tr}</em>
                                            )}
                                            <span>{sample.source} · {sample.country_name || sample.country_code || 'Global'} · {sample.evidence_role || 'evidence'}</span>
                                        </a>
                                    )
                                })}
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    )
}
