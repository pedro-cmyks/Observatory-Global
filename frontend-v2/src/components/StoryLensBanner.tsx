import { createPortal } from 'react-dom'
import { useStoryLens } from '../contexts/StoryLensContext'
import { LabelReviewChip } from '../lib/labelReviewChip'
import './storyLens.css'

/** Portaled story-lens banner — same reasoning as EclipseChrome: rendered to
 * document.body so it sits above the absolutely-positioned command bar and
 * outside any #root filter. Cyan, not eclipse-red (calm scoping, not a
 * dramatic takeover) and z-indexed BELOW the eclipse ribbon so the eclipse
 * always wins when both are active. */
export function StoryLensBanner() {
  const { state, data, error, loading, exit } = useStoryLens()
  if (!state.active) return null
  const anchor = data?.anchor ?? null
  const label = anchor?.label ?? state.anchorId ?? ''
  return createPortal(
    <div className="sl-banner" role="status">
      <span className="sl-banner-mark">◈ STORY</span>
      <span className="sl-banner-label" data-tip={label}>{label}</span>
      {anchor?.label_status ? (
        <LabelReviewChip labelStatus={anchor.label_status} variant="chip" className="sl-banner-court" />
      ) : null}
      {data ? (
        <span className="sl-banner-counts">
          {data.siblings.length} hermanos · {anchor?.countries.length ?? 0} países
        </span>
      ) : null}
      {loading ? <span className="sl-banner-note">measuring…</span> : null}
      {error ? <span className="sl-banner-note sl-banner-degraded">⚠ {error}</span> : null}
      <button type="button" className="sl-banner-exit" onClick={exit} aria-label="Exit story lens" data-tip="Exit story lens">
        ✕
      </button>
    </div>,
    document.body,
  )
}
