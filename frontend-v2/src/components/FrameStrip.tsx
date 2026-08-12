// Exploration Flywheel Task 2.4 — the FRAME strip.
//
// Distinct from FocusIndicator (the ephemeral compound FOCUS — country ∧
// theme ∧ person, cleared on navigation): this strip shows the analyst's
// DELIBERATE pins for the active investigation, auto-sorted into three
// lanes (lib/pinLanes.ts — WHO/WHERE/WHAT) so "the investigation you're
// building" reads as a frame, not a flat list. Prominence gradient by
// design: invisible until the first pin lands, so it never competes with
// an analyst who hasn't started investigating yet.
//
// Renders the deliberate pins (presentational) PLUS the quiet ◎ detected-
// relationship callout (Task 4.3), which fetches the console thread pool ONCE
// the analyst crosses the detector's ≥2-pin floor. Detection is measured-not-
// asserted by construction (lib/briefRelationDetector.ts — text|context only).
import { useEffect, useMemo, useState } from 'react'
import { useWorkspace, type PinnedItem } from '../contexts/WorkspaceContext'
import { getActiveInvestigationId, getInvestigation } from '../lib/workbench'
import { groupPinsByLane, type Lane } from '../lib/pinLanes'
import {
    detectBriefRelations, hasEnoughSignal, topBriefRelation,
    type BriefThreadLike,
} from '../lib/briefRelationDetector'
import './FrameStrip.css'

interface FrameStripProps {
    onOpenPin?: (item: PinnedItem) => void
    /** ◎ callout — open + scope the console to the connected brief thread
     *  (Phase-1 compound setters, via App's thread opener). */
    onScopeThread?: (threadId: string, label: string) => void
    /** ◎ callout — open the Workbench to build a report from these pins. */
    onOpenReport?: () => void
}

const LANES: { key: Lane; label: string }[] = [
    { key: 'who', label: 'WHO' },
    { key: 'where', label: 'WHERE' },
    { key: 'what', label: 'WHAT' },
]

export function FrameStrip({ onOpenPin, onScopeThread, onOpenReport }: FrameStripProps) {
    // items = the ACTIVE investigation's pins already (WorkspaceContext derives
    // them from getActiveInvestigationId(); see contexts/WorkspaceContext.tsx).
    // items.length doubles as "no active investigation OR 0 pins" in one check.
    const { items, version } = useWorkspace()

    // Title isn't exposed by useWorkspace — read it straight from the
    // workbench store, re-derived whenever `version` bumps (every pin/unpin/
    // note/sync mutation) so a rename or a pull-from-sync stays live.
    const title = useMemo(() => {
        void version
        const activeId = getActiveInvestigationId()
        const inv = activeId ? getInvestigation(activeId) : null
        return inv?.title ?? ''
    }, [version])

    const lanes = useMemo(
        () =>
            groupPinsByLane(
                items.map(it => ({
                    ...it,
                    anchorType: it.type,
                    snapshot: {
                        countryCode:
                            typeof it.meta?.countryCode === 'string' ? it.meta.countryCode : undefined,
                    },
                }))
            ),
        [items]
    )

    // ── ◎ detected-relationship callout (Task 4.3) ──────────────────────────
    // The detector needs the active investigation's RICH pins (snapshot.evidence
    // headlines); the adapted `items` above carry no evidence, so read the
    // WorkbenchPins straight from the store (re-derived on every `version` bump).
    const relInput = useMemo(() => {
        void version
        const activeId = getActiveInvestigationId()
        const inv = activeId ? getInvestigation(activeId) : null
        return (inv?.pins ?? []).map(p => ({
            anchorId: p.anchorId,
            anchorType: p.anchorType,
            label: p.label,
            snapshot: { countryCode: p.snapshot?.countryCode, evidence: p.snapshot?.evidence },
        }))
    }, [version])

    // Candidate pool = the console's current threads. Fetched ONCE the analyst
    // crosses the ≥2-pin floor (never for a one-off explorer), warm-cached by the
    // global fetch shim; any failure degrades to no callout — the pins/lanes are
    // never affected. This is the ONLY fetch in the strip.
    const enoughPins = items.length >= 2
    const [threads, setThreads] = useState<BriefThreadLike[]>([])
    useEffect(() => {
        if (!enoughPins) { setThreads([]); return }
        let alive = true
        fetch('/api/v2/threads?hours=24&limit=40')
            .then(r => (r.ok ? r.json() : Promise.reject(new Error('threads'))))
            .then(d => { if (alive) setThreads(Array.isArray(d?.threads) ? d.threads : []) })
            .catch(() => { if (alive) setThreads([]) })
        return () => { alive = false }
    }, [enoughPins])

    // Strongest-first, threshold-gated. Never 'strong'/'weak' — the detector's
    // tier ceiling is text|context, so the callout can never over-claim.
    const relation = useMemo(() => {
        if (!enoughPins || threads.length === 0) return null
        const rels = detectBriefRelations(relInput, threads)
        return hasEnoughSignal(items.length, rels) ? topBriefRelation(rels) : null
    }, [enoughPins, threads, relInput, items.length])

    if (items.length === 0) return null

    return (
        <div className="frame-strip" role="status">
            <div className="frame-strip-header">
                <span className="frame-strip-title" data-tip={title}>
                    {title}
                </span>
                <span className="frame-strip-count">· {items.length} pinned</span>
            </div>
            <div className="frame-strip-lanes">
                {LANES.map(({ key, label }) => {
                    const pins = lanes[key]
                    if (pins.length === 0) return null
                    return (
                        <div className="frame-strip-lane" key={key}>
                            <span className="frame-strip-lane-label">{label}</span>
                            <div className="frame-strip-chips">
                                {pins.map(item => (
                                    <button
                                        key={item.id}
                                        type="button"
                                        className="frame-strip-chip"
                                        onClick={() => onOpenPin?.(item)}
                                        data-tip={item.title}
                                    >
                                        {item.title}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )
                })}
            </div>
            {relation && (
                <div className="frame-strip-detect" role="note">
                    <span className="frame-strip-detect-icon" aria-hidden="true">◎</span>
                    <span className="frame-strip-detect-text">
                        <b>{relation.pinLabel}</b> · <b>{relation.threadLabel}</b>{' '}
                        {relation.tier === 'text'
                            ? <>connect on &ldquo;{relation.term}&rdquo;</>
                            : <>share coverage in {relation.sharedCountry}</>}
                    </span>
                    {/* Mandatory honesty label — a flex sibling (never inside the
                        truncating text) so it can never be clipped away. */}
                    <span
                        className="frame-strip-detect-tag"
                        data-tip="A measured overlap in headline text (or subject country) between a pin and a story in today's console — not a claim the stories are causally linked or mutually corroborated."
                    >measured, not asserted</span>
                    {onScopeThread && (
                        <button
                            type="button"
                            className="frame-strip-detect-action"
                            onClick={() => onScopeThread(relation.threadId, relation.threadLabel)}
                            data-tip="Open and scope the console to the connected story"
                        >Scope</button>
                    )}
                    {onOpenReport && (
                        <button
                            type="button"
                            className="frame-strip-detect-action frame-strip-detect-action--report"
                            onClick={onOpenReport}
                            data-tip="Open the Workbench to build a report from these pins"
                        >＋Report</button>
                    )}
                </div>
            )}
        </div>
    )
}
