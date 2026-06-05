export interface ThemeDetailEmptyStateInput {
  label: string
  countryName?: string | null
  hours: number
  openedFrom?: 'thread' | 'topic' | 'public_attention'
}

export interface ThemeDetailEmptyState {
  title: string
  body: string
  primaryAction: string
  secondaryNote: string
}

export function buildThemeDetailEmptyState(_input: ThemeDetailEmptyStateInput): ThemeDetailEmptyState {
  const input = _input
  const label = input.label || 'this thread'
  const hoursLabel = `${input.hours}h`
  if (input.countryName) {
    return {
      title: `No country-scoped evidence for ${label} in ${input.countryName}`,
      body: `Atlas opened the thread detail, but the ${input.countryName} slice has no signals that cleared the current thread quality gate in the last ${hoursLabel}. The country can still have signals in other threads.`,
      primaryAction: 'Return to global thread',
      secondaryNote: 'Use global view to inspect the full thread, or change the time range if this should include older evidence.',
    }
  }
  return {
    title: `No evidence cleared the current gate for ${label}`,
    body: `Atlas found no signals for this detail view that cleared the current thread quality gate in the last ${hoursLabel}.`,
    primaryAction: 'Return to stream',
    secondaryNote: 'Try a broader time range or open a related thread if this topic should have older evidence.',
  }
}
