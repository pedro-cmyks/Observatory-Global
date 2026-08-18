/**
 * cardWarnings — the pure join between the L1 story cards and the measured
 * marks the payload ALREADY serves about them.
 *
 * Panel ciego 2026-08-18: the defect all three reviewers named was the front
 * page printing a story the backend had already flagged — "Wildfires in France
 * and Spain" rode `subject_geography_grab_bag` in the daily-publication payload
 * and the card printed no mark. This module carries the mark to the card. It
 * MEASURES NOTHING and invents nothing: every warning here is a backend
 * measurement that was already traveling in the served payload; this is only
 * the join (by thread_id and/or exact normalized label) that was missing.
 *
 * What actually travels (verified against the backend, 2026-08-18):
 *
 *   SEALED edition (/api/v2/investigation/daily-publication)
 *   - `package.gaps: string[]` carries one
 *     `subject_geography_grab_bag:<label>` entry per story whose receipts'
 *     significant countries do NOT co-occur (investigation_graph.py:875,
 *     measured by measure_subject_geography_coherence — coherence contract
 *     atlas-subject-coherence-v1). The label is the node label verbatim —
 *     the same string the front page renders.
 *   - each story node's `snapshot.spine_layout_reason` is
 *     'spine_demoted_grab_bag_umbrella' for the same measurement
 *     (daily_edition.order_spine_by_publishability), keyed by node, so it
 *     joins by thread_id.
 *   - sealed story nodes carry NO label-court fields (daily_publication.py
 *     freezes label/signal_count/sources/receipts/movement only) — which is
 *     why a sealed card never showed a court chip. sealedCourtTrust below
 *     recovers the chip ONLY where a pure identity join permits it.
 *
 *   LIVE briefing (/api/v2/briefing top_threads)
 *   - rows carry the court fields (label_status/label_proposed/
 *     court_withheld/avg_confidence) and `subject_geography_status`
 *     ('verified'|'partial'|'unavailable'|'missing' — the subject-country
 *     VERIFICATION contract), but the grab-bag COHERENCE measurement is not
 *     served on live rows. That is a payload hole, reported upstream — this
 *     module must not paper over it with a client-side guess.
 */

/** The gap-string prefix the publication package uses for grab-bag stories. */
export const GRAB_BAG_GAP_PREFIX = 'subject_geography_grab_bag:'

/** The spine layout reason the daily edition stamps on a grab-bag story node. */
export const SPINE_GRAB_BAG_REASON = 'spine_demoted_grab_bag_umbrella'

/**
 * Join key for a label. NOT a similarity heuristic — both sides of the join
 * hold the SAME backend string (the node label), so this only neutralizes
 * incidental whitespace/case differences introduced by transport or rendering.
 */
export function normalizeWarningLabel(label: string | null | undefined): string {
  return (label ?? '').replace(/\s+/g, ' ').trim().toLowerCase()
}

/** The minimal shape of a sealed story node this join needs. */
export interface StoryNodeMark {
  threadId?: string | null
  label?: string | null
  spineLayoutReason?: string | null
}

/** Index of served grab-bag marks, queryable by thread id or label. */
export interface CardWarningIndex {
  grabBagThreadIds: Set<string>
  grabBagLabels: Set<string>
}

export function buildCardWarningIndex(input: {
  /** `package.gaps` of the served sealed edition (string reason codes). */
  packageGaps?: readonly string[] | null
  /** The sealed graph's story nodes (thread id + label + spine reason). */
  storyNodes?: readonly StoryNodeMark[] | null
}): CardWarningIndex {
  const grabBagThreadIds = new Set<string>()
  const grabBagLabels = new Set<string>()
  for (const gap of input.packageGaps ?? []) {
    if (typeof gap !== 'string' || !gap.startsWith(GRAB_BAG_GAP_PREFIX)) continue
    const label = normalizeWarningLabel(gap.slice(GRAB_BAG_GAP_PREFIX.length))
    if (label) grabBagLabels.add(label)
  }
  for (const node of input.storyNodes ?? []) {
    if (node.spineLayoutReason !== SPINE_GRAB_BAG_REASON) continue
    if (node.threadId) grabBagThreadIds.add(node.threadId)
    const label = normalizeWarningLabel(node.label)
    if (label) grabBagLabels.add(label)
  }
  return { grabBagThreadIds, grabBagLabels }
}

/**
 * Does the served payload mark this rendered row as a subject-geography
 * grab-bag? Pure lookup: thread id first (the precise key), exact normalized
 * label second (the key `package.gaps` carries).
 */
export function isMixedGeography(
  row: { thread_id?: string | null; label?: string | null },
  index: CardWarningIndex,
): boolean {
  if (row.thread_id && index.grabBagThreadIds.has(row.thread_id)) return true
  const label = normalizeWarningLabel(row.label)
  return label.length > 0 && index.grabBagLabels.has(label)
}

/** The label-trust fields the shared LabelReviewChip consumes. */
export interface CourtTrustFields {
  label_status?: string | null
  label_proposed?: string | null
  avg_confidence?: number | null
  confidence_measured?: boolean
  court_withheld?: boolean
}

/**
 * Recover the Label Court verdict for a SEALED card from the live briefing
 * payload — the sealed graph freezes no court fields, so a sealed card was
 * structurally chip-blind even when the court had vetoed the very same label
 * (the "Ceuta Migrant Crisis" finding).
 *
 * STRICT identity join, never a transfer between different claims: the court's
 * verdict is about one label text on one thread, so it is carried over ONLY
 * when the live row has the SAME thread_id AND the SAME normalized label. A
 * sealed row the edition relabeled gets nothing — the live verdict would be
 * about a different sentence.
 */
export function sealedCourtTrust(
  sealedRow: { thread_id?: string | null; label?: string | null },
  liveThreads: readonly ({ thread_id?: string | null; label?: string | null } & CourtTrustFields)[],
): CourtTrustFields | null {
  if (!sealedRow.thread_id) return null
  const sealedLabel = normalizeWarningLabel(sealedRow.label)
  if (!sealedLabel) return null
  for (const live of liveThreads) {
    if (live.thread_id !== sealedRow.thread_id) continue
    if (normalizeWarningLabel(live.label) !== sealedLabel) return null
    return {
      label_status: live.label_status ?? null,
      label_proposed: live.label_proposed ?? null,
      avg_confidence: typeof live.avg_confidence === 'number' ? live.avg_confidence : null,
      confidence_measured: live.confidence_measured === true,
      court_withheld: live.court_withheld === true,
    }
  }
  return null
}
