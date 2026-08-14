// Count-measurement wording (fix round 2026-08-14, Pedro's dt-242 read).
//
// The count-qualifier contract says every printed number states its base. Two
// bases on the thread detail were stating the WRONG one, and a third number
// was not a measurement at all:
//
//   * `total` was labelled "lifetime". It is `dynamic_topics.agg_n_signals`,
//     which the projection ACCUMULATES per clustering pass, so a story seen in
//     17 passes has its members counted up to 17 times (dt-242's passes sum
//     43+34+34+34+... = exactly the 323 served). "Lifetime" makes a reader hear
//     "323 articles"; the honest word names the passes.
//   * `currentTotal` was labelled "last 7d". It is ONE pass — the latest
//     snapshot — whose clustering window ENDED at the snapshot timestamp.
//   * the "Sources" tile printed `topSources.length`, the length of a 20-item
//     display slice, while the same payload's 37 receipts carried 36 distinct
//     outlets. A capped preview is not a count.
//
// Wording lives here (pure, tested) so the header, the stat tiles and the tips
// cannot drift apart the way they did.

export interface CumulativeCountDescription {
  /** Short qualifier printed beside the number, e.g. "across 17 passes". */
  qualifier: string
  /** Plain-language explanation for the data-tip. */
  tip: string
}

/**
 * Describe the cumulative per-pass total. NEVER the word "lifetime": the
 * number double-counts by construction, and the true distinct figure is not
 * recoverable (7-day hot retention has deleted the member rows).
 */
export function describeCumulativeCount({
  total,
  snapshotCount,
}: {
  total: number | null | undefined
  snapshotCount: number | null | undefined
}): CumulativeCountDescription {
  const n = (total ?? 0).toLocaleString()
  if (snapshotCount == null || snapshotCount <= 0) {
    return {
      qualifier: 'cumulative',
      tip:
        `${n} is a running total the engine adds to every time it re-clusters ` +
        `this story, so a signal still present in a later pass is counted again. ` +
        `How many passes it spans is not reported here, so read it as a scale, ` +
        `not as a number of articles.`,
    }
  }
  const passWord = snapshotCount === 1 ? 'pass' : 'passes'
  return {
    qualifier: `across ${snapshotCount} ${passWord}`,
    tip:
      `${n} summed across ${snapshotCount} clustering ${passWord} — not ${n} ` +
      `distinct articles. Each pass re-counts the story's current members, so a ` +
      `signal that survives into later passes is counted once per pass.`,
  }
}

export interface SourceCountDescription {
  /** What the tile prints. '—' when the lane never answered. */
  value: string
  /** Sub-label naming the receipt basis, or null when there is none. */
  subnote: string | null
  /** Plain-language explanation for the data-tip. */
  tip: string
}

/**
 * Describe the outlet count. The served `sourceCount` is counted over the
 * receipts actually resolved — uncapped, so it can never saturate at the
 * preview slice — and the subnote names that basis so it is never read as the
 * story's full outlet total.
 */
export function describeSourceCount({
  sourceCount,
  sourceSampleSize,
  previewLength,
}: {
  sourceCount: number | null | undefined
  sourceSampleSize: number | null | undefined
  previewLength: number
}): SourceCountDescription {
  const receipts = sourceSampleSize ?? 0

  // No counted value: fall back to the preview length rather than printing
  // nothing, but never invent a 0 — an unanswered lane is degraded, not empty.
  if (sourceCount == null) {
    return {
      value: previewLength > 0 ? String(previewLength) : '—',
      subnote: null,
      tip:
        previewLength > 0
          ? `${previewLength} outlets listed below. This payload did not report a ` +
            `counted total, so this is the length of the shown list — more ` +
            `outlets may carry the story.`
          : 'Not measured — no receipts were resolved for this story.',
    }
  }

  const receiptWord = receipts === 1 ? 'receipt' : 'receipts'
  return {
    value: String(sourceCount),
    subnote: receipts > 0 ? `in ${receipts} ${receiptWord}` : null,
    tip:
      `${sourceCount} distinct outlets among the ${receipts} ${receiptWord} shown ` +
      `for this story. That is a count over the receipts we could resolve, not the ` +
      `full set of outlets covering it — more outlets may carry it than appear here.`,
  }
}
