/**
 * The Lens's sections, as data.
 *
 * The Lens is one anatomy at N scopes: identity, what it says, WHERE IT LIVES,
 * CONNECTED, attention — always that order, at every scope. This module owns
 * the two the phone gained in #236 Task 8 (the ones that absorbed the retired
 * Map and Universe tabs) plus attention, and it owns them as a PURE
 * transformation so the rules below are testable without a renderer.
 *
 * TWO RULES, both inherited rather than invented here:
 *
 * 1. AN EMPTY SECTION RENDERS ITS REASON. Never blank, never filler. A section
 *    that shows nothing and says nothing is indistinguishable from a section
 *    that is broken, and the reader cannot tell which.
 *
 * 2. A CONNECTED ROW ALWAYS CARRIES ITS RECEIPT. This section is the phone's
 *    stand-in for the Universe, and the story lens shipped DARK
 *    (STORY_LENS_AUTO=false) on exactly this point: its own pre-registered gate
 *    refused to ship a lens whose receipts were honest but whose neighbours
 *    measured false. A neighbour without a stated basis is a claim with no
 *    evidence, so an unreceipted row is dropped — and the drop is COUNTED
 *    (`withheld`), because silent filtering is the other half of the same
 *    dishonesty.
 *
 * WHY `loading` IS A STATE AND NOT AN EMPTY SECTION. Three states — ok, empty,
 * degraded — cannot express "not measured yet", and the only way to render an
 * in-flight lane without a fourth state is to call it empty. That is precisely
 * the defect this codebase already shipped and paid to remove once: a timed-out
 * search rendered as "No results", so the heaviest subjects looked emptiest.
 * A lane that has not answered is not a lane that answered "none".
 */

/** A country this scope's signal actually lands in, with its count. */
export interface CountryRow {
  code: string
  name: string
  count: number
}

/** A measured neighbour. `receipt` is the basis — what makes it a neighbour. */
export interface ConnectedRow {
  id: string
  label: string
  receipt: string
  /** Which Lens scope opening this row moves to. Display never depends on it. */
  kind?: 'thread' | 'country' | 'person'
}

export interface AttentionRow {
  source: string
  title: string
  score: number
}

export interface LensPayload {
  countries: CountryRow[]
  connected: ConnectedRow[]
  attention: AttentionRow[]
}

export type SectionKey = 'whereItLives' | 'connected' | 'attention'

/**
 * What a lane reports about ITSELF, independent of how many rows it returned.
 *
 * `ok` is the default and needs no entry. The rest all exist because zero rows
 * means something different in each case, and only the lane knows which:
 * - `loading`  — has not answered yet.
 * - `no_anchor`— nothing is focused, so there was no subject to measure against.
 * - `no_subject` — something IS focused, but the lane could not resolve it to a
 *   subject it can measure. Distinct from `no_anchor` (which is about the
 *   reader having opened nothing) and from a measured zero: nothing was
 *   compared, so "none matched" would claim a comparison that never ran.
 * - `unavailable` — this scope kind has no such lane; nothing was attempted.
 * - `db_error` / `timeout` — it was attempted and it failed.
 */
export type LaneStatus =
  | 'ok' | 'loading' | 'no_anchor' | 'no_subject' | 'unavailable' | 'db_error' | 'timeout'

export type LaneStatuses = Partial<Record<SectionKey, LaneStatus>>

export type SectionState = 'ok' | 'empty' | 'degraded' | 'loading'

export interface Section<T> {
  state: SectionState
  /** Present on every state but `ok`. What to render instead of rows. */
  reason?: string
  rows: T[]
  /**
   * Rows the section refused to show, and why it is not silent about them.
   * Only set when non-zero, so an untouched section stays exactly three keys.
   */
  withheld?: number
}

export interface LensSections {
  whereItLives: Section<CountryRow>
  connected: Section<ConnectedRow>
  attention: Section<AttentionRow>
}

