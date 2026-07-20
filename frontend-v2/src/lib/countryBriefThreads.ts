export interface CountryBriefThemeRow {
  name: string
  count: number
}

export interface CountryBriefThreadInput {
  thread_id?: string
  label?: string
  signal_count?: number
  /** #214: signals that cleared the relevance gate (what the detail panel shows). */
  gated_signal_count?: number
  /** #214: signals the gate has scored. 0 = gate hasn't run on this topic yet. */
  gate_scored_count?: number
  /** Label Court verdict (N15): 'entailed' | 'partial' | 'failed' | null. */
  label_status?: string | null
  anchor_topics?: string[]
}

export interface CountryBriefThreadRow {
  name: string
  label: string
  /** Display count: the gated number once scored, the raw count while pending. */
  count: number
  /** Raw assigned count (shown on hover) — may exceed `count`. */
  rawCount: number
  /** Gate scored this topic but kept ZERO — raw headlines exist but none cleared
   *  the relevance gate. These belong in the UNVERIFIED tray, not the lead list. */
  belowGate: boolean
  /** Label Court verdict carried through so the row can mark a failed/partial
   *  label under review (N15 — every label surface, one chip). */
  labelStatus: string | null
}

interface CountryBriefThreadSummaryInput {
  threads: CountryBriefThreadInput[]
  fallbackThemes: CountryBriefThemeRow[]
}

export function buildCountryBriefThreadSummary({
  threads,
  fallbackThemes: _fallbackThemes,
}: CountryBriefThreadSummaryInput): {
  count: number
  label: 'threads'
  rows: CountryBriefThreadRow[]
} {
  const threadRows: CountryBriefThreadRow[] = threads
    .filter(thread => thread.thread_id)
    .map(thread => {
      const raw = thread.signal_count || 0
      // Default gated to raw when the field is absent (older atlas-fill rows that
      // don't carry the gate count) so they don't all collapse into the tray.
      const gated = thread.gated_signal_count ?? raw
      const scored = thread.gate_scored_count ?? 0
      const belowGate = scored > 0 && gated === 0 && raw > 0
      return {
        name: thread.thread_id!,
        label: thread.label || thread.thread_id!,
        count: scored > 0 ? gated : raw,
        rawCount: raw,
        belowGate,
        labelStatus: thread.label_status ?? null,
      }
    })

  // The headline "N threads" metric counts only threads we stand behind —
  // below-gate ones are surfaced separately, never as confident threads.
  return {
    count: threadRows.filter(r => !r.belowGate).length,
    label: 'threads',
    rows: threadRows,
  }
}
