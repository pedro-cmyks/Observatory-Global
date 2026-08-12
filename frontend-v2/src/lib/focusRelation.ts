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
//
// GHOST-SCOPE REGRESSION (2026-08-12). A cold console with no action taken
// rendered "SLOVENIA · OWN INSTRUMENTS" in the markets dock and "PUBLIC
// ATTENTION · SLOVENIA — No attention data" in the anomaly dock. Two
// independent defects produced that ghost, both fixed here / in the hook:
//   1. The argmax was `nodes.reduce((m, n) => count(n) > count(m) ? n : m,
//      nodes[0])`. Strict `>` means the SEED survives every tie — and the
//      /nodes payload is sorted by ANOMALY HEAT, not volume (backend
//      workspace.py:391), so nodes[0] is structurally the most anomalous, i.e.
//      the tiny-corpus slot. Under a narrow focus where several countries carry
//      one signal each, "dominant" was just whichever row the backend happened
//      to return first. Fixed by the two gates below.
//   2. The relation was derived from STALE nodes (see `trackFocusNodes`).
// The rule the fixes share: an arbitrary scope is worse than no scope. When the
// measurement does not support a claim, panels stay global.

export interface FocusRelationNode {
  id: string
  signalCount?: number
}

export type FocusRelationKind = 'country' | 'person' | 'theme' | 'thread' | 'entity' | null

export interface FocusRelation {
  kind: FocusRelationKind
  value: string | null
  /**
   * The country the focus concentrates in most (camera target / panel scope).
   * NULL when the measurement does not support a claim — a tie, or a lead too
   * thin to be distinguishable from tagging noise.
   */
  dominantCountry: string | null
  /**
   * code -> relevance weight in [0,1] (volume-normalised), for relation-scoped
   * paint. Measured field, NOT a claim: this stays populated even when the
   * dominant-country claim is refused, so dimming/lighting consumers keep
   * working where a scope chip would be dishonest.
   */
  relationCountries: Record<string, number>
  /** False when no SCOPE CLAIM is warranted — panels MUST stay global, not blank. */
  relationActive: boolean
  /**
   * Signals behind the leading country. Measured, so it is reported whether or
   * not the claim cleared the gates — it is the number panels print to make the
   * re-scope self-evident ("SI leads this thread with 7 of 12 signals").
   */
  leaderSignals: number | null
  /** Signals across every country in the focus-scoped relation (the denominator). */
  totalSignals: number
}

/**
 * Minimum signals the leader must carry before it can claim a panel's scope.
 *
 * Under a narrow thread/person focus a single mis-geotagged article — or one
 * story plus its syndicated twin — is enough to put a country on top. Three is
 * the smallest count that cannot be produced by one item and one duplicate, so
 * it is the floor below which a "lead" is indistinguishable from tagging noise.
 * A focus genuinely concentrated in one country clears it immediately.
 */
export const MIN_LEADER_SIGNALS = 3

/**
 * How far ahead of the runner-up the leader must be. 1 = strictly greater.
 *
 * Named rather than inlined because the old code's implicit answer was ZERO
 * (ties silently went to nodes[0]) and that is precisely the defect. A tie is
 * not a dominant country.
 */
export const MIN_LEAD_MARGIN = 1

const EMPTY: FocusRelation = {
  kind: null, value: null, dominantCountry: null, relationCountries: {},
  relationActive: false, leaderSignals: null, totalSignals: 0,
}

const ENTITY_KINDS = new Set<FocusRelationKind>(['person', 'theme', 'thread', 'entity'])

const count = (n: FocusRelationNode) => n.signalCount || 0

