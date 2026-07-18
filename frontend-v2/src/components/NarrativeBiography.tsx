// NARRATIVE BIOGRAPHY (BUILD-B, 2026-07-18) — how this story EVOLVED, week by
// week, stitched across the hot/archive seam by the narrative-lineage census
// (OpenAI-space, backend/scripts/narrative_lineage_census.py).
//
// Surface rules:
// - Renders ONLY when /api/v2/theme/{id}/lineage returns >=2 present weeks —
//   absence is honest (no section, no placeholder).
// - Horizontal WEEKLY SPINE: time is the literal axis; node size = volume;
//   color = tier (hot live topic vs archive weekly clusters); edge style =
//   MEASURED drift (steady vs shifting — the cosine is printed on the edge);
//   candidate stitches dashed + labeled.
// - Label-of-era shown when it CHANGED — the renames tell the transformation.
// - Click a week -> that era's receipts (DayEvidence renderer discipline:
//   tier label, decoded headlines, TranslatableHeadline when a signal id
//   exists, links out).
// - Foot = glass-box method line (space, thresholds, member coverage).
import { useCallback, useEffect, useState } from 'react'
import { fetchLineage, presentWeeks, type LineageResponse, type LineageWeek } from '../lib/lineage'
import { buildLineageSpine, type SpineEdge, type SpineNode } from '../lib/lineageSpine'
import { decodeEntities } from '../lib/decodeEntities'
import { resolveCountryName } from '../lib/countryNames'
import { TranslatableHeadline } from './TranslatableHeadline'
import { track } from '../lib/telemetry'
import './NarrativeBiography.css'

const SVG_H = 132

function fmtWeek(week: string): string {
    return new Date(week + 'T00:00:00Z')
        .toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
}

function edgeTip(e: SpineEdge): string {
    const drift = e.drift == null
        ? 'drift unmeasured'
        : `drift cos ${e.drift.toFixed(2)} — ${e.kind === 'steady' ? 'narrative steady' : 'narrative shifting'}`
    const parts = [drift]
    if (e.spansGap) parts.push('crosses quiet week(s)')
    if (e.candidate) parts.push('candidate link — below the asserted threshold')
    return parts.join(' · ')
}

