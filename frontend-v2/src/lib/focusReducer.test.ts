import { describe, it, expect } from 'vitest'
import { nextFocusDims, EMPTY_DIMS, type FocusDims } from './focusReducer'

const dims = (over: Partial<FocusDims> = {}): FocusDims => ({ ...EMPTY_DIMS, ...over })

describe('nextFocusDims — compound intersection', () => {
  it('person no longer clears country or theme (the core fix)', () => {
    const start = dims({ country: 'IL', theme: 'gaza-ceasefire', themeLabel: 'Gaza ceasefire' })
    const out = nextFocusDims(start, { dim: 'person', value: 'Netanyahu' })
    expect(out.person).toBe('Netanyahu')
    expect(out.entity).toBe('Netanyahu')
    expect(out.country).toBe('IL')
    expect(out.theme).toBe('gaza-ceasefire')
    expect(out.themeLabel).toBe('Gaza ceasefire')
  })

  it('country no longer clears an active person', () => {
    const start = dims({ person: 'Netanyahu', entity: 'Netanyahu' })
    const out = nextFocusDims(start, { dim: 'country', value: 'EG' })
    expect(out.country).toBe('EG')
    expect(out.person).toBe('Netanyahu')
    expect(out.entity).toBe('Netanyahu')
  })

  it('theme keeps country and person, sets label', () => {
    const start = dims({ country: 'EG', person: 'al-Sisi', entity: 'al-Sisi' })
    const out = nextFocusDims(start, { dim: 'theme', value: 'ceasefire', label: 'Ceasefire mediation' })
    expect(out.theme).toBe('ceasefire')
    expect(out.themeLabel).toBe('Ceasefire mediation')
    expect(out.country).toBe('EG')
    expect(out.person).toBe('al-Sisi')
  })

  it('all three compose from a deep-link order theme→country→person', () => {
    let s = nextFocusDims(EMPTY_DIMS, { dim: 'theme', value: 't', label: 'T' })
    s = nextFocusDims(s, { dim: 'country', value: 'US' })
    s = nextFocusDims(s, { dim: 'person', value: 'X' })
    expect([s.theme, s.country, s.person]).toEqual(['t', 'US', 'X'])
  })

  it('clearing person clears its entity mirror only', () => {
    const start = dims({ country: 'US', person: 'X', entity: 'X' })
    const out = nextFocusDims(start, { dim: 'person', value: null })
    expect(out.person).toBeNull()
    expect(out.entity).toBeNull()
    expect(out.country).toBe('US')
  })

  it('thread stays an exclusive reset dimension', () => {
    const start = dims({ country: 'US', theme: 't', person: 'X' })
    const out = nextFocusDims(start, { dim: 'thread', value: 'dynamic-topic-9' })
    expect(out.thread).toBe('dynamic-topic-9')
    expect([out.country, out.theme, out.person]).toEqual([null, null, null])
  })

  it('clear resets every dimension', () => {
    const out = nextFocusDims(dims({ country: 'US', theme: 't', person: 'X' }), { dim: 'clear' })
    expect(out).toEqual(EMPTY_DIMS)
  })

  it('does not mutate its input', () => {
    const start = dims({ country: 'US' })
    nextFocusDims(start, { dim: 'person', value: 'X' })
    expect(start.person).toBeNull()
  })

  it('entity keeps country/theme; drops person only when it was the mirror and differs', () => {
    const start = dims({ country: 'US', theme: 't', person: 'X', entity: 'X' })
    const out = nextFocusDims(start, { dim: 'entity', value: 'Y' })
    expect(out.entity).toBe('Y')
    expect(out.person).toBeNull()
    expect(out.country).toBe('US')
    expect(out.theme).toBe('t')
  })

  it('entity re-setting the same value keeps person intact', () => {
    const start = dims({ country: 'US', person: 'X', entity: 'X' })
    const out = nextFocusDims(start, { dim: 'entity', value: 'X' })
    expect(out.entity).toBe('X')
    expect(out.person).toBe('X')
    expect(out.country).toBe('US')
  })

  it('concept keeps country, nulls thread/entity/person/themeLabel', () => {
    const start = dims({ country: 'US', theme: 't', person: 'X', entity: 'X', themeLabel: 'T' })
    const out = nextFocusDims(start, { dim: 'concept', value: { foo: 'bar' } })
    expect(out.concept).toEqual({ foo: 'bar' })
    expect(out.country).toBe('US')
    expect(out.thread).toBeNull()
    expect(out.entity).toBeNull()
    expect(out.person).toBeNull()
    expect(out.themeLabel).toBeNull()
    expect(out.theme).toBe('t')
  })

  it('region is a full reset except region itself', () => {
    const start = dims({ country: 'US', theme: 't', person: 'X', concept: { foo: 'bar' } })
    const out = nextFocusDims(start, { dim: 'region', value: { baz: 'qux' } })
    expect(out.region).toEqual({ baz: 'qux' })
    expect([out.country, out.theme, out.person, out.concept, out.thread, out.entity]).toEqual([null, null, null, null, null, null])
  })
})
