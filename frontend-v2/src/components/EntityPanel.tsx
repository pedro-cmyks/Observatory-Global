import { useState, useEffect } from 'react'
import { getThemeLabel, resolveThreadLabel } from '../lib/themeLabels'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { buildKeySubjects, type SubjectType } from '../lib/countryBriefSubjects'

const SUBJECT_BADGE: Record<SubjectType, string> = {
    person: 'person', place: 'place', organization: 'org', group: 'group', event: 'event',
}
import { buildGeoNarrative } from '../lib/geoNarrative'
import { groupThemeTopics } from '../lib/themeHierarchy'
import { Pin, PinOff } from '../lib/icons'
import { CompareSearchModal } from './CompareSearchModal'
import PinReceiptButton from './PinReceiptButton'
import { EvidenceRoute } from './EvidenceRoute'
import { buildPersonEvidenceRoute } from '../lib/evidenceRoute'
import { receiptFrom } from '../lib/capturePayloads'
import './EntityPanel.css'

interface FocusNode {
    country_code: string
    signal_count: number
    avg_sentiment: number
    unique_sources: number
}

interface FocusData {
    summary: { total_signals: number; total_countries: number }
    nodes: FocusNode[]
    related_topics: Array<{ topic: string; count: number }>
    top_sources: Array<{ source: string; count: number; avg_sentiment: number }>
    headlines: Array<{ url: string; source: string; headline: string | null; time: string | null }>
    key_people: Array<{ person: string; signal_count: number; avg_sentiment: number; country_count: number }>
    key_subjects?: Array<{ name: string; type: SubjectType; signal_count: number; unverified?: boolean }>
}

interface EntityPanelProps {
    focusType: 'person' | 'theme'
    focusValue: string
    onClose: () => void
    onThemeSelect?: (theme: string) => void
    onCountrySelect?: (code: string) => void
    onSourceClick?: (domain: string) => void
    onCompareClick?: (person: string) => void
    onPersonSelect?: (name: string) => void
    inline?: boolean
}

function sentimentColor(s: number): string {
    if (s > 0.5) return '#4ade80'
    if (s < -0.5) return '#f87171'
    return '#fbbf24'
}

function sentimentLabel(s: number): string {
    if (s > 1) return 'positive'
    if (s > 0.2) return 'slightly positive'
    if (s < -1) return 'negative'
    if (s < -0.2) return 'slightly negative'
    return 'neutral'
}

function formatCount(n: number): string {
    if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
    return String(n)
}

