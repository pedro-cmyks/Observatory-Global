// Lead-story selection for the L1 Intelligence Brief.
//
// The lead is the TOP-RANKED thread in the window — nothing more. Threads
// arrive pre-ranked from the backend (`rank_threads`: movement + volume +
// coherence, no source bias). The brief must surface that #1 mover.
//
// History (the regression this guards against): the brief used to pick the
// first thread that *happened* to carry `evidence_samples`, on the assumption
// that dynamic threads ranked first and always carried evidence while
// atlas-fill threads did not. Unified ranking (2026-06-24) broke that
// invariant — atlas-fill threads can now legitimately rank #1 but arrive with
// empty `evidence_samples` at the list level, so `.find(evidence>0)` skipped
// the real top mover and led the global front page with a low-ranked
// micro-thread. The lead is now always the first thread; it renders evidence
// headlines when present and degrades gracefully when absent.

export interface LeadCandidate {
    thread_id: string
    evidence_samples?: unknown[] | null
}

/**
 * Select the lead story for the global front page.
 *
 * @param threads  pre-ranked threads (index 0 = highest rank)
 * @param countryFilter  active country filter; when set, the brief renders the
 *                       country view and has no global lead (returns null).
 * @returns the top-ranked thread, or null when filtered/empty.
 */
export function selectLeadThread<T extends LeadCandidate>(
    threads: readonly T[] | null | undefined,
    countryFilter: string | null | undefined,
): T | null {
    if (countryFilter) return null
    if (!threads || threads.length === 0) return null
    return threads[0] ?? null
}
