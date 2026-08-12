/**
 * The containment path — `World ▸ Country ▸ Person ▸ Story ▸ signal`.
 *
 * THIS MODULE HOLDS NO STATE AND INVENTS NONE. Every crumb is a projection of
 * scope state that already exists (FocusContext's `filter`, the open thread,
 * the open signal). The folder model Pedro described — "me voy metiendo como a
 * subcarpetas" — was already true of the console's behaviour (#234 propagates
 * every focus to every surface); what was missing was a way to READ it. So this
 * is representation, not a second notion of "what am I looking at". If a crumb
 * and a panel ever disagree, the bug is upstream in the state, never here.
 *
 * WHY A PATH AND NOT A CHIP ROW. The chips that came before (FocusIndicator)
 * printed the same dimensions as a flat, unordered set with a hidden 18px ✕ per
 * chip and one more for "all" — R4's cold reader never found the way out. A
 * path says two things a set cannot: WHERE the current scope sits, and that
 * every ancestor is one click away. The exit stops being a glyph you have to
 * discover and becomes the first crumb, which is also the only word on the
 * surface that never changes.
 *
 * ORDER IS CONTAINMENT, NOT VISIT HISTORY. `World ▸ Colombia ▸ Petro ▸ Story`
 * reads as narrowing: each crumb is the scope you get by dropping everything to
 * its right. That is why compound focus (country ∧ person ∧ theme can all be
 * active at once — see nextFocusDims in lib/focusReducer.ts) renders as a path
 * rather than as three peers: the reader does not need to know the console
 * keeps three independent dimensions, only that stepping left widens the view.
 * The trade is deliberate and named: you can no longer drop the MIDDLE
 * dimension alone (peel the country while keeping the person). That gesture
 * existed, was 14px wide, and was not found; going up a folder is.
 *
 * A NOTE ON `person`. A person is not geographically inside a country, and
 * this file does not claim it is. Its slot in the order is about NARROWING:
 * with both set, the console shows that person's signal WITHIN that country, so
 * the person is the finer scope and belongs to the right of it.
 */

/** The levels the console can actually be in, widest first. */
export type ScopeLevel = 'world' | 'country' | 'person' | 'story' | 'signal'

/** Widest → narrowest. The order the path is built in, and the only place it is written down. */
export const SCOPE_ORDER: ScopeLevel[] = ['world', 'country', 'person', 'story', 'signal']

export interface ScopeCrumb {
  level: ScopeLevel
  /**
   * Stable identity for React keys AND for the navigation handler, which needs
   * to know WHICH country/person/story to re-open. `'*'` at the world level.
   */
  id: string
  /**
   * The type word — `Country`, `Person`, `Story`, `Theme`, `Signal`. `null` at
   * the world level, where the label already is the type.
   *
   * Inherited verbatim from FocusIndicator, including the one distinction that
   * cost R4 a round: a `dynamic-topic-*` id is a STORY, and `Theme` survives
   * only for atlas category ids. Two words for one object read as a nesting
   * that does not exist, so the rule lives in exactly one function.
   */
  typeLabel: string | null
  /** What the crumb prints. Never a raw id — see `pending`. */
  label: string
  /**
   * True when the scope is known but its NAME is not yet.
   *
   * A cold-loaded story is the case: the id is `dynamic-topic-8057`, the label
   * arrives with the detail fetch, and the resolver's fallback for an opaque id
   * is the generic word `Story`. Printed next to the type word that is also
   * `Story`, that renders "STORY Story" — a stutter that says nothing and looks
   * like a bug (found in the P1 pass). A pending crumb prints an ellipsis
   * instead: the type word already carries what kind of thing it is, and the
   * ellipsis is honest about the only thing missing, which is its name.
   */
  pending: boolean
}

export interface ScopeInput {
  /** `filter.country` — an ISO code. */
  country?: string | null
  /** Display name for the country; the code is the fallback, never the printed truth. */
  countryName?: string | null
  /** `filter.person` — already a human name. */
  person?: string | null
  /**
   * `filter.thread` and `filter.theme`. They are EXCLUSIVE by construction
   * (opening a full thread resets the others; setting any of the three clears
   * `thread` — focusReducer.ts), and this module relies on that: one story
   * crumb, never two. Both are accepted because both doors exist.
   */
  thread?: string | null
  theme?: string | null
  /**
   * The story's KNOWN label, if any door supplied one — `thread.label`, an
   * opener's `labelHint`, or `filter.themeLabel`. Deliberately the raw known
   * label rather than an already-resolved display string: a resolver that has
   * fallen back to the generic word is indistinguishable from a real answer
   * once it has been applied, and telling those apart is exactly what `pending`
   * is for.
   */
  storyLabel?: string | null
  /** The open signal, if the reader has one on screen. */
  signal?: { id: string; label?: string | null } | null
}