/** The heading each section wears. Named once so no caller re-types them. */
export const SECTION_LABELS: Record<SectionKey, string> = {
  whereItLives: 'where it lives',
  connected: 'connected',
  attention: 'attention',
}

/**
 * The copy for every state a lane can be in, per section.
 *
 * Written out per section rather than templated, because the honest sentence
 * genuinely differs: "no country resolved" is a fact about geocoding, "no
 * measured neighbour cleared the bar" is a fact about a ranking threshold, and
 * a shared template would blur them into one vague line.
 *
 * `no_subject` is produced by `connected` alone today — its lane measures a
 * thread against the ranked pool that thread is IN, and a deep-linked thread
 * can be outside it. The other two are written anyway rather than typed as
 * optional, because a lane with no sentence would render blank, which is the
 * one outcome this table exists to make unrepresentable.
 */
const REASONS: Record<SectionKey, Record<Exclude<LaneStatus, 'ok'> | 'none', string>> = {
  whereItLives: {
    none: 'No country resolved for this scope.',
    loading: 'Measuring where this lives…',
    no_anchor: 'Nothing is focused yet.',
    no_subject: 'This scope could not be resolved to a measurable subject.',
    unavailable: 'Where this lives is not measured for this scope.',
    db_error: 'Where this lives could not be measured right now.',
    timeout: 'Where this lives could not be measured right now.',
  },
  connected: {
    none: 'No measured neighbour cleared the bar.',
    loading: 'Measuring the neighbourhood…',
    no_anchor: 'Open a thread, a country or a person — neighbours are measured against a subject.',
    no_subject: 'This story is not in the current ranked field, so no neighbourhood was measured.',
    unavailable: 'Neighbours are not measured for this scope yet.',
    db_error: 'Neighbours could not be measured right now.',
    timeout: 'Neighbours could not be measured right now.',
  },
  attention: {
    none: 'No public attention matched this scope.',
    loading: 'Reading public attention…',
    no_anchor: 'Nothing is focused yet.',
    no_subject: 'This scope could not be resolved to a measurable subject.',
    unavailable: 'Public attention is not measured for this scope.',
    db_error: 'Public attention could not be read right now.',
    timeout: 'Public attention could not be read right now.',
  },
}

/**
 * The `/api/v2/nodes` query that answers "where does THIS live", or `null` when
 * the scope has no honest mapping onto the endpoint's focus keys.
 *
 * `null` is not a failure — it is the difference between a lane that returned
 * nothing and a lane that was never asked, and the section says so differently.
 * `thread` maps to `focus_type=theme` because that is the key the endpoint uses
 * for a topic id; the Lens calls the same thing a thread.
 *
 * Only the three fields the rows render are requested.
 */
export function nodesQueryFor(scope: { kind: string; id: string }): string | null {
  const base = '/api/v2/nodes?range=24h&fields=id,name,signalCount'
  switch (scope.kind) {
    case 'field': return base
    case 'thread': return `${base}&focus_type=theme&focus_value=${encodeURIComponent(scope.id)}`
    case 'country': return `${base}&focus_type=country&focus_value=${encodeURIComponent(scope.id)}`
    case 'person': return `${base}&focus_type=person&focus_value=${encodeURIComponent(scope.id)}`
    // story (a free-text query), attention (a trends/wiki item), chokepoint (a
    // maritime passage) and signal have no country-footprint key on this
    // endpoint. Guessing one would put a real-looking list under a scope it was
    // never measured for.
    default: return null
  }
}

/**
 * Turn a `/api/v2/nodes` payload into rows plus the lane's honest status.
 *
 * THE WHOLE POINT IS THE `error` KEY. That endpoint answers HTTP 200 on
 * failure: its handler ends `except Exception as e: return {"nodes": [],
 * "count": 0, "error": str(e), ...}` (backend/app/routers/workspace.py:412),
 * and the success payload carries no `error` key at all. A timeout stringifies
 * to the EMPTY STRING, so the common failure arrives as `error: ""` — which
 * means testing the value for truthiness classifies exactly the failure we
 * care about as success, and the section then reports a timed-out query as
 * "No country resolved for this scope."
 *
 * That is the timeout-as-absence defect this codebase already shipped once and
 * removed, reappearing on a new surface. Measured, not theorised: the same
 * thread query returned `count=0, error=""` four times and `count=20` on the
 * fifth, in five consecutive calls. Presence of the key is the test.
 */
