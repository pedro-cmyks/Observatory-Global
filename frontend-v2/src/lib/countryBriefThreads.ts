export interface CountryBriefThemeRow {
  name: string
  count: number
}

export interface CountryBriefThreadInput {
  thread_id?: string
  label?: string
  signal_count?: number
  anchor_topics?: string[]
}

export interface CountryBriefThreadRow {
  name: string
  label: string
  count: number
}

interface CountryBriefThreadSummaryInput {
  threads: CountryBriefThreadInput[]
  fallbackThemes: CountryBriefThemeRow[]
}

export function buildCountryBriefThreadSummary({
  threads,
  fallbackThemes: _fallbackThemes,
}: CountryBriefThreadSummaryInput): { count: number; label: 'threads'; rows: CountryBriefThreadRow[] } {
  const threadRows = threads
    .filter(thread => thread.thread_id)
    .map(thread => ({
      name: thread.thread_id!,
      label: thread.label || thread.thread_id!,
      count: thread.signal_count || 0,
    }))

  return {
    count: threadRows.length,
    label: 'threads',
    rows: threadRows,
  }
}
