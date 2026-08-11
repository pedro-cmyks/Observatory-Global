import { useEffect, useState } from 'react'
import type { LivingThreadSelection } from './NarrativeThreads'
import { PanelSkeleton } from './PanelSkeleton'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { resolveCountryName } from '../lib/countryNames'
import { getSourceFamilyMeta } from '../lib/sourceFamily'
import { threadCountryPresentation } from '../lib/threadGeography'
import {
    confidenceBucketTip,
    confidenceBucketWord,
    resolveConfidenceBucket,
} from '../lib/threadConfidence'
import './ThreadFocusPanel.css'

interface ThreadPacket {
    graphSignals?: Array<{ headline: string; country: string | null; source: string; sentiment: number; url?: string }>
    countryBreakdown?: Array<{ code: string; count: number; sentiment: number }>
    topSources?: Array<{ name: string; count: number; sentiment: number; family?: string }>
    topPersons?: Array<{ name: string; count: number }>
    timeline?: Array<{ hour: string; count: number; sentiment: number }>
    lanes?: { media: number; social: number; state: number; other: number }
    relatedThemes?: Array<{ theme: string; count: number }>
    public_attention?: { trends?: unknown[]; wiki?: unknown[] } | null
}

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

interface NarrativeNote {
    lede: string
    movement: string
    evidence: string
    caveat?: string | null
    quality: 'strong' | 'provisional' | 'thin'
    source: string
}

type ThreadDetail = LivingThreadSelection & {
    avg_confidence?: number
    /** Served coarse band (thread_intelligence.confidence_band) on the detail payload. */
    confidence?: string
    why_now?: string
    narrative_note?: NarrativeNote | null
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
    packet?: ThreadPacket | null
}

interface ThreadFocusPanelProps {
    thread: LivingThreadSelection
    hours: number
    onClose: () => void
    onCountrySelect?: (code: string) => void
    onSourceClick?: (domain: string) => void
}

const formatCount = (value: number) => value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value.toLocaleString()
const getSentimentColor = (s: number) => s > 0.1 ? '#4ade80' : s < -0.1 ? '#f87171' : '#fbbf24'