export interface ScopePathOptions {
  /**
   * How to name a story id that carries no known label. Injected rather than
   * imported so this module stays free of the label table (and of React), and
   * so the app keeps ONE resolver — `resolveThreadLabel` — instead of growing a
   * second copy of slug-prettifying here.
   */
  resolveStoryLabel?: (id: string, known?: string | null) => string
  /** The world crumb's word. Injected for the bilingual surfaces. */
  worldLabel?: string
}

/**
 * Labels a resolver returns when it has NOTHING but the id — the generic
 * fallbacks, not names. A crumb wearing one of these is `pending`.
 *
 * Compared case-insensitively against the resolved label. The risk of a real
 * story genuinely being called "Story" is accepted: it would print `STORY …`
 * for as long as it took the detail to land, which is the same thing the
 * unresolved case prints, and strictly better than the stutter.
 */
const GENERIC_STORY_LABELS = new Set(['story', 'stories', 'unknown', 'narrative thread', 'narrative threads'])

/** An id that carries no name of its own — `dynamic-topic-8057`, `cluster-12`. */
export function isOpaqueStoryId(id: string): boolean {
  return /^(dynamic-topic|emergent-cluster|cluster)-\d+/.test(id.split('--')[0])
}

/**
 * `Story` for a dynamic topic, `Theme` for an atlas category id.
 *
 * The R4 vocabulary fix, moved here from FocusIndicator when the chips were
 * retired: a dynamic topic IS a story, and "Theme" stays only for the R3
 * category lens.
 */
export function storyTypeLabel(id: string): string {
  return isOpaqueStoryId(id) || id.startsWith('dynamic-topic-') ? 'Story' : 'Theme'
}

const DEFAULT_RESOLVE = (id: string, known?: string | null): string => (known?.trim() ? known.trim() : id)

/**
 * Build the containment path. Always at least one crumb: the world is a scope,
 * not the absence of one, and printing it is how the reader learns that
 * stepping left is possible before they have anything to step back from.
 */
export function buildScopePath(input: ScopeInput, opts: ScopePathOptions = {}): ScopeCrumb[] {
  const resolve = opts.resolveStoryLabel ?? DEFAULT_RESOLVE
  const path: ScopeCrumb[] = [
    { level: 'world', id: '*', typeLabel: null, label: opts.worldLabel ?? 'World', pending: false },
  ]

  const country = input.country?.trim()
  if (country) {
    path.push({
      level: 'country',
      id: country,
      typeLabel: 'Country',
      // A resolved name or nothing — the raw code is a last resort, never a lie.
      label: input.countryName?.trim() || country,
      pending: false,
    })
  }

  const person = input.person?.trim()
  if (person) {
    path.push({ level: 'person', id: person, typeLabel: 'Person', label: person, pending: false })
  }

  // Exclusive by construction; `thread` wins if the invariant ever slips, since
  // it is the door that resets the others.
  const storyId = input.thread?.trim() || input.theme?.trim()
  if (storyId) {
    const known = input.storyLabel?.trim() || null
    const resolved = (known || resolve(storyId, known) || '').trim()
    const pending = !resolved || resolved === storyId || GENERIC_STORY_LABELS.has(resolved.toLowerCase())
    path.push({
      level: 'story',
      id: storyId,
      typeLabel: storyTypeLabel(storyId),
      label: pending ? '…' : resolved,
      pending,
    })
  }

  if (input.signal) {
    const label = input.signal.label?.trim()
    path.push({
      level: 'signal',
      id: input.signal.id,
      typeLabel: 'Signal',
      label: label || '…',
      pending: !label,
    })
  }

  return path
}

/** True when nothing is focused — the console is showing the whole field. */
export function isWorldScope(path: ScopeCrumb[]): boolean {
  return path.length === 1
}

/** The crumb the reader is standing in. */
export function currentScope(path: ScopeCrumb[]): ScopeCrumb {
  return path[path.length - 1]
}

/**
 * The levels that must be dropped to navigate to `index` — everything to its
 * right, widest-first.
 *
 * Exported and tested because the handler that does the dropping lives in a
 * component (it has to: it calls the console's own openers), and the RULE for
 * what a crumb click means should not only exist there. A click never drops
 * anything to the LEFT of the crumb: going up a folder keeps the folders above.
 */
export function levelsDroppedBy(path: ScopeCrumb[], index: number): ScopeLevel[] {
  if (index < 0 || index >= path.length) return []
  return path.slice(index + 1).map((c) => c.level)
}

/** A click on the current (last) crumb changes nothing — the caller should no-op. */
export function isCurrentScope(path: ScopeCrumb[], index: number): boolean {
  return index === path.length - 1
}
