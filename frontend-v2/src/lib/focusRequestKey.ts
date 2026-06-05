import type { FocusType } from '../contexts/FocusContext'
import type { TimeRange } from './timeRanges'

interface FocusRequestKeyInput {
  timeRange: TimeRange
  isActive: boolean
  focusType: FocusType
  focusValue: string | null
}

export function buildFocusRequestKey(input: FocusRequestKeyInput): string {
  const focus = input.isActive && input.focusType && input.focusValue
    ? `${input.focusType}:${input.focusValue}`
    : 'global'

  return `range=${input.timeRange}|focus=${focus}`
}
