import React, { useEffect, useState } from 'react'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { decodeEntities } from '../lib/decodeEntities'
import { resolveCountryName } from '../lib/countryNames'
import { buildKeySubjects, type SubjectType } from '../lib/countryBriefSubjects'
import { resolveTierChip } from '../lib/sourceProvenance'
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

// "Where this fits" (#168/#234 truncated-thread connection): the living threads
// this signal connects to. `basis` = how the link was made:
//   member  — the signal is assigned to the thread (gate may be kept/below)
//   semantic — connected via its nearest embedding neighbours' thread
//   keyword  — fallback: headline keywords overlap a living thread label
// This is the Atlas replacement for the GDELT-taxonomy "relates to" chips.
interface ConnectedThread {
    thread_id: string
    label: string
    basis: 'member' | 'semantic' | 'keyword'
    strength: number | null
    discussion?: boolean
    gate_kept?: boolean | null
    shared?: string[]
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
    connected_threads: ConnectedThread[]
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
    /** Original language of the headline (ISO 639-1), for translation toggle */
    source_lang?: string | null
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
    /** Task 5.5 — open a semantic neighbor in-app (swap the panel to it) instead
     *  of only leaking to its external URL. The parent controls `signal`, so it
     *  just re-points at the neighbor and the panel re-fetches ITS context. */
    onSignalOpen?: (signal: Signal) => void
}

