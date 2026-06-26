import { useEffect, useState } from 'react'
import './ConnectionsSection.css'

/**
 * "Where this fits" — the truncated-narrative-thread section (spec
 * 2026-06-26). Given a signal id (e.g. a forum post), shows the living
 * narrative threads it connects to, each basis-badged (member vs semantic)
 * with strength, plus the nearest verified evidence. Honest empty state when
 * nothing connects — never fabricates a connection. ADDITIVE (P-ADD): hosts
 * mount it alongside their existing content, never replacing it.
 */

interface ConnectedThread {
    thread_id: string
    label: string
    basis: 'member' | 'semantic'
    strength: number | null
    gate_kept?: boolean | null
}

interface Neighbor {
    signal_id: number
    headline: string
    country_code?: string | null
    source?: string | null
    url?: string | null
    similarity: number
    gate_status: 'assigned' | 'below_gate'
}

interface ContextResponse {
    connected_threads?: ConnectedThread[]
    semantic_neighbors?: Neighbor[]
    notes?: string[]
}

interface Props {
    signalId: number
    /** Open a connected thread by its slug (the thread_id). */
    onThreadClick?: (slug: string) => void
    hours?: number
}

function strengthPct(s: number | null): string {
    if (s == null) return ''
    // member strength is a gate_score (~0..1); semantic is a cosine sim.
    return `${Math.round(Math.min(1, Math.max(0, s)) * 100)}%`
}

export function ConnectionsSection({ signalId, onThreadClick, hours = 336 }: Props) {
    const [data, setData] = useState<ContextResponse | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        let ignore = false
        setLoading(true)
        fetch(`/api/v2/signal/${signalId}/context?hours=${hours}&neighbors=4`)
            .then(r => (r.ok ? r.json() : null))
            .then(d => { if (!ignore) { setData(d); setLoading(false) } })
            .catch(() => { if (!ignore) { setData(null); setLoading(false) } })
        return () => { ignore = true }
    }, [signalId, hours])

    if (loading) {
        return (
            <section className="connections-section">
                <div className="connections-label">Where this fits</div>
                <div className="connections-empty">Finding narrative connections…</div>
            </section>
        )
    }

    const threads = data?.connected_threads ?? []
    const neighbors = (data?.semantic_neighbors ?? []).slice(0, 3)
    const notEmbedded = (data?.notes ?? []).some(n => /not embedded/i.test(n))

    return (
        <section className="connections-section">
            <div className="connections-label">Where this fits</div>

            {threads.length === 0 ? (
                <div className="connections-empty">
                    {notEmbedded
                        ? 'Not analyzed yet — no narrative connection available for this item.'
                        : 'No strong narrative connection — this looks like local chatter, not part of a tracked thread.'}
                </div>
            ) : (
                <div className="connections-threads">
                    {threads.map(t => (
                        <button
                            key={t.thread_id}
                            className="connections-thread"
                            onClick={() => onThreadClick?.(t.thread_id)}
                            data-tip={`Open the "${t.label}" narrative thread`}
                        >
                            <span className={`connections-basis connections-basis--${t.basis}`}>
                                {t.basis === 'member' ? 'in thread' : 'related'}
                            </span>
                            <span className="connections-thread-label">{t.label}</span>
                            {t.strength != null && (
                                <span className="connections-strength">{strengthPct(t.strength)}</span>
                            )}
                        </button>
                    ))}
                </div>
            )}

            {neighbors.length > 0 && (
                <div className="connections-neighbors">
                    <div className="connections-sublabel">Nearest verified coverage</div>
                    {neighbors.map(n => (
                        <a
                            key={n.signal_id}
                            className="connections-neighbor"
                            href={n.url ?? '#'}
                            target="_blank"
                            rel="noopener noreferrer"
                            data-tip={`${n.source ?? ''} · ${Math.round(n.similarity * 100)}% similar`}
                        >
                            <span className={`connections-gate connections-gate--${n.gate_status}`}>
                                {n.gate_status === 'assigned' ? '✓' : '○'}
                            </span>
                            <span className="connections-neighbor-headline">{n.headline}</span>
                        </a>
                    ))}
                </div>
            )}
        </section>
    )
}
