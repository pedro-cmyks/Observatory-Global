// X5 · the student's missing button (colegio ciego 2026-08-13).
//
// "the Ukraine page was genuinely a one-stop source list … One change that
// would most help: a copy citation / export source list button that gives
// outlet + headline + date + URL per story."
//
// Two affordances, one idiom:
//   ⧉ on a receipt row  → that row as one citable line.
//   ⧉ Copy source list  → every VISIBLE receipt of this story/dossier, numbered.
//
// Deliberately quiet: the same footprint and rest-opacity as the ◇ pin beside
// it, so adding it shifts no layout and steals no attention from the headline.
// It is always in the DOM (never hover-mounted) — a hover-only *mount* is
// unreachable on touch, and the council's two mobile readers both ended their
// session on unreachable controls.
import { useCallback, useState } from 'react'
import { copyText } from '../lib/copyText'
import { formatCitation, formatSourceList, type CitableReceipt, type SourceListOptions } from '../lib/citationFormat'
import { flashPinToast } from '../lib/pinToast'
import './CopyCitationButton.css'

type CopyState = 'idle' | 'ok' | 'failed'

function useCopyAction(buildText: () => string, okMessage: string) {
  const [state, setState] = useState<CopyState>('idle')
  const run = useCallback(async (e: React.MouseEvent) => {
    // Receipt rows are wrapped in <a>/clickable containers — copying must
    // never navigate or open the row (same guard the pin button carries).
    e.preventDefault()
    e.stopPropagation()
    const text = buildText()
    const ok = await copyText(text)
    setState(ok ? 'ok' : 'failed')
    // A failed copy SAYS so; it never leaves the reader believing the citation
    // is on their clipboard.
    flashPinToast(ok ? okMessage : 'Copy failed — your browser blocked the clipboard')
    setTimeout(() => setState('idle'), 1400)
  }, [buildText, okMessage])
  return { state, run }
}

const GLYPH: Record<CopyState, string> = { idle: '⧉', ok: '✓', failed: '⚠' }

interface CopyCitationButtonProps {
  receipt: CitableReceipt
  className?: string
}

/** One receipt → `Outlet — “Headline” (Language), date. url` on the clipboard. */
export default function CopyCitationButton({ receipt, className }: CopyCitationButtonProps) {
  const { state, run } = useCopyAction(() => formatCitation(receipt), 'Citation copied')
  // Nothing citable on this row → no dead button.
  if (!formatCitation(receipt)) return null
  return (
    <button
      type="button"
      className={`copy-citation-btn copy-citation-btn--${state} ${className ?? ''}`}
      onClick={run}
      aria-label="Copy citation"
      data-tip="Copy citation — outlet, headline, original language, date and link"
    >
      {GLYPH[state]}
    </button>
  )
}

interface CopySourceListButtonProps {
  receipts: CitableReceipt[]
  /** Story / country / investigation the list belongs to (header line). */
  title?: string | null
  className?: string
}

/** Story- and dossier-level: every visible receipt as a numbered source list. */
export function CopySourceListButton({ receipts, title, className }: CopySourceListButtonProps) {
  const opts: SourceListOptions = { title, retrievedAt: new Date().toISOString().slice(0, 10) }
  const { state, run } = useCopyAction(
    () => formatSourceList(receipts, opts),
    'Source list copied',
  )
  // Count what will actually be emitted (deduped, citable) — a button that
  // promises 12 and copies 9 is the count-divergence defect in miniature.
  const emitted = formatSourceList(receipts, opts)
  if (!emitted) return null
  const n = emitted.split('\n').filter(l => /^\d+\. /.test(l)).length
  return (
    <button
      type="button"
      className={`copy-source-list-btn copy-source-list-btn--${state} ${className ?? ''}`}
      onClick={run}
      aria-label={`Copy source list — ${n} receipt${n === 1 ? '' : 's'}`}
      data-tip="Copy every receipt shown here as a numbered source list — outlet, headline, original language, date and link"
    >
      {GLYPH[state]} {state === 'ok' ? 'Copied' : state === 'failed' ? 'Copy failed' : `Copy source list (${n})`}
    </button>
  )
}