// R3c defect 8: theme vars — noir's var values ARE these literals
// (#4ade80 / #f87171 / #94a3b8), so intel-noir renders byte-identically.
const getSentimentColor = (s: number) => {
    if (s > 0.1) return 'var(--color-sentiment-positive)'
    if (s < -0.1) return 'var(--color-sentiment-negative)'
    return 'var(--color-sentiment-neutral)'
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

// A semantic neighbor carries only identity + provenance (signal_id, headline,
// country, source, url) — not sentiment/themes/persons (there is no single-
// signal-by-id endpoint on the backend). Opening it in-app swaps the panel to
// this neighbor; the panel then re-fetches ITS context (connected threads +
// neighbors) by id. The unavailable fields render as empty/neutral — an honest
// absence (themes/persons show nothing), never a fabricated value; a fuller
// open would need a backend signal-by-id endpoint (follow-up).
function neighborToSignal(n: SemanticNeighbor): Signal {
    return {
        id: n.signal_id,
        timestamp: '',
        country: n.country_code ?? '',
        source: n.source ?? '',
        url: n.url ?? '',
        headline: n.headline,
        sentiment: 0,
        themes: [],
        persons: [],
    }
}

export const SignalDetailPanel: React.FC<Props> = ({
    signal, onClose, onThemeClick, onCountryClick, onPersonClick, allowlist = [],
    relatedSignals, onPin, isPinned, onSignalOpen
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
                        {signal.headline ? decodeEntities(signal.headline) : `Signal from ${signal.source}`}
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
                        {(() => {
                            // Gold-eval defect: this header carried no tier reference — no
                            // origin/is_state_media on this shape, so 'unknown' is
                            // suppressed rather than guessed (absence over noise).
                            const tc = resolveTierChip(signal.source, undefined)
                            return tc.tier !== 'unknown' ? (
                                <span className={`l2-tier-chip l2-tier-chip--${tc.tier}`} data-tip={tc.tip}>{tc.label}</span>
                            ) : null
                        })()}
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

                    {/* WHERE THIS FITS — the living Narrative Threads this signal
                        connects to (#168/#234 truncated-thread connection). The
                        Atlas story model, primary. Replaces the old GDELT-taxonomy
                        "relates to" with thread connections (member / semantic /
                        keyword). When NOTHING connects we say so honestly instead
                        of hiding it — a missing connection is a gap to surface,
                        not a fact of nature (no silent filtering). */}
                    {context && (
                        <div>
                            <div
                                className="sdp-section-label"
                                data-tip="The living Narrative Threads this signal belongs to or connects to. IN THREAD = assigned membership; RELATED = linked via nearest-meaning neighbours; KEYWORD = headline-term overlap with a thread."
                            >
                                Where this fits
                            </div>
                            {context.connected_threads.length > 0 ? (
                                <div className="sdp-tags">
                                    {context.connected_threads.map(t => {
                                        const unverified = t.gate_kept === false || t.discussion === true
                                        const badge = t.basis === 'member'
                                            ? (unverified ? 'UNVERIFIED' : 'IN THREAD')
                                            : t.basis === 'semantic'
                                                ? `RELATED${t.strength != null ? ` ${Math.round(t.strength * 100)}%` : ''}`
                                                : 'KEYWORD'
                                        const tip = t.basis === 'member'
                                            ? (unverified ? 'Assigned to this thread but below the quality gate — unverified membership' : 'Verified thread membership')
                                            : t.basis === 'semantic'
                                                ? 'Connected via its nearest-meaning neighbours — not a direct membership'
                                                : `Headline-keyword overlap${t.shared?.length ? `: ${t.shared.join(', ')}` : ''} — weakest link, no embedding yet`
                                        return (
                                            <span
                                                key={`${t.basis}-${t.thread_id}`}
                                                className={`sdp-thread-tag${unverified || t.basis !== 'member' ? ' sdp-thread-tag--belowgate' : ''}`}
                                                data-tip={tip}
                                                onClick={() => { onThemeClick(t.thread_id); onClose(); }}
                                            >
                                                {decodeEntities(t.label)}
                                                <span className={`sdp-basis-badge sdp-basis-badge--${t.basis}`}>{badge}</span>
                                            </span>
                                        )
                                    })}
                                </div>
                            ) : (
                                <div className="sdp-empty-connect" data-tip="This signal isn't linked to any living thread yet — it may not be embedded (nightly NER/embed lag) or no thread matches. The connection is missing, not absent by design.">
                                    Not connected to a living thread yet
                                    {context.notes.length > 0 && (
                                        <span className="sdp-empty-note"> · {context.notes[0]}</span>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {signal.themes.length > 0 && (
                        <details className="sdp-taxonomy-details">
                            <summary
                                className="sdp-section-label sdp-section-label--taxonomy"
                                data-tip="GDELT taxonomy codes — a navigation index, not the story model. 'Where this fits' above is the product unit. Collapsed by default; being phased out of the surface."
                            >
                                GDELT Taxonomy · {signal.themes.length}
                            </summary>
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
                        </details>
                    )}

                    {signal.persons.length > 0 && (() => {
                        // J: the raw GDELT persons array carries orgs/places
                        // mistyped as people ("nvidia gpus"). Type via the shared
                        // subjects gazetteer; only real persons stay clickable.
                        const SDP_BADGE: Record<SubjectType, string> = {
                            person: 'person', place: 'place', organization: 'org',
                            group: 'group', event: 'event',
                        }
                        const subjects = buildKeySubjects(
                            signal.persons.map(name => ({ name, count: 1 })), 12)
                        if (subjects.length === 0) return null
                        return (
                            <div>
                                <div className="sdp-section-label">Key Subjects</div>
                                <div className="sdp-tags">
                                    {subjects.map(s => (
                                        <span
                                            key={`${s.type}:${s.name}`}
                                            className={`sdp-person-tag${s.type === 'person' ? '' : ' sdp-person-tag--static'}`}
                                            data-tip={s.type === 'person' ? undefined : SDP_BADGE[s.type]}
                                            onClick={s.type === 'person' ? () => { onPersonClick(s.name); onClose(); } : undefined}
                                        >
                                            {s.name}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )
                    })()}

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
                                    <div key={n.signal_id} className="sdp-related-row sdp-related-row--nav">
                                        {/* Task 5.5 — in-app open (primary) instead of leaking
                                            straight to the external URL. Opens the neighbor in
                                            this panel to explore ITS threads + neighbors; falls
                                            back to scoping the stream to its country when no
                                            in-app opener is wired. The original stays as a small
                                            secondary "read original" escape. */}
                                        <button
                                            type="button"
                                            className="sdp-related-open"
                                            data-tip={onSignalOpen
                                                ? 'Open this neighbor in-app — explore its connected threads and neighbors'
                                                : 'Scope the stream to this neighbor’s country'}
                                            onClick={() => {
                                                if (onSignalOpen) onSignalOpen(neighborToSignal(n))
                                                else if (n.country_code) onCountryClick(n.country_code)
                                            }}
                                        >
                                            <span className="sdp-related-headline">{decodeEntities(n.headline)}</span>
                                            <div className="sdp-related-meta">
                                                {n.country_code && (
                                                    <span className="sdp-related-country">{resolveCountryName(n.country_code, n.country_code)}</span>
                                                )}
                                                {n.source && <span className="sdp-related-source">{n.source}</span>}
                                                {n.source && (() => {
                                                    const tc = resolveTierChip(n.source, undefined)
                                                    return tc.tier !== 'unknown' ? (
                                                        <span className={`l2-tier-chip l2-tier-chip--${tc.tier}`} data-tip={tc.tip}>{tc.label}</span>
                                                    ) : null
                                                })()}
                                                <span className="sdp-similarity">{Math.round(n.similarity * 100)}%</span>
                                                {n.gate_status === 'below_gate' && (
                                                    <span className="sdp-gate-badge">UNVERIFIED</span>
                                                )}
                                            </div>
                                        </button>
                                        {n.url && (
                                            <a
                                                className="sdp-related-original"
                                                href={n.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                data-tip="Read the original article"
                                            >↗</a>
                                        )}
                                    </div>
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
                                        <span className="sdp-related-headline">{r.headline ? decodeEntities(r.headline) : `Signal from ${r.source}`}</span>
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