export function EntityPanel({ focusType, focusValue, onClose, onThemeSelect, onCountrySelect, onSourceClick, onCompareClick, onPersonSelect, inline }: EntityPanelProps) {
    const cls = `entity-panel${inline ? ' entity-panel--inline' : ''}`
    const [data, setData] = useState<FocusData | null>(null)
    const [loading, setLoading] = useState(true)
    const [showCompareModal, setShowCompareModal] = useState(false)
    // The panel owns its window now (VIEW selector retired 2026-07-15):
    // entity focus reads the live day, like the map it re-scopes.
    const hours = 24
    const { pinItem, unpinItem, isPinned } = useWorkspace()

    useEffect(() => {
        setLoading(true)
        setData(null)
        const params = new URLSearchParams({
            focus_type: focusType,
            value: focusValue,
            hours: String(hours)
        })
        fetch(`/api/v2/focus?${params}`)
            .then(r => r.ok ? r.json() : null)
            .then(json => { if (json) setData(json) })
            .catch(() => {})
            .finally(() => setLoading(false))
    }, [focusType, focusValue, hours])

    // Truncated-thread connections (spec T3, P-ADD): the living threads this
    // person participates in. Reuses the precise /threads?person= relation (#234).
    const [personThreads, setPersonThreads] = useState<Array<{ thread_id: string; label: string; signal_count: number; discussion_count?: number }>>([])
    useEffect(() => {
        if (focusType !== 'person') { setPersonThreads([]); return }
        let ignore = false
        fetch(`/api/v2/threads?hours=${hours}&person=${encodeURIComponent(focusValue)}&limit=8`)
            .then(r => r.ok ? r.json() : null)
            .then(d => { if (!ignore) setPersonThreads(d?.threads ?? []) })
            .catch(() => { if (!ignore) setPersonThreads([]) })
        return () => { ignore = true }
    }, [focusType, focusValue, hours])

    const displayName = focusType === 'person'
        ? focusValue.replace(/\b\w/g, c => c.toUpperCase())
        : resolveThreadLabel(focusValue)

    const globalSentiment = data?.nodes?.length
        ? data.nodes.reduce((sum, n) => sum + n.avg_sentiment * n.signal_count, 0) /
          data.nodes.reduce((sum, n) => sum + n.signal_count, 0)
        : null

    const totalSources = data?.nodes?.reduce((sum, n) => sum + n.unique_sources, 0) ?? 0
    const topNodes = data?.nodes?.slice(0, 10) ?? []
    const geoNarrative = data ? buildGeoNarrative(data.nodes) : null
    // #176: typed subjects — prefer the server's key_subjects (NER-typed),
    // fall back to client-typing the legacy key_people for older responses.
    const keySubjects = (data?.key_subjects && data.key_subjects.length > 0)
        ? data.key_subjects.map(s => ({ name: s.name, type: s.type, count: s.signal_count }))
        : buildKeySubjects((data?.key_people ?? []).map(p => ({ name: p.person, count: p.signal_count })))
    const relatedThemeGroups = groupThemeTopics((data?.related_topics ?? []).slice(0, 12))

    return (
        <div className={cls}>
            {/* Header */}
            <div className="entity-header" id="ep-header">
                <div className="entity-header-meta">
                    <span className="entity-type-tag">
                        {focusType === 'person' ? 'PERSON' : 'THEME'}
                    </span>
                    <span className="entity-timerange">{hours}h</span>
                </div>
                <button className="entity-close" onClick={onClose}>×</button>
            </div>

            <div className="entity-title-block">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <h2 className="entity-name">{displayName}</h2>
                        <button 
                            onClick={() => {
                                const pinnedId = `${focusType}-${focusValue}`
                                if (isPinned(pinnedId)) {
                                    unpinItem(pinnedId)
                                } else {
                                    const params = new URLSearchParams()
                                    params.set(focusType, focusValue)
                                    pinItem({
                                        id: pinnedId,
                                        type: focusType,
                                        title: displayName,
                                        urlParams: `?${params.toString()}`
                                    })
                                }
                            }}
                            data-tip={isPinned(`${focusType}-${focusValue}`) ? `Unpin ${focusType}` : `Pin ${focusType} to Workspace`}
                            style={{ background: 'transparent', border: '1px solid rgba(var(--color-ink-rgb),0.1)', color: isPinned(`${focusType}-${focusValue}`) ? '#10b981' : 'var(--color-sentiment-neutral)', width: '24px', height: '24px', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', transition: 'all 0.2s' }}
                        >
                            {isPinned(`${focusType}-${focusValue}`) ? <PinOff size={12} /> : <Pin size={12} />}
                        </button>
                    </div>
                    {focusType === 'person' && onCompareClick && (
                        <div style={{ position: 'relative' }}>
                            <button
                                className="entity-compare-btn"
                                onClick={() => setShowCompareModal(v => !v)}
                                style={{ background: showCompareModal ? 'rgba(99,102,241,0.15)' : 'transparent', border: '1px solid #6366f1', color: '#a5b4fc', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
                            >
                                Compare With...
                            </button>
                            {showCompareModal && (
                                <CompareSearchModal
                                    onSelect={name => { onCompareClick(name); setShowCompareModal(false) }}
                                    onClose={() => setShowCompareModal(false)}
                                />
                            )}
                        </div>
                    )}
                </div>
                {data && (
                    <>
                        <div className="entity-subtitle">
                            <span>{formatCount(data.summary.total_signals)} signals</span>
                            <span className="entity-dot">·</span>
                            <span>{data.summary.total_countries} countries</span>
                            {globalSentiment !== null && (
                                <>
                                    <span className="entity-dot">·</span>
                                    <span style={{ color: sentimentColor(globalSentiment) }}>
                                        {sentimentLabel(globalSentiment)}
                                    </span>
                                </>
                            )}
                        </div>
                        {geoNarrative && (
                            <div className="entity-geo-narrative">{geoNarrative}</div>
                        )}
                    </>
                )}
            </div>

            {loading && (
                <div className="entity-loading">
                    {[80, 65, 90, 72, 85, 60, 78, 68].map((w, i) => (
                        <div key={i} className="entity-skeleton" style={{ width: `${w}%` }} />
                    ))}
                </div>
            )}

            {!loading && data && (
                <div className="entity-body">

                    {/* #173 Evidence Route — the entity funnel: mentioned-in ->
                        countries [-> threads, person focus only] -> key subjects.
                        Real counts from the payloads this panel already fetched. */}
                    <EvidenceRoute
                        steps={buildPersonEvidenceRoute({
                            personName: displayName,
                            signalCount: data.summary.total_signals,
                            countryCount: data.summary.total_countries,
                            threadCount: focusType === 'person' ? personThreads.length : undefined,
                            keySubjectCount: keySubjects.length,
                        })}
                        onStepClick={id => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                    />

                    {/* Trust Indicators */}
                    <div className="entity-section">
                        <div className="section-label entity-section-label">Trust Indicators</div>
                        <div className="entity-indicators">
                            <div className="entity-indicator">
                                <span className="indicator-label">Source Diversity</span>
                                <span className="indicator-value">{Math.min(totalSources, 999)}</span>
                            </div>
                            <div className="entity-indicator">
                                <span className="indicator-label">Countries Reporting</span>
                                <span className="indicator-value">{data.summary.total_countries}</span>
                            </div>
                            <div className="entity-indicator">
                                <span className="indicator-label">Global Sentiment</span>
                                <span className="indicator-value" style={{ color: globalSentiment !== null ? sentimentColor(globalSentiment) : undefined }}>
                                    {globalSentiment !== null ? globalSentiment.toFixed(2) : '—'}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Top Countries */}
                    {topNodes.length > 0 && (
                        <div className="entity-section" id="ep-countries">
                            <div className="section-label entity-section-label">Coverage by Country</div>
                            <div className="entity-country-list">
                                {topNodes.map((node, i) => (
                                    <div
                                        key={node.country_code}
                                        className="entity-country-row"
                                        onClick={() => onCountrySelect?.(node.country_code)}
                                    >
                                        <span className="entity-country-rank">#{i + 1}</span>
                                        <span className="entity-country-code">{node.country_code}</span>
                                        <div className="entity-country-bar-wrap">
                                            <div
                                                className="entity-country-bar"
                                                style={{
                                                    width: `${(node.signal_count / topNodes[0].signal_count) * 100}%`,
                                                    background: sentimentColor(node.avg_sentiment)
                                                }}
                                            />
                                        </div>
                                        <span className="entity-country-count">{formatCount(node.signal_count)}</span>
                                        <span className="entity-country-sentiment" style={{ color: sentimentColor(node.avg_sentiment) }}>
                                            {node.avg_sentiment > 0 ? '+' : ''}{node.avg_sentiment.toFixed(1)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Threads this person participates in (spec T3) — the living
                        narrative threads, ABOVE the demoted GDELT "Related Themes". */}
                    {focusType === 'person' && personThreads.length > 0 && (
                        <div className="entity-section" id="ep-threads">
                            <div className="section-label entity-section-label">Threads {displayName} participates in</div>
                            <div className="entity-threads">
                                {personThreads.slice(0, 6).map(t => (
                                    <button
                                        key={t.thread_id}
                                        className="entity-thread-row"
                                        onClick={() => onThemeSelect?.(t.thread_id)}
                                        data-tip={`Open the "${t.label}" narrative thread`}
                                    >
                                        <span className="entity-thread-label">{t.label}</span>
                                        {t.discussion_count != null && t.discussion_count > 0 && (
                                            <span className="entity-thread-forum" data-tip={`${t.discussion_count} forum post(s) discussing this`}>FORUM {t.discussion_count}</span>
                                        )}
                                        <span className="entity-thread-count">
                                            {t.signal_count > 999 ? `${(t.signal_count / 1000).toFixed(1)}k` : t.signal_count}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Top Themes */}
                    {relatedThemeGroups.length > 0 && (
                        <div className="entity-section">
                            <div className="section-label entity-section-label">Related Themes</div>
                            <div className="entity-theme-groups">
                                {relatedThemeGroups.map(group => (
                                    <div key={group.cluster.id} className="entity-theme-group">
                                        <div className="entity-theme-group-label">{group.cluster.label}</div>
                                        <div className="entity-themes">
                                            {group.items.map(t => (
                                                <button
                                                    key={t.topic}
                                                    className="entity-theme-chip"
                                                    onClick={() => onThemeSelect?.(t.topic)}
                                                    data-tip={`${t.count} signals`}
                                                >
                                                    {getThemeLabel(t.topic)}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Key Subjects — typed: person is one type (#176) */}
                    {keySubjects.length > 0 && (
                        <div className="entity-section" id="ep-subjects">
                            <div className="section-label entity-section-label">Key Subjects</div>
                            <div className="entity-people">
                                {keySubjects.map(s => {
                                    const fullData = data.key_people.find(k => k.person === s.name)
                                    const clickable = s.type === 'person' && !!onPersonSelect
                                    return (
                                        <div
                                            key={`${s.type}:${s.name}`}
                                            className={`entity-person-row${clickable ? '' : ' entity-person-row--static'}`}
                                            onClick={clickable ? () => onPersonSelect?.(s.name) : undefined}
                                        >
                                            <span className="badge entity-subject-badge" data-type={s.type}>{SUBJECT_BADGE[s.type]}</span>
                                            <span className="entity-person-name">{s.name}</span>
                                            <span className="entity-person-count">{formatCount(s.count)}</span>
                                            {fullData && fullData.country_count > 1 && (
                                                <span className="entity-person-countries">{fullData.country_count} ctrs</span>
                                            )}
                                            {fullData && (
                                                <span
                                                    className="entity-person-dot"
                                                    style={{ background: sentimentColor(fullData.avg_sentiment) }}
                                                />
                                            )}
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    )}

                    {/* Source Framing Split */}
                    {data.top_sources.length > 0 && (() => {
                        const sources = data.top_sources.slice(0, 8)
                        const positive = sources.filter(s => s.avg_sentiment > 0.2).sort((a, b) => b.avg_sentiment - a.avg_sentiment)
                        const negative = sources.filter(s => s.avg_sentiment < -0.2).sort((a, b) => a.avg_sentiment - b.avg_sentiment)
                        const neutral  = sources.filter(s => Math.abs(s.avg_sentiment) <= 0.2)
                        const showSplit = positive.length + negative.length >= 2
                        const spread = positive.length && negative.length
                            ? positive[0].avg_sentiment - negative[0].avg_sentiment
                            : null

                        if (!showSplit) {
                            return (
                                <div className="entity-section">
                                    <div className="section-label entity-section-label">Top Sources</div>
                                    <div className="entity-sources">
                                        {sources.map(s => (
                                            <div key={s.source} className="entity-source-row"
                                                style={{ cursor: onSourceClick ? 'pointer' : 'default' }}
                                                onClick={() => onSourceClick?.(s.source)}>
                                                <span className="entity-source-name">{s.source}</span>
                                                <span className="entity-source-count">{formatCount(s.count)}</span>
                                                <span className="entity-source-sentiment" style={{ color: sentimentColor(s.avg_sentiment) }}>
                                                    {s.avg_sentiment > 0 ? '+' : ''}{s.avg_sentiment.toFixed(1)}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )
                        }

                        const maxRows = Math.max(positive.length, negative.length, 1)
                        return (
                            <div className="entity-section">
                                <div className="section-label entity-section-label">Framing Split</div>
                                {spread !== null && spread > 0.4 && (
                                    <div className="entity-framing-spread">
                                        <span className="framing-spread-label">Narrative spread</span>
                                        <div className="framing-spread-bar">
                                            <div className="framing-spread-fill" style={{ width: `${Math.min(spread / 4 * 100, 100)}%` }} />
                                        </div>
                                        <span className="framing-spread-value" style={{ color: spread > 2 ? '#f87171' : spread > 1 ? '#fbbf24' : '#888' }}>
                                            {spread > 2 ? 'High' : spread > 1 ? 'Med' : 'Low'} ({spread.toFixed(1)})
                                        </span>
                                    </div>
                                )}
                                <div className="entity-framing-grid">
                                    <div className="framing-col framing-col--pos">
                                        <div className="framing-col-header">Positive</div>
                                        {Array.from({ length: maxRows }, (_, i) => positive[i]).map((s, i) => s ? (
                                            <div key={s.source} className="framing-source-row"
                                                style={{ cursor: onSourceClick ? 'pointer' : 'default' }}
                                                onClick={() => onSourceClick?.(s.source)}>
                                                <span className="framing-source-name">{s.source}</span>
                                                <span className="framing-source-sent positive">+{s.avg_sentiment.toFixed(1)}</span>
                                            </div>
                                        ) : <div key={i} className="framing-source-row framing-source-row--empty" />)}
                                    </div>
                                    <div className="framing-col framing-col--neg">
                                        <div className="framing-col-header">Negative</div>
                                        {Array.from({ length: maxRows }, (_, i) => negative[i]).map((s, i) => s ? (
                                            <div key={s.source} className="framing-source-row"
                                                style={{ cursor: onSourceClick ? 'pointer' : 'default' }}
                                                onClick={() => onSourceClick?.(s.source)}>
                                                <span className="framing-source-name">{s.source}</span>
                                                <span className="framing-source-sent negative">{s.avg_sentiment.toFixed(1)}</span>
                                            </div>
                                        ) : <div key={i} className="framing-source-row framing-source-row--empty" />)}
                                    </div>
                                </div>
                                {neutral.length > 0 && (
                                    <div className="framing-neutral-row">
                                        <span className="framing-neutral-label">Neutral:</span>
                                        {neutral.map(s => (
                                            <span key={s.source} className="framing-neutral-source"
                                                style={{ cursor: onSourceClick ? 'pointer' : 'default' }}
                                                onClick={() => onSourceClick?.(s.source)}>
                                                {s.source}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )
                    })()}

                    {/* Recent Coverage */}
                    {data.headlines.length > 0 && (
                        <div className="entity-section" id="ep-coverage">
                            <div className="section-label entity-section-label">Recent Coverage</div>
                            <div className="entity-headlines">
                                {data.headlines.slice(0, 8).map((h, i) => {
                                    const displayText = h.headline
                                        ? h.headline.replace(/^\d{6,}\./, '').trim().slice(0, 90)
                                        : h.url.replace(/^https?:\/\/[^/]+/, '').replace(/[-_]/g, ' ').slice(0, 70)
                                    return (
                                        <a
                                            key={i}
                                            href={h.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="entity-headline"
                                        >
                                            <div className="entity-headline-row">
                                                <span className="entity-headline-source">{h.source}</span>
                                                <PinReceiptButton
                                                    className="entity-headline-pin"
                                                    citation={receiptFrom({
                                                        headline: h.headline ?? '',
                                                        source: h.source,
                                                        url: h.url,
                                                        publishedDate: h.time?.slice(0, 10),
                                                    })}
                                                    contextLabel={displayName}
                                                />
                                            </div>
                                            <span className="entity-headline-title" data-tip={displayText}>{displayText}</span>
                                        </a>
                                    )
                                })}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {!loading && !data && (
                <div className="entity-empty">No data available for this {focusType}</div>
            )}
        </div>
    )
}
