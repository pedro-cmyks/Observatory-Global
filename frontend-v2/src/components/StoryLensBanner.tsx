import { createPortal } from 'react-dom'
import { useStoryLens } from '../contexts/StoryLensContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { LabelReviewChip } from '../lib/labelReviewChip'
import { decodeEntities } from '../lib/decodeEntities'
import { resolveThreadTitle } from '../lib/themeLabels'
import { siblingChipText } from '../lib/storyLens'
import { threadPin } from '../lib/capturePayloads'
import { getActiveInvestigationId, mergePinSnapshot, PIN_SIBLING_FREEZE_CAP } from '../lib/workbench'
import './storyLens.css'

/** Portaled story-lens banner — same reasoning as EclipseChrome: rendered to
 * document.body so it sits above the absolutely-positioned command bar and
 * outside any #root filter. Cyan, not eclipse-red (calm scoping, not a
 * dramatic takeover) and z-indexed BELOW the eclipse ribbon so the eclipse
 * always wins when both are active. */
export function StoryLensBanner() {
  const { state, data, error, loading, exit } = useStoryLens()
  const { pinItem, isPinned } = useWorkspace()
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
  const pinId = state.anchorId ? `theme-${state.anchorId}` : null
  const alreadyPinned = Boolean(pinId && isPinned(pinId))

  // Task 9: freeze this measured neighborhood into the analyst's active
  // investigation. `pinItem` handles the pin + its own async panel-snapshot
  // enrichment (evidence/summary/labelStatus); the sibling freeze below is a
  // SEPARATE write to the same pin. Write order between the two no longer
  // matters — mergePinSnapshot (Task 9) merges fields instead of replacing,
  // so whichever lands second never erases the other.
  //
  // Quality-review fold: onPin is a ONE-SHOT freeze, never a refresh. Once
  // pinned, this early-returns — no re-pin, so no re-fetched panel snapshot,
  // so the frozen `capturedAt` stamp (incumbent-wins, see mergePinSnapshot)
  // can never end up paired with content that's newer than the stamp says.
  // Managing/updating an existing pin is the Workbench's job, not the lens.
  const onPin = () => {
    if (!state.anchorId || !anchor || alreadyPinned) return
    pinItem(threadPin(state.anchorId, label, { lens: true }))
    const invId = getActiveInvestigationId()
    if (invId) {
      mergePinSnapshot(invId, `theme-${state.anchorId}`, {
        siblings: (data?.siblings ?? []).slice(0, PIN_SIBLING_FREEZE_CAP).map((s) => ({
          id: s.id, label: s.label, weight: s.weight, reason: siblingChipText(s).text,
        })),
      })
    }
  }

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
      {/* No pinning an unmeasured story: only renders once the anchor resolved. */}
      {anchor ? (
        <button
          type="button"
          className="sl-banner-pin"
          data-pinned={alreadyPinned}
          disabled={alreadyPinned}
          onClick={onPin}
          data-tip={alreadyPinned
            ? 'Frozen in your investigation — manage in the Workbench'
            : 'Freeze this neighborhood into an investigation'}
        >
          {alreadyPinned ? '◆ pinned' : '◇ Pin story'}
        </button>
      ) : null}
      <button type="button" className="sl-banner-exit" onClick={exit} aria-label="Exit story lens" data-tip="Exit story lens">
        ✕
      </button>
    </div>,
    document.body,
  )
}
