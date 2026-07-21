import { describe, it, expect } from 'vitest'
import { buildBriefParams, parseConsoleDeepLink } from './navParams'

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
})
