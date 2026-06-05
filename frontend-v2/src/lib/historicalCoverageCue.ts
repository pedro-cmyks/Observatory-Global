export interface HistoricalCoverageCueInput {
  source?: string | null
  coverage?: {
    source?: string | null
    modelVersion?: string | null
    requestedHours?: number | null
    partialCoverage?: boolean | null
  } | null
}

export interface HistoricalCoverageCue {
  label: string
  tip: string
}

export function buildHistoricalCoverageCue(_input: HistoricalCoverageCueInput): HistoricalCoverageCue | null {
  const input = _input
  if (input.source !== 'historical_topic_country_daily' && input.coverage?.source !== 'historical_processed') {
    return null
  }
  const model = input.coverage?.modelVersion || 'processed history'
  const label = input.coverage?.partialCoverage ? 'Partial historical processed' : 'Historical processed'
  const partial = input.coverage?.partialCoverage ? ' Partial coverage is available for this window.' : ''
  return {
    label,
    tip: `This long-window map is served from compact processed historical aggregates (${model}), not raw hot-store rows.${partial}`,
  }
}
