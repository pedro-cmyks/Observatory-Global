import { describe, it, expect } from 'vitest'
import { buildEclipseSets, eclipseTopicColor, countryLens, threadEclipseRole } from './eclipseSets'
import type { EclipseData } from './attentionEclipse'

const data: EclipseData = {
  eclipse: true, tier: 'total',
  dominant: { topic_id: 'dynamic-topic-1', countries: ['US', 'IR'] },
  window: {},
  selected: [{ topic_id: 'dynamic-topic-9', label: 's', attention: 10, attention_share: 0.01,
               consequence: 0.5, language_breadth: 3, country_breadth: 4, velocity: 0,
               lane: 'general', reason_codes: [], countries: ['SD', 'US'] }],
}

describe('eclipseSets', () => {
  it('builds eclipse/shadow topic + country sets, dominant wins shared country', () => {
    const s = buildEclipseSets(data, ['dynamic-topic-2'])
    expect(s.eclipseTopics.has('dynamic-topic-1')).toBe(true)
    expect(s.eclipseTopics.has('dynamic-topic-2')).toBe(true)
    expect(s.shadowTopics.has('dynamic-topic-9')).toBe(true)
    expect(s.eclipseCountries.has('US')).toBe(true)
    expect(s.shadowCountries.has('US')).toBe(false)
    expect(s.shadowCountries.has('SD')).toBe(true)
  })
  it('colors and roles', () => {
    const s = buildEclipseSets(data)
    expect(eclipseTopicColor('dynamic-topic-1', s)).toBe('var(--eclipse-red, #e23a1a)')
    expect(eclipseTopicColor('dynamic-topic-9', s)).toBe('var(--eclipse-cyan, #2aa7ad)')
    expect(eclipseTopicColor('unknown', s)).toBeNull()
    expect(countryLens('IR', s)).toBe('eclipse')
    expect(countryLens('SD', s)).toBe('shadow')
    expect(countryLens('BR', s)).toBeNull()
    expect(threadEclipseRole(['dynamic-topic-9'], 'theme-x', s)).toBe('shadow')
    expect(threadEclipseRole([], 'dynamic-topic-1', s)).toBe('eclipse')
  })
})
