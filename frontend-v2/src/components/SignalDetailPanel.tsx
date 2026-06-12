import React, { useEffect, useState } from 'react'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { resolveCountryName } from '../lib/countryNames'
import './SignalDetailPanel.css'

// Per-signal narrative context (#228 §2.3): the Narrative Threads this signal
// belongs to (primary story model) + semantic neighbors from the embedding
// corpus. Replaces the old related-by-any-shared-GDELT-theme heuristic.
interface SignalThreadRef {
    slug: string
    label: string
    gate_kept: boolean | null
    gate_score: number | null
}

interface SemanticNeighbor {
    signal_id: number
    headline: string
    country_code?: string | null
    source?: string | null
    url?: string | null
    similarity: number
    gate_status: 'assigned' | 'below_gate'
}

interface SignalContext {
    threads: SignalThreadRef[]
    semantic_neighbors: SemanticNeighbor[]
    notes: string[]
}

export interface Signal {
    id: number
    timestamp: string
    country: string
    source: string
    url: string
    headline: string | null
    snippet?: string | null
    sentiment: number
    themes: string[]
    persons: string[]
    /** Stream lane from backend relevance scoring (#177): analyst|sports|entertainment|general */
    lane?: 'analyst' | 'sports' | 'entertainment' | 'general'
    relevanceScore?: number
    framing?: string | null
}

interface Props {
    signal: Signal
    onClose: () => void
    onThemeClick: (theme: string) => void
    onCountryClick: (country: string) => void
    onPersonClick: (person: string) => void
    allowlist?: string[]
    relatedSignals?: Signal[]
    onPin?: () => void
    isPinned?: boolean
}

const getSentimentColor = (s: number) => {
    if (s > 0.1) return '#4ade80'
    if (s < -0.1) return '#f87171'
    return '#94a3b8'
}

const getSentimentLabel = (s: number) => {
    if (s > 1) return 'POSITIVE'
    if (s > 0.1) return 'SLIGHT POS'
    if (s < -1) return 'NEGATIVE'
    if (s < -0.1) return 'SLIGHT NEG'
    return 'NEUTRAL'
}

const formatTimestamp = (ts: string) => {
    try {
        return new Date(ts).toLocaleString(undefined, {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        })
    } catch {
        return ts
    }
}

const barLeft = (s: number) => {
    const clamped = Math.max(-3, Math.min(3, s))
    if (clamped >= 0) {
        return { left: '50%', width: `${(clamped / 3) * 50}%` }
    }
    const w = (Math.abs(clamped) / 3) * 50
    return { left: `${50 - w}%`, width: `${w}%` }
}

