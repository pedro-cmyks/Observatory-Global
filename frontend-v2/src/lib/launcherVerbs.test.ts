import { describe, it, expect } from 'vitest'
import { resolveLauncherVerbs } from './launcherVerbs'

describe('resolveLauncherVerbs', () => {
  it('coverage gap → fresh-query only', () => {
    expect(resolveLauncherVerbs('coverage-gap').map(v => v.verb)).toEqual(['fresh-query'])
  })
  it('cross-read tension + contested figure → corroborate', () => {
    expect(resolveLauncherVerbs('cross-read-tension').map(v => v.verb)).toContain('corroborate')
    expect(resolveLauncherVerbs('contested-figure').map(v => v.verb)).toContain('corroborate')
  })
  it('lead + connected-thread → open (+ keep for lead)', () => {
    expect(resolveLauncherVerbs('lead').map(v => v.verb)).toEqual(expect.arrayContaining(['open', 'keep']))
    expect(resolveLauncherVerbs('connected-thread').map(v => v.verb)).toContain('open')
  })
  it('semantic neighbor → open, isolated pin → keep + drop', () => {
    expect(resolveLauncherVerbs('semantic-neighbor').map(v => v.verb)).toContain('open')
    expect(resolveLauncherVerbs('isolated-pin').map(v => v.verb)).toEqual(expect.arrayContaining(['keep', 'drop']))
  })
  it('every verb descriptor has a label and tip', () => {
    for (const kind of ['coverage-gap','cross-read-tension','contested-figure','lead','connected-thread','semantic-neighbor','isolated-pin','gaps-sentence'] as const) {
      for (const v of resolveLauncherVerbs(kind)) {
        expect(typeof v.label).toBe('string'); expect(v.label.length).toBeGreaterThan(0)
        expect(typeof v.tip).toBe('string')
      }
    }
  })
})
