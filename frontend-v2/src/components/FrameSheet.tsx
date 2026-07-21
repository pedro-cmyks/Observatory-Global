// Exploration Flywheel Task 6.3c — the mobile Frame.
//
// On a phone the reading is primary, so the Frame lives in a QUIET pull-up
// sheet above the tab bar instead of a top strip: collapsed it's a thin handle
// with the pin count; pulled up it reveals the same FrameStrip content
// (WHO/WHERE/WHAT lanes + the ◎ detected-relationship callout). Detection
// renders ONLY here on mobile — never a mid-read banner (design §8). Appears
// on the first pin (prominence gradient), hidden entirely at zero.
import { useState } from 'react'
import { useWorkspace, type PinnedItem } from '../contexts/WorkspaceContext'
import { FrameStrip } from './FrameStrip'
import './FrameSheet.css'

interface FrameSheetProps {
    onOpenPin?: (item: PinnedItem) => void
    onScopeThread?: (threadId: string, label: string) => void
    onOpenReport?: () => void
    /** Lift the sheet above the floating focus chip when one is present (both
     *  are fixed just above the tab bar and would otherwise collide). */
    raised?: boolean
}

export function FrameSheet({ raised, ...props }: FrameSheetProps) {
    const { items } = useWorkspace()
    const [open, setOpen] = useState(false)

    // Prominence gradient: no pins → no sheet (never burdens a reader).
    if (items.length === 0) return null

    return (
        <div className={`frame-sheet${open ? ' frame-sheet--open' : ''}${raised ? ' frame-sheet--raised' : ''}`}>
            <button
                type="button"
                className="frame-sheet-handle"
                onClick={() => setOpen(o => !o)}
                aria-expanded={open}
                aria-label={open ? 'Collapse the investigation frame' : 'Expand the investigation frame'}
            >
                <span className="frame-sheet-grip" aria-hidden="true" />
                <span className="frame-sheet-badge">◆ {items.length}</span>
                <span className="frame-sheet-title">the investigation you’re building</span>
                <span className="frame-sheet-chevron" aria-hidden="true">{open ? '▾' : '▴'}</span>
            </button>
            {open && (
                <div className="frame-sheet-body">
                    {/* Reuses FrameStrip verbatim — its lanes + the ◎ callout +
                        its own thread-pool fetch. The sheet CSS restacks it
                        vertically and drops the top-strip command-bar clearance. */}
                    <FrameStrip {...props} />
                </div>
            )}
        </div>
    )
}
