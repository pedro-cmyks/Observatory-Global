import { useMemo, useState } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import {
  computeFocusRelation,
  trackFocusNodes,
  type FocusNodesTracker,
  type FocusRelation,
  type FocusRelationKind,
  type FocusRelationNode,
} from '../lib/focusRelation'

/** Stable empty array so the memo below does not re-run on every stale render. */
const NO_NODES: FocusRelationNode[] = []

/**
 * Shared focus-relation context (#234, Paper 7 — analyst workflow).
 *
 * Any panel can subscribe to know what the current focus *relates to* — the
 * countries it concentrates in and the dominant one — and re-scope itself,
 * instead of each panel re-deriving relation logic. Honest by construction:
 * `relationActive` is false when there is no signal, so panels stay global
 * rather than fabricating or blanking.
 *
 * Derives from the already-focus-scoped FocusDataContext nodes (the /nodes fetch
 * passes focus_type/value) plus the active country filter.
 *
 * STALENESS (ghost-scope fix, 2026-08-12): this recomputed the instant
 * focus.type/value changed, while `nodes` still held the PREVIOUS focus's array
 * (the focus-scoped fetch is in flight — and FocusDataContext deliberately
 * KEEPS the old list when the new response is empty). Panels therefore claimed
 * a scope derived from data unrelated to the focus. App.tsx:1058 already
 * immunised the map fly-to with a nodes-identity guard; the same guard now
 * covers the panels. While the nodes are stale the relation sees NO nodes at
 * all, so it reports an honest absence instead of a ghost. The country branch
 * is unaffected — it never reads nodes.
 *
 * The tracker is adjusted DURING render (React's sanctioned "adjusting state
 * when props change" pattern) rather than in an effect: an effect lands one
 * render too late, so the stale relation would already have painted — and it
 * would keep painting, because nothing re-renders until `nodes` finally
 * changes. `trackFocusNodes` itself is pure, derived only from its arguments.
 */
export function useFocusRelation(): FocusRelation {
  const { focus, filter } = useFocus()
  const { nodes } = useFocusData()

  const [tracked, setTracked] = useState<FocusNodesTracker | null>(null)
  const focusKey = focus.type && focus.value ? `${focus.type}:${focus.value}` : null
  const { tracker, stale } = trackFocusNodes(tracked, focusKey, nodes)
  // Re-seeds only when the focus itself changed (trackFocusNodes returns the
  // same object otherwise), so this settles in one extra render and never loops.
  if (tracked !== tracker) setTracked(tracker)

  return useMemo(
    () => computeFocusRelation({
      focusType: focus.type as FocusRelationKind,
      focusValue: focus.value,
      filterCountry: filter.country,
      nodes: stale ? NO_NODES : nodes,
    }),
    [focus.type, focus.value, filter.country, nodes, stale],
  )
}
