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

describe('resolveThreadTitle (council STILL-BROKEN: deep-link cold title)', () => {
  it('while the first fetch is in flight an opaque thread id titles as a neutral loading state — never the raw id, never a resolved-looking generic', async () => {
    const { resolveThreadTitle } = await import('./themeLabels')
    expect(resolveThreadTitle('dynamic-topic-3667', null, true)).toBe('Loading thread…')
    expect(resolveThreadTitle('emergent-cluster-17', undefined, true)).toBe('Loading thread…')
  })
  it('a known label wins even while loading (list row carried it)', async () => {
    const { resolveThreadTitle } = await import('./themeLabels')
    expect(resolveThreadTitle('dynamic-topic-3667', 'Iran Attacks US Bases', true)).toBe('Iran Attacks US Bases')
  })
  it('after loading settles with no label, falls to the resolveThreadLabel fallback (fetch failed — honest generic, not a fake loading state)', async () => {
    const { resolveThreadTitle } = await import('./themeLabels')
    expect(resolveThreadTitle('dynamic-topic-3667', null, false)).toBe('Narrative Thread')
  })
  it('atlas slugs and GDELT codes carry their own names — no loading state needed', async () => {
    const { resolveThreadTitle } = await import('./themeLabels')
    expect(resolveThreadTitle('election-legitimacy--co', null, true)).toBe('Election Legitimacy')
    expect(resolveThreadTitle('ARMEDCONFLICT', null, true)).toBe('Armed Conflict')
  })
})

// Council R4 N28 (T-N17 / D-N19 / P-N24, three seats): the eclipse dominant is
// a category BUCKET whose served "label" IS its raw slug
// (`earthquake-volcano-disaster`) — a machine string must never reach user copy.
describe('isMachineSlug', () => {
  it('detects a hyphenated machine slug', async () => {
    const { isMachineSlug } = await import('./themeLabels')
    expect(isMachineSlug('earthquake-volcano-disaster')).toBe(true)
    expect(isMachineSlug('dynamic-topic-8072')).toBe(true)
    expect(isMachineSlug('election-legitimacy--co')).toBe(true)
    expect(isMachineSlug('fuel_subsidy_unrest')).toBe(true)
  })
  it('leaves genuine human labels alone', async () => {
    const { isMachineSlug } = await import('./themeLabels')
    expect(isMachineSlug('World Cup Final')).toBe(false)
    expect(isMachineSlug('Gaza')).toBe(false)
    expect(isMachineSlug('US Bombards Iran')).toBe(false)
    expect(isMachineSlug('Trump Ultimatum to Iran')).toBe(false)
    expect(isMachineSlug('')).toBe(false)
    expect(isMachineSlug(null)).toBe(false)
  })
})

describe('resolveDisplayLabel', () => {
  it('resolves a category bucket whose label is its own slug', async () => {
    const { resolveDisplayLabel } = await import('./themeLabels')
    expect(resolveDisplayLabel('earthquake-volcano-disaster', 'earthquake-volcano-disaster'))
      .toBe('Earthquake Volcano Disaster')
  })
  it('passes a real human label through untouched', async () => {
    const { resolveDisplayLabel } = await import('./themeLabels')
    expect(resolveDisplayLabel('World Cup Final', 'dynamic-topic-8072')).toBe('World Cup Final')
  })
  it('falls back to the id when no label was served', async () => {
    const { resolveDisplayLabel } = await import('./themeLabels')
    expect(resolveDisplayLabel(null, 'earthquake-volcano-disaster')).toBe('Earthquake Volcano Disaster')
  })
  it('never renders a raw opaque topic id', async () => {
    const { resolveDisplayLabel } = await import('./themeLabels')
    expect(resolveDisplayLabel('dynamic-topic-8072', 'dynamic-topic-8072')).toBe('Narrative Thread')
  })
  it('uses the caller fallback when there is nothing to resolve', async () => {
    const { resolveDisplayLabel } = await import('./themeLabels')
    expect(resolveDisplayLabel(null, null, 'one story')).toBe('one story')
    expect(resolveDisplayLabel('  ', undefined, 'one story')).toBe('one story')
  })
})
