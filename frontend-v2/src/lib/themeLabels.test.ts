import { describe, expect, it } from 'vitest'
import { getThemeLabel } from './themeLabels'

describe('getThemeLabel', () => {
  it('formats unknown GDELT theme codes without leaking raw taxonomy prefixes', () => {
    expect(getThemeLabel('WB_2024_ANTI_CORRUPTION')).toBe('Anti-Corruption')
    expect(getThemeLabel('WB_PEACE_OPERATIONS_AND_CONFLICT_MANAGEMENT')).toBe('Peace Operations & Conflict Management')
    expect(getThemeLabel('USPEC_POLICY_ECONOMIC2')).toBe('US Economic Policy')
    expect(getThemeLabel('EPU_NONDEFENSE_SPENDING')).toBe('Policy: Non-Defense Spending')
    expect(getThemeLabel('EPU_CATS_NATIONAL_SECURITY')).toBe('National Security')
    expect(getThemeLabel('CRISISLEX_C07_SAFETY')).toBe('Public Safety')
    expect(getThemeLabel('UNGP_FORESTS_RIVERS_OCEANS')).toBe('Environment')
  })
})
