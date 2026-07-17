// Receipt-level pin affordance (council wish 1, W4/#227 lineage).
//
// A single ◆ toggle rendered on EVERY evidence row — ThemeDetail coverage,
// CountryBrief top_stories, ResearchPlanPanel semantic_evidence, the Brief
// unassembled-tray receipts, SignalStream rows. Click pins the receipt (with
// FROZEN provenance read off the row payload) to the ACTIVE investigation; if
// none exists it creates one from the row context — the same ramp as the
// existing first-pin-creates-investigation flow. Re-click removes (toggle).
import { useCallback, useState } from 'react'
import {
  addCitation,
  citationId,
  createInvestigation,
  getActiveInvestigationId,
  getInvestigation,
  isCitationPinned,
  removeCitation,
  type CitationInput,
} from '../lib/workbench'
import './PinReceiptButton.css'

// A body-level, layout-decoupled toast so the button can live inside an <a>/row
// without disturbing its geometry. Best-effort — never throws.
let toastEl: HTMLDivElement | null = null
let toastTimer: number | null = null
function flashToast(message: string) {
  try {
    if (!toastEl) {
      toastEl = document.createElement('div')
      toastEl.className = 'pin-receipt-toast'
      document.body.appendChild(toastEl)
    }
    toastEl.textContent = message
    toastEl.classList.add('pin-receipt-toast--show')
    if (toastTimer) window.clearTimeout(toastTimer)
    toastTimer = window.setTimeout(() => {
      toastEl?.classList.remove('pin-receipt-toast--show')
    }, 1800)
  } catch {
    /* toast is non-essential */
  }
}

interface PinReceiptButtonProps {
  /** Frozen provenance read off the row (id/capturedAt/investigationId stamped
   *  by the store). */
  citation: CitationInput
  /** Names a NEW investigation when none is active (same ramp as first-pin). */
  contextLabel: string
  /** Let the host re-render its own pinned indicators after a toggle. */
  onChange?: () => void
  className?: string
}

export default function PinReceiptButton({
  citation, contextLabel, onChange, className,
}: PinReceiptButtonProps) {
  const id = citation.id ?? citationId(citation)
  const [pinned, setPinned] = useState(() =>
    isCitationPinned(getActiveInvestigationId(), id))

  const toggle = useCallback((e: React.MouseEvent) => {
    // Rows are often wrapped in <a>/clickable containers — never navigate or
    // bubble into the row's own open handler.
    e.preventDefault()
    e.stopPropagation()

    let invId = getActiveInvestigationId()
    if (!invId || !getInvestigation(invId)) {
      invId = createInvestigation(contextLabel || citation.headline).id
    }

    if (isCitationPinned(invId, id)) {
      removeCitation(invId, id)
      setPinned(false)
      flashToast('Receipt unpinned')
    } else {
      addCitation(invId, { ...citation, id })
      setPinned(true)
      const inv = getInvestigation(invId)
      flashToast(`Pinned to ${inv?.title ?? 'investigation'}`)
    }
    onChange?.()
  }, [id, citation, contextLabel, onChange])

  return (
    <button
      type="button"
      className={`pin-receipt-btn ${pinned ? 'pin-receipt-btn--on' : ''} ${className ?? ''}`}
      onClick={toggle}
      aria-pressed={pinned}
      data-tip={pinned ? 'Unpin this receipt' : 'Pin this receipt to your investigation'}
    >
      {pinned ? '◆' : '◇'}
    </button>
  )
}
