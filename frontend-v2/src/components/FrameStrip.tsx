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
// Presentational only — no fetching, no side effects beyond onOpenPin.
import { useMemo } from 'react'
import { useWorkspace, type PinnedItem } from '../contexts/WorkspaceContext'
import { getActiveInvestigationId, getInvestigation } from '../lib/workbench'
import { groupPinsByLane, type Lane } from '../lib/pinLanes'
import './FrameStrip.css'

interface FrameStripProps {
    onOpenPin?: (item: PinnedItem) => void
}

const LANES: { key: Lane; label: string }[] = [
    { key: 'who', label: 'WHO' },
    { key: 'where', label: 'WHERE' },
    { key: 'what', label: 'WHAT' },
]

export function FrameStrip({ onOpenPin }: FrameStripProps) {
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
        </div>
    )
}
