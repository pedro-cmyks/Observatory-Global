// Council N5 (survived R2 + R3): thread rows re-sort under the cursor — the
// relation sort (person focus / open-thread siblings) and the 5-min poll both
// reorder the list, so a row moves out from under the pointer between hover and
// click and the WRONG thread opens (3/6 personas mis-opened, twice).
//
// Fix: while the pointer is over the list, FREEZE the visual row order. Content
// (counts, chips, dimming) still updates live — only the order is pinned. New
// threads arriving mid-hover append at the end rather than shuffling the rows
// under the cursor. On pointer-leave the order re-settles to the live sort.

export interface Orderable {
    thread_id: string
}

/**
 * Given the current items in their LIVE (relation-sorted) order and an optional
 * frozen id order, return the items to render:
 *  - frozenIds === null → the live order unchanged (not hovering).
 *  - frozenIds set → items whose id is in frozenIds first, in the frozen order;
 *    then any items not in frozenIds (threads that arrived while frozen), in
 *    their live order. Frozen ids that no longer exist are dropped. Pure.
 */
export function freezeThreadOrder<T extends Orderable>(
    live: T[],
    frozenIds: string[] | null,
): T[] {
    if (!frozenIds || frozenIds.length === 0) return live
    const rank = new Map<string, number>()
    frozenIds.forEach((id, i) => rank.set(id, i))
    const known = live
        .filter(n => rank.has(n.thread_id))
        .sort((a, b) => (rank.get(a.thread_id)! - rank.get(b.thread_id)!))
    const fresh = live.filter(n => !rank.has(n.thread_id)) // preserves live order
    return [...known, ...fresh]
}
