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

export interface StoryLensState {
  active: boolean
  anchorId: string | null
  // T11 gate fix (L4): the opener's already-known label — a fallback title
  // used only until the fetch resolves its own `anchor.label`, and the only
  // title left when a degraded fetch never resolves one at all.
  labelHint?: string | null
}

// One-line kill switch for the auto-enter behavior (Task 10): flip to false
// to make opening a thread stop entering the lens, with zero other changes.
// K1 (finder-v2 pre-registration, 2026-07-29): the field's blob density makes
// auto-entered lens neighborhoods dishonest on the anchors /threads serves most
// (dt-466 class). The lens ships DARK until identity heals — deep link
// ?lens=story&theme= stays live for dogfooding (explicit request, ungated).
export const STORY_LENS_AUTO = false

// Story Lens (Task 10): v1 lens anchors are DYNAMIC topics only — the
// siblings endpoint returns unsupported_anchor_type for atlas 'slug--cc' and
// emergent-cluster ids (no dynamic_topics centroid; T2 quality-review issue
// 3, recorded decision — backend contract at story.py:221). Shared by every
// thread-open door syncLensToThreadOpen wires (App.tsx) plus the `?lens=
// story` deep-link entry point, so none of them can drift from the other's
// definition of "lens-eligible".
export function isLensAnchor(id: string): boolean {
  return id.startsWith('dynamic-topic-')
}

// Mirrors TOPIC_PARAM_MAX in lib/streamTabs.ts (backend _TOPIC_FILTER_MAX = 12).
// The backend sibling cap (story_siblings.DEFAULT_CAP) is 11, so anchor +
// siblings is exactly 12 ids — this cap is a ceiling, never a truncation.
export const LENS_TOPIC_CAP = 12

export interface LensSets {
  anchor: Set<string>
  siblings: Set<string>
}

// True only when the payload carries something the lens can honestly scope to.
// Honest empties (anchor null, or zero siblings) must NOT activate lens ordering —
// downstream consumers gate on this, never on lensSets != null.
export function hasLensContent(d: StoryLensData | null | undefined): boolean {
  return Boolean(d?.anchor && d.siblings.length > 0)
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

export interface SiblingChipText { text: string; isBlob: boolean }

// Chip text + structured blob flag — consumers branch tooltips on isBlob,
// never by re-parsing the rendered string.
export function siblingChipText(s: StoryLensSibling): SiblingChipText {
  const base = siblingReasonText(s)
  return { text: s.is_blob ? `${base} · ⚠ grab-bag` : base, isBlob: s.is_blob }
}

// T11 gate fix (L2): the banner used to report EVERY sibling as a "hermano"
// (direct measured edge) regardless of `kinship` — erasing the hermano/primo
// distinction that is the design's honesty core (a primo is an INDIRECT
// walk, not a direct edge) and overstating measured directness. Zero-count
// parts are omitted rather than printed as "0 hermanos · 3 primos", except
// when BOTH are zero (an anchor with no kin at all still needs a count).
export function siblingKinshipSummary(siblings: StoryLensSibling[]): string {
  const hermanos = siblings.filter((s) => s.kinship === 'hermano').length
  const primos = siblings.filter((s) => s.kinship === 'primo').length
  const parts: string[] = []
  if (hermanos > 0) parts.push(`${hermanos} hermano${hermanos === 1 ? '' : 's'}`)
  if (primos > 0) parts.push(`${primos} primo${primos === 1 ? '' : 's'}`)
  if (!parts.length) parts.push('0 hermanos')
  return parts.join(' · ')
}

// User-facing copy for the siblings endpoint's closed reason-code set.
// A failed lookup must never read as a measured absence, and internal
// codes must never reach the screen verbatim.
export function lensErrorCopy(code: string | null | undefined): string {
  switch (code) {
    case 'unsupported_anchor_type':
      return 'No measured neighborhood for this thread type yet'
    case 'seed_not_found_or_no_centroid':
      return 'Story not in the active measured field'
    case 'invalid_thread_id':
      return 'Invalid story reference'
    case 'db_unavailable':
    case 'db_error':
      return 'Neighborhood lookup failed — not a measured absence'
    case 'whitening_unavailable':
    case 'internal_error':
      return 'Measurement space unavailable'
    default:
      return 'Neighborhood unavailable'
  }
}
