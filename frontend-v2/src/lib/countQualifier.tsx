// Count-qualifier contract (council wish 5 / P1-5, the "42/347/3,762 killer"):
// every printed number states its base — "N · <window> · <base>" — with a
// data-tip explaining what the base means. The helper never changes a number;
// it explains it, so the same object showing different counts on different
// surfaces stops reading as a contradiction.
import React from 'react'
import './countQualifier.css'

export type CountBase = 'raw' | 'verified' | 'sourced' | 'lifetime' | 'frozen' | 'gated' | 'rollup'

export interface CountQualifierResult {
  /** Full "N · <window> · <base>" line. */
  label: string
  /** Just the qualifier segment ("<window> · <base>") for rendering next to an
   * existing number without re-printing it. */
  suffix: string
  /** Plain-language explanation of the base, for the data-tip. */
  tip: string
}

const BASE_TIPS: Record<CountBase, (n: string, w: string | null) => string> = {
  raw: (n, w) =>
    `${n} signals assigned to this object${w ? ` in the last ${w}` : ''} — matched before the relevance gate ran, so some may be off-topic. The verified count is smaller by design.`,
  verified: (n, w) =>
    `${n} signals kept by the relevance gate${w ? ` in the last ${w}` : ''} — the precise, verified set the detail view serves.`,
  sourced: (n, w) =>
    `${n} signals fetched as the readable sample${w ? ` for the last ${w}` : ''} — the subset retrieved with headline + outlet for this view, not the full assigned set.`,
  lifetime: n =>
    `${n} signals over this object's whole lifetime — an all-time total, not limited to the current window.`,
  frozen: (n, w) =>
    `${n} items captured at pin time${w ? ` (${w})` : ''} — frozen with the pin, these numbers do not update as live data drifts.`,
  // Fix round 2026-07-17 item 2: the threads-row number for dynamic threads is
  // the SERVED membership for the window — smaller than the detail's raw
  // assignment count BY DESIGN. Stating this base kills the "42 here, 347
  // there, identical tooltip" contradiction.
  gated: (n, w) =>
    `${n} signals in this story's curated serving membership${w ? ` for the last ${w}` : ''} — the set the engine serves after relevance gating. The detail view counts every raw assignment, which can be larger.`,
  // Fix round 2026-08-12 pair (a): Germany read 4,840 on the country card (a
  // live raw scan) and 3,836 in the density list (the hourly rollup). Same
  // quantity, two freshness levels — and the card called itself 'raw', which
  // this file defines as "before the relevance gate", implying a gating
  // difference that does not exist. Naming the rollup lane lets the reader
  // reconcile the two instead of reading a contradiction.
  rollup: (n, w) =>
    `${n} signals counted from the hourly aggregate${w ? ` over the last ${w}` : ''} — the same roll-up the map and the country density list read, so these numbers agree. It refreshes on a cycle, so it can trail the live count by up to an hour.`,
}

const BASE_LABEL: Record<CountBase, string> = {
  raw: 'raw',
  verified: 'verified',
  sourced: 'sourced',
  lifetime: 'lifetime',
  frozen: 'frozen',
  gated: 'gated',
  rollup: 'rollup',
}

/**
 * Turn a MEASURED window in hours into the printed word.
 *
 * Council R4 N19: both the thread row and the theme detail hardcoded '24h'.
 * Measured 2026-08-11, the dynamic engine clusters over `snapshot_window_h`
 * = 168h (3,080/3,080 clusters at the latest snapshot), so a dynamic row's
 * number was never a 24h count. The backend now serves the window it actually
 * counted over; this is the single place that renders it.
 *
 * Absence returns null rather than a default: silently printing '24h' over an
 * unknown window is precisely the bug being fixed. Callers pick their own
 * fallback explicitly (atlas rows genuinely are filtered to the request).
 */
export function formatCountWindow(hours: number | null | undefined): string | null {
  if (hours == null || !Number.isFinite(hours) || hours <= 0) return null
  // 24 stays '24h': it is the established wording for the day window and is
  // correct for the hours-filtered atlas path — churning it to '1d' would
  // rename a right label for nothing.
  if (hours < 48) return `${hours}h`
  return hours % 24 === 0 ? `${hours / 24}d` : `${hours}h`
}

export function countQualifier(
  count: number,
  windowLabel: string | null,
  base: CountBase,
): CountQualifierResult {
  const n = count.toLocaleString('en-US')
  // A lifetime total is not windowed — printing a window on it would be the
  // exact polysemy this helper exists to kill.
  const w = base === 'lifetime' ? null : windowLabel
  const suffix = [w, BASE_LABEL[base]].filter(Boolean).join(' · ')
  return {
    label: [n, suffix].filter(Boolean).join(' · '),
    suffix,
    tip: BASE_TIPS[base](n, w),
  }
}

/** Tiny chip rendered NEXT TO an existing number: "· 24h · raw" with the
 * explanatory data-tip. The number itself stays exactly as the surface
 * already prints it. */
export function CountQualifierChip({ count, windowLabel, base }: {
  count: number
  windowLabel: string | null
  base: CountBase
}): React.ReactElement {
  const q = countQualifier(count, windowLabel, base)
  return (
    <span className="count-qualifier" data-tip={q.tip}>
      {q.suffix}
    </span>
  )
}
