import { useMemo } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import { computeFocusRelation, type FocusRelation, type FocusRelationKind } from '../lib/focusRelation'

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
 */
export function useFocusRelation(): FocusRelation {
  const { focus, filter } = useFocus()
  const { nodes } = useFocusData()
  return useMemo(
    () => computeFocusRelation({
      focusType: focus.type as FocusRelationKind,
      focusValue: focus.value,
      filterCountry: filter.country,
      nodes,
    }),
    [focus.type, focus.value, filter.country, nodes],
  )
}
