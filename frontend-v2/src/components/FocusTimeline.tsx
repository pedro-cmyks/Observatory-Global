/**
 * Track C4b — THE COMBINED CHART (spec §3): the universal activity-timeline
 * section every focus gets. ONE x-axis (time), channels as TOGGLES:
 *   · diverging volume bars  — extent = volume, up/down = average tone
 *                              (sentiment by POSITION, freeing color for lines)
 *   · key-subject trend lines — rarity-normalized presence per subject over
 *                              time; stable color per entity; a line that ENDS
 *                              = the connection died
 *   · voice-mix band          — who covers it (language mix) over time
 *   · edge-diff overlay (C3)  — churn-vs-narrative lives in the endpoint hover
 *                              + a "relationships since" strip; NO marker layer
 *
 * Data: GET /api/v2/focus/{ref}/timeline (C4a, focus-timeline-v0) merged
 * client-side with GET /api/v2/focus/{ref}/edge-diff (C3, focus-edge-diff-v0).
 * Honest-degrade per channel status; never render a degraded channel as zero.
 *
 * Pure math lives in ../lib/focusTimelineLayout (unit-tested). This file is
 * only fetch + SVG. Vanilla CSS + SVG, no Tailwind, theme via CSS vars.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import {
    buildSubjectSeries,
    maxVolume,
    maxPresence,
    barPixels,
    subjectLinePoints,
    isChannelUsable,
    channelGapLabel,
    summarizeChanges,
    diedReasonLabel,
    dormantForSubject,
    type FocusTimelineResponse,
    type EdgeDiffResponse,
    type TimelineBucket,
    type SubjectSeries,
} from '../lib/focusTimelineLayout'
import './FocusTimeline.css'

// avg_sentiment arrives on roughly the ±1 scale the rest of the panel uses
// (getSentimentColor thresholds at ±0.1); clamp keeps a stray ±10 GDELT tone
// from overshooting the volume extent.
const SENT_FULL = 1

interface FocusTimelineProps {
    /** thread id (`dynamic-topic-N` / `slug--cc` / identity_key), 2-letter
     *  country code, or a person name — the endpoint auto-detects the kind. */
    focusRef: string
    /** Optional explicit override of the auto-detected focus kind. */
    focusType?: 'thread' | 'country' | 'person'
    hours: number
    granularity?: 'hour' | 'day'
    /** Human label for the header (falls back to the ref). */
    label?: string
    /** Legacy per-hour timeline (data.timeline) used ONLY when the new
     *  endpoint yields no buckets (e.g. an atlas-category thread that doesn't
     *  resolve to a dynamic topic) — keeps the section from regressing. */
    fallbackTimeline?: Array<{ hour: string; count: number; sentiment: number }>
}

interface Hover {
    x: number
    y: number
    title: string
    lines: string[]
}

const PLOT_H = 220
const M = { top: 14, right: 48, bottom: 26, left: 46 }
const VOICE_H = 30

// Deterministic hue per language code (voice-mix band) — independent of the
// subject palette (different channel, different meaning), stable per lang.
function langColor(lang: string): string {
    let h = 0
    for (let i = 0; i < lang.length; i++) h = (h * 31 + lang.charCodeAt(i)) % 360
    return `hsl(${h}, 55%, 55%)`
}