export const SignalDetailPanel: React.FC<Props> = ({
    signal, onClose, onThemeClick, onCountryClick, onPersonClick, allowlist = [],
    relatedSignals, onPin, isPinned
}) => {
    const [context, setContext] = useState<SignalContext | null>(null)

    useEffect(() => {
        let cancelled = false
        setContext(null)
        fetch(`/api/v2/signal/${signal.id}/context?hours=168`)
            .then(r => r.ok ? r.json() : null)
            .then(d => { if (!cancelled && d) setContext(d) })
            .catch(() => { /* context is enrichment — panel works without it */ })
        return () => { cancelled = true }
    }, [signal.id])

    const getSourceClass = (source: string) => {
        const s = source.toLowerCase()
        if (allowlist.some(a => s.includes(a.toLowerCase()))) return 'source-trusted'
        if (s.includes('yahoo') || s.includes('msn') || s.includes('aol') || s.includes('newsbreak')) return 'source-tabloid'
        return ''
    }

    const barStyle = barLeft(signal.sentiment)
    const sentimentColor = getSentimentColor(signal.sentiment)

    const handleOverlayClick = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) onClose()
    }

    return (
        <div className="signal-detail-overlay" onClick={handleOverlayClick}>
            <div className="signal-detail-panel">
                <div className="sdp-header">
                    <span className="sdp-label">Signal Detail</span>
                    <button className="sdp-close" onClick={onClose}>×</button>
                </div>

                <div className="sdp-body">
                    <div className="sdp-headline">
                        {signal.headline || `Signal from ${signal.source}`}
                    </div>

                    {signal.snippet && (
                        <p className="sdp-snippet">{signal.snippet}</p>
                    )}

                    <div className="sdp-meta-row">
                        <span
                            className="sdp-country clickable"
                            onClick={() => { onCountryClick(signal.country); onClose(); }}
                        >
                            {signal.country || 'GLO'}
                        </span>
                        <span className={`sdp-source ${getSourceClass(signal.source)}`}>
                            {signal.source}
                        </span>
                        <span className="sdp-time">{formatTimestamp(signal.timestamp)}</span>
                    </div>

                    <div className="sdp-divider" />

                    <div>
                        <div className="sdp-section-label">Sentiment</div>
                        <div className="sdp-sentiment-row">
                            <span className="sdp-sentiment-label" style={{ color: sentimentColor }}>
                                {getSentimentLabel(signal.sentiment)}
                            </span>
                            <div className="sdp-sentiment-bar-track">
                                <div
                                    className="sdp-sentiment-bar-fill"
                                    style={{
                                        left: barStyle.left,
                                        width: barStyle.width,
                                        background: sentimentColor,
                                    }}
                                />
                            </div>
                            <span className="sdp-sentiment-value">
                                {signal.sentiment > 0 ? '+' : ''}{signal.sentiment.toFixed(2)}
                            </span>
                        </div>
                    </div>

                    {/* NARRATIVE THREADS — the product story model, primary.
                        GDELT taxonomy demoted below (#228 §2.3). */}
                    {context && context.threads.length > 0 && (
                        <div>
                            <div className="sdp-section-label">Narrative Threads</div>
                            <div className="sdp-tags">
                                {context.threads.map(t => (
                                    <span
                                        key={t.slug}
                                        className={`sdp-thread-tag${t.gate_kept === false ? ' sdp-thread-tag--belowgate' : ''}`}
                                        data-tip={t.gate_kept === false
                                            ? 'Assigned to this thread but below the quality gate — unverified membership'
                                            : 'Verified thread membership'}
                                        onClick={() => { onThemeClick(t.slug); onClose(); }}
                                    >
                                        {t.label}
                                        {t.gate_kept === false && <span className="sdp-gate-badge">UNVERIFIED</span>}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {signal.themes.length > 0 && (
                        <div>
                            <div
                                className="sdp-section-label sdp-section-label--taxonomy"
                                data-tip="GDELT taxonomy codes — a navigation index, not the story model. Narrative Threads above are the product unit."
                            >
                                GDELT Taxonomy
                            </div>
                            <div className="sdp-tags sdp-tags--taxonomy">
                                {signal.themes.map(t => (
                                    <span
                                        key={t}
                                        className="sdp-theme-tag"
                                        onClick={() => { onThemeClick(t); onClose(); }}
                                    >
                                        {getThemeIcon(t)} {getThemeLabel(t)}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {signal.persons.length > 0 && (
                        <div>
                            <div className="sdp-section-label">People</div>
                            <div className="sdp-tags">
                                {signal.persons.map(p => (
                                    <span
                                        key={p}
                                        className="sdp-person-tag"
                                        onClick={() => { onPersonClick(p); onClose(); }}
                                    >
                                        {p}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* SEMANTIC NEIGHBORS — nearest signals in embedding space,
                        each labeled with similarity + gate status. Replaces the
                        related-by-shared-GDELT-theme heuristic (which connected
                        a Pakistan blast to an Illinois tornado) and its dead
                        onClick. Falls back to the legacy prop only while the
                        context fetch is in flight. */}
                    {context && context.semantic_neighbors.length > 0 ? (
                        <div>
                            <div
                                className="sdp-section-label"
                                data-tip="Nearest signals by meaning (multilingual embedding similarity), not by shared taxonomy code. Similarity shown per item; UNVERIFIED = not assigned to any gated thread."
                            >
                                Semantic Neighbors
                            </div>
                            <div className="sdp-related-list">
                                {context.semantic_neighbors.map(n => (
                                    <a
                                        key={n.signal_id}
                                        className="sdp-related-row sdp-related-row--link"
                                        href={n.url ?? undefined}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        data-tip="Open original article"
                                    >
                                        <span className="sdp-related-headline">{n.headline}</span>
                                        <div className="sdp-related-meta">
                                            {n.country_code && (
                                                <span className="sdp-related-country">{resolveCountryName(n.country_code, n.country_code)}</span>
                                            )}
                                            {n.source && <span className="sdp-related-source">{n.source}</span>}
                                            <span className="sdp-similarity">{Math.round(n.similarity * 100)}%</span>
                                            {n.gate_status === 'below_gate' && (
                                                <span className="sdp-gate-badge">UNVERIFIED</span>
                                            )}
                                        </div>
                                    </a>
                                ))}
                            </div>
                        </div>
                    ) : !context && relatedSignals && relatedSignals.length > 0 && (
                        <div>
                            <div className="sdp-section-label">Related Signals</div>
                            <div className="sdp-related-list">
                                {relatedSignals.map(r => (
                                    <a
                                        key={r.id}
                                        className="sdp-related-row sdp-related-row--link"
                                        href={r.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        <span className="sdp-related-headline">{r.headline || `Signal from ${r.source}`}</span>
                                        <div className="sdp-related-meta">
                                            <span className="sdp-related-country">{r.country || 'GLO'}</span>
                                            <span className="sdp-related-source">{r.source}</span>
                                        </div>
                                    </a>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                <div className="sdp-footer">
                    {onPin && (
                        <button className={`sdp-pin-btn${isPinned ? ' pinned' : ''}`} onClick={onPin}
                            data-tip={isPinned ? 'Unpin from Workspace' : 'Pin to Workspace'}>
                            {isPinned ? '— Unpin' : '+ Pin'}
                        </button>
                    )}
                    <a className="sdp-read-btn" href={signal.url} target="_blank" rel="noopener noreferrer">
                        Read original ↗
                    </a>
                </div>
            </div>
        </div>
    )
}
