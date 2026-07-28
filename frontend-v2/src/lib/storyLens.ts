// Story Lens pure model — mirrors lib/attentionEclipse.ts + lib/eclipseSets.ts.
//
// Consumes GET /api/v2/story/{thread_id}/siblings (contract "story-siblings-v1"):
// anchor + siblings walked via kinship (hermano = direct edge, primo = indirect
// walk) from the substrate already built for the walked-constellation / chains
// feature. This module has no fetch/state of its own — it only classifies ids
// and builds the topic-scope param, the same separation eclipseSets.ts and
// streamTabs.ts keep from attentionEclipse.ts.

export interface StoryLensReason { basis: string; value: string }

export interface StoryLensSibling {
  id: string
  label: string
  weight: number
  degree: number
  kinship: 'hermano' | 'primo'
  through_blob: boolean
  is_blob: boolean
  via_parent: string | null
  folded: string[]
  label_status?: string | null
  countries: string[]
  reasons: StoryLensReason[]
}

export interface StoryLensData {
  contract: string
  generated_at: string
  anchor: { id: string; label: string; label_status?: string | null; countries: string[] } | null
  siblings: StoryLensSibling[]
  notes: string[]
}

// One-line kill switch for the auto-enter behavior (Task 10): flip to false
// to make opening a thread stop entering the lens, with zero other changes.
export const STORY_LENS_AUTO = true

// Mirrors TOPIC_PARAM_MAX in lib/streamTabs.ts (backend _TOPIC_FILTER_MAX = 12).
export const LENS_TOPIC_CAP = 12

export interface LensSets {
  anchor: Set<string>
  siblings: Set<string>
}

/** `folded` ids (near-duplicate blobs absorbed into a sibling) count as that
 *  sibling for role purposes — a thread row for a folded id should still read
 *  as part of the lens, not as an unrelated outsider. */
export function buildLensSets(d: StoryLensData | null | undefined): LensSets {
  const anchor = new Set<string>()
  const siblings = new Set<string>()
  if (d?.anchor) anchor.add(d.anchor.id)
  for (const s of d?.siblings ?? []) {
    siblings.add(s.id)
    for (const f of s.folded ?? []) siblings.add(f)
  }
  return { anchor, siblings }
}

export type LensRole = 'anchor' | 'sibling' | null

/** Union match [threadId, ...anchorTopics] — same shape as
 *  eclipseSets.threadEclipseRole, so a row's own id and any topic ids it
 *  carries (e.g. an atlas thread's member topics) are both checked. */
export function threadLensRole(
  anchorTopics: string[] | undefined,
  threadId: string,
  sets: LensSets,
): LensRole {
  const ids = [threadId, ...(anchorTopics ?? [])]
  if (ids.some((id) => sets.anchor.has(id))) return 'anchor'
  if (ids.some((id) => sets.siblings.has(id))) return 'sibling'
  return null
}

/** Comma-joined topic ids for `/api/v2/signals?topic=` — anchor first, then
 *  siblings in served order, capped. Returns null (never '') when there is no
 *  anchor or no ids survive: an empty `topic=` reads server-side as "asked for
 *  a scope, nothing valid" and would answer with zero signals, which is wrong
 *  when there is simply no lens data yet. */
export function lensTopicParam(
  d: StoryLensData | null | undefined,
  cap: number = LENS_TOPIC_CAP,
): string | null {
  if (!d?.anchor) return null
  const ids = [d.anchor.id, ...d.siblings.map((s) => s.id)].slice(0, Math.max(0, cap))
  return ids.length ? ids.join(',') : null
}

/** Short human-readable reason for a sibling chip — first measured basis, or
 *  the kinship word when no reasons were returned. */
export function siblingReasonText(s: StoryLensSibling): string {
  const first = s.reasons[0]
  return first ? `${first.basis} ${first.value}` : s.kinship
}
