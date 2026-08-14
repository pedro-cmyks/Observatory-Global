import { createPortal } from 'react-dom'
import { useLocation, useSearchParams } from 'react-router-dom'
import { useStoryLens } from '../contexts/StoryLensContext'
import { useWorkspace } from '../contexts/WorkspaceContext'
import { LabelReviewChip } from '../lib/labelReviewChip'
import { decodeEntities } from '../lib/decodeEntities'
import { resolveThreadTitle } from '../lib/themeLabels'
import { siblingChipText, siblingFamilySummary, siblingKinshipSummary } from '../lib/storyLens'
import { threadPin } from '../lib/capturePayloads'
import { getActiveInvestigationId, mergePinSnapshot, PIN_SIBLING_FREEZE_CAP } from '../lib/workbench'
import './storyLens.css'

/** Portaled story-lens banner — same reasoning as EclipseChrome: rendered to
 * document.body so it sits above the absolutely-positioned command bar and
 * outside any #root filter. Cyan, not eclipse-red (calm scoping, not a
 * dramatic takeover) and z-indexed BELOW the eclipse ribbon so the eclipse
 * always wins when both are active. */
export function StoryLensBanner() {
  const { state, data, error, loading, notes, exit } = useStoryLens()
  const { pinItem, isPinned } = useWorkspace()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  // Spec-review fix (issue 4 — deep-link resurrection): an explicit ✕ must
  // strip `lens=` from the URL, not just reset context state. Without this,
  // the NEXT focus-driven URL write (mergeFocusIntoParams preserves every
  // param it doesn't own, including `lens`) leaves `lens=story&theme=X`
  // intact in the URL; the deep-link effect then refires on that change,
  // reads `!state.active` as true (the analyst just exited), and silently
  // re-enters the lens they just closed. Confirmed live: exit → click a
  // country → banner came back before this fix. Twin of App.tsx's
  // stripLensParam (the other exit paths there — clearAll/popPanel/closeAll
  // — need the same URL cleanup; this component calls context.exit()
  // directly and can't reach that helper) — keep the two in sync.
  const onExit = () => {
    exit()
    // .has(), not a truthy get(): an empty `lens=` must be stripped too,
    // matching App.tsx's stripLensParam exactly.
    if (searchParams.has('lens')) {
      const next = new URLSearchParams(searchParams)
      next.delete('lens')
      setSearchParams(next, { replace: true })
    }
  }
  if (!state.active) return null
  // Task 10 route guard: this banner portals to document.body from inside the
  // keep-alive App shell (main.tsx AppBriefKeepAlive gives App display:none
  // while the router is on /brief) — but a PORTAL ESCAPES an ancestor's
  // display:none, so without this the banner would float over the Brief
  // reading surface whenever a lens session was left active. The lens is
  // console-only (its anchors are dynamic-topic threads opened in the
  // console), so hide it off the console route. Predicate matches main.tsx's
  // own `isApp = pathname === '/app'` exactly — no other path is "the console".
  if (location.pathname !== '/app') return null
  const anchor = data?.anchor ?? null
  // Decode entity-encoded labels BEFORE resolveThreadTitle (which passes a
  // truthy knownLabel straight through) so the banner never shows raw
  // '&#x...;' soup — same decode NarrativeThreads applies on the same field.
  // T11 gate fix (L4): the resolved payload's own anchor.label wins when it
  // exists; otherwise fall back to state.labelHint — the clicked row's
  // ALREADY-KNOWN label, captured at the moment the analyst opened it. This
  // is the ONLY title available on the degraded path (db_error / network
  // throw never populates `data.anchor`), where the banner used to drop to
  // the generic "Narrative Thread" even though the clicked row carried the
  // full name the whole time.
  const knownLabel = anchor?.label
    ? decodeEntities(anchor.label)
    : state.labelHint ? decodeEntities(state.labelHint) : null
  // Never render a raw opaque id (council N9 class): while the fetch is in
  // flight this reads "Loading thread…"; once settled without a label it
  // falls back to the honest generic, never state.anchorId verbatim.
  const label = resolveThreadTitle(state.anchorId, knownLabel, loading)
  const familySummary = siblingFamilySummary(data?.siblings ?? [])
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
        // T11 gate fix (L2): truthful hermano/primo split — the payload's
        // own `kinship` per sibling, never a flat "N hermanos" that erases
        // the direct-edge-vs-indirect-walk distinction the design exists to
        // carry.
        <span className="sl-banner-counts">
          {siblingKinshipSummary(data?.siblings ?? [])} · {anchor.countries.length} countries
        </span>
      ) : null}
      {/* Z3 (2026-08-14): an R2 umbrella can now be in this neighborhood. It is
          a CONTAINER of stories, not a peer — and the kinship split above
          cannot say so, because level and directness are orthogonal (a family
          can be a hermano). Its own note rather than a third word in that
          split. Null when every sibling is a leaf, so a leaf-only lens looks
          exactly as it did. */}
      {familySummary ? (
        <span
          className="sl-banner-note sl-banner-flag"
          data-tip="One or more neighbours is an R2 FAMILY — an umbrella rolling up several stories of one event. Their edges were measured against an aggregate centroid, a weaker claim than a match to a single story."
        >
          ◫ {familySummary}
        </span>
      ) : null}
      {/* T11 gate fix (M1): the payload's own measured caveats, made visible
          — an umbrella walked via a stand-in child, or a degraded (not
          absent) country-receipt lane. Both can coexist with a resolved
          anchor, so neither is gated on `loading`/`error`. */}
      {notes.includes('umbrella_resolved_via_child') ? (
        <span
          className="sl-banner-note sl-banner-flag"
          data-tip="This umbrella's neighborhood was measured from its largest child story — a stand-in, not the umbrella itself"
        >
          via child story
        </span>
      ) : null}
      {notes.includes('country_receipts_degraded') ? (
        <span
          className="sl-banner-note sl-banner-degraded"
          data-tip="The country footprint query failed — shared-country receipts are missing, not absent"
        >
          ⚠ country lane degraded
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
      <button type="button" className="sl-banner-exit" onClick={onExit} aria-label="Exit story lens" data-tip="Exit story lens">
        ✕
      </button>
    </div>,
    document.body,
  )
}
