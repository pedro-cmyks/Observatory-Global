import './CoverageBadge.css'

export interface CoverageMeta {
  source?: string
  modelVersion?: string
  requestedHours?: number
  coveredDays?: number
  hotFloor?: string
  processed?: {
    from?: string
    to?: string
    row_count?: number
  } | null
  partialCoverage?: boolean
}

interface CoverageBadgeProps {
  coverage?: CoverageMeta | null
  source?: string | null
  warnings?: string[]
  compact?: boolean
}

function formatRows(n?: number): string {
  if (!n) return '0'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}m`
  if (n >= 1_000) return `${Math.round(n / 1_000)}k`
  return String(n)
}

export function CoverageBadge({ coverage, source, warnings = [], compact = false }: CoverageBadgeProps) {
  const isHistorical = source === 'historical_topic_country_daily' || coverage?.source === 'historical_processed'
  const label = isHistorical ? 'processed history' : 'hot window'
  const partial = Boolean(coverage?.partialCoverage)
  const processed = coverage?.processed
  const tooltip = isHistorical
    ? [
      `Source: ${source || coverage?.source || 'historical processed'}`,
      coverage?.modelVersion ? `Model: ${coverage.modelVersion}` : null,
      processed?.from && processed?.to ? `Range: ${processed.from} to ${processed.to}` : null,
      processed?.row_count ? `Signals represented: ${formatRows(processed.row_count)}` : null,
      coverage?.coveredDays ? `Covered days: ${coverage.coveredDays}` : null,
      partial ? 'Partial coverage: yes' : 'Partial coverage: no',
      warnings.length ? `Warnings: ${warnings.join(', ')}` : null,
    ].filter(Boolean).join('\n')
    : 'Live hot-store data from the current product window.'

  return (
    <span
      className={`coverage-method-badge${isHistorical ? ' coverage-method-badge--history' : ''}${partial ? ' coverage-method-badge--partial' : ''}${compact ? ' coverage-method-badge--compact' : ''}`}
      data-tip={tooltip}
    >
      {partial ? 'partial ' : ''}{label}
    </span>
  )
}