function fmtDay(iso: string): string {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return iso.slice(5, 10)
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function FocusTimeline({
    focusRef, focusType, hours, granularity = 'day', label, fallbackTimeline,
}: FocusTimelineProps) {
    const [data, setData] = useState<FocusTimelineResponse | null>(null)
    const [diff, setDiff] = useState<EdgeDiffResponse | null>(null)
    const [loading, setLoading] = useState(true)
    const [err, setErr] = useState(false)

    // channel toggles — default = diverging bars + key-subject lines (spec §3)
    const [showBars, setShowBars] = useState(true)
    const [showSubjects, setShowSubjects] = useState(true)
    const [showVoice, setShowVoice] = useState(false)
    const [tone, setTone] = useState(true)

    const [width, setWidth] = useState(680)
    const wrapRef = useRef<HTMLDivElement | null>(null)
    const [hover, setHover] = useState<Hover | null>(null)

    // measure available width (crisp bars, undistorted strokes)
    useEffect(() => {
        const el = wrapRef.current
        if (!el || typeof ResizeObserver === 'undefined') return
        const ro = new ResizeObserver(entries => {
            const w = entries[0]?.contentRect?.width
            if (w && w > 100) setWidth(Math.floor(w))
        })
        ro.observe(el)
        return () => ro.disconnect()
    }, [])

    // fetch the timeline
    useEffect(() => {
        const ctrl = new AbortController()
        setLoading(true)
        setErr(false)
        setDiff(null)
        const params = new URLSearchParams({
            hours: String(hours), granularity,
        })
        if (focusType) params.set('focus_type', focusType)
        fetch(`/api/v2/focus/${encodeURIComponent(focusRef)}/timeline?${params}`, { signal: ctrl.signal })
            .then(r => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
            .then((d: FocusTimelineResponse) => setData(d))
            .catch(e => { if (e.name !== 'AbortError') { setErr(true); setData(null) } })
            .finally(() => setLoading(false))
        return () => ctrl.abort()
    }, [focusRef, focusType, hours, granularity])

    // fetch the edge-diff once the timeline lands, since = the first bucket
    // (changes across the visible window). Thread focus only — edge-diff
    // resolves threads; a country/person ref returns honest-empty, so skip.
    useEffect(() => {
        if (!data || data.focus_type !== 'thread' || data.buckets.length === 0) return
        const since = data.buckets[0]?.bucket_start
        if (!since) return
        const ctrl = new AbortController()
        fetch(`/api/v2/focus/${encodeURIComponent(focusRef)}/edge-diff?since=${encodeURIComponent(since)}`,
            { signal: ctrl.signal })
            .then(r => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
            .then((d: EdgeDiffResponse) => setDiff(d))
            .catch(() => { /* diff is enrichment; its absence is not an error */ })
        return () => ctrl.abort()
    }, [data, focusRef])

    // ---- resolve which buckets to draw (endpoint, else legacy fallback) ----
    const usingFallback = !!(data && data.buckets.length === 0 && fallbackTimeline && fallbackTimeline.length > 0)
    const buckets: TimelineBucket[] = useMemo(() => {
        if (data && data.buckets.length > 0) return data.buckets
        if (usingFallback) {
            return fallbackTimeline!.map(t => ({
                bucket_start: t.hour,
                volume: { count: t.count, avg_sentiment: t.sentiment },
                key_subjects: null,
                voice_mix: null,
            }))
        }
        return []
    }, [data, fallbackTimeline, usingFallback])

    const volStatus = usingFallback ? 'live' : data?.channels?.volume
    const ksStatus = usingFallback ? 'unavailable' : data?.channels?.key_subjects
    const vmStatus = usingFallback ? 'unavailable' : data?.channels?.voice_mix

    const series: SubjectSeries[] = useMemo(() => {
        if (!data || !isChannelUsable(ksStatus)) return []
        return buildSubjectSeries(buckets, data.key_subjects_candidates)
            .filter(s => s.lastIndex >= 0) // drop subjects never present in-window
    }, [data, buckets, ksStatus])

    if (loading && !data) {
        return (
            <div className="ft-wrap" ref={wrapRef}>
                <div className="ft-loading">Loading activity timeline…</div>
            </div>
        )
    }
    if (err || !data) {
        return (
            <div className="ft-wrap" ref={wrapRef}>
                <div className="ft-empty">Activity timeline unavailable.</div>
            </div>
        )
    }

    const nB = buckets.length
    const barsDrawable = isChannelUsable(volStatus) && nB > 0
    const linesDrawable = showSubjects && series.length > 0

    // ---------------------------------------------------------------- scales
    const plotW = Math.max(60, width - M.left - M.right)
    const slotW = nB > 0 ? plotW / nB : plotW
    const barW = Math.max(2, Math.min(slotW * 0.62, 22))
    const halfBand = PLOT_H / 2
    const yZero = M.top + halfBand
    const plotTop = M.top
    const plotBottom = M.top + PLOT_H
    const maxCount = Math.max(1, maxVolume(buckets))
    const maxPres = Math.max(1e-9, maxPresence(series))

    const xCenter = (i: number) => M.left + slotW * (i + 0.5)
    // presence line y: 0 at plot bottom, maxPres at plot top (own right axis)
    const yPres = (v: number) => plotBottom - (v / maxPres) * PLOT_H

    // x-axis date labels — first, middle, last (avoid clutter)
    const labelIdx = nB <= 1 ? [0] : nB <= 4 ? buckets.map((_, i) => i)
        : [0, Math.floor(nB / 2), nB - 1]

    const diffSummary = diff ? summarizeChanges(diff.changes) : null
    const diedChanges = diff ? diff.changes.filter(c => (c.change_type || '').toLowerCase() === 'died') : []
    const dormant = diff?.dormant ?? []

    const headerKind = data.focus_type
    const svgH = M.top + PLOT_H + M.bottom + (showVoice ? VOICE_H + 18 : 0)

    // -------------------------------------------------------------- hover mk
    const setHoverAt = (evt: React.MouseEvent, title: string, lines: string[]) => {
        const rect = wrapRef.current?.getBoundingClientRect()
        if (!rect) return
        setHover({ x: evt.clientX - rect.left, y: evt.clientY - rect.top, title, lines })
    }

    return (
        <div className="ft-wrap" ref={wrapRef}>
            <div className="ft-head">
                <div className="ft-title">
                    Activity Timeline
                    <span className="ft-kind">{headerKind}</span>
                </div>
                <div className="ft-toggles" role="group" aria-label="chart channels">
                    <Toggle on={showBars} onClick={() => setShowBars(v => !v)} label="Volume" swatch="bar" />
                    <Toggle on={showSubjects} onClick={() => setShowSubjects(v => !v)} label="Subjects" swatch="line" />
                    <Toggle on={showVoice} onClick={() => setShowVoice(v => !v)} label="Voice mix" swatch="voice" />
                    <Toggle on={tone} onClick={() => setTone(v => !v)} label="Tone" swatch="tone" disabled={!showBars} />
                </div>
            </div>

            {nB === 0 ? (
                <div className="ft-empty">
                    {data.reason === 'topic_not_found'
                        ? 'No extended timeline for this thread type.'
                        : data.reason === 'no_activity_in_window'
                            ? 'No activity in this window.'
                            : `No timeline (${data.reason || 'no data'}).`}
                </div>
            ) : !barsDrawable && !linesDrawable ? (
                <div className="ft-degraded">
                    <span className="ft-degraded-dot" /> Volume {channelGapLabel(volStatus, data.reason)}
                </div>
            ) : (
                <svg
                    className="ft-svg"
                    width={width}
                    height={svgH}
                    role="img"
                    aria-label={`Activity timeline for ${label || focusRef}`}
                    onMouseLeave={() => setHover(null)}
                >
                    {/* baseline / zero line for diverging bars */}
                    {showBars && barsDrawable && tone && (
                        <line x1={M.left} x2={M.left + plotW} y1={yZero} y2={yZero} className="ft-zero" />
                    )}
                    {showBars && barsDrawable && tone && (
                        <>
                            <text x={M.left - 6} y={plotTop + 9} className="ft-axis-lab" textAnchor="end">+tone</text>
                            <text x={M.left - 6} y={plotBottom - 3} className="ft-axis-lab" textAnchor="end">−tone</text>
                        </>
                    )}
                    {/* volume left-axis tick */}
                    {showBars && barsDrawable && (
                        <text x={M.left - 6} y={tone ? yZero + 3 : plotBottom - 3} className="ft-axis-lab" textAnchor="end"
                            data-tip="volume axis">{maxCount}</text>
                    )}

                    {/* diverging (or flat) volume bars — ONE neutral fill; tone is position, not color */}
                    {showBars && barsDrawable && buckets.map((b, i) => {
                        const count = b.volume?.count ?? 0
                        const avg = b.volume?.avg_sentiment ?? null
                        const cx = xCenter(i)
                        if (tone) {
                            const { upH, downH } = barPixels(count, avg, maxCount, halfBand, SENT_FULL)
                            return (
                                <g key={`bar-${i}`}
                                    onMouseMove={e => setHoverAt(e, fmtDay(b.bucket_start), [
                                        `${count.toLocaleString()} signals`,
                                        avg == null ? 'tone n/a' : `avg tone ${avg > 0 ? '+' : ''}${avg.toFixed(2)} (up/down = average)`,
                                    ])}>
                                    {upH > 0 && <rect className="ft-bar" x={cx - barW / 2} y={yZero - upH} width={barW} height={upH} />}
                                    {downH > 0 && <rect className="ft-bar" x={cx - barW / 2} y={yZero} width={barW} height={downH} />}
                                    {upH === 0 && downH === 0 && <rect className="ft-bar ft-bar-empty" x={cx - barW / 2} y={yZero - 1} width={barW} height={2} />}
                                </g>
                            )
                        }
                        const h = (count / maxCount) * PLOT_H
                        return (
                            <rect key={`bar-${i}`} className="ft-bar" x={cx - barW / 2} y={plotBottom - h} width={barW} height={Math.max(1, h)}
                                onMouseMove={e => setHoverAt(e, fmtDay(b.bucket_start), [`${count.toLocaleString()} signals`])} />
                        )
                    })}

                    {/* key-subject trend lines (own right axis: share × rarity) */}
                    {linesDrawable && (
                        <text x={M.left + plotW + 6} y={plotTop + 9} className="ft-axis-lab ft-axis-r"
                            data-tip="relationship strength = share of the bucket's signals × rarity weight">rel.</text>
                    )}
                    {linesDrawable && series.map((s, si) => {
                        const pts = subjectLinePoints(s.presences)
                        if (pts.length === 0) return null
                        const d = pts.map((p, k) =>
                            `${k === 0 ? 'M' : 'L'}${xCenter(p.index).toFixed(1)},${yPres(p.value).toFixed(1)}`).join(' ')
                        const endP = pts[pts.length - 1]
                        const ex = xCenter(endP.index)
                        const ey = yPres(endP.value)
                        const dorm = dormantForSubject(s.name, dormant)
                        return (
                            <g key={`line-${si}`}>
                                <path className="ft-line" d={d} stroke={s.color} />
                                {/* endpoint: where the connection ends / latest presence */}
                                <circle
                                    className={`ft-endpoint${s.endsEarly ? ' ft-endpoint-ended' : ''}`}
                                    cx={ex} cy={ey} r={s.endsEarly ? 4 : 3}
                                    fill={s.color}
                                    onMouseMove={e => setHoverAt(e, s.name, [
                                        s.endsEarly
                                            ? `line ends ${fmtDay(buckets[endP.index].bucket_start)} — relationship faded`
                                            : `still present · ${fmtDay(buckets[endP.index].bucket_start)}`,
                                        ...(dorm.length > 0
                                            ? [`latent: still co-appears with ${dorm.map(x =>
                                                x.entity_a.toLowerCase() === s.name.toLowerCase() ? x.entity_b : x.entity_a).slice(0, 2).join(', ')} — no current story`]
                                            : []),
                                        s.unverified ? 'subject unverified (gazetteer-typed)' : '',
                                    ].filter(Boolean))}
                                />
                            </g>
                        )
                    })}

                    {/* honest grey gap when the subjects channel was requested but not measured */}
                    {showSubjects && !isChannelUsable(ksStatus) && !usingFallback && (
                        <text x={M.left + plotW / 2} y={plotTop + 16} className="ft-gap-note" textAnchor="middle">
                            key-subject lines {channelGapLabel(ksStatus, data.reason)}
                        </text>
                    )}

                    {/* x-axis date labels */}
                    {labelIdx.map(i => (
                        <text key={`xl-${i}`} x={xCenter(i)} y={plotBottom + 14} className="ft-axis-lab" textAnchor="middle">
                            {fmtDay(buckets[i].bucket_start)}
                        </text>
                    ))}

                    {/* voice-mix band (who covers it — language mix over time) */}
                    {showVoice && (() => {
                        const bandTop = plotBottom + M.bottom
                        if (!isChannelUsable(vmStatus)) {
                            return (
                                <text x={M.left + plotW / 2} y={bandTop + VOICE_H / 2} className="ft-gap-note" textAnchor="middle">
                                    voice mix {usingFallback ? 'unavailable for this thread type' : channelGapLabel(vmStatus, data.reason)}
                                </text>
                            )
                        }
                        return (
                            <>
                                <text x={M.left - 6} y={bandTop + VOICE_H / 2 + 3} className="ft-axis-lab" textAnchor="end">langs</text>
                                {buckets.map((b, i) => {
                                    const vm = b.voice_mix
                                    if (!vm || vm.top_languages.length === 0) return null
                                    const total = vm.top_languages.reduce((a, l) => a + l.n, 0) || 1
                                    let acc = 0
                                    const cx = xCenter(i)
                                    return (
                                        <g key={`vm-${i}`}
                                            onMouseMove={e => setHoverAt(e, `${fmtDay(b.bucket_start)} · coverage`,
                                                vm.top_languages.map(l => `${l.lang} · ${l.n}`))}>
                                            {vm.top_languages.map((l, k) => {
                                                const h = (l.n / total) * VOICE_H
                                                const y = bandTop + acc
                                                acc += h
                                                return <rect key={k} x={cx - barW / 2} y={y} width={barW} height={Math.max(0.5, h)}
                                                    fill={langColor(l.lang)} className="ft-voice-seg" />
                                            })}
                                        </g>
                                    )
                                })}
                            </>
                        )
                    })()}
                </svg>
            )}

            {hover && (
                <div className="ft-tip" style={{ left: Math.min(hover.x + 12, width - 180), top: hover.y + 12 }}>
                    <div className="ft-tip-title">{hover.title}</div>
                    {hover.lines.map((l, i) => <div key={i} className="ft-tip-line">{l}</div>)}
                </div>
            )}

            {/* legend — subject color swatches */}
            {linesDrawable && (
                <div className="ft-legend">
                    {series.map((s, i) => (
                        <span key={i} className="ft-leg-item" data-tip={s.unverified ? 'unverified — gazetteer-typed' : s.type || 'subject'}>
                            <span className="ft-leg-swatch" style={{ background: s.color }} />
                            <span className={`ft-leg-name${s.endsEarly ? ' ft-leg-ended' : ''}`}>{s.name}</span>
                            {s.endsEarly && <span className="ft-leg-x" data-tip="line ends before the window — connection faded">ends</span>}
                        </span>
                    ))}
                </div>
            )}

            {/* Legibility: the lines are the SAME key subjects as the panel below,
                but only those present across multiple days trace a visible line
                (share × rarity over time). A subject seen on a single day doesn't
                "move", so it draws no line even if it ranks high by mention count —
                which is why the line here can differ from the Key Subjects top. */}
            {linesDrawable && (
                <div className="ft-note ft-note--subjects">
                    Lines trace key subjects that move across days — a single-day subject
                    draws no line even if highly covered. Full ranked list: Key Subjects below.
                </div>
            )}

            {/* honest note on the diverging encoding */}
            {showBars && barsDrawable && tone && (
                <div className="ft-note">
                    Bars: height = signal volume; up/down = <em>average</em> tone (position, not a per-signal count).
                    {usingFallback && ' Extended channels unavailable for this thread type.'}
                </div>
            )}

            {/* edge-diff strip (C3) — relationships since the window start */}
            {diff && diffSummary && (diffSummary.formed + diffSummary.died + diffSummary.weakened > 0 || dormant.length > 0) && (
                <div className="ft-diff">
                    <div className="ft-diff-head">
                        Relationships since {fmtDay(diff.since || buckets[0].bucket_start)}
                    </div>
                    <div className="ft-diff-row">
                        {diffSummary.formed > 0 && <span className="ft-diff-chip ft-formed">▲ {diffSummary.formed} formed</span>}
                        {diffSummary.weakened > 0 && <span className="ft-diff-chip ft-weak">~ {diffSummary.weakened} weakened</span>}
                        {diedChanges.map((c, i) => (
                            <span key={i} className="ft-diff-chip ft-died"
                                data-tip={`${diedReasonLabel(c.reason)} · ${c.identity_key_a} ↔ ${c.identity_key_b}`}>
                                ✖ ended{c.reason ? ` (${c.reason.replace(/_/g, ' ')})` : ''}
                            </span>
                        ))}
                    </div>
                    {dormant.length > 0 && (
                        <div className="ft-diff-dormant">
                            <span className="ft-dormant-lab" data-tip="§4 divergence: actors still co-appear, but no current thread binds them">latent</span>
                            {dormant.slice(0, 4).map((d, i) => (
                                <span key={i} className="ft-dormant-item">{d.entity_a} ↔ {d.entity_b} <em>({d.cooccur_count}×)</em></span>
                            ))}
                        </div>
                    )}
                    {diffSummary.died > 0 && (
                        <div className="ft-diff-caveat">
                            {diffSummary.diedChurn > 0 && `${diffSummary.diedChurn} ended by substrate churn (topic re-founded/merged), not narrative change. `}
                            {diffSummary.diedNarrative > 0 && `${diffSummary.diedNarrative} genuine narrative change.`}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

function Toggle({ on, onClick, label, swatch, disabled }: {
    on: boolean; onClick: () => void; label: string; swatch: string; disabled?: boolean
}) {
    return (
        <button
            type="button"
            className={`ft-toggle${on ? ' ft-toggle-on' : ''}`}
            onClick={onClick}
            disabled={disabled}
            aria-pressed={on}
        >
            <span className={`ft-toggle-swatch ft-sw-${swatch}`} />
            {label}
        </button>
    )
}
