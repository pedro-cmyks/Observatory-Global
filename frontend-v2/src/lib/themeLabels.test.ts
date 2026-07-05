import { describe, expect, it } from 'vitest'
import { getThemeLabel, isThreadId, resolveThreadLabel } from './themeLabels'

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

describe('isThreadId', () => {
  it('detects dynamic-topic / emergent-cluster ids and atlas slugs', () => {
    expect(isThreadId('dynamic-topic-821')).toBe(true)
    expect(isThreadId('emergent-cluster-17')).toBe(true)
    expect(isThreadId('cluster-9')).toBe(true)
    expect(isThreadId('election-legitimacy--co')).toBe(true)
  })
  it('does not flag genuine GDELT theme codes', () => {
    expect(isThreadId('ARMEDCONFLICT')).toBe(false)
    expect(isThreadId('WB_2024_ANTI_CORRUPTION')).toBe(false)
    expect(isThreadId('CRISISLEX_C07_SAFETY')).toBe(false)
  })
})

describe('resolveThreadLabel', () => {
  it('prefers the known human label for a thread id (the bug: no raw "dynamic-topic-821")', () => {
    expect(resolveThreadLabel('dynamic-topic-821', 'Portugal Beach Croatia 2-1')).toBe('Portugal Beach Croatia 2-1')
  })
  it('never echoes a raw numeric thread id when no label is known', () => {
    expect(resolveThreadLabel('dynamic-topic-821')).toBe('Narrative Thread')
    expect(resolveThreadLabel('emergent-cluster-17')).toBe('Narrative Thread')
  })
  it('prettifies an atlas slug when no label is known', () => {
    expect(resolveThreadLabel('election-legitimacy--co')).toBe('Election Legitimacy')
  })
  it('falls back to getThemeLabel for genuine GDELT theme codes', () => {
    expect(resolveThreadLabel('CRISISLEX_C07_SAFETY')).toBe('Public Safety')
    expect(resolveThreadLabel('ARMEDCONFLICT')).toBe('Armed Conflict')
  })
  it('uses the known label even for a GDELT code (explicit override)', () => {
    expect(resolveThreadLabel('ARMEDCONFLICT', 'Custom Name')).toBe('Custom Name')
  })
})
