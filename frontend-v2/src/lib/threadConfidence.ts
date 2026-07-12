export interface ThreadConfidenceInput {
  avgConfidence: number | null
  confidenceMeasured: boolean
  trend: 'accelerating' | 'stable' | 'fading'
  crisisRelevant: boolean
}

export interface ThreadConfidencePresentation {
  confidencePct: number | null
  confidenceLabel: string
  showConfidenceBar: boolean
  trendColor: string
}

export function threadConfidencePresentation(
  input: ThreadConfidenceInput,
): ThreadConfidencePresentation {
  const measured = input.confidenceMeasured && Number.isFinite(input.avgConfidence)
  const confidencePct = measured
    ? Math.round(Math.max(0, Math.min(1, input.avgConfidence as number)) * 100)
    : null

  let trendColor = '#60a5fa'
  if (input.trend === 'accelerating') {
    trendColor = input.crisisRelevant ? '#ef4444' : '#34d399'
  } else if (input.trend === 'fading') {
    trendColor = '#64748b'
  }

  return {
    confidencePct,
    confidenceLabel: confidencePct == null ? 'unscored' : `${confidencePct}% confidence`,
    showConfidenceBar: confidencePct != null,
    trendColor,
  }
}
