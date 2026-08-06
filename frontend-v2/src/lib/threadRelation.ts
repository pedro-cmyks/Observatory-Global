/**
 * The #234 thread-sibling relation: which OTHER threads relate to the one you
 * opened, and — always — on what basis.
 *
 * Two bases, and the second one is the whole point:
 *
 * 1. SHARED PRIMARY GEOGRAPHY — a country in the anchor's top TWO, not its top
 *    five. Sharing the dominant country (usually US) is too broad to be a
 *    sibling; it relates half the field to the other half.
 *
 * 2. SHARED DISTINCTIVE ENTITY — an actor carried by FEW threads in this pool.
 *    Naive entity overlap was measured HARMFUL: "donald trump" appeared in
 *    14 of 30 threads, so relating on any shared entity linked every unrelated
 *    thread to every other. Rarity is what makes the signal real — a common
 *    actor is noise, a rare shared actor is a genuine sibling. The cap is a
 *    quarter of the pool, never above 3 and never below 2.
 *
 * DOCUMENT FREQUENCY IS A PROPERTY OF THE POOL, NOT OF THE ENTITY. The same
 * actor can be distinctive in one pool and ubiquitous in another, so a caller
 * measuring against a different pool (a country-scoped list, say) can honestly
 * get a different receipt for the same pair. That is the rule working, not
 * drifting — but it does mean two surfaces that must agree have to measure
 * against the same pool, not merely call the same function.
 *
 * WHY THIS IS A MODULE AND NOT A FEW LINES IN A COMPONENT. It has two callers
 * — the console's thread list and the phone's Lens — and this repo's
 * most-repeated defect is the same rule hand-transcribed per call site until
 * the copies disagree. One function, one set of tests.
 *
 * WHY IT IS THE RELATION THE LENS SURFACES. The other candidate, the story
 * lens's `GET /api/v2/story/{id}/siblings` walk, ships DARK: hand-judged at
 * 30 of 50 top-5 rows being an unrelated story presented as kin, on a field
 * that is 61.25% blob. This relation is weaker but CHECKABLE — every row's
 * basis is a country or an actor the reader can see on both rows.
 */

/** The fields the relation reads. Both arrays may be absent on a partial row. */
export interface RelatableThread {
  thread_id: string
  top_countries?: string[]
  top_entities?: string[]
}

/** A related thread with the basis that made it one. Never one without the other. */
export interface RelatedThread<T> {
  thread: T
  receipt: string
}

export interface ThreadRelation<T> {
  /** The anchor row, or `null` when no id was given or the pool has no such row. */
  anchor: T | null
  /** The anchor's primary countries — the codes a sibling may match on. */
  countries: Set<string>
  /** The anchor's distinctive entities, normalized. */
  entities: Set<string>
  /**
   * The relation has an anchor, at least one basis, and at least one OTHER row
   * that shares it. Callers gate re-sorting and dimming on this: a relation
   * that surfaces nobody must leave the list exactly as it was.
   */
  active: boolean
  isRelated(thread: T): boolean
  /** The basis, or `null` for the anchor itself and for an unrelated row. */
  reason(thread: T): string | null
  /** Every related row except the anchor, in pool order, each with its receipt. */
  related: RelatedThread<T>[]
}

/** How many of the anchor's countries count as its primary geography. */
export const PRIMARY_COUNTRIES = 2

/**
 * How many threads may carry an entity before it stops being distinctive.
 *
 * Floor of 2 rather than 1: at a cap of 1 no entity could ever be SHARED (an
 * entity on both the anchor and a sibling already has a document frequency of
 * 2), which would silently reduce a small pool to geography alone.
 */
export function distinctiveCap(poolSize: number): number {
  return Math.max(2, Math.min(3, Math.floor(poolSize * 0.25)))
}

const norm = (e: string) => e.toLowerCase().trim()

/**
 * Document frequency per entity over the pool: how many THREADS carry it, not
 * how many times it appears. A thread that lists an actor twice must not make
 * that actor look rarer than one that lists it once.
 */
export function entityDocumentFrequency(pool: readonly RelatableThread[]): Map<string, number> {
  const df = new Map<string, number>()
  for (const n of pool) {
    for (const e of new Set((n.top_entities || []).map(norm).filter(Boolean))) {
      df.set(e, (df.get(e) || 0) + 1)
    }
  }
  return df
}

export function buildThreadRelation<T extends RelatableThread>(
  pool: readonly T[],
  anchorId: string | null | undefined,
  opts: { resolveCountryName?: (code: string) => string } = {},
): ThreadRelation<T> {
  // Identity, not a display name, is the honest default: a receipt reading `ZZ`
  // is a code the reader can still check against the row. Inventing a name here
  // would be a second source for one the app already owns.
  const resolveCountryName = opts.resolveCountryName ?? ((code: string) => code)

  const anchor = anchorId ? pool.find(n => n.thread_id === anchorId) ?? null : null
  const countries = new Set((anchor?.top_countries || []).slice(0, PRIMARY_COUNTRIES))

  const df = entityDocumentFrequency(pool)
  const cap = distinctiveCap(pool.length)
  const entities = new Set(
    (anchor?.top_entities || []).map(norm).filter(e => e && (df.get(e) || 0) <= cap),
  )

  const isRelated = (thread: T): boolean =>
    !!anchor && (
      thread.thread_id === anchorId ||
      (thread.top_countries || []).some(c => countries.has(c)) ||
      (thread.top_entities || []).some(e => entities.has(norm(e)))
    )

  const reason = (thread: T): string | null => {
    if (!anchor || thread.thread_id === anchorId) return null
    // The entity first: it is the more specific of the two bases, and it is
    // reported in the SIBLING's own spelling — that is the string the reader
    // sees on that row, so it is the one they can check.
    const sharedEntity = (thread.top_entities || []).find(e => entities.has(norm(e)))
    if (sharedEntity) return sharedEntity
    const sharedCountry = (thread.top_countries || []).find(c => countries.has(c))
    return sharedCountry ? resolveCountryName(sharedCountry) : null
  }

  const related = pool
    .filter(n => n.thread_id !== anchorId && isRelated(n))
    // A receipt is never fabricated here: `reason` returns a basis for every
    // row `isRelated` accepted, and a caller that receives an empty one must
    // withhold the row rather than show a neighbour with no evidence.
    .map(n => ({ thread: n, receipt: reason(n) ?? '' }))

  const active = !!anchor && (countries.size > 0 || entities.size > 0) && related.length > 0

  return { anchor, countries, entities, active, isRelated, reason, related }
}