export function NarrativeBiography({ theme }: { theme: string }) {
    const [data, setData] = useState<LineageResponse | null>(null)
    const [selected, setSelected] = useState<string | null>(null)
    const [width, setWidth] = useState(720)

    // Callback-ref ResizeObserver — the mount-only-observer-behind-a-loading-
    // branch bug bit the universe view (2026-07-02); never again.
    const wrapRef = useCallback((el: HTMLDivElement | null) => {
        if (!el) return
        const ro = new ResizeObserver(entries => {
            const w = entries[0]?.contentRect?.width
            if (w && w > 200) setWidth(w)
        })
        ro.observe(el)
    }, [])

    useEffect(() => {
        let alive = true
        setData(null)
        setSelected(null)
        fetchLineage(theme).then(d => { if (alive) setData(d) })
        return () => { alive = false }
    }, [theme])

    const present = presentWeeks(data?.weeks)
    if (!data || present.length < 2) return null // honest absence

    const spine = buildLineageSpine(data.weeks, { width })
    if (!spine.hasSpine) return null

    const selectedEra: LineageWeek | undefined = selected
        ? present.find(w => w.week === selected)
        : undefined
    const selectedNode: SpineNode | undefined = selected
        ? spine.nodes.find(n => n.week === selected)
        : undefined

    const openWeek = (week: string) => {
        const next = selected === week ? null : week
        setSelected(next)
        if (next) track('biography_week_open', { theme, week: next })
    }

    const stitch = data.stitch
    const shownLabelWeeks = spine.nodes.filter(n => n.showLabel && n.label).map(n => n.week)

    return (
        <div className="theme-section narrative-biography">
            <div className="theme-section-title" style={{ color: '#818cf8' }}>
                NARRATIVE BIOGRAPHY · {spine.weekSpan} WEEKS
                {stitch?.candidate && (
                    <span className="nb-candidate-chip" data-tip="The stitch between the live thread and the archive lineage scored below the measured threshold — shown as a candidate, not asserted.">
                        CANDIDATE STITCH
                    </span>
                )}
            </div>

            <div className="nb-canvas" ref={wrapRef}>
                <svg width="100%" height={SVG_H} viewBox={`0 0 ${width} ${SVG_H}`} role="img"
                    aria-label={`Weekly narrative biography spine, ${spine.weekSpan} weeks`}>
                    {/* edges first (under the nodes) */}
                    {spine.edges.map(e => (
                        <g key={`e-${e.toWeek}`}>
                            <line
                                className={`nb-edge nb-edge--${e.kind}${e.candidate ? ' nb-edge--candidate' : ''}${e.spansGap ? ' nb-edge--gap' : ''}`}
                                x1={e.x1} y1={SVG_H / 2} x2={e.x2} y2={SVG_H / 2}
                            />
                            {/* glass-box: the measured cosine rides ON the edge */}
                            {e.drift != null && (
                                <text className={`nb-edge-drift nb-edge-drift--${e.kind}`}
                                    x={(e.x1 + e.x2) / 2} y={SVG_H / 2 + 16}>
                                    {e.drift.toFixed(2)}
                                </text>
                            )}
                        </g>
                    ))}
                    {spine.nodes.map(n => (
                        <g key={n.week} className="nb-node-group" onClick={() => openWeek(n.week)}>
                            <circle
                                className={`nb-node nb-node--${n.tier}${n.candidate ? ' nb-node--candidate' : ''}${selected === n.week ? ' nb-node--selected' : ''}`}
                                cx={n.x} cy={n.y} r={n.r}
                            />
                            {n.showLabel && n.label && (
                                <text className="nb-era-label" x={n.x}
                                    /* alternate rows so adjacent renames don't collide */
                                    y={n.y - n.r - (shownLabelWeeks.indexOf(n.week) % 2 === 1 ? 26 : 10)}
                                    /* border eras anchor inward so labels never clip
                                       (inline style: the CSS class sets text-anchor) */
                                    style={{ textAnchor: n.x < 90 ? 'start' : n.x > width - 90 ? 'end' : 'middle' }}>
                                    {decodeEntities(n.label).slice(0, 34)}{n.label.length > 34 ? '…' : ''}
                                </text>
                            )}
                            {(n.showLabel || n === spine.nodes[spine.nodes.length - 1]) && (
                                <text className="nb-week-label" x={n.x} y={SVG_H - 8}>
                                    {fmtWeek(n.week)}
                                </text>
                            )}
                        </g>
                    ))}
                </svg>
                {/* HTML hover strip for the edges' full explanation (data-tip is
                    an HTML-attr tooltip; SVG hit areas get a parallel strip) */}
                <div className="nb-edge-tips">
                    {spine.edges.map(e => {
                        // inset by the node radius so the zones never shadow node clicks
                        const x0 = Math.min(e.x1, e.x2) + 18
                        const w = Math.max(0, Math.abs(e.x2 - e.x1) - 36)
                        return (
                            <span key={`t-${e.toWeek}`} className="nb-edge-tip-zone"
                                style={{ left: `${(x0 / width) * 100}%`, width: `${(w / width) * 100}%` }}
                                data-tip={edgeTip(e)} />
                        )
                    })}
                </div>
            </div>

            <div className="nb-legend">
                <span><i className="nb-dot nb-dot--hot" /> live thread</span>
                <span><i className="nb-dot nb-dot--archive" /> archive era</span>
                <span><i className="nb-line nb-line--steady" /> steady</span>
                <span><i className="nb-line nb-line--shifting" /> shifting</span>
                <span><i className="nb-line nb-line--candidate" /> candidate link</span>
            </div>

            {selectedEra && selectedNode && (
                <div className="nb-era">
                    <div className="nb-era-head">
                        <div>
                            <div className="nb-era-kicker">
                                WEEK OF {fmtWeek(selectedEra.week).toUpperCase()}
                                {' · '}{selectedEra.tier === 'hot' ? 'LIVE THREAD' : 'FROM THE ARCHIVE — sample'}
                            </div>
                            <div className="nb-era-title">{decodeEntities(selectedEra.label ?? '')}</div>
                        </div>
                        <button className="nb-era-close" onClick={() => setSelected(null)} aria-label="Close era">×</button>
                    </div>
                    <div className="nb-era-meta">
                        {selectedEra.n_signals ?? 0} signals
                        {selectedEra.tier === 'archive' && selectedEra.n_units
                            ? ` · ${selectedEra.n_units} archive unit${selectedEra.n_units > 1 ? 's' : ''}` : ''}
                        {selectedNode.driftCosPrev != null && (
                            <span data-tip="Cosine similarity of this week's era centroid vs the previous era — measured in OpenAI embedding space.">
                                {' · '}drift vs prev {selectedNode.driftCosPrev.toFixed(2)}
                            </span>
                        )}
                        {(selectedEra.countries ?? []).length > 0 &&
                            ` · ${(selectedEra.countries ?? []).slice(0, 4).map(c => resolveCountryName(c, c)).join(', ')}`}
                        {selectedEra.candidate && <span className="nb-era-candidate"> · candidate era</span>}
                    </div>
                    {(selectedEra.receipts ?? []).length === 0 ? (
                        <div className="nb-era-empty">No stored receipts for this era — honest empty, not filler.</div>
                    ) : (
                        <ul className="nb-receipts">
                            {(selectedEra.receipts ?? []).map((r, i) => (
                                <li key={i}>
                                    {r.signal_id ? (
                                        // translatable headlines carry a toggle BUTTON —
                                        // never nest it in an <a> (toggle would navigate);
                                        // the link becomes a trailing affordance instead.
                                        <span>
                                            <TranslatableHeadline signalId={r.signal_id} original={decodeEntities(r.headline)} sourceLang={r.source_lang} />
                                            {r.url && <a className="nb-receipt-link" href={r.url} target="_blank" rel="noopener noreferrer" data-tip="Open source article">↗</a>}
                                        </span>
                                    ) : r.url ? (
                                        <a href={r.url} target="_blank" rel="noopener noreferrer">{decodeEntities(r.headline)}</a>
                                    ) : (
                                        <span>{decodeEntities(r.headline)}</span>
                                    )}
                                    {r.source && <span className="nb-receipt-src"> — {decodeEntities(r.source)}</span>}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            )}

            {stitch && (
                <div className="nb-method">
                    stitched in OpenAI space
                    {stitch.theta_topic_unit != null && <> · θ topic↔era {stitch.theta_topic_unit}</>}
                    {stitch.theta_unit_unit != null && <> · θ era↔era {stitch.theta_unit_unit}</>}
                    {stitch.topic_sim != null && <> · stitch sim {stitch.topic_sim.toFixed(2)}</>}
                    {stitch.member_coverage != null && <> · member coverage {Math.round(stitch.member_coverage * 100)}%</>}
                    {' · '}hot = live thread · archive = weekly archive clusters
                </div>
            )}
        </div>
    )
}

export default NarrativeBiography
