import { createPortal } from 'react-dom'
import { useStoryLens } from '../contexts/StoryLensContext'
import { LabelReviewChip } from '../lib/labelReviewChip'
import { decodeEntities } from '../lib/decodeEntities'
import { resolveThreadTitle } from '../lib/themeLabels'
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
  // Decode entity-encoded labels BEFORE resolveThreadTitle (which passes a
  // truthy knownLabel straight through) so the banner never shows raw
  // '&#x...;' soup — same decode NarrativeThreads applies on the same field.
  const knownLabel = anchor?.label ? decodeEntities(anchor.label) : null
  // Never render a raw opaque id (council N9 class): while the fetch is in
  // flight this reads "Loading thread…"; once settled without a label it
  // falls back to the honest generic, never state.anchorId verbatim.
  const label = resolveThreadTitle(state.anchorId, knownLabel, loading)
  return createPortal(
    <div className="sl-banner">
      <span className="sl-banner-mark">◈ STORY</span>
      <span className="sl-banner-label" data-tip={label}>{label}</span>
      {anchor?.label_status ? (
        <LabelReviewChip labelStatus={anchor.label_status} variant="chip" className="sl-banner-court" />
      ) : null}
      {anchor ? (
        <span className="sl-banner-counts">
          {data?.siblings.length ?? 0} hermanos · {anchor.countries.length} countries
        </span>
      ) : null}
      {loading ? <span className="sl-banner-note" role="status">measuring…</span> : null}
      {error ? <span className="sl-banner-note sl-banner-degraded" role="status">⚠ {error}</span> : null}
      <button type="button" className="sl-banner-exit" onClick={exit} aria-label="Exit story lens" data-tip="Exit story lens">
        ✕
      </button>
    </div>,
    document.body,
  )
}