const Sparkline = ({ data, trend }: { data: Array<{ hour: string; count: number }>, trend: string }) => {
    if (!data || data.length < 2) return <div className="thread-focus-empty-chart">No timeline yet.</div>
    const max = Math.max(...data.map(point => point.count), 1)
    const points = data.map((point, index) => {
        const x = (index / (data.length - 1)) * 100
        const y = 34 - (point.count / max) * 30
        return `${x},${y}`
    }).join(' ')
    // Growth ≠ danger (dataviz audit fix 3): accelerating = positive accent, not critical red.
    const stroke = trend === 'accelerating' ? '#4ade80' : trend === 'fading' ? '#64748b' : '#60a5fa'
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
        fetch(`/api/v2/threads/${encodeURIComponent(thread.thread_id)}?hours=${hours}&llm=1`, { signal: controller.signal })
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
    // N14 (council R4): the stat tile reads the served BAND, never a raw
    // percent — the detail payload carries `confidence` (confidence_band) and
    // the row carries the bucket already folded by the threads panel.
    const confidenceBucket = resolveConfidenceBucket({
        band: (active as ThreadDetail).confidence ?? active.confidence_band ?? null,
        avgConfidence: (active as ThreadDetail).avg_confidence ?? null,
    })
    const lexPct = active.quality?.lex_pct != null ? Math.round(active.quality.lex_pct * 1000) / 10 : null
    const topSources = active.source_mix?.top_sources || active.top_sources || []
    const geography = threadCountryPresentation(active)
    const countryPairs = geography.codes.map((code, index) => ({
        code,
        name: geography.names[index] || resolveCountryName(code, code),
    }))

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
                    {active.narrative_note ? (
                        <section className={`thread-focus-note thread-focus-note-${active.narrative_note.quality}`}>
                            <p className="thread-focus-note-lede">{active.narrative_note.lede}</p>
                            <p>{active.narrative_note.movement}</p>
                            <p>{active.narrative_note.evidence}</p>
                            {active.narrative_note.caveat && (
                                <p className="thread-focus-note-caveat">{active.narrative_note.caveat}</p>
                            )}
                        </section>
                    ) : (
                        <p className="thread-focus-why">{active.why_now || `${formatCount(active.signal_count)} signals across ${active.country_count} countries.`}</p>
                    )}

                    <div className="thread-focus-stats">
                        <div><strong>{formatCount(active.signal_count)}</strong><span>signals</span></div>
                        <div><strong>{active.country_count}</strong><span>countries</span></div>
                        <div><strong>{active.source_count}</strong><span>sources</span></div>
                        <div data-tip={confidenceBucketTip(confidenceBucket.bucket, confidenceBucket.source)}>
                            <strong>{confidenceBucketWord(confidenceBucket.bucket)}</strong><span>confidence</span>
                        </div>
                    </div>

                    <div className="thread-focus-section">
                        <div className="thread-focus-section-title">{geography.label} Geography</div>
                        <div className="thread-focus-chip-row">
                            {countryPairs.map(country => (
                                <button key={country.code} className="thread-focus-chip" onClick={() => onCountrySelect?.(country.code)}>
                                    {country.code}<span>{country.name}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="thread-focus-section">
                        <div className="thread-focus-section-title">10h Signal Change</div>
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

                    {/* PACKET: Sentiment Timeline */}
                    {!!active.packet?.timeline?.length && (
                        <div className="thread-focus-section">
                            <div className="thread-focus-section-title">Activity Timeline</div>
                            <div className="thread-focus-timeline-chart">
                                {active.packet.timeline!.map((t, i) => (
                                    <div
                                        key={i}
                                        className="thread-focus-timeline-bar"
                                        style={{
                                            height: `${Math.max(10, (t.count / Math.max(...active.packet!.timeline!.map(x => x.count))) * 100)}%`,
                                            backgroundColor: getSentimentColor(t.sentiment),
                                        }}
                                        data-tip={`${t.hour}: ${t.count} signals`}
                                    />
                                ))}
                            </div>
                            <div className="thread-focus-timeline-legend">
                                <span><span className="thread-focus-legend-dot" style={{ background: '#4ade80' }} /> Positive</span>
                                <span><span className="thread-focus-legend-dot" style={{ background: '#fbbf24' }} /> Neutral</span>
                                <span><span className="thread-focus-legend-dot" style={{ background: '#f87171' }} /> Negative</span>
                            </div>
                        </div>
                    )}

                    {/* PACKET: Country Edges */}
                    {!!active.packet?.countryBreakdown?.length && (
                        <div className="thread-focus-section">
                            <div className="thread-focus-section-title">Country Breakdown</div>
                            <div className="thread-focus-country-breakdown">
                                {active.packet.countryBreakdown!.slice(0, 10).map(c => (
                                    <button
                                        key={c.code}
                                        className="thread-focus-country-row"
                                        onClick={() => onCountrySelect?.(c.code)}
                                        data-tip={`${resolveCountryName(c.code)} · ${c.count} signals · tone ${c.sentiment > 0 ? '+' : ''}${c.sentiment.toFixed(2)}`}
                                    >
                                        <span className="thread-focus-country-code">{c.code}</span>
                                        <span className="thread-focus-country-name">{resolveCountryName(c.code)}</span>
                                        <span className="thread-focus-country-count">{c.count}</span>
                                        <span
                                            className="thread-focus-country-sentiment"
                                            style={{ color: getSentimentColor(c.sentiment) }}
                                        >
                                            {c.sentiment > 0 ? '+' : ''}{c.sentiment.toFixed(2)}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* PACKET: Source Lanes + Top Sources */}
                    {(!!active.packet?.lanes || !!active.packet?.topSources?.length) && (
                        <div className="thread-focus-section">
                            <div className="thread-focus-section-title">Source Lanes</div>
                            {active.packet?.lanes && (
                                <div className="thread-focus-lane-chips">
                                    {active.packet.lanes.media > 0 && (
                                        <span className="thread-focus-lane-chip thread-focus-lane-media" data-tip="Media outlets">
                                            media <strong>{active.packet.lanes.media}</strong>
                                        </span>
                                    )}
                                    {active.packet.lanes.state > 0 && (
                                        <span className="thread-focus-lane-chip thread-focus-lane-state" data-tip="State-affiliated sources">
                                            state <strong>{active.packet.lanes.state}</strong>
                                        </span>
                                    )}
                                    {active.packet.lanes.social > 0 && (
                                        <span className="thread-focus-lane-chip thread-focus-lane-social" data-tip="Social / wire sources">
                                            social <strong>{active.packet.lanes.social}</strong>
                                        </span>
                                    )}
                                    {active.packet.lanes.other > 0 && (
                                        <span className="thread-focus-lane-chip thread-focus-lane-other" data-tip="Other sources">
                                            other <strong>{active.packet.lanes.other}</strong>
                                        </span>
                                    )}
                                </div>
                            )}
                            {!!active.packet?.topSources?.length && (
                                <div className="thread-focus-packet-source-list">
                                    {active.packet.topSources!.slice(0, 8).map(s => {
                                        const family = getSourceFamilyMeta(s.family)
                                        return (
                                            <div
                                                key={s.name}
                                                className="thread-focus-packet-source-row"
                                                data-tip={`${family.tip} · tone ${s.sentiment > 0 ? '+' : ''}${s.sentiment.toFixed(2)}`}
                                            >
                                                <button
                                                    className="thread-focus-packet-source-name"
                                                    onClick={() => onSourceClick?.(s.name)}
                                                >
                                                    {s.name}
                                                </button>
                                                <span className={`thread-focus-source-family-badge ${family.className}`}>{family.label}</span>
                                                <span className="thread-focus-packet-source-count">{s.count}</span>
                                                <span
                                                    className="thread-focus-packet-source-sentiment"
                                                    style={{ color: getSentimentColor(s.sentiment) }}
                                                >
                                                    {s.sentiment > 0 ? '+' : ''}{s.sentiment.toFixed(2)}
                                                </span>
                                            </div>
                                        )
                                    })}
                                </div>
                            )}
                        </div>
                    )}

                    {/* PACKET: Related Themes */}
                    {!!active.packet?.relatedThemes?.length && (
                        <div className="thread-focus-section">
                            <div className="thread-focus-section-title">Related Topics</div>
                            <div className="thread-focus-chip-row">
                                {active.packet.relatedThemes!.slice(0, 8).map(t => (
                                    <span key={t.theme} className="thread-focus-related-chip" data-tip={`${t.count} co-occurrences`}>
                                        <span className="thread-focus-related-icon">{getThemeIcon(t.theme)}</span>
                                        <span className="thread-focus-related-label">{getThemeLabel(t.theme)}</span>
                                        <span className="thread-focus-related-count">{t.count}</span>
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* PACKET: Public Attention */}
                    {(!!(active.packet?.public_attention?.trends as unknown[] | undefined)?.length ||
                      !!(active.packet?.public_attention?.wiki as unknown[] | undefined)?.length) && (
                        <div className="thread-focus-section">
                            <div className="thread-focus-section-title">Public Attention</div>
                            <div className="thread-focus-attention-row">
                                {!!(active.packet!.public_attention!.trends as unknown[])?.length && (
                                    <div className="thread-focus-attention-card">
                                        <span className="thread-focus-attention-icon">SEARCH</span>
                                        <div>
                                            <div className="thread-focus-attention-label">People are searching for this</div>
                                            <div className="thread-focus-attention-detail">
                                                {(active.packet!.public_attention!.trends as Array<{ keyword?: string; title?: string }>)
                                                    .slice(0, 3)
                                                    .map((item, i) => (
                                                        <span key={i} className="thread-focus-trending-kw">
                                                            {item.keyword ?? item.title ?? ''}
                                                        </span>
                                                    ))}
                                            </div>
                                        </div>
                                    </div>
                                )}
                                {!!(active.packet!.public_attention!.wiki as unknown[])?.length && (
                                    <div className="thread-focus-attention-card">
                                        <span className="thread-focus-attention-icon">WIKI</span>
                                        <div>
                                            <div className="thread-focus-attention-label">Wikipedia activity</div>
                                            <div className="thread-focus-attention-detail">
                                                {(active.packet!.public_attention!.wiki as Array<{ title?: string; views?: number }>)
                                                    .slice(0, 3)
                                                    .map((item, i) => (
                                                        <span key={i} className="thread-focus-wiki-article">{item.title ?? ''}</span>
                                                    ))}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}
