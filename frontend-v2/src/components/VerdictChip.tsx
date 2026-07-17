// VerdictChip — an actionable dossier self-critique (Inés's flywheel).
//
// Each chip stands next to a critique the dossier already raised and offers the
// ONE action that resolves it. Resolving performs the real state change (drop a
// receipt, flag for corroboration, request a snapshot, flag a bad label) AND
// logs the decision with full provenance to the verdict log — the #204 gold.
// A resolved chip shows its outcome + an Undo (the toast+undo discipline).
import { useState } from 'react'
import {
  resolveVerdictAction,
  type VerdictAction,
  type VerdictChipDescriptor,
} from '../lib/verdictChips'
import { logVerdict, isTargetResolved, listVerdictLog, undoVerdict } from '../lib/verdictLog'
import './VerdictChip.css'

const RESOLVED_LABEL: Record<string, string> = {
  'split-relabel': 'Flagged: label under review',
  'drop-receipt': 'Receipt dropped',
  'needs-corroboration': 'Flagged: needs corroboration',
  'request-snapshot': 'Snapshot requested',
}

export function VerdictChip({ descriptor, investigationId, perform, onChange }: {
  descriptor: VerdictChipDescriptor
  investigationId: string
  /** Real state change for the action (remove the citation/pin, etc.). Flag-only
   *  actions may omit it — the verdict-log entry IS the persistent flag. */
  perform?: (descriptor: VerdictChipDescriptor, action: VerdictAction) => void
  onChange?: () => void
}) {
  const [, setTick] = useState(0)
  const rerender = () => setTick(t => t + 1)
  const action = resolveVerdictAction(descriptor.kind)
  const resolved = isTargetResolved(investigationId, descriptor.targetId, action.kind)

  const resolve = () => {
    perform?.(descriptor, action)
    logVerdict({
      investigationId,
      dossierTargetId: descriptor.targetId,
      targetKind: descriptor.targetKind,
      critique: descriptor.kind,
      action: action.kind,
      citations: descriptor.provenance,
    })
    rerender()
    onChange?.()
  }

  const undo = () => {
    // Undo the most recent matching entry (drop-receipt removal is not restored
    // here — the workbench toast+undo owns pin/citation restoration; this undoes
    // the LOGGED flag so the chip re-offers the decision).
    const entry = listVerdictLog(investigationId)
      .filter(e => e.dossierTargetId === descriptor.targetId && e.action === action.kind)
      .slice(-1)[0]
    if (entry) undoVerdict(entry.id)
    rerender()
    onChange?.()
  }

  if (resolved) {
    return (
      <span className="verdict-chip verdict-chip--resolved" data-action={action.kind}>
        ✓ {RESOLVED_LABEL[action.kind] ?? 'Resolved'}
        <button className="verdict-chip-undo" onClick={undo} data-tip="Undo this resolution — the chip will re-offer the action.">Undo</button>
      </span>
    )
  }

  return (
    <span className="verdict-chip" data-kind={descriptor.kind}>
      <span className="verdict-chip-critique">{descriptor.critique}</span>
      <button
        className={`verdict-chip-action${action.destructive ? ' verdict-chip-action--danger' : ''}`}
        onClick={resolve}
        data-tip={action.tip}
      >{action.label}</button>
    </span>
  )
}
