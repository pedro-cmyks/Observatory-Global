import type { FocusType } from '../contexts/FocusContext'

// The time range left this key 2026-07-15 (the VIEW selector is gone; the
// ambient fetch is always the live 24h picture) — focus identity is the only
// thing that can differentiate concurrent requests now.
interface FocusRequestKeyInput {
  isActive: boolean
  focusType: FocusType
  focusValue: string | null
}

export function buildFocusRequestKey(input: FocusRequestKeyInput): string {
  const focus = input.isActive && input.focusType && input.focusValue
    ? `${input.focusType}:${input.focusValue}`
    : 'global'

  return `focus=${focus}`
}