export function readNodesResponse(
  json: unknown,
  opts: { resolveName?: (code: string, apiName?: string) => string; cap?: number } = {},
): { rows: CountryRow[]; lane: LaneStatus } {
  const resolveName = opts.resolveName ?? ((code: string, apiName?: string) => apiName || code)
  const cap = opts.cap ?? Infinity
  if (!json || typeof json !== 'object') return { rows: [], lane: 'db_error' }
  if ('error' in (json as Record<string, unknown>)) return { rows: [], lane: 'db_error' }

  const raw = (json as { nodes?: unknown }).nodes
  if (!Array.isArray(raw)) return { rows: [], lane: 'db_error' }

  const rows = (raw as Array<{ id?: string; name?: string; signalCount?: number }>)
    .filter((n) => !!n?.id)
    .map((n) => ({ code: n.id!, name: resolveName(n.id!, n.name), count: n.signalCount || 0 }))
    .sort((a, b) => b.count - a.count)
    .slice(0, cap)
  return { rows, lane: 'ok' }
}

/**
 * A lane that FAILED, as opposed to one that has not answered or was not tried.
 * A type guard rather than a boolean so the compiler carries the distinction
 * into the branch — the difference between a failure and an absence is the
 * whole subject of this module, and it should not survive only in prose.
 */
function isFailure(status: LaneStatus): status is 'db_error' | 'timeout' {
  return status === 'db_error' || status === 'timeout'
}

function section<T>(key: SectionKey, rows: T[], status: LaneStatus, withheld = 0): Section<T> {
  const out: Section<T> = { state: 'ok', rows }
  if (withheld > 0) out.withheld = withheld

  // A failing lane reports the failure whether or not it managed some rows:
  // partial data from a broken lane is still partial, and saying so is the
  // whole point of the `degraded` rail.
  if (isFailure(status)) {
    out.state = 'degraded'
    out.reason = REASONS[key][status]
    return out
  }
  if (status === 'loading') {
    // Rows already in hand keep showing while the rest arrives — a refresh
    // must not blank a section that has content.
    if (rows.length > 0) return out
    out.state = 'loading'
    out.reason = REASONS[key].loading
    return out
  }
  if (rows.length > 0) return out

  out.state = 'empty'
  // `no_anchor` and `unavailable` are empty for a reason that is NOT "we looked
  // and found none" — naming them separately is what stops the section from
  // claiming a measurement it never made.
  out.reason = status === 'ok' ? REASONS[key].none : REASONS[key][status]
  return out
}

/**
 * Build the three sections from what the scope could gather.
 *
 * `lanes` is how a caller says something the row count cannot: that a lane is
 * still in flight, was never applicable, or failed. Omitting it means every
 * lane answered, and zero rows therefore means a measured zero.
 */
export function buildSections(payload: LensPayload, lanes: LaneStatuses = {}): LensSections {
  // Rule 2, enforced here rather than at the render site: a row whose basis is
  // missing or blank cannot be shown, because the phone has no room for a
  // caveat and an uncaveated neighbour reads as a measured fact.
  const receipted = payload.connected.filter((r) => !!r.receipt && r.receipt.trim().length > 0)
  const withheld = payload.connected.length - receipted.length

  return {
    whereItLives: section('whereItLives', payload.countries, lanes.whereItLives ?? 'ok'),
    connected: section('connected', receipted, lanes.connected ?? 'ok', withheld),
    attention: section('attention', payload.attention, lanes.attention ?? 'ok'),
  }
}
