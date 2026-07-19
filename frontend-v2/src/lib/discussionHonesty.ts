// #248 discussion-attach relevance honesty — pure display helpers for the
// community-discussion lane (#237). The backend serves each attached post's
// MEASURED attach similarity (topic_members.confidence) and a noise `lane`
// tag (hobby/sports/entertainment/lifestyle — damped, never dropped). These
// helpers render those honestly: no similarity → no chip (never fake one).

/** "93% match" from a measured 0..1 similarity; null when absent/invalid. */
export function formatAttachSimilarity(sim: number | null | undefined): string | null {
    if (sim == null || Number.isNaN(sim) || sim < 0 || sim > 1) return null
    return `${Math.round(sim * 100)}% match`
}

/** Uppercase chip text for a backend noise lane; null for news-y items. */
export function laneTag(lane: string | null | undefined): string | null {
    if (!lane) return null
    return lane.toUpperCase()
}

/** "showing X of N" when the list is truncated; null when all are visible. */
export function truncationNote(shown: number, total: number): string | null {
    if (total <= shown) return null
    return `showing ${shown} of ${total}`
}
