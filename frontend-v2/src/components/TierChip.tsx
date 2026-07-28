import { resolveTierChip } from '../lib/sourceProvenance'

// Shared L2 receipt-row tier chip (Story Lens Task 8 follow-up). The six
// call sites that render this (CountryBrief Top Publishers, SignalStream
// footer, ThemeDetail article meta + PA evidence rows, SignalDetailPanel
// header + semantic-neighbor meta) had each re-implemented the same
// three-line resolve-and-render inline — this is the one place that logic
// lives now.
//
// Absence over noise: with no origin data the classifier downgrades local→unknown,
// and an unknown tier renders NOTHING — the chip only speaks when it knows.
export function TierChip({ source }: { source: string | null | undefined }) {
  const tc = resolveTierChip(source, undefined)
  if (tc.tier === 'unknown') return null
  return (
    <span className={`l2-tier-chip l2-tier-chip--${tc.tier}`} data-tip={tc.tip}>
      {tc.label}
    </span>
  )
}