export function computeFocusRelation(input: {
  focusType: FocusRelationKind
  focusValue: string | null | undefined
  filterCountry: string | null | undefined
  nodes: FocusRelationNode[]
}): FocusRelation {
  const { focusType, focusValue, filterCountry, nodes } = input

  // Country focus: the focused country is its own dominant. (The map paints its
  // co-occurrence partners from flows; that relation set stays in the map.)
  // No discovery happened here, so there is no basis to report.
  if (filterCountry) {
    return {
      kind: 'country', value: filterCountry, dominantCountry: filterCountry,
      relationCountries: { [filterCountry]: 1 }, relationActive: true,
      leaderSignals: null, totalSignals: 0,
    }
  }

  // Entity focus (person/theme/thread): the focus-scoped nodes ARE the
  // concentration — the /nodes fetch already filtered to this entity.
  if (ENTITY_KINDS.has(focusType) && focusValue && nodes.length > 0) {
    const attributable = nodes.filter(n => !!n.id)
    if (attributable.length === 0) return EMPTY

    const max = Math.max(...attributable.map(count), 1)
    const relationCountries: Record<string, number> = {}
    let totalSignals = 0
    for (const n of attributable) {
      relationCountries[n.id] = count(n) / max
      totalSignals += count(n)
    }

    // Rank a COPY — `nodes` is React context state, never sort it in place.
    const ranked = [...attributable].sort((a, b) => count(b) - count(a))
    const leaderSignals = count(ranked[0])
    const runnerUpSignals = ranked.length > 1 ? count(ranked[1]) : 0
    // Both gates, in the order they read: is the leader supported at all, and
    // is it actually leading? Either failure means no scope claim.
    const claimable =
      leaderSignals >= MIN_LEADER_SIGNALS &&
      leaderSignals - runnerUpSignals >= MIN_LEAD_MARGIN

    return {
      kind: focusType,
      value: focusValue,
      dominantCountry: claimable ? ranked[0].id : null,
      relationCountries,
      relationActive: claimable,
      leaderSignals,
      totalSignals,
    }
  }

  return EMPTY
}

const KIND_NOUN: Record<string, string> = {
  person: 'person',
  // A `theme` focus IS a narrative thread in this console (filter.theme carries
  // the thread id) — the panels already label it THREAD.
  theme: 'thread',
  thread: 'thread',
  entity: 'entity',
}

export function relationKindNoun(kind: FocusRelationKind): string {
  return KIND_NOUN[kind ?? ''] ?? 'focus'
}

/**
 * The measured basis behind a re-scope, as one printable clause:
 * "SI leads this thread with 7 of 12 signals".
 *
 * Panels re-scoped by the relation MUST show this. The ghost was not only that
 * the wrong country won — it was that nothing on screen said why any country
 * won, so an unexplainable scope looked like a fact. Returns null whenever
 * there is no discovered claim to explain.
 *
 * `countryLabel` lets a caller substitute a resolved country name; the raw
 * ISO code is the default so the lib stays free of the name gazetteer.
 */
export function relationBasisLabel(r: FocusRelation, countryLabel?: string): string | null {
  if (!r.relationActive || !r.dominantCountry || r.kind === 'country') return null
  if (r.leaderSignals == null || r.totalSignals <= 0) return null
  return `${countryLabel || r.dominantCountry} leads this ${relationKindNoun(r.kind)}`
    + ` with ${r.leaderSignals} of ${r.totalSignals} signals`
}

export interface FocusNodesTracker {
  key: string
  nodesAtChange: unknown
}

/**
 * Stale-nodes guard — the second half of the ghost fix, mirroring the
 * `nodesAtChange` identity guard App.tsx already carries for the map fly-to
 * ("on focus change `nodes` is briefly the previous focus's data (refetch in
 * flight), so flying immediately centres on the wrong place").
 *
 * The relation has exactly the same hazard, and it is worse here: when the
 * focus-scoped /api/v2/nodes fetch comes back EMPTY, FocusDataContext
 * deliberately KEEPS the previous list. Without this guard the relation would
 * happily claim a dominant country derived from a dataset with no connection to
 * the current focus — which is how a scope chip appears for a country the panel
 * then reports "no data" for.
 *
 * Pure so it can be tested without a renderer: the hook holds `tracker` in a
 * ref and passes it back on the next render.
 */
export function trackFocusNodes(
  previous: FocusNodesTracker | null,
  focusKey: string | null,
  nodes: unknown,
): { tracker: FocusNodesTracker | null; stale: boolean } {
  if (!focusKey) return { tracker: null, stale: false }
  // Re-seed on every focus change; keep the seed while the focus holds.
  const tracker = previous && previous.key === focusKey
    ? previous
    : { key: focusKey, nodesAtChange: nodes }
  // Same array identity as at focus-change time ⇒ the focus's own data has not
  // landed yet ⇒ there is no relation to speak of.
  return { tracker, stale: tracker.nodesAtChange === nodes }
}
