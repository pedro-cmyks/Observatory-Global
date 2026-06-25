// Shared focus-relation context (#234, Paper 7 — analyst workflow).
//
// RQ: when an analyst focuses an entity in a multi-surface narrative dashboard,
// how should every surface re-scope to that entity's relations — honestly, never
// fabricating a relation when there is no signal?
//
// Today each panel re-scopes with its own bespoke logic (map heat, threads). As
// we extend re-scoping to the remaining panels (dock, public attention), a
// single derived relation — computed once from the focus-scoped data — keeps it
// DRY and consistent. `computeFocusRelation` is that single source: a pure
// function (no React) so it is unit-testable; `useFocusRelation` wraps it.

export interface FocusRelationNode {
  id: string
  signalCount?: number
}

export type FocusRelationKind = 'country' | 'person' | 'theme' | 'thread' | 'entity' | null

export interface FocusRelation {
  kind: FocusRelationKind
  value: string | null
  /** The country the focus concentrates in most (camera target / panel scope). */
  dominantCountry: string | null
  /** code -> relevance weight in [0,1] (volume-normalised), for relation-scoped paint. */
  relationCountries: Record<string, number>
  /** False when there is no relation signal — panels MUST stay global, not blank. */
  relationActive: boolean
}

const EMPTY: FocusRelation = {
  kind: null, value: null, dominantCountry: null, relationCountries: {}, relationActive: false,
}

const ENTITY_KINDS = new Set<FocusRelationKind>(['person', 'theme', 'thread', 'entity'])

export function computeFocusRelation(input: {
  focusType: FocusRelationKind
  focusValue: string | null | undefined
  filterCountry: string | null | undefined
  nodes: FocusRelationNode[]
}): FocusRelation {
  const { focusType, focusValue, filterCountry, nodes } = input

  // Country focus: the focused country is its own dominant. (The map paints its
  // co-occurrence partners from flows; that relation set stays in the map.)
  if (filterCountry) {
    return {
      kind: 'country', value: filterCountry, dominantCountry: filterCountry,
      relationCountries: { [filterCountry]: 1 }, relationActive: true,
    }
  }

  // Entity focus (person/theme/thread): the focus-scoped nodes ARE the
  // concentration — the /nodes fetch already filtered to this entity.
  if (ENTITY_KINDS.has(focusType) && focusValue && nodes.length > 0) {
    const max = Math.max(...nodes.map(n => n.signalCount || 0), 1)
    const relationCountries: Record<string, number> = {}
    for (const n of nodes) {
      if (n.id) relationCountries[n.id] = (n.signalCount || 0) / max
    }
    const dominant = nodes.reduce(
      (m, n) => ((n.signalCount || 0) > (m.signalCount || 0) ? n : m),
      nodes[0],
    )
    if (!dominant?.id) return EMPTY
    return {
      kind: focusType, value: focusValue, dominantCountry: dominant.id,
      relationCountries, relationActive: true,
    }
  }

  return EMPTY
}
