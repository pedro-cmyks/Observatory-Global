import { useEffect, useState } from 'react'
import { addPin, getActiveInvestigationId, createInvestigation, setActiveInvestigation } from '../lib/workbench'
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
    basis: 'member' | 'semantic' | 'keyword'
    strength: number | null
    gate_kept?: boolean | null
    /** A forum post attached semantically — a discussion member, not evidence. */
    discussion?: boolean
    /** For keyword matches: the shared term(s) that linked the item to the thread. */
    shared?: string[]
}

function basisLabel(t: ConnectedThread): string {
    if (t.basis === 'member') return t.discussion ? 'discussed' : 'in story'
    if (t.basis === 'keyword') return 'keyword'
    return 'related'
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
    /** The item's headline — when present, the truncated thread can be PINNED (T4). */
    label?: string
}

function strengthPct(s: number | null): string {
    if (s == null) return ''
    // member strength is a gate_score (~0..1); semantic is a cosine sim.
    return `${Math.round(Math.min(1, Math.max(0, s)) * 100)}%`
}

export function ConnectionsSection({ signalId, onThreadClick, hours = 336, label }: Props) {
    const [data, setData] = useState<ContextResponse | null>(null)
    const [loading, setLoading] = useState(true)
    const [pinned, setPinned] = useState(false)

    // T4: pin the truncated thread — freeze WHERE this item connects, so the
    // investigation keeps the analyst's read even after the live data drifts.
    function pinTruncatedThread() {
        let invId = getActiveInvestigationId()
        if (!invId) {
            const inv = createInvestigation(label || `Item ${signalId}`)
            invId = inv.id
            setActiveInvestigation(inv.id)
        }
        const cts = data?.connected_threads ?? []
        addPin(invId, {
            anchorId: `truncated-${signalId}`,
            anchorType: 'connections',
            label: label || `Item ${signalId}`,
            open: { surface: 'signal_context', params: { signal_id: signalId } },
            snapshot: {
                capturedAt: new Date().toISOString(),
                summary: cts.length > 0
                    ? `Connects to ${cts.length} ${cts.length > 1 ? 'stories' : 'story'}: ${cts.slice(0, 2).map(t => t.label).join(', ')}`
                    : 'No strong narrative connection at pin time',
                metrics: { connectedThreads: cts.length },
                evidence: cts.slice(0, 3).map(t => ({
                    headline: `${basisLabel(t)} → ${t.label}${t.strength != null ? ` (${strengthPct(t.strength)})` : t.shared?.[0] ? ` (↔ ${t.shared[0]})` : ''}`,
                })),
            },
        })
        setPinned(true)
    }

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
            <div className="connections-head">
                <span className="connections-label">Where this fits</span>
                {label && (
                    <button
                        className={`connections-pin${pinned ? ' connections-pin--done' : ''}`}
                        onClick={pinTruncatedThread}
                        disabled={pinned}
                        data-tip={pinned ? 'Pinned to your investigation' : 'Pin this — freezes where it connects into your investigation'}
                    >
                        {pinned ? '📌 pinned' : '📌 pin'}
                    </button>
                )}
            </div>

            {threads.length === 0 ? (
                <div className="connections-empty">
                    {notEmbedded
                        ? 'Not analyzed yet — no narrative connection available for this item.'
                        : 'No strong narrative connection — this looks like local chatter, not part of a tracked story.'}
                </div>
            ) : (
                <div className="connections-threads">
                    {threads.map(t => (
                        <button
                            key={t.thread_id}
                            className="connections-thread"
                            onClick={() => onThreadClick?.(t.thread_id)}
                            data-tip={`Open the "${t.label}" story`}
                        >
                            <span className={`connections-basis connections-basis--${t.discussion ? 'discussion' : t.basis}`}>
                                {basisLabel(t)}
                            </span>
                            <span className="connections-thread-label">{t.label}</span>
                            {t.strength != null ? (
                                <span className="connections-strength">{strengthPct(t.strength)}</span>
                            ) : t.basis === 'keyword' && t.shared && t.shared.length > 0 ? (
                                <span className="connections-shared" data-tip={`Linked by the shared term "${t.shared[0]}"`}>↔ {t.shared[0]}</span>
                            ) : null}
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
