import { describe, it, expect } from 'vitest'
import { buildBriefParams, parseConsoleDeepLink, mergeFocusIntoParams } from './navParams'

describe('navParams', () => {
  it('buildBriefParams carries theme+label+q+country forward', () => {
    const qs = buildBriefParams({ country: 'US', theme: 'gaza', themeLabel: 'Gaza ceasefire', storyQuery: 'oil' })
    const p = new URLSearchParams(qs)
    expect(p.get('country')).toBe('US')
    expect(p.get('theme')).toBe('gaza')
    expect(p.get('label')).toBe('Gaza ceasefire')
    expect(p.get('q')).toBe('oil')
  })
  it('buildBriefParams omits absent fields', () => {
    expect(buildBriefParams({ country: 'US' })).toBe('country=US')
    expect(buildBriefParams({})).toBe('')
  })
  it('parseConsoleDeepLink reads q/theme/label/country/attention', () => {
    expect(parseConsoleDeepLink('?theme=gaza&label=Gaza&country=US&q=oil'))
      .toEqual({ theme: 'gaza', label: 'Gaza', country: 'US', q: 'oil', attention: null })
  })
  it('parseConsoleDeepLink returns nulls for missing keys', () => {
    expect(parseConsoleDeepLink('')).toEqual({ theme: null, label: null, country: null, q: null, attention: null })
  })

  describe('mergeFocusIntoParams', () => {
    it('preserves carry-context params (q/label) while setting focus dims', () => {
      const merged = mergeFocusIntoParams('?q=oil&label=Gaza%20ceasefire', { theme: 'gaza', country: 'US', person: null })
      const p = new URLSearchParams(merged)
      expect(p.get('q')).toBe('oil')
      expect(p.get('label')).toBe('Gaza ceasefire')
      expect(p.get('theme')).toBe('gaza')
      expect(p.get('country')).toBe('US')
      expect(p.get('person')).toBeNull()
    })
    it('deletes focus dims that go empty but keeps the rest', () => {
      const merged = mergeFocusIntoParams('?theme=gaza&country=US&person=petro&entry=brief', { theme: null, country: 'US', person: null })
      const p = new URLSearchParams(merged)
      expect(p.get('theme')).toBeNull()
      expect(p.get('person')).toBeNull()
      expect(p.get('country')).toBe('US')
      expect(p.get('entry')).toBe('brief') // carry-context param untouched
    })
    it('empty focus with a lone ?q=x keeps q=x', () => {
      const merged = mergeFocusIntoParams('?q=x', { theme: null, country: null, person: null })
      expect(merged).toBe('q=x')
    })
    it('sets a focus dim onto an empty search string', () => {
      const merged = mergeFocusIntoParams('', { theme: 'gaza', country: null, person: null })
      expect(merged).toBe('theme=gaza')
    })
  })
})
